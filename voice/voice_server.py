import socket
import threading
from utils.logger import logger

class VoiceServer:
    def __init__(self, port: int, auth_validator=None, channel_router=None):
        self.port = port
        self.auth_validator = auth_validator
        self.channel_router = channel_router
        self.sock = None
        self.is_running = False
        self.thread = None
        
        # Maps user_id -> UDP endpoint (ip, port)
        self.clients = {}
        self.lock = threading.Lock()

    def start(self, host_ip: str):
        """Starts the UDP voice forwarding server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((host_ip, self.port))
            self.is_running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            logger.info(f"Voice UDP forwarding server listening on {host_ip}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to bind Voice UDP server: {e}")
            raise e

    def stop(self):
        """Stops the UDP voice forwarding server."""
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        logger.info("Voice UDP forwarding server stopped.")

    def run(self):
        """Background thread receiving voice packets and broadcasting them."""
        # Preallocate buffer
        buf_size = 4096
        while self.is_running:
            try:
                data, addr = self.sock.recvfrom(buf_size)
                if not data or len(data) < 2:
                    continue
                    
                # Packet format:
                # [1 byte user_id_len] + [user_id as UTF-8 string] + [Opus bytes...]
                user_id_len = data[0]
                if len(data) < 1 + user_id_len:
                    continue
                    
                user_id = data[1 : 1 + user_id_len].decode("utf-8", errors="ignore")
                
                # Security: Reject unauthenticated senders if a validator is provided
                if self.auth_validator and not self.auth_validator(user_id):
                    continue
                
                with self.lock:
                    # Update or register this user's current UDP endpoint
                    self.clients[user_id] = addr
                    
                    # Determine sender's voice channel
                    sender_channel = None
                    if self.channel_router:
                        sender_channel = self.channel_router(user_id)
                    
                    # Broadcast packet to all other active voice clients in the same channel
                    for uid, client_addr in self.clients.items():
                        if uid != user_id:
                            # Check channel membership if router is provided
                            if self.channel_router:
                                recipient_channel = self.channel_router(uid)
                                if recipient_channel != sender_channel:
                                    continue
                            try:
                                self.sock.sendto(data, client_addr)
                            except Exception:
                                pass
            except Exception as e:
                if self.is_running:
                    logger.debug(f"Voice UDP server loop error: {e}")
