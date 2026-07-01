import asyncio
import threading
from PySide6.QtCore import QObject, Signal
from network.host import TailChatHost
from network.client import TailChatClient
from voice.voice_server import VoiceServer
from voice.sender import VoiceSender
from voice.receiver import VoiceReceiver
from voice.speaker import SpeakerMixer
from video.video_server import VideoServer
from video.video_sender import VideoSender
from video.video_receiver import VideoReceiver
from database import rooms as db_rooms, room_members as db_members
from auth.session import session
from utils.constants import DEFAULT_CHAT_PORT, DEFAULT_VOICE_PORT, DEFAULT_FILE_PORT, DEFAULT_VIDEO_PORT
from utils.logger import logger

class RoomServiceSignals(QObject):
    # Signals for UI notifications
    room_joined = Signal()
    room_left = Signal()
    error_occurred = Signal(str)

class RoomService:
    def __init__(self):
        self.signals = RoomServiceSignals()
        self.loop = None
        self.loop_thread = None
        
        # Network Nodes
        self.host_node = None
        self.voice_server_node = None
        self.client_node = TailChatClient()
        
        # Audio Clients
        self.mixer = SpeakerMixer()
        self.voice_sender = None
        self.voice_receiver = None
        
        # Video Clients
        self.video_server_node = None
        self.video_sender = None
        self.video_receiver = None
        
        # Current room data
        self.current_room = None
        self.is_host = False
        
        self.start_event_loop()

    def start_event_loop(self):
        """Starts a background thread dedicated to running the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        
        def run_forever():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
            
        self.loop_thread = threading.Thread(target=run_forever, daemon=True)
        self.loop_thread.start()
        logger.info("Background asyncio event loop thread started.")

    def run_coro(self, coro):
        """Runs a coroutine thread-safely in our background loop."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def host_room(self, room_name: str, password: str = None) -> None:
        """Starts asynchronous host process. UI will be notified via signals."""
        self.run_coro(self._host_room_async(room_name, password))

    async def _host_room_async(self, room_name: str, password: str = None) -> bool:
        """Internal coroutine to start servers and publish room to Supabase."""
        try:
            logger.info(f"Attempting to host room: '{room_name}'")
            self.is_host = True
            
            # 1. Start TCP chat & file server
            self.host_node = TailChatHost(
                chat_port=DEFAULT_CHAT_PORT, 
                file_port=DEFAULT_FILE_PORT,
                room_password=password
            )
            await self.host_node.start(session.tailscale_ip)
            
            # 2. Start UDP voice forwarding server (with authentication validator)
            auth_validator = lambda uid: uid in self.host_node.clients
            channel_router = lambda uid: self.host_node.get_user_voice_channel(uid)
            
            self.voice_server_node = VoiceServer(DEFAULT_VOICE_PORT, auth_validator=auth_validator, channel_router=channel_router)
            self.voice_server_node.start(session.tailscale_ip)
            
            # 3. Create room registry in Supabase
            room = db_rooms.create_room(
                name=room_name,
                host_port=DEFAULT_CHAT_PORT,
                voice_port=DEFAULT_VOICE_PORT,
                file_port=DEFAULT_FILE_PORT,
                password=password
            )
            
            if not room:
                raise RuntimeError("Failed to register room in Supabase registry.")
                
            self.current_room = room
            
            # 4. Join room members table
            db_members.join_room(room["id"])
            
            # 5. Connect a fresh client node to the local server so signals
            #    are always bound to a live instance (matches join_room behaviour)
            self.client_node = TailChatClient()
            connected = await self.client_node.connect_to_host(session.tailscale_ip, DEFAULT_CHAT_PORT)
            if not connected:
                raise RuntimeError("Failed to connect client to local host server.")
                
            # 6. Voice is started later when user clicks a voice channel
            self.voice_sender = None
            self.voice_receiver = None
            
            # 7. Start local video server (but don't start sender/receiver until user joins VC)
            self.video_server_node = VideoServer(DEFAULT_VIDEO_PORT, auth_validator=auth_validator, channel_router=channel_router)
            self.video_server_node.start(session.tailscale_ip)
            
            self.video_sender = None
            self.video_receiver = None
            
            logger.info("Room hosted successfully.")
            self.signals.room_joined.emit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to host room: {e}")
            self.signals.error_occurred.emit(str(e))
            await self._cleanup_room_async()

    def join_room(self, room_id: str, password: str = None) -> None:
        """Starts asynchronous join process. UI will be notified via signals."""
        self.run_coro(self._join_room_async(room_id, password))

    async def _join_room_async(self, room_id: str, password: str = None) -> bool:
        """Internal coroutine to fetch host details, connect client, and start audio."""
        try:
            logger.info(f"Attempting to join room: {room_id}")
            self.is_host = False
            
            # 1. Fetch room details
            room = db_rooms.get_room_by_id(room_id)
            if not room:
                raise ValueError("Room not found or no longer active.")
                
            self.current_room = room
            
            # 2. Join roster in Supabase
            db_members.join_room(room_id)
            
            # 3. Connect client TCP node to host
            self.client_node = TailChatClient()
            success = await self.client_node.connect_to_host(room["host_ip"], room["host_port"], password)
            if not success:
                raise RuntimeError("Could not connect to host TCP server. Is host offline?")
                
            # 4. Voice is started later when user clicks a voice channel
            self.voice_sender = None
            self.voice_receiver = None
            
            # 5. Video sender/receiver are started later when user joins a voice channel
            self.video_sender = None
            self.video_receiver = None
            
            logger.info("Room joined successfully.")
            self.signals.room_joined.emit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to join room: {e}")
            self.signals.error_occurred.emit(str(e))
            await self._cleanup_room_async()

    def leave_room(self):
        """Synchronous wrapper to leave the current room."""
        future = self.run_coro(self._cleanup_room_async())
        try:
            future.result(timeout=5)
        except Exception as e:
            logger.error(f"Error or timeout during leave_room cleanup: {e}")

    async def _cleanup_room_async(self):
        """Internal cleanup coroutine to reset states, close servers, and delete tables."""
        logger.info("Leaving/Cleaning up room services...")
        
        # 1. Stop voice sender & receiver
        if self.voice_sender:
            self.voice_sender.stop()
            self.voice_sender = None
        if self.voice_receiver:
            self.voice_receiver.stop()
            self.voice_receiver = None
            
        # Stop video sender & receiver
        if self.video_sender:
            self.video_sender.stop()
            self.video_sender = None
        if self.video_receiver:
            self.video_receiver.stop()
            self.video_receiver = None
            
        # 2. Disconnect client
        if self.client_node:
            await self.client_node.disconnect()
            
        # 3. Database cleanups
        if self.current_room:
            room_id = self.current_room["id"]
            
            # Leave room member roster
            db_members.leave_room(room_id)
            
            # If host, delete room registry
            if self.is_host:
                db_rooms.delete_room(room_id)
                
        # 4. Shut down hosting nodes
        if self.host_node:
            await self.host_node.stop()
            self.host_node = None
            
        if self.voice_server_node:
            self.voice_server_node.stop()
            self.voice_server_node = None
            
        if self.video_server_node:
            self.video_server_node.stop()
            self.video_server_node = None
            
        self.current_room = None
        self.is_host = False
        self.signals.room_left.emit()
        logger.info("Cleanup complete.")

# Global instance
room_service = RoomService()
