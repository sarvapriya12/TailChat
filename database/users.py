from database.supabase import get_supabase
from utils.logger import logger

def get_user_profile(user_id: str) -> dict | None:
    """Fetches a user profile by their ID."""
    try:
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.error(f"Failed to fetch user profile for {user_id}: {e}")
    return None

def update_user_profile(user_id: str, updates: dict) -> bool:
    """Updates profile fields for a user."""
    try:
        supabase = get_supabase()
        supabase.table("users").update(updates).eq("id", user_id).execute()
        logger.info(f"User profile updated for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update profile for {user_id}: {e}")
        return False
