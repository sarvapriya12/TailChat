import os
import json
import time
from utils.constants import APPDATA_DIR
from database.supabase import get_supabase
from utils.helpers import get_tailscale_ip
from utils.logger import logger

class UserSession:
    def __init__(self):
        self.user_id = None
        self.display_name = ""
        self.email = ""
        self.avatar_url = ""
        self.tailscale_ip = ""
        self.access_token = None
        self.refresh_token = None
        self.bio = ""
        self.links = ""

    def is_logged_in(self) -> bool:
        return self.user_id is not None
        
    @property
    def net_id(self) -> str:
        """
        Returns a unique ID for network communication and room logic.
        Uses the tailscale_ip if available to prevent collisions when testing
        with the same user_id across multiple devices, otherwise falls back to user_id.
        """
        return self.tailscale_ip if self.tailscale_ip else self.user_id

    def sync_to_supabase(self, auth_user) -> bool:
        """
        Extracts details from the authenticated Supabase Auth user,
        saves it in the session state, and synchronizes/upserts it to the public 'users' table.
        """
        try:
            self.user_id = auth_user.id
            self.email = auth_user.email or ""
            
            # Extract metadata from Google identity
            metadata = getattr(auth_user, "user_metadata", {}) or {}
            # Check for local settings overrides
            from config.settings import load_settings
            local_settings = load_settings()
            custom_name = local_settings.get("profile_name", "").strip()
            custom_pic = local_settings.get("profile_picture", "").strip()
            
            self.display_name = custom_name if custom_name else (metadata.get("full_name") or metadata.get("name") or self.email.split("@")[0])
            self.avatar_url = custom_pic if custom_pic else (metadata.get("avatar_url") or "")
            self.bio = local_settings.get("profile_bio", "")
            self.links = local_settings.get("profile_links", "")
            
            # Fetch local Tailscale IP
            self.tailscale_ip = get_tailscale_ip()
            
            # Synchronize to Supabase public users table
            supabase = get_supabase()
            user_data = {
                "id": self.user_id,
                "display_name": self.display_name,
                "email": self.email,
                "avatar_url": self.avatar_url,
                "avatar_url": self.avatar_url,
                "last_seen_at": datetime.datetime.utcnow().isoformat() if 'datetime' in globals() else time.strftime('%Y-%m-%dT%H:%M:%S')
            }
            
            # Perform upsert
            supabase.table("users").upsert(user_data).execute()
            logger.info(f"User session synced to Supabase: {self.display_name} ({self.tailscale_ip})")
            return True
        except Exception as e:
            logger.error(f"Failed syncing user session to Supabase: {e}")
            return False

    def update_profile(self):
        """Updates the local profile based on settings and syncs to Supabase."""
        if not self.user_id:
            return False
            
        from config.settings import load_settings
        local_settings = load_settings()
        custom_name = local_settings.get("profile_name", "").strip()
        custom_pic = local_settings.get("profile_picture", "").strip()
        
        if custom_name:
            self.display_name = custom_name
        if custom_pic:
            self.avatar_url = custom_pic
            
        try:
            supabase = get_supabase()
            user_data = {
                "id": self.user_id,
                "display_name": self.display_name,
                "email": self.email,
                "avatar_url": self.avatar_url
            }
            supabase.table("users").upsert(user_data).execute()
            self.save_local_session()
            logger.info(f"User profile updated and synced to Supabase: {self.display_name}")
            return True
        except Exception as e:
            logger.error(f"Failed syncing updated profile to Supabase: {e}")
            return False

    def clear(self):
        """Logs out the user and clears session state."""
        self.user_id = None
        self.display_name = ""
        self.email = ""
        self.avatar_url = ""
        self.tailscale_ip = ""
        self.access_token = None
        self.refresh_token = None
        try:
            get_supabase().auth.sign_out()
            
            # Remove local session file if it exists
            session_file = os.path.join(APPDATA_DIR, "session.json")
            if os.path.exists(session_file):
                os.remove(session_file)
                
            logger.info("Successfully signed out and cleared local session.")
        except Exception as e:
            logger.debug(f"Error during sign-out: {e}")
            
    def save_local_session(self):
        """Saves session info to disk so we can 'Remember Me' for 7 days."""
        try:
            os.makedirs(APPDATA_DIR, exist_ok=True)
            session_file = os.path.join(APPDATA_DIR, "session.json")
            with open(session_file, "w") as f:
                json.dump({
                    "user_id": self.user_id,
                    "display_name": self.display_name,
                    "email": self.email,
                    "avatar_url": self.avatar_url,
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "timestamp": time.time()
                }, f)
            logger.info("Session saved locally for 7 days.")
        except Exception as e:
            logger.error(f"Failed to save local session: {e}")
            
    def try_load_local_session(self) -> bool:
        """Attempts to load a valid session (< 7 days old) from disk."""
        session_file = os.path.join(APPDATA_DIR, "session.json")
        if not os.path.exists(session_file):
            return False
            
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                
            # Check if older than 7 days
            if time.time() - data.get("timestamp", 0) > 7 * 24 * 3600:
                os.remove(session_file)
                return False
                
            # Use overrides if available
            from config.settings import load_settings
            local_settings = load_settings()
            custom_name = local_settings.get("profile_name", "").strip()
            custom_pic = local_settings.get("profile_picture", "").strip()
            
            self.user_id = data.get("user_id")
            self.display_name = custom_name if custom_name else data.get("display_name")
            self.email = data.get("email")
            self.avatar_url = custom_pic if custom_pic else data.get("avatar_url")
            self.bio = local_settings.get("profile_bio", "")
            self.links = local_settings.get("profile_links", "")
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.tailscale_ip = get_tailscale_ip()
            
            if self.access_token and self.refresh_token:
                try:
                    get_supabase().auth.set_session(self.access_token, self.refresh_token)
                except Exception as e:
                    logger.warning(f"Failed to restore Supabase session via tokens: {e}")
                    os.remove(session_file)
                    self.clear()
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Failed to load local session: {e}")
            return False

# Global Session instance
session = UserSession()
