from supabase import create_client, Client
from config.config import SUPABASE_URL, SUPABASE_ANON_KEY
from utils.logger import logger

_client: Client = None

def get_supabase() -> Client:
    """Initializes and returns the global Supabase client instance."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            logger.error("Supabase credentials are not configured. Please update your .env file.")
            raise ValueError("Supabase credentials missing.")
        try:
            logger.info("Initializing Supabase Client...")
            _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("Supabase Client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise e
    return _client
