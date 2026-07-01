import socket
from video.camera import CameraCapture
from auth.session import session
from utils.constants import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_JPEG_QUALITY
from utils.logger import logger

# Max safe UDP payload (65507 bytes minus our header)
MAX_UDP_PAYLOAD = 65000


class VideoSender:
    def __init__(self, host_ip: str, host_port: int, local_callback=None):
        self.host_ip = host_ip
        self.host_port = host_port
        self.sock = None
        self.camera = None
        self.local_callback = local_callback
        self._header = None  # Pre-computed packet header

    def start(self) -> bool:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Increase send buffer to reduce dropped frames on burst
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
        except Exception:
            pass
        
        # Pre-compute the user_id header once instead of every frame
        user_id_bytes = session.user_id.encode("utf-8")
        self._header = bytes([len(user_id_bytes)]) + user_id_bytes
        
        self.camera = CameraCapture(
            self.send_video_frame, 
            width=VIDEO_WIDTH, 
            height=VIDEO_HEIGHT, 
            fps=VIDEO_FPS, 
            jpeg_quality=VIDEO_JPEG_QUALITY
        )
        return self.camera.start()

    def set_camera_enabled(self, enabled: bool):
        if self.camera:
            self.camera.set_enabled(enabled)

    def send_video_frame(self, jpeg_bytes: bytes):
        if self.local_callback:
            self.local_callback(jpeg_bytes)
            
        if not self.sock or not self._header:
            return
            
        try:
            packet = self._header + jpeg_bytes
            
            # Drop oversized frames instead of crashing the socket
            if len(packet) > MAX_UDP_PAYLOAD:
                return
            
            self.sock.sendto(packet, (self.host_ip, self.host_port))
        except Exception:
            pass

    def stop(self):
        if self.camera:
            self.camera.stop()
            self.camera = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("VideoSender stopped.")
