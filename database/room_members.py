from database.supabase import get_supabase
from auth.session import session
from utils.logger import logger

def join_room(room_id: str) -> bool:
    """Adds the current user to the room_members roster in Supabase."""
    if not session.is_logged_in():
        return False
    try:
        supabase = get_supabase()
        member_data = {
            "room_id": room_id,
            "user_id": session.user_id
        }
        supabase.table("room_members").insert(member_data).execute()
        logger.info(f"User {session.display_name} joined room roster: {room_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to join room roster: {e}")
        return False

def leave_room(room_id: str) -> bool:
    """Removes the current user from the room_members roster in Supabase."""
    if not session.is_logged_in():
        return False
    try:
        supabase = get_supabase()
        supabase.table("room_members").delete().eq("room_id", room_id).eq("user_id", session.user_id).execute()
        logger.info(f"User {session.display_name} left room roster: {room_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to leave room roster: {e}")
        return False

def get_room_members(room_id: str) -> list:
    """
    Fetches all members currently registered in the room, joining their profile details.
    """
    try:
        supabase = get_supabase()
        result = supabase.table("room_members").select("*, users(id, display_name, email, avatar_url)").eq("room_id", room_id).order("joined_at").execute()
        members = []
        for item in (result.data or []):
            if "users" in item and item["users"]:
                members.append(item["users"])
        return members
    except Exception as e:
        logger.error(f"Failed to fetch room members: {e}")
        return []
