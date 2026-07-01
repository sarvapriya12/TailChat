import socket
import threading
import time
from PySide6.QtCore import QObject, Signal
from auth.session import session
from utils.logger import logger

class VideoReceiverSignals(QObject):
    frame_received = Signal(str, bytes) # user_id, jpeg_bytes

class VideoReceiver:
    def __init__(self, host_ip: str, host_port: int):
        self.host_ip = host_ip
        self.host_port = host_port
        self.signals = VideoReceiverSignals()
        
        self.sock = None
        self.is_running = False
        self.thread = None
        self.keepalive_thread = None
        self.is_deafened = False

    def set_deafened(self, deafened: bool):
        self.is_deafened = deafened
        logger.info(f"Video deafen state changed: {deafened}")

    def start(self) -> bool:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enlarge receive buffer to prevent dropped frames
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 524288)
        except Exception:
            pass
        try:
            self.sock.bind(("", 0))
            self.is_running = True
            
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            
            self.keepalive_thread = threading.Thread(target=self.keepalive_loop, daemon=True)
            self.keepalive_thread.start()
            
            logger.info(f"VideoReceiver started on local UDP port: {self.sock.getsockname()[1]}")
            return True
        except Exception as e:
            logger.error(f"Failed to bind local UDP video socket: {e}")
            return False

    def keepalive_loop(self):
        user_id_bytes = session.user_id.encode("utf-8")
        reg_packet = bytes([len(user_id_bytes)]) + user_id_bytes
        
        while self.is_running:
            try:
                if self.sock:
                    self.sock.sendto(reg_packet, (self.host_ip, self.host_port))
            except Exception:
                pass
            time.sleep(5)

    def run(self):
        buf_size = 65535 # Max UDP size for video frames
        while self.is_running:
            try:
                data, _ = self.sock.recvfrom(buf_size)
                if not data or len(data) < 2 or self.is_deafened:
                    continue
                    
                user_id_len = data[0]
                if len(data) < 1 + user_id_len:
                    continue
                    
                user_id = data[1 : 1 + user_id_len].decode("utf-8", errors="ignore")
                jpeg_bytes = data[1 + user_id_len :]
                
                if jpeg_bytes:
                    self.signals.frame_received.emit(user_id, jpeg_bytes)
                    
            except Exception as e:
                if self.is_running:
                    pass

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception: pass
            self.sock = None
        logger.info("VideoReceiver stopped.")
