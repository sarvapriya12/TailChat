from database.supabase import get_supabase
from auth.session import session
from utils.logger import logger

def create_room(name: str, host_port: int, voice_port: int, file_port: int, password: str = None) -> dict | None:
    """
    Creates a new room in the Supabase database.
    Returns the created room dict or None on failure.
    """
    if not session.is_logged_in() or not session.tailscale_ip:
        logger.error("Cannot create room: User not logged in or Tailscale IP unavailable.")
        return None
        
    try:
        supabase = get_supabase()
        room_data = {
            "name": name,
            "host_id": session.user_id,
            "host_ip": session.tailscale_ip,
            "host_port": host_port,
            "voice_port": voice_port,
            "file_port": file_port
        }
        
        if password:
            room_data["password"] = password
        
        result = supabase.table("rooms").insert(room_data).execute()
        if result.data:
            room = result.data[0]
            logger.info(f"Room '{name}' created in database with ID: {room['id']}")
            return room
    except Exception as e:
        logger.error(f"Failed to create room in database: {e}")
        
    return None

def delete_room(room_id: str) -> bool:
    """
    Deletes (closes) a room in the Supabase database.
    """
    try:
        supabase = get_supabase()
        supabase.table("rooms").delete().eq("id", room_id).execute()
        logger.info(f"Room {room_id} deleted from database.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete room {room_id}: {e}")
        return False

def list_active_rooms() -> list:
    """
    Fetches the list of active rooms from the database, joining host user details.
    """
    try:
        supabase = get_supabase()
        # Query joining users table explicitly specifying the foreign key relationship and room_members
        result = supabase.table("rooms").select("*, users!rooms_host_id_fkey(display_name, email, avatar_url), room_members(user_id)").execute()
        rooms = result.data or []
        
        valid_rooms = []
        import datetime
        for room in rooms:
            try:
                created_at_str = room.get("created_at", "")
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str[:-1] + "+00:00"
                created_at = datetime.datetime.fromisoformat(created_at_str)
                age = (datetime.datetime.now(datetime.timezone.utc) - created_at).total_seconds()
                
                # Check for zombie room: 0 members and older than 60s
                if len(room.get("room_members", [])) == 0 and age > 60:
                    # Attempt to clean it up (will only succeed if this user is the host due to RLS)
                    try:
                        supabase.table("rooms").delete().eq("id", room["id"]).execute()
                        logger.info(f"Cleaned up zombie room: {room['id']}")
                    except Exception:
                        pass
                    continue
            except Exception as e:
                pass
                
            valid_rooms.append(room)
            
        return valid_rooms
    except Exception as e:
        logger.error(f"Failed to list active rooms: {e}")
        return []

def get_room_by_id(room_id: str) -> dict | None:
    """
    Fetches a single room record by ID.
    """
    try:
        supabase = get_supabase()
        result = supabase.table("rooms").select("*, users!rooms_host_id_fkey(display_name, email, avatar_url)").eq("id", room_id).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.error(f"Failed to fetch room details for {room_id}: {e}")
    return None
