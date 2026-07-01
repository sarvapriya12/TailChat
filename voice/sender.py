import socket
from pyogg.opus import OpusEncoder
from voice.microphone import MicrophoneReader
from auth.session import session
from utils.logger import logger

class VoiceSender:
    def __init__(self, host_ip: str, host_port: int, on_speaking_changed=None):
        self.host_ip = host_ip
        self.host_port = host_port
        self.on_speaking_changed = on_speaking_changed
        self.sock = None
        self.encoder = None
        self.mic = None
        self.is_muted = False
        self.last_speaking_state = False

    def start(self) -> bool:
        """Starts the voice encoder and microphone capture."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Initialize Opus Encoder
        try:
            self.encoder = OpusEncoder()
            if hasattr(self.encoder, 'set_application'):
                self.encoder.set_application("voip")
            if hasattr(self.encoder, 'set_sampling_frequency'):
                self.encoder.set_sampling_frequency(24000)
            if hasattr(self.encoder, 'set_channels'):
                self.encoder.set_channels(1)
        except Exception as e:
            logger.error(f"Failed to initialize Opus Encoder: {e}")
            return False

        # Start Microphone Reader
        self.mic = MicrophoneReader(self.send_audio_frame)
        return self.mic.start()

    def set_muted(self, muted: bool):
        """Mutes or unmutes the sender."""
        self.is_muted = muted
        logger.info(f"Voice mute state changed: {muted}")

    def send_audio_frame(self, pcm_bytes: bytes, is_speaking: bool):
        """Callback invoked by the mic reader. Encodes and transmits the frame."""
        if self.is_muted or not self.sock or not self.encoder:
            if self.last_speaking_state:
                self.last_speaking_state = False
                if self.on_speaking_changed:
                    self.on_speaking_changed(False)
            return
            
        if is_speaking != self.last_speaking_state:
            self.last_speaking_state = is_speaking
            if self.on_speaking_changed:
                self.on_speaking_changed(is_speaking)
                
        if not is_speaking:
            return
            
        try:
            # Encode PCM to Opus (returns a memoryview of encoded bytes)
            encoded = self.encoder.encode(pcm_bytes)
            if not encoded:
                return
                
            # Pack details: [1 byte user_id_len] + [user_id as string] + [Opus bytes]
            user_id_bytes = session.user_id.encode("utf-8")
            packet = bytes([len(user_id_bytes)]) + user_id_bytes + bytes(encoded)
            
            # Send UDP packet to host
            self.sock.sendto(packet, (self.host_ip, self.host_port))
        except Exception as e:
            logger.debug(f"Failed to send UDP voice packet: {e}")

    def stop(self):
        """Stops recording and closes the UDP socket."""
        if self.last_speaking_state and self.on_speaking_changed:
            self.on_speaking_changed(False)
            self.last_speaking_state = False
            
        if self.mic:
            self.mic.stop()
            self.mic = None
        if self.sock:
            try:
                self.sock.close()
            except Exception: pass
            self.sock = None
        self.encoder = None
        logger.info("VoiceSender stopped.")
