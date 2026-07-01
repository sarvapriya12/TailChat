import asyncio
from PySide6.QtCore import QObject, Signal
from network.protocol import send_packet, read_packet
from auth.session import session
from utils.logger import logger

class ClientSignals(QObject):
    connected = Signal()
    disconnected = Signal(str)
    chat_received = Signal(dict)       # {"sender_id": ..., "sender_name": ..., "content": ..., "timestamp": ...}
    user_joined = Signal(dict)        # {"id": ..., "display_name": ..., "email": ..., "avatar_url": ..., "tailscale_ip": ...}
    members_list = Signal(list)       # list of user_info dicts
    user_left = Signal(str)           # user_id
    file_offer = Signal(dict)         # {"file_id": ..., "file_name": ..., "file_size": ..., "sender_name": ..., "sender_id": ...}
    file_accepted = Signal(dict)      # {"file_id": ..., "recipient_id": ...}
    file_declined = Signal(dict)      # {"file_id": ...}
    file_expired = Signal(dict)       # {"file_id": ...}
    voice_state_changed = Signal(dict)# {"user_id": ..., "muted": ...}
    speaking_state_changed = Signal(dict) # {"user_id": ..., "is_speaking": ...}
    voice_channel_changed = Signal(dict) # {"user_id": ..., "channel_name": ...}
    room_shutdown = Signal(str)       # reason message

