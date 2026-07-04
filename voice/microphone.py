import sounddevice as sd
import numpy as np
from utils.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE
from utils.logger import logger

class MicrophoneReader:
    def __init__(self, callback):
        """
        callback(pcm_bytes): Function called every 20ms with raw PCM data.
        """
        self.callback = callback
        self.stream = None
        self.device_index = None  # None uses system default

    def set_device(self, device_index):
        self.device_index = device_index
        if self.stream and self.stream.active:
            self.stop()
            self.start()

    def start(self) -> bool:
        """Starts recording audio from the microphone."""
        if self.stream:
            return True
            
        try:
            def sd_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Microphone status: {status}")
                # Convert float32 or int16 data to raw 16-bit signed PCM bytes
                rms = np.sqrt(np.mean(indata.astype(np.float32)**2))
                is_speaking = rms > 150  # VAD threshold
                
                pcm_data = indata.tobytes()
                self.callback(pcm_data, is_speaking, float(rms))
                
            self.stream = sd.InputStream(
                device=self.device_index,
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='int16',
                blocksize=AUDIO_CHUNK_SIZE,
                callback=sd_callback
            )
            self.stream.start()
            logger.info("Microphone stream started.")
            return True
        except Exception as e:
            logger.error(f"Failed to start microphone stream: {e}")
            self.stream = None
            return False

    def stop(self):
        """Stops recording audio."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            logger.info("Microphone stream stopped.")

    @staticmethod
    def get_input_devices() -> list[dict]:
        """Returns a list of available input audio devices."""
        devices = []
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    devices.append({
                        "index": idx,
                        "name": dev['name'],
                        "channels": dev['max_input_channels']
                    })
        except Exception as e:
            logger.error(f"Error querying audio input devices: {e}")
        return devices
