import sounddevice as sd
import numpy as np
from collections import deque
import threading
from utils.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE
from utils.logger import logger

class SpeakerMixer:
    def __init__(self):
        self.stream = None
        self.device_index = None  # None uses system default
        
        # Dictionary of speaker queues: {user_id: deque(maxlen=20)}
        self.speaker_queues = {}
        self.lock = threading.Lock()

    def set_device(self, device_index):
        self.device_index = device_index
        if self.stream and self.stream.active:
            self.stop()
            self.start()

    def add_audio_frame(self, user_id: str, pcm_bytes: bytes):
        """Adds a decoded PCM frame for a specific user to their playback queue."""
        with self.lock:
            if user_id not in self.speaker_queues:
                # Max 20 frames buffer (~400ms) to prevent latency buildup
                self.speaker_queues[user_id] = deque(maxlen=20)
                
            q = self.speaker_queues[user_id]
            
        # Deque is thread-safe for append, so we can do it outside the lock
        # maxlen automatically drops the oldest item if full
        q.append(pcm_bytes)

    def remove_speaker(self, user_id: str):
        """Clean up queues when a user leaves the voice channel."""
        with self.lock:
            if user_id in self.speaker_queues:
                del self.speaker_queues[user_id]

    def start(self) -> bool:
        """Starts the audio output stream."""
        if self.stream:
            return True
            
        try:
            def sd_callback(outdata, frames, time_info, status):
                if status:
                    logger.debug(f"Speaker status: {status}")
                    
                # We need to mix the frames from all active speaker queues
                mixed_frame = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int32)
                active_speakers = 0
                
                # Safely copy the list of queues
                with self.lock:
                    queues = list(self.speaker_queues.values())
                    
                for q in queues:
                    try:
                        # Try to get one 20ms frame (deque popleft is thread-safe)
                        pcm_bytes = q.popleft()
                        pcm_data = np.frombuffer(pcm_bytes, dtype=np.int16)
                        # Sum up the speakers
                        mixed_frame += pcm_data
                        active_speakers += 1
                    except IndexError:
                        # Write comfort silence for this speaker
                        pass
                if active_speakers > 0:
                    # Clip to prevent overflow when casting back to int16
                    clipped_frame = np.clip(mixed_frame, -32768, 32767).astype(np.int16)
                    outdata[:, 0] = clipped_frame
                else:
                    # Silence
                    outdata.fill(0)
                    
            self.stream = sd.OutputStream(
                device=self.device_index,
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='int16',
                blocksize=AUDIO_CHUNK_SIZE,
                callback=sd_callback
            )
            self.stream.start()
            logger.info("Speaker output stream started.")
            return True
        except Exception as e:
            logger.error(f"Failed to start speaker stream: {e}")
            self.stream = None
            return False

    def stop(self):
        """Stops the audio output stream."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            logger.info("Speaker output stream stopped.")
            
        with self.lock:
            self.speaker_queues.clear()

    @staticmethod
    def get_output_devices() -> list[dict]:
        """Returns a list of available output audio devices."""
        devices = []
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev['max_output_channels'] > 0:
                    devices.append({
                        "index": idx,
                        "name": dev['name'],
                        "channels": dev['max_output_channels']
                    })
        except Exception as e:
            logger.error(f"Error querying audio output devices: {e}")
        return devices