class TailChatClient:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.signals = ClientSignals()
        self.is_connected = False
        self.read_task = None
        self.message_history = []
        # Stores the initial members list from join_ack so it can be
        # replayed after the GUI has connected its signals (there is a race
        # between the host sending join_ack and the Qt GUI thread wiring up
        # its signal handlers).
        self._pending_members = []

    async def connect_to_host(self, host_ip: str, host_port: int, password: str = None) -> bool:
        """Connects to the host TCP chat server."""
        try:
            logger.info(f"Connecting to host at {host_ip}:{host_port}...")
            # Import MAX_PACKET_SIZE if not imported, or just use 1048576 (1MB)
            from network.protocol import MAX_PACKET_SIZE
            self.reader, self.writer = await asyncio.open_connection(host_ip, host_port, limit=MAX_PACKET_SIZE)
            self.is_connected = True
            
            # Send join packet
            join_packet = {
                "type": "join",
                "user_id": session.user_id,
                "display_name": session.display_name,
                "email": session.email,
                "avatar_url": session.avatar_url,
                "tailscale_ip": session.tailscale_ip,
                "bio": session.bio,
                "links": session.links
            }
            if password:
                join_packet["password"] = password
            await send_packet(self.writer, join_packet)
            
            # Start reader loop task
            self.read_task = asyncio.create_task(self.read_loop())
            self.signals.connected.emit()
            logger.info("Successfully connected and joined room.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to host: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Closes connection to the host."""
        if not self.is_connected:
            return
            
        logger.info("Disconnecting from host...")
        self.is_connected = False
        
        # Cancel reader task
        if self.read_task:
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
                
        # Send leave packet (best effort)
        try:
            if self.writer:
                await send_packet(self.writer, {"type": "leave", "user_id": session.user_id})
                self.writer.close()
                await self.writer.wait_closed()
        except Exception:
            pass
            
        self.reader = None
        self.writer = None
        self.signals.disconnected.emit("Disconnected from room.")

    async def send_chat_message(self, text: str, timestamp: str, channel: str = "general"):
        """Sends a text chat message to the host."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "chat",
            "content": text,
            "timestamp": timestamp,
            "channel": channel
        }
        await send_packet(self.writer, packet)

    async def join_channel(self, channel_type: str, channel_name: str):
        """Notifies the host that this client switched text or voice channels."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "join_channel",
            "channel_type": channel_type,
            "channel_name": channel_name
        }
        await send_packet(self.writer, packet)

    async def leave_channel(self, channel_type: str):
        """Notifies the host that this client left a channel."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "leave_channel",
            "channel_type": channel_type
        }
        await send_packet(self.writer, packet)

    async def send_file_offer(self, file_id: str, file_name: str, file_size: int, recipient_id: str = None):
        """Announces a file offer to a specific user (or the whole room if recipient_id is None)."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "file_offer",
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "sender_name": session.display_name,
            "sender_id": session.user_id,
            "recipient_id": recipient_id
        }
        await send_packet(self.writer, packet)

    async def send_file_accept(self, file_id: str, sender_id: str):
        """Notifies the sender that their file offer is accepted."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "file_accept",
            "file_id": file_id,
            "recipient_id": sender_id # Route back to sender
        }
        await send_packet(self.writer, packet)

    async def send_file_decline(self, file_id: str, sender_id: str):
        """Notifies the sender that their file offer is declined."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "file_decline",
            "file_id": file_id,
            "recipient_id": sender_id
        }
        await send_packet(self.writer, packet)

    async def send_file_expire(self, file_id: str, recipient_id: str = None):
        """Announces that a file offer has expired or was cancelled."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "file_expire",
            "file_id": file_id,
            "recipient_id": recipient_id
        }
        await send_packet(self.writer, packet)

    async def send_voice_state(self, muted: bool):
        """Informs the room about mic status changes."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "voice_state",
            "user_id": session.user_id,
            "muted": muted
        }
        await send_packet(self.writer, packet)

    async def send_speaking_state(self, is_speaking: bool):
        """Informs the room that this user started/stopped speaking (VAD)."""
        if not self.is_connected or not self.writer:
            return
        packet = {
            "type": "speaking_state",
            "user_id": session.user_id,
            "is_speaking": is_speaking
        }
        await send_packet(self.writer, packet)

    async def read_loop(self):
        """Background loop reading newline-terminated packets from the host server."""
        try:
            while self.is_connected:
                packet = await read_packet(self.reader)
                if not packet:
                    # Connection lost
                    break
                    
                packet_type = packet.get("type")
                if packet_type == "join_ack":
                    # Store history and members so replay_join_ack() can
                    # deliver them once the GUI has connected its signals.
                    for msg in packet.get("history", []):
                        self.message_history.append(msg)
                    if "members" in packet:
                        self._pending_members = packet["members"]
                    # Emit members_list now — if GUI signals are already
                    # connected this arrives immediately; if not the GUI
                    # must call replay_join_ack() from initialize_room_view.
                    if self._pending_members:
                        self.signals.members_list.emit(self._pending_members)
                    # Replay chat history
                    for msg in self.message_history:
                        self.signals.chat_received.emit(msg)
                        
                elif packet_type == "chat":
                    self.message_history.append(packet)
                    self.signals.chat_received.emit(packet)
                    
                elif packet_type == "user_joined":
                    self.signals.user_joined.emit(packet["user"])
                    
                elif packet_type == "user_left":
                    self.signals.user_left.emit(packet["user_id"])
                    
                elif packet_type == "file_offer":
                    self.signals.file_offer.emit(packet)
                    
                elif packet_type == "file_accept":
                    self.signals.file_accepted.emit(packet)
                    
                elif packet_type == "file_decline":
                    self.signals.file_declined.emit(packet)
                    
                elif packet_type == "file_expire":
                    self.signals.file_expired.emit(packet)
                    
                elif packet_type == "voice_state":
                    self.signals.voice_state_changed.emit(packet)
                elif packet_type == "speaking_state":
                    self.signals.speaking_state_changed.emit(packet)
                elif packet_type == "voice_channel_update":
                    self.signals.voice_channel_changed.emit(packet)
                    
                elif packet_type == "shutdown":
                    self.signals.room_shutdown.emit(packet.get("message", "Room closed."))
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in client read loop: {e}")
        finally:
            self.is_connected = False
            self.signals.disconnected.emit("Lost connection to host.")

    def replay_join_ack(self):
        """Re-emits the members list and chat history that arrived in join_ack.

        The host sends join_ack immediately after the client connects, often
        before the Qt GUI thread has wired up its signal handlers.  Call this
        from RoomPage.initialize_room_view() *after* reconnect_signals() so
        the initial room state is always delivered to the UI.
        """
        if self._pending_members:
            logger.info(f"Replaying join_ack: {len(self._pending_members)} members, {len(self.message_history)} history messages.")
            self.signals.members_list.emit(self._pending_members)
        for msg in self.message_history:
            self.signals.chat_received.emit(msg)
