import asyncio
import json
import uuid
import time
from collections import deque
from network.protocol import send_packet, read_packet
from utils.logger import logger

class TailChatHost:
    def __init__(self, chat_port: int, file_port: int, room_password: str = None):
        self.chat_port = chat_port
        self.file_port = file_port
        self.room_password = room_password
        
        self.chat_server = None
        self.file_server = None
        
        # Room clients: {user_id: (reader, writer, user_info)}
        self.clients = {}
        # History of last 100 messages: [{"sender_id": ..., "sender_name": ..., "content": ..., "timestamp": ...}]
        self.message_history = deque(maxlen=100)
        
        # Pending file transfers: {file_id: {"sender": (r, w), "recipient": (r, w)}}
        self.pending_files = {}
        self.files_lock = asyncio.Lock()

    async def start(self, host_ip: str):
        """Starts both the Chat and File Forwarding TCP servers."""
        try:
            from network.protocol import MAX_PACKET_SIZE
            self.chat_server = await asyncio.start_server(
                self.handle_chat_client, host_ip, self.chat_port, limit=MAX_PACKET_SIZE
            )
            logger.info(f"Chat server listening on {host_ip}:{self.chat_port}")
            
            self.file_server = await asyncio.start_server(
                self.handle_file_client, host_ip, self.file_port, limit=MAX_PACKET_SIZE
            )
            logger.info(f"File forwarding server listening on {host_ip}:{self.file_port}")
            
        except Exception as e:
            logger.error(f"Failed to start host servers on {host_ip}: {e}")
            raise e

    async def stop(self):
        """Gracefully stops all servers and disconnects clients."""
        logger.info("Stopping host servers...")
        
        # Disconnect chat clients
        for user_id, (r, w, _) in list(self.clients.items()):
            try:
                await send_packet(w, {"type": "shutdown", "message": "Host closed the room."})
                w.close()
                await w.wait_closed()
            except Exception:
                pass
        self.clients.clear()
        
        # Close servers
        if self.chat_server:
            self.chat_server.close()
            await self.chat_server.wait_closed()
        if self.file_server:
            self.file_server.close()
            await self.file_server.wait_closed()
            
        logger.info("Host servers stopped.")

    # --- Chat handling ---
    async def handle_chat_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles incoming client TCP connections for chat and signaling."""
        peer = writer.get_extra_info('peername')
        logger.info(f"New TCP connection from peer {peer}")
        
        user_id = None
        try:
            # 1. Wait for join packet
            join_packet = await read_packet(reader)
            if not join_packet or join_packet.get("type") != "join":
                logger.warning(f"Peer {peer} did not send join packet on connect.")
                writer.close()
                return
                
            user_id = join_packet.get("user_id")
            if not user_id:
                writer.close()
                return
                
            provided_pwd = join_packet.get("password")
            if self.room_password and provided_pwd != self.room_password:
                logger.warning(f"Peer {peer} provided incorrect room password.")
                writer.close()
                return
            try:
                uuid.UUID(user_id)
            except ValueError:
                logger.warning(f"Invalid user_id format from {peer}")
                writer.close()
                return

            user_info = {
                "user_id": user_id,
                "display_name": join_packet.get("display_name", "Unknown"),
                "email": join_packet.get("email", ""),
                "avatar_url": join_packet.get("avatar_url", ""),
                "tailscale_ip": join_packet.get("tailscale_ip", ""),
                "bio": join_packet.get("bio", ""),
                "links": join_packet.get("links", ""),
                "text_channel": "general",
                "voice_channel": None
            }
            
            logger.info(f"User {user_info['display_name']} ({user_id}) joined room.")
            
            # Register client with a unique connection ID to support multiple connections from the same user (e.g., local testing)
            connection_id = str(uuid.uuid4())
            self.clients[connection_id] = (reader, writer, user_info)
            
            # Send join acknowledgement + message history
            await send_packet(writer, {
                "type": "join_ack",
                "history": list(self.message_history),
                "members": [client_info for _, _, client_info in self.clients.values()]
            })
            
            # Broadcast user join to others
            await self.broadcast({
                "type": "user_joined",
                "user": user_info
            }, exclude_conn_id=connection_id)
            
            # 2. Start read loop
            last_msg_time = 0
            msg_count = 0
            while True:
                packet = await read_packet(reader)
                if not packet:
                    break
                    
                # Global Rate limiting: max 50 packets per second per user to prevent DoS
                now = time.time()
                if now - last_msg_time > 1.0:
                    last_msg_time = now
                    msg_count = 0
                msg_count += 1
                
                if msg_count > 50:
                    logger.warning(f"Global rate limit exceeded for user {user_id}")
                    continue

                packet_type = packet.get("type")
                if packet_type == "join_channel":
                    channel_type = packet.get("channel_type")
                    channel_name = packet.get("channel_name")
                    if channel_type == "text":
                        user_info["text_channel"] = channel_name
                    elif channel_type == "voice":
                        user_info["voice_channel"] = channel_name
                        logger.info(f"User {user_id} moved to voice channel: {channel_name}")
                        await self.broadcast({
                            "type": "voice_channel_update",
                            "user_id": user_id,
                            "channel_name": channel_name
                        })
                        
                elif packet_type == "leave_channel":
                    channel_type = packet.get("channel_type")
                    if channel_type == "voice":
                        user_info["voice_channel"] = None
                        logger.info(f"User {user_id} left voice channel")
                        await self.broadcast({
                            "type": "voice_channel_update",
                            "user_id": user_id,
                            "channel_name": None
                        })
                        
                elif packet_type == "chat":
                    msg = {
                        "type": "chat",
                        "sender_id": user_id,
                        "sender_name": user_info["display_name"],
                        "content": packet.get("content", ""),
                        "timestamp": packet.get("timestamp", ""),
                        "channel": packet.get("channel", "general")
                    }
                    self.message_history.append(msg)
                    # For deque, we need to cast to list when sending history
                    await self.broadcast(msg)
                    
                elif packet_type in ("file_offer", "file_accept", "file_decline", "file_expire", "profile_req", "profile_res"):
                    # Route private signals to recipient
                    recipient_id = packet.get("recipient_id")
                    if recipient_id:
                        await self.unicast(recipient_id, packet)
                    else:
                        # Broadcast if no recipient
                        await self.broadcast(packet, exclude_conn_id=connection_id)
                        
                elif packet_type in ("voice_state", "speaking_state"):
                    # Broadcast voice state changes (e.g. mute/unmute, speaking glow)
                    await self.broadcast(packet, exclude_conn_id=connection_id)
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error handling chat client {user_id}: {e}")
        finally:
            # Cleanup
            if connection_id in self.clients:
                del self.clients[connection_id]
                logger.info(f"User {user_id} disconnected.")
                # Broadcast user departure
                await self.broadcast({
                    "type": "user_left",
                    "user_id": user_id
                })
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def broadcast(self, packet: dict, exclude_conn_id: str = None):
        """Sends a packet to all connected room clients."""
        logger.debug(f"Broadcasting packet: {packet.get('type')}")
        tasks = []
        for cid, (_, writer, _) in list(self.clients.items()):
            if cid != exclude_conn_id:
                tasks.append(send_packet(writer, packet))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def unicast(self, recipient_id: str, packet: dict) -> bool:
        """Sends a packet to all connections of a specific user."""
        success = False
        for cid, (_, writer, info) in list(self.clients.items()):
            if info.get("user_id") == recipient_id:
                if await send_packet(writer, packet):
                    success = True
        if not success:
            logger.warning(f"Unicast failed: Recipient user {recipient_id} not connected.")
        return success

    # --- File stream handling ---
    async def handle_file_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Handles dynamic TCP pipe creation for in-flight files.
        Connects sender reader to recipient writer.
        """
        try:
            # 1. Read header packet
            header = await read_packet(reader)
            if not header or "file_id" not in header or "role" not in header:
                writer.close()
                return
                
            file_id = header["file_id"]
            role = header["role"]
            
            async with self.files_lock:
                if file_id not in self.pending_files:
                    self.pending_files[file_id] = {}
                self.pending_files[file_id][role] = (reader, writer)
                
            logger.info(f"File transfer client registered: File {file_id} as {role}")
            
            # 2. Check if both roles are connected
            sender_conn = None
            recipient_conn = None
            
            # Wait up to 30 seconds for the other party to connect
            for _ in range(60):
                async with self.files_lock:
                    conns = self.pending_files.get(file_id, {})
                    if "sender" in conns and "recipient" in conns:
                        sender_conn = conns["sender"]
                        recipient_conn = conns["recipient"]
                        # Remove from pending now that we matched them
                        if file_id in self.pending_files:
                            del self.pending_files[file_id]
                        break
                await asyncio.sleep(0.5)
                
            if not sender_conn or not recipient_conn:
                logger.warning(f"File transfer {file_id} timed out waiting for {role} counterpart.")
                writer.close()
                async with self.files_lock:
                    if file_id in self.pending_files:
                        del self.pending_files[file_id]
                return
            
            # 3. If matched, start the stream pipe
            if sender_conn and recipient_conn:
                s_reader, s_writer = sender_conn
                r_reader, r_writer = recipient_conn
                
                logger.info(f"Starting direct socket transfer for File {file_id}")
                try:
                    # Pipe bytes from sender to recipient
                    while True:
                        chunk = await s_reader.read(64 * 1024) # 64KB chunks
                        if not chunk:
                            break
                        r_writer.write(chunk)
                        await r_writer.drain()
                    logger.info(f"Direct transfer for File {file_id} completed successfully.")
                except Exception as stream_err:
                    logger.error(f"Error streaming file {file_id}: {stream_err}")
                finally:
                    # Close all sockets for this transfer
                    try:
                        s_writer.close()
                        await s_writer.wait_closed()
                    except Exception: pass
                    try:
                        r_writer.close()
                        await r_writer.wait_closed()
                    except Exception: pass
            else:
                # Wait for the other party (this connection stays open in background)
                pass
                
        except Exception as e:
            logger.error(f"Error handling file connection: {e}")
            try:
                writer.close()
            except Exception: pass

    def get_user_voice_channel(self, user_id: str) -> str:
        """Returns the current voice channel name for a connected user."""
        client = self.clients.get(user_id)
        if client:
            return client[2].get("voice_channel", "General VC")
        return None
