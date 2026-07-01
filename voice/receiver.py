import socket
import threading
import time
from pyogg.opus import OpusDecoder
from voice.speaker import SpeakerMixer
from auth.session import session
from utils.logger import logger

class VoiceReceiver:
    def __init__(self, host_ip: str, host_port: int, mixer: SpeakerMixer):
        self.host_ip = host_ip
        self.host_port = host_port
        self.mixer = mixer
        
        self.sock = None
        self.is_running = False
        self.thread = None
        self.keepalive_thread = None
        
        # Maps user_id -> OpusDecoder instance
        self.decoders = {}
        self.lock = threading.Lock()
        self.is_deafened = False

    def start(self) -> bool:
        """Starts the UDP receiver and speaker playback."""
        # Start speaker mixer
        if not self.mixer.start():
            return False
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to any local port
        try:
            self.sock.bind(("", 0))
            self.is_running = True
            
            # Start receiver thread
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            
            # Start keepalive registration loop
            self.keepalive_thread = threading.Thread(target=self.keepalive_loop, daemon=True)
            self.keepalive_thread.start()
            
            logger.info(f"VoiceReceiver started on local UDP port: {self.sock.getsockname()[1]}")
            return True
        except Exception as e:
            logger.error(f"Failed to bind local UDP receiver socket: {e}")
            return False

    def get_decoder(self, user_id: str) -> OpusDecoder | None:
        """Retrieves or creates a dedicated OpusDecoder for a specific speaker."""
        with self.lock:
            if user_id not in self.decoders:
                try:
                    decoder = OpusDecoder()
                    decoder.set_sampling_frequency(24000)
                    decoder.set_channels(1)
                    self.decoders[user_id] = decoder
                    logger.debug(f"Created OpusDecoder for user: {user_id}")
                except Exception as e:
                    logger.error(f"Failed to create OpusDecoder for user {user_id}: {e}")
                    return None
            return self.decoders[user_id]

    def remove_decoder(self, user_id: str):
        """Discards decoder for a user who left."""
        with self.lock:
            if user_id in self.decoders:
                del self.decoders[user_id]

    def keepalive_loop(self):
        """Sends periodic empty UDP packets to the host so it knows our UDP endpoint address."""
        user_id_bytes = session.user_id.encode("utf-8")
        # Empty packet has 0-length Opus bytes
        reg_packet = bytes([len(user_id_bytes)]) + user_id_bytes
        
        while self.is_running:
            try:
                if self.sock:
                    self.sock.sendto(reg_packet, (self.host_ip, self.host_port))
            except Exception:
                pass
            time.sleep(5)

    def set_deafened(self, deafened: bool):
        self.is_deafened = deafened

    def run(self):
        """Background thread receiving voice packets from host and decoding them."""
        buf_size = 4096
        while self.is_running:
            try:
                data, _ = self.sock.recvfrom(buf_size)
                if not data or len(data) < 2:
                    continue
                    
                # Parse packet: [1 byte user_id_len] + [user_id as UTF-8] + [Opus bytes]
                user_id_len = data[0]
                if len(data) < 1 + user_id_len:
                    continue
                    
                user_id = data[1 : 1 + user_id_len].decode("utf-8", errors="ignore")
                opus_bytes = data[1 + user_id_len :]
                
                # If there are no Opus bytes, it's just a registration/keepalive ping packet
                if not opus_bytes:
                    continue
                    
                # Discard audio if we are deafened
                if self.is_deafened:
                    continue
                    
                decoder = self.get_decoder(user_id)
                if decoder:
                    # Decode back to PCM bytes
                    pcm_bytes = bytes(decoder.decode(opus_bytes))
                    # Add to speaker mixer queue
                    self.mixer.add_audio_frame(user_id, pcm_bytes)
                    
            except Exception as e:
                if self.is_running:
                    logger.debug(f"Voice UDP receiver socket error: {e}")

    def stop(self):
        """Stops the UDP receiver and speaker mixer."""
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception: pass
            self.sock = None
            
        self.mixer.stop()
        
        with self.lock:
            self.decoders.clear()
            
        logger.info("VoiceReceiver stopped.")
