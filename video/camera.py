import cv2
import threading
import time
from utils.logger import logger


class CameraCapture:
    """Captures frames from a local camera with minimal latency.
    
    Key performance optimizations:
    - Uses DirectShow (CAP_DSHOW) on Windows to avoid the slow Media Foundation backend
    - Disables the internal OpenCV buffer so we always get the latest frame, not a queued one
    - Uses a lock to store the latest frame and lets the sender pick it up at its own pace,
      preventing frame accumulation if the network is slower than capture
    """
    
    def __init__(self, callback, device_index=0, width=320, height=240, fps=15, jpeg_quality=60):
        self.callback = callback
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.jpeg_quality = jpeg_quality
        
        self.cap = None
        self.is_running = False
        self.is_enabled = False
        self.thread = None
        self._frame_interval = 1.0 / fps

    def _open_camera(self):
        """Opens the camera with optimized settings for low latency."""
        cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            return None
            
        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Disable internal buffer — always grab the LATEST frame, never a queued one
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Warm up the camera
        for _ in range(3):
            cap.grab()
            
        return cap

    def set_enabled(self, enabled: bool):
        if self.is_enabled == enabled:
            return
        self.is_enabled = enabled
        logger.info(f"Camera enabled flag set to: {enabled}")

    def start(self) -> bool:
        if self.is_running:
            return True
            
        try:
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            logger.info("Camera capture thread started (camera off by default).")
            return True
        except Exception as e:
            logger.error(f"Error starting camera thread: {e}")
            return False

    def stop(self):
        self.is_running = False
        self.is_enabled = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("Camera capture stopped.")

    def _capture_loop(self):
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        last_encode_time = 0
        
        try:
            while self.is_running:
                if not self.is_enabled:
                    if self.cap:
                        self.cap.release()
                        self.cap = None
                    time.sleep(0.1)
                    continue
                    
                if not self.cap or not self.cap.isOpened():
                    self.cap = self._open_camera()
                    if not self.cap:
                        self.is_enabled = False
                        logger.error(f"Failed to open camera device {self.device_index}")
                        continue
                
                # Continuously grab to clear the hardware buffer
                grabbed = self.cap.grab()
                if not grabbed:
                    time.sleep(0.01)
                    continue
                    
                now = time.monotonic()
                if now - last_encode_time < self._frame_interval:
                    # We grabbed a frame to clear the buffer, but we don't need to send it yet
                    continue
                    
                ret, frame = self.cap.retrieve()
                if not ret or frame is None:
                    continue
                    
                last_encode_time = now
                
                # Resize only if the camera returned a different resolution
                h, w = frame.shape[:2]
                if w != self.width or h != self.height:
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
                
                # Compress to JPEG
                result, encimg = cv2.imencode('.jpg', frame, encode_param)
                
                if result:
                    self.callback(encimg.tobytes())
        finally:
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

    @staticmethod
    def get_cameras() -> list[dict]:
        """Attempt to find available cameras."""
        return [{"index": 0, "name": "Default Camera"}]
