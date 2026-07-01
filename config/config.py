import os
from pathlib import Path
from utils.constants import APPDATA_DIR

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent.resolve()

def load_env_vars():
    """Manually parse .env files if present, fallback to os.environ."""
    env_vars = {}
    
    # Check project root .env first
    root_env = ROOT_DIR / ".env"
    # Check appdata .env as fallback
    appdata_env = APPDATA_DIR / ".env"
    
    for env_path in [root_env, appdata_env]:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            env_vars[key.strip()] = val.strip()
            except Exception:
                pass
                
    return env_vars

# Load environment variables
_env = load_env_vars()

SUPABASE_URL = _env.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = _env.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    # We will log a warning, but won't crash on import, in case the user configures it later.
    from utils.logger import logger
    logger.warning("SUPABASE_URL or SUPABASE_ANON_KEY is not defined in .env or environment variables.")
