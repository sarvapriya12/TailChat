import json
from pathlib import Path
from utils.constants import CONFIG_FILE
from utils.logger import logger

DEFAULT_SETTINGS = {
    "microphone_index": None,
    "speaker_index": None,
    "download_directory": str(Path.home() / "Downloads"),
    "profile_name": "",
    "profile_picture": "",
    "profile_bio": "",
    "profile_links": "",
    "theme": "dark"
}

def load_settings() -> dict:
    """Loads settings from config.json, returning defaults if file doesn't exist."""
    if not CONFIG_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            # Merge loaded settings with defaults to ensure all keys exist
            settings = DEFAULT_SETTINGS.copy()
            settings.update(loaded)
            return settings
    except Exception as e:
        logger.error(f"Failed to load settings from JSON: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> bool:
    """Saves settings to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        logger.info("Application settings saved successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        return False

def get_setting(key: str, default=None):
    """Retrieves a single setting value."""
    settings = load_settings()
    return settings.get(key, default)
