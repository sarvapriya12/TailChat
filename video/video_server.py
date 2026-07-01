import socket
import threading
from utils.logger import logger

class VideoServer:
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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((host_ip, self.port))
            self.is_running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            logger.info(f"Video UDP forwarding server listening on {host_ip}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to bind Video UDP server: {e}")
            raise e

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception: pass
        logger.info("Video UDP forwarding server stopped.")

    def run(self):
        buf_size = 65535
        while self.is_running:
            try:
                data, addr = self.sock.recvfrom(buf_size)
                if not data or len(data) < 2:
                    continue
                    
                user_id_len = data[0]
                if len(data) < 1 + user_id_len:
                    continue
                    
                user_id = data[1 : 1 + user_id_len].decode("utf-8", errors="ignore")
                
                # Security: Reject unauthenticated senders if a validator is provided
                if self.auth_validator and not self.auth_validator(user_id):
                    continue
                
                with self.lock:
                    self.clients[user_id] = addr
                    
                    sender_channel = None
                    if self.channel_router:
                        sender_channel = self.channel_router(user_id)
                    
                    for uid, client_addr in self.clients.items():
                        if uid != user_id:
                            if self.channel_router:
                                recipient_channel = self.channel_router(uid)
                                if recipient_channel != sender_channel:
                                    continue
                            try:
                                self.sock.sendto(data, client_addr)
                            except Exception:
                                pass
            except Exception as e:
                pass
