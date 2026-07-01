import os
from pathlib import Path

# Application Names
APP_NAME = "TailChat"
APP_DISPLAY_NAME = "TailChat"

# Directories
APPDATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = APPDATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TEMP_DIR = APPDATA_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APPDATA_DIR / "config.json"

# Network Defaults
DEFAULT_CHAT_PORT = 52341
DEFAULT_FILE_PORT = 52342
DEFAULT_VOICE_PORT = 52343
DEFAULT_VIDEO_PORT = 52344

# Video Settings
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 360
VIDEO_FPS = 15
VIDEO_JPEG_QUALITY = 60

# Tailscale Constants
TAILSCALE_INSTALLER_URL = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe"
TAILSCALE_DEFAULT_PATH = Path("C:/Program Files/Tailscale/tailscale.exe")

# Local Loopback Server Port for Supabase Auth
OAUTH_REDIRECT_PORT = 50002

# Audio Settings
AUDIO_SAMPLE_RATE = 24000  # Opus supports 8k, 12k, 16k, 24k, 48k
AUDIO_CHANNELS = 1         # Mono
AUDIO_FRAME_DURATION = 20  # milliseconds (Opus frame size: 2.5, 5, 10, 20, 40, 60 ms)
AUDIO_CHUNK_SIZE = int(AUDIO_SAMPLE_RATE * (AUDIO_FRAME_DURATION / 1000))  # Frames per chunk
