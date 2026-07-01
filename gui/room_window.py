import os
import uuid
import datetime
import html
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QCheckBox, QMessageBox, QFileDialog, QProgressBar, QSplitter, QFrame, QSizePolicy
from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from qfluentwidgets import TransparentPushButton, PrimaryPushButton, SmoothScrollArea, InfoBar, InfoBarPosition, TransparentToolButton, FluentIcon, IndeterminateProgressRing
import cv2
import numpy as np
from services.room_service import room_service
from database.room_members import get_room_members
from files.uploader import stream_file_to_host
from files.downloader import stream_file_from_host
from config.settings import get_setting
from auth.session import session
from utils.logger import logger

class FileTransferProgressSignals(QObject):
    progress = Signal(str, int, int)      # file_id, processed, total
    finished = Signal(str, bool, str)     # file_id, success, message

# Global tracker for progress signals
transfer_signals = FileTransferProgressSignals()

class VoicePiPWidget(QWidget):
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(60, 60)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Return to Call")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.circle = QLabel(self)
        self.circle.setFixedSize(60, 60)
        self.circle.setStyleSheet("background-color: #1a1625; border-radius: 30px; border: 2px solid #8ab4f8; font-size: 24px;")
        self.circle.setAlignment(Qt.AlignCenter)
        self.circle.setText("🔊")
        layout.addWidget(self.circle)
        
        self.is_dragging = False
        self.drag_start_pos = None
        self.click_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.click_start_pos = event.globalPosition().toPoint()
            
    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.snap_to_corner()
            if self.click_start_pos:
                dist = (event.globalPosition().toPoint() - self.click_start_pos).manhattanLength()
                if dist < 5:
                    self.clicked.emit()
            
    def snap_to_corner(self):
        screen = self.screen().availableGeometry()
        center = self.frameGeometry().center()
        
        x = screen.left() + 20 if center.x() < screen.center().x() else screen.right() - self.width() - 20
        y = screen.top() + 20 if center.y() < screen.center().y() else screen.bottom() - self.height() - 20
        self.move(x, y)

class RoundedVideoLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAttribute(Qt.WA_StyledBackground, True)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen
        from PySide6.QtCore import Qt, QRectF
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(1, 1, -1, -1), 16, 16)
        
        # Fill background
        painter.fillPath(path, QColor("#1C2435"))
        
        # Draw image
        if self._pixmap and not self._pixmap.isNull():
            painter.setClipPath(path)
            scaled = self._pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)
            painter.setClipping(False)
            
        # Draw border
        pen = QPen(QColor(255, 255, 255, 13))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)

class VideoFeedWidget(QWidget):
    def __init__(self, name="Unknown", parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = RoundedVideoLabel(self)
        layout.addWidget(self.video_label, 0, Qt.AlignCenter)
        
        overlay_layout = QVBoxLayout(self.video_label)
        overlay_layout.setContentsMargins(16, 16, 16, 16)
        
        self.spinner = IndeterminateProgressRing(self.video_label)
        self.spinner.setFixedSize(48, 48)
        self.spinner.setStrokeWidth(4)
        self.spinner.start()
        
        spinner_row = QHBoxLayout()
        spinner_row.addStretch()
        spinner_row.addWidget(self.spinner)
        spinner_row.addStretch()
        
        overlay_layout.addStretch()
        overlay_layout.addLayout(spinner_row)
        overlay_layout.addStretch()
        
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        
        self.pill = QWidget(self.video_label)
        self.pill.setStyleSheet("background-color: rgba(0,0,0,0.45); border-radius: 16px;")
        self.pill.setFixedHeight(32)
        
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(12, 0, 12, 0)
        pill_layout.setSpacing(8)
        
        self.name_label = QLabel(name, self.pill)
        self.name_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px; background: transparent;")
        
        self.signal_label = QLabel("<span style='color: #81c995'> ▂▄▆</span>", self.pill)
        self.signal_label.setStyleSheet("background: transparent; font-size: 11px;")
        
        pill_layout.addWidget(self.name_label)
        pill_layout.addWidget(self.signal_label)
        
        bottom_row.addWidget(self.pill)
        bottom_row.addStretch()
        
        overlay_layout.addLayout(bottom_row)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Calculate maximum 16:9 rectangle that fits within the current size
        size = event.size()
        w = size.width()
        h = size.height()
        
        if w * 9 > h * 16:
            new_w = int(h * 16 / 9)
            new_h = h
        else:
            new_w = w
            new_h = int(w * 9 / 16)
            
        self.video_label.setFixedSize(new_w, new_h)

    def setPixmap(self, pixmap):
        if self.spinner.isVisible():
            self.spinner.stop()
            self.spinner.setVisible(False)
        self.video_label.setPixmap(pixmap)
        
    def set_name(self, name):
        self.name_label.setText(name)

class RoomPage(QWidget):
    local_frame_signal = Signal(bytes)
    local_speaking_signal = Signal(bool)
    
    def __init__(self, on_leave, parent=None):
        super().__init__(parent)
        self.local_speaking_signal.connect(self._update_local_speaking_ui)
        self.on_leave = on_leave
        self.members_cache = {}
        self.fifo_users = []
        self.pip = VoicePiPWidget(self)
        self.pip.clicked.connect(self.return_to_vc_screen)
        self.pip.hide()
        
        # Track ongoing transfers: {file_id: (filename, progressBar_widget)}
        self.active_transfers = {}
        # Outgoing file paths queued: {file_id: local_filepath}
        self.outgoing_files = {}
        # Incoming file paths queued: {file_id: save_filepath}
        self.incoming_files = {}
        
        # Track active timers for outgoing file offers: {file_id: (QTimer, remaining_secs)}
        self.offer_timers = {}
        # Cache of incoming file offer packets: {file_id: packet}
        self.pending_offers = {}
        # Track open QMessageBox popups: {file_id: QMessageBox}
        self.active_offer_dialogs = {}
        
        self.setStyleSheet("RoomPage { background-color: #000000; }")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # We use a QSplitter for resizable side panels
        self.central_splitter = QSplitter(Qt.Horizontal, self)
        self.layout.addWidget(self.central_splitter)
        
        # --- LEFT PANEL: Channels ---
        self.left_panel = QWidget(self)
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setMinimumWidth(200)
        self.left_panel.setMaximumWidth(280)
        self.left_panel.setStyleSheet("QWidget#leftPanel { background-color: #111111; border-right: 1px solid rgba(255,255,255,0.05); }")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(16, 24, 16, 24)
        left_layout.setSpacing(12)
        
        # Text Channels Section
        text_channels_header = QHBoxLayout()
        self.text_lbl = QLabel("TEXT CHANNELS", self)
        self.text_lbl.setStyleSheet("font-weight: 600; font-size: 11px; color: #9aa0a6; letter-spacing: 1px;")
        self.add_text_btn = QPushButton("+", self)
        self.add_text_btn.setObjectName("iconButton")
        self.add_text_btn.setFixedSize(24, 24)
        self.add_text_btn.setStyleSheet("border-radius: 12px; font-weight: bold;")
        self.add_text_btn.clicked.connect(self.create_text_channel)
        
        self.del_text_btn = QPushButton("−", self)
        self.del_text_btn.setObjectName("iconButton")
        self.del_text_btn.setFixedSize(24, 24)
        self.del_text_btn.setStyleSheet("border-radius: 12px; font-weight: bold;")
        self.del_text_btn.clicked.connect(self.delete_text_channel)
        
        text_channels_header.addWidget(self.text_lbl)
        text_channels_header.addStretch()
        text_channels_header.addWidget(self.del_text_btn)
        text_channels_header.addWidget(self.add_text_btn)
        left_layout.addLayout(text_channels_header)
        
        self.text_channels_list = QListWidget(self)
        self.text_channels_list.setFixedHeight(150)
        self.text_channels_list.setStyleSheet("QListWidget { background-color: transparent; border: none; outline: none; } QListWidget::item { padding: 10px 14px; border-radius: 10px; color: #e8eaed; margin-bottom: 2px; } QListWidget::item:hover { background-color: rgba(255,255,255,0.06); } QListWidget::item:selected { background-color: #2b2d31; border: 1px solid #4a4d53; font-weight: bold; }")
        self.text_channels_list.addItem("💬 general")
        self.text_channels_list.setCurrentRow(0)
        self.text_channels_list.itemClicked.connect(self.on_text_channel_clicked)
        left_layout.addWidget(self.text_channels_list)
        
        # Voice Channels Section
        voice_channels_header = QHBoxLayout()
        voice_channels_header.setContentsMargins(0, 10, 0, 0)
        self.voice_lbl = QLabel("VOICE CHANNELS", self)
        self.voice_lbl.setStyleSheet("font-weight: 600; font-size: 11px; color: #9aa0a6; letter-spacing: 1px;")
        self.add_voice_btn = QPushButton("+", self)
        self.add_voice_btn.setObjectName("iconButton")
        self.add_voice_btn.setFixedSize(24, 24)
        self.add_voice_btn.setStyleSheet("border-radius: 12px; font-weight: bold;")
        self.add_voice_btn.clicked.connect(self.create_voice_channel)
        
        self.del_voice_btn = QPushButton("-", self)
        self.del_voice_btn.setObjectName("iconButton")
        self.del_voice_btn.setFixedSize(24, 24)
        self.del_voice_btn.setStyleSheet("border-radius: 12px; font-weight: bold;")
        self.del_voice_btn.clicked.connect(self.delete_voice_channel)
        
        voice_channels_header.addWidget(self.voice_lbl)
        voice_channels_header.addStretch()
        voice_channels_header.addWidget(self.del_voice_btn)
        voice_channels_header.addWidget(self.add_voice_btn)
        left_layout.addLayout(voice_channels_header)
        
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
        self.voice_channels_tree = QTreeWidget(self)
        self.voice_channels_tree.setHeaderHidden(True)
        self.voice_channels_tree.setIndentation(15)
        self.voice_channels_tree.setAnimated(True)
        self.voice_channels_tree.setStyleSheet("QTreeWidget { background-color: transparent; border: none; outline: none; } QTreeWidget::item { padding: 8px 10px; border-radius: 8px; color: #e8eaed; margin-bottom: 2px; } QTreeWidget::item:hover { background-color: rgba(255,255,255,0.06); } QTreeWidget::item:selected { background-color: #2b2d31; border: 1px solid #4a4d53; font-weight: bold; }")
        
        general_vc = QTreeWidgetItem(self.voice_channels_tree, ["🔊 General VC"])
        self.voice_channels_tree.addTopLevelItem(general_vc)
        general_vc.setExpanded(True)
        
        self.voice_channels_tree.itemClicked.connect(self.on_voice_channel_clicked)
        left_layout.addWidget(self.voice_channels_tree)
        
        left_layout.addStretch() # Push everything up
        
        # Voice Controls Box (Discord-like static left panel)
        self.voice_controls_box = QWidget(self)
        self.voice_controls_box.setStyleSheet("background-color: #202124; border-radius: 8px;")
        self.voice_controls_box.setVisible(False)
        voice_box_layout = QVBoxLayout(self.voice_controls_box)
        voice_box_layout.setContentsMargins(8, 8, 8, 8)
        voice_box_layout.setSpacing(4)
        
        # Status header
        self.audio_status_lbl = QPushButton("Voice Connected", self)
        self.audio_status_lbl.setCursor(Qt.PointingHandCursor)
        self.audio_status_lbl.setStyleSheet("color: #81c995; font-weight: bold; font-size: 11px; text-align: left; background: transparent; border: none;")
        self.audio_status_lbl.clicked.connect(self.return_to_vc_screen)
        voice_box_layout.addWidget(self.audio_status_lbl)
        
        # Buttons row
        voice_btns_layout = QHBoxLayout()
        voice_btns_layout.setSpacing(8)
        
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.icon_dir = os.path.join(base_dir, "assets", "icons")
        
        self.btn_camera_toggle = QPushButton(self)
        self.btn_camera_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "media.png"))) # Default camera off
        self.btn_camera_toggle.setIconSize(QSize(24, 24))
        self.btn_camera_toggle.setObjectName("iconButton")
        self.btn_camera_toggle.setFixedSize(40, 40)
        self.btn_camera_toggle.setToolTip("Camera On")
        self.btn_camera_toggle.clicked.connect(self.toggle_camera)
        
        self.btn_deafen_toggle = QPushButton(self)
        self.btn_deafen_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "music.png"))) # Default undeafened
        self.btn_deafen_toggle.setIconSize(QSize(24, 24))
        self.btn_deafen_toggle.setObjectName("iconButton")
        self.btn_deafen_toggle.setFixedSize(40, 40)
        self.btn_deafen_toggle.setToolTip("Deafen")
        self.btn_deafen_toggle.clicked.connect(self.toggle_deafen)
        
        self.btn_mic_toggle = QPushButton(self)
        self.btn_mic_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "microphone.png"))) # Default mic on
        self.btn_mic_toggle.setIconSize(QSize(24, 24))
        self.btn_mic_toggle.setObjectName("iconButton")
        self.btn_mic_toggle.setFixedSize(40, 40)
        self.btn_mic_toggle.setToolTip("Mute")
        self.btn_mic_toggle.clicked.connect(self.toggle_mic)
        

        self.btn_disconnect = QPushButton(self)
        self.btn_disconnect.setIcon(QIcon(os.path.join(self.icon_dir, "callEnd.png")))
        self.btn_disconnect.setIconSize(QSize(24, 24))
        self.btn_disconnect.setObjectName("dangerButton")
        self.btn_disconnect.setFixedSize(40, 40)
        self.btn_disconnect.setStyleSheet("border-radius: 20px; background-color: #EF4444;")
        self.btn_disconnect.setToolTip("Disconnect")
        self.btn_disconnect.clicked.connect(self.disconnect_call)
        
        voice_btns_layout.addWidget(self.btn_camera_toggle)
        voice_btns_layout.addWidget(self.btn_deafen_toggle)
        voice_btns_layout.addWidget(self.btn_mic_toggle)
        voice_btns_layout.addStretch()
        voice_btns_layout.addWidget(self.btn_disconnect)
        
        voice_box_layout.addLayout(voice_btns_layout)
        left_layout.addWidget(self.voice_controls_box)
        
        # Profile Footer in Left Panel
        profile_layout = QHBoxLayout()
        profile_layout.setContentsMargins(0, 10, 0, 0)
        
        self.avatar_label = QLabel("?", self)
        self.avatar_label.setFixedSize(36, 36)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("background-color: rgba(138,180,248,0.15); border-radius: 18px; font-weight: bold; font-size: 14px;")
        
        self.user_name_label = QLabel("Guest", self)
        self.user_name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        
        # Ping display
        self.ping_label = QLabel("🟢", self)
        self.ping_label.setStyleSheet("font-size: 14px; font-weight: bold; background-color: transparent; padding: 0px 4px;")
        self.ping_label.setFixedHeight(24)
        
        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self._update_ping)
        self.ping_timer.start(3000)
        
        # User settings
        self.btn_settings = QPushButton("⚙️", self)
        self.btn_settings.setObjectName("iconButton")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setStyleSheet("font-size: 16px;")
        self.btn_settings.setToolTip("User Settings")
        self.btn_settings.clicked.connect(self.open_settings)
        
        self.btn_home = TransparentToolButton(FluentIcon.HOME, self)
        self.btn_home.setFixedSize(32, 32)
        # TransparentToolButton handles its own styling nicely
        self.btn_home.setToolTip("Lobby")
        self.btn_home.clicked.connect(self.go_to_lobby)
        
        profile_layout.addWidget(self.avatar_label)
        profile_layout.addWidget(self.user_name_label)
        profile_layout.addStretch()
        profile_layout.addWidget(self.ping_label)
        profile_layout.addWidget(self.btn_settings)
        profile_layout.addWidget(self.btn_home)
        
        left_layout.addLayout(profile_layout)
        
        self.update_profile()
        
        # State
        self.current_text_channel = "general"
        self.current_voice_channel = "General VC"
        self.messages_cache = {"general": []}
        
        self.central_splitter.addWidget(self.left_panel)
        
        # --- CENTER PANEL: Chat and Video ---
        self.center_panel = QWidget(self)
        self.center_panel.setObjectName("centerPanel")
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # Header Info
        self.header_frame = QFrame(self.center_panel)
        self.header_frame.setStyleSheet("background-color: #111111; border-bottom: 1px solid rgba(255,255,255,0.1);") 
        
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        self.btn_toggle_right = QPushButton("📁", self.header_frame)
        self.btn_toggle_right.setObjectName("iconButton")
        self.btn_toggle_right.setFixedSize(30, 30)
        self.btn_toggle_right.setToolTip("Show File Sharing")
        self.btn_toggle_right.setVisible(False)
        self.btn_toggle_right.clicked.connect(self.restore_right_panel)
        
        self.room_title = QLabel("💬 General", self.header_frame)
        self.room_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #e8eaed;")
        
        self.owner_label = QLabel("OWNER : Unknown", self.header_frame)
        self.owner_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #9aa0a6; letter-spacing: 1px;")
        
        title_owner_layout = QVBoxLayout()
        title_owner_layout.setSpacing(2)
        title_owner_layout.addWidget(self.room_title)
        title_owner_layout.addWidget(self.owner_label)
        
        # Chat Tray Icon
        self.btn_chat_toggle = QPushButton(self)
        self.btn_chat_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "message.png")))
        self.btn_chat_toggle.setIconSize(QSize(24, 24))
        self.btn_chat_toggle.setObjectName("secondaryButton")
        self.btn_chat_toggle.setFixedSize(40, 40)
        self.btn_chat_toggle.setStyleSheet("border-radius: 20px; background-color: rgba(138,180,248,0.25); border: 1px solid rgba(138,180,248,0.5);")
        self.btn_chat_toggle.setToolTip("Toggle Chat")
        self.btn_chat_toggle.clicked.connect(self.toggle_chat)
        
        # Roster Tray Icon
        self.btn_roster = QPushButton(self)
        self.btn_roster.setIcon(QIcon(os.path.join(self.icon_dir, "user.png")))
        self.btn_roster.setIconSize(QSize(24, 24))
        self.btn_roster.setObjectName("secondaryButton")
        self.btn_roster.setFixedSize(40, 40)
        self.btn_roster.setStyleSheet("border-radius: 20px; background-color: rgba(138,180,248,0.10); border: 1px solid rgba(138,180,248,0.25);")
        self.btn_roster.setToolTip("Active Users")
        
        from PySide6.QtWidgets import QMenu, QWidgetAction
        self.roster_menu = QMenu(self)
        self.roster_menu.setStyleSheet("QMenu { background-color: #292a2d; border: 1px solid rgba(95,99,104,0.3); border-radius: 12px; }")
        
        self.roster_list = QListWidget(self)
        self.roster_list.setSelectionMode(QListWidget.NoSelection)
        self.roster_list.itemDoubleClicked.connect(self.on_roster_double_clicked)
        self.roster_list.setFixedSize(250, 300)
        
        self.roster_action = QWidgetAction(self.roster_menu)
        self.roster_action.setDefaultWidget(self.roster_list)
        self.roster_menu.addAction(self.roster_action)
        
        self.btn_roster.clicked.connect(lambda: self.roster_menu.exec(self.btn_roster.mapToGlobal(self.btn_roster.rect().bottomLeft())))
        
        header_layout.addLayout(title_owner_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_toggle_right)
        header_layout.addWidget(self.btn_chat_toggle)
        header_layout.addWidget(self.btn_roster)
        center_layout.addWidget(self.header_frame)
        
        # ---- CENTER CONTENT: Video Area + Chat Area ----
        from PySide6.QtWidgets import QGridLayout
        
        self.center_content_splitter = QSplitter(Qt.Horizontal, self)
        self.center_content_splitter.setHandleWidth(1)
        self.center_content_splitter.setStyleSheet("QSplitter::handle { background-color: rgba(95,99,104,0.3); }")
        
        # Left: Video Grid (hidden by default, shown when camera is on)
        self.video_area = QWidget(self)
        self.video_layout = QGridLayout(self.video_area)
        self.video_layout.setContentsMargins(20, 20, 20, 20)
        self.video_layout.setSpacing(15)
        self.video_area.setVisible(False)
        self.center_content_splitter.addWidget(self.video_area)
        
        # Right: Chat Area (always visible by default)
        self.chat_container = QWidget(self)
        self.chat_container.setStyleSheet("background-color: transparent; border: none;")
        chat_container_layout = QVBoxLayout(self.chat_container)
        chat_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_scroll = SmoothScrollArea(self)
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background-color: #292a2d; border-radius: 8px; border: none;")
        
        self.chat_content_widget = QWidget()
        self.chat_content_widget.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(12)
        self.chat_layout.setContentsMargins(12, 12, 12, 12)
        
        self.chat_scroll.setWidget(self.chat_content_widget)
        chat_container_layout.addWidget(self.chat_scroll, stretch=1)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        input_layout.setContentsMargins(16, 8, 16, 16)
        
        self.attach_btn = QPushButton("+", self)
        self.attach_btn.setObjectName("secondaryButton")
        self.attach_btn.setFixedSize(60, 36)
        self.attach_btn.setStyleSheet("""
            QPushButton { font-size: 24px; font-weight: bold; border-radius: 18px; background-color: #292a2d; border: none; color: white; }
            QPushButton:hover { background-color: #3c4043; }
        """)
        self.attach_btn.clicked.connect(self.send_image_in_chat)
        
        self.chat_input = QLineEdit(self)
        self.chat_input.setFixedHeight(36)
        self.chat_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.chat_input.setStyleSheet("""
            QLineEdit { background-color: #292a2d; color: #e8eaed; border: 1px solid rgba(255,255,255,0.7); border-radius: 18px; padding: 0px 16px; font-weight: 600; }
            QLineEdit:focus { background-color: #3c4043; border: 1px solid white; }
        """)
        self.chat_input.setPlaceholderText("Type a message...")
        self.chat_input.returnPressed.connect(self.send_message)
        
        input_layout.addWidget(self.attach_btn)
        input_layout.addWidget(self.chat_input)
        chat_container_layout.addLayout(input_layout)
        
        self.center_content_splitter.addWidget(self.chat_container)
        
        # Video takes ~70%, Chat takes ~30%
        self.center_content_splitter.setSizes([700, 300])
        
        center_layout.addWidget(self.center_content_splitter, stretch=1)
        self.central_splitter.addWidget(self.center_panel)
        
        # Maps user_id to QLabel showing video
        self.video_labels = {}
        
        # --- RIGHT PANEL: File Sharing & Actions ---
        self.right_panel = QWidget(self)
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet("QWidget#rightPanel { background-color: #111111; border-left: 1px solid rgba(255,255,255,0.1); }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(24, 24, 24, 24)
        
        self.files_label = QLabel("File Sharing", self)
        self.files_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #9aa0a6; letter-spacing: 1px; text-transform: uppercase;")
        right_layout.addWidget(self.files_label)
        
        # File Action Buttons
        self.send_file_room_btn = QPushButton("Send File to Room", self)
        self.send_file_room_btn.setObjectName("secondaryButton")
        self.send_file_room_btn.clicked.connect(self.send_file_to_room)
        right_layout.addWidget(self.send_file_room_btn)
        
        self.send_file_user_btn = QPushButton("Send File to Selected User", self)
        self.send_file_user_btn.setObjectName("secondaryButton")
        self.send_file_user_btn.clicked.connect(self.send_file_to_user)
        right_layout.addWidget(self.send_file_user_btn)
        
        # Active transfers header
        self.transfers_header = QLabel("Active Transfers", self)
        self.transfers_header.setStyleSheet("font-weight: 600; margin-top: 15px; color: #9aa0a6; font-size: 12px;")
        right_layout.addWidget(self.transfers_header)
        
        # List of active progress bars
        self.transfers_layout = QVBoxLayout()
        self.transfers_layout.setAlignment(Qt.AlignTop)
        right_layout.addLayout(self.transfers_layout)
        right_layout.addStretch()
        
        self.central_splitter.addWidget(self.right_panel)
        
        # Splitter proportion defaults
        self.central_splitter.setSizes([180, 520, 200])
        
        # Wire up incoming TCP client signals
        self.connect_signals()
        
        # Splitter event for collapsible panels
        self.central_splitter.splitterMoved.connect(self.on_splitter_moved)
    
    def update_profile(self):
        initial = session.display_name[0].upper() if session.display_name else "?"
        self.avatar_label.setText(initial)
        self.user_name_label.setText(session.display_name or "Guest")

    @Slot(bool)
    def _update_local_speaking_ui(self, is_speaking):
        if is_speaking:
            self.avatar_label.setStyleSheet("background-color: rgba(138,180,248,0.15); border-radius: 18px; font-weight: bold; font-size: 14px; border: 2px solid white;")
        else:
            self.avatar_label.setStyleSheet("background-color: rgba(138,180,248,0.15); border-radius: 18px; font-weight: bold; font-size: 14px; border: none;")

    def open_settings(self):
        from gui.settings_window import SettingsDialog
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.update_profile()
            
    def on_splitter_moved(self, pos, index):
        sizes = self.central_splitter.sizes()
        self.btn_toggle_right.setVisible(sizes[2] == 0)
    def restore_right_panel(self):
        sizes = self.central_splitter.sizes()
        sizes[2] = 220 # Restore width
        if sizes[1] < 100: sizes[1] = 100
        self.central_splitter.setSizes(sizes)
        self.btn_toggle_right.setVisible(False)
        
    def disconnect_call(self):
        """Leaves the current voice channel and turns off camera."""
        self.pip.hide()
        self.current_voice_channel = None
        
        # Stop voice services
        if room_service.voice_sender:
            room_service.voice_sender.stop()
            room_service.voice_sender = None
        if room_service.voice_receiver:
            room_service.voice_receiver.stop()
            room_service.voice_receiver = None
            
        # Turn off camera
        if self.is_camera_on:
            self.is_camera_on = False
            if room_service.video_sender:
                room_service.video_sender.set_camera_enabled(False)
            
        # Stop video services
        if room_service.video_sender:
            room_service.video_sender.stop()
            room_service.video_sender = None
        if room_service.video_receiver:
            room_service.video_receiver.stop()
            room_service.video_receiver = None
            
        # Clear all video labels
        for uid, lbl in list(self.video_labels.items()):
            self.video_layout.removeWidget(lbl)
            lbl.deleteLater()
        self.video_labels.clear()
        self.video_area.setVisible(False)
            
        # Let server know we left
        room_service.run_coro(room_service.client_node.leave_channel("voice"))
        
        # Reset UI audio state
        self.is_mic_muted = False
        self.is_deafened = False
        self.btn_mic_toggle.setObjectName("controlButton")
        self.btn_deafen_toggle.setObjectName("controlButton")
        self.btn_camera_toggle.setObjectName("controlButton")
        self.btn_mic_toggle.style().unpolish(self.btn_mic_toggle)
        self.btn_mic_toggle.style().polish(self.btn_mic_toggle)
        self.btn_deafen_toggle.style().unpolish(self.btn_deafen_toggle)
        self.btn_deafen_toggle.style().polish(self.btn_deafen_toggle)
        self.btn_camera_toggle.style().unpolish(self.btn_camera_toggle)
        self.btn_camera_toggle.style().polish(self.btn_camera_toggle)
        self.voice_controls_box.setVisible(False)
        self.chat_container.setVisible(True)
        self.audio_status_lbl.setVisible(False)

    def _update_ping(self):
        if not room_service.current_room:
            self.ping_label.setText("")
            self.ping_label.setToolTip("")
            return
            
        import subprocess, platform
        host = room_service.current_room["host_ip"]
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        
        try:
            output = subprocess.check_output(['ping', param, '1', host], timeout=1.0, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == 'windows' else 0)
            
            ms = -1
            if 'time=' in output:
                ms = int(output.split('time=')[1].split('ms')[0].strip())
            elif 'time<' in output:
                ms = int(output.split('time<')[1].split('ms')[0].strip())
                
            if ms >= 0:
                if ms < 100:
                    bars = "🟢"
                elif ms < 200:
                    bars = "🟡"
                else:
                    bars = "🔴"
                self.ping_label.setText(bars)
                self.ping_label.setToolTip(f"{ms} ms")
                self.ping_label.setStyleSheet("font-size: 14px; font-weight: bold; background-color: transparent; padding: 0px 4px;")
            else:
                self.ping_label.setText("<span style='color: #5f6368'> ▂▄▆</span>")
                self.ping_label.setToolTip("Unknown latency")
                self.ping_label.setStyleSheet("font-size: 14px; font-weight: bold; background-color: transparent; padding: 0px 4px;")
        except Exception:
            self.ping_label.setText("<span style='color: #ea4335'> ▂▄▆</span>")
            self.ping_label.setToolTip("Offline")
            self.ping_label.setStyleSheet("font-size: 14px; font-weight: bold; background-color: transparent; padding: 0px 4px;")

    def go_to_lobby(self):
        """Navigates back to the lobby without disconnecting from the room."""
        main_win = self.window()
        if hasattr(main_win, 'sidebar'):
            main_win.sidebar.setVisible(True)
        if hasattr(main_win, 'navigate_to'):
            main_win.navigate_to(1)

    def connect_signals(self):
        """Wire up signals from the current client_node to this RoomPage.
        Called once at __init__ for the initial (host) client_node.
        reconnect_signals() must be called after join_room replaces client_node."""
        c = room_service.client_node
        c.signals.chat_received.connect(self.on_chat_received)
        c.signals.user_joined.connect(self.on_user_joined)
        c.signals.members_list.connect(self.on_members_list)
        c.signals.user_left.connect(self.on_user_left)
        self.local_frame_signal.connect(self._on_local_frame)
        c.signals.file_offer.connect(self.on_file_offer)
        c.signals.file_accepted.connect(self.on_file_accepted)
        c.signals.file_declined.connect(self.on_file_declined)
        c.signals.file_expired.connect(self.on_file_expired)
        c.signals.voice_state_changed.connect(self.on_voice_state_changed)
        c.signals.speaking_state_changed.connect(self.on_speaking_state_changed)
        c.signals.room_shutdown.connect(self.on_room_shutdown)
        c.signals.disconnected.connect(self.on_disconnected)
        c.signals.voice_channel_changed.connect(self.on_voice_channel_updated)
        
        # Custom transfer progress signals
        transfer_signals.progress.connect(self.on_transfer_progress)
        transfer_signals.finished.connect(self.on_transfer_finished)

    def reconnect_signals(self):
        """Rewire all client_node signals to the *current* room_service.client_node.
        
        join_room() replaces room_service.client_node with a brand-new TailChatClient
        instance, so the bindings made in __init__ point at the dead old object.
        This must be called every time we enter the room view after a join/host.
        """
        c = room_service.client_node
        # Connect each signal (Qt is safe to call connect multiple times on the same
        # slot only if the target object differs, which it does here since client_node
        # is a new instance). Using a fresh ClientSignals QObject every time means
        # there are no leftover connections on the new object.
        c.signals.chat_received.connect(self.on_chat_received)
        c.signals.user_joined.connect(self.on_user_joined)
        c.signals.members_list.connect(self.on_members_list)
        c.signals.user_left.connect(self.on_user_left)
        c.signals.file_offer.connect(self.on_file_offer)
        c.signals.file_accepted.connect(self.on_file_accepted)
        c.signals.file_declined.connect(self.on_file_declined)
        c.signals.file_expired.connect(self.on_file_expired)
        c.signals.voice_state_changed.connect(self.on_voice_state_changed)
        c.signals.speaking_state_changed.connect(self.on_speaking_state_changed)
        c.signals.room_shutdown.connect(self.on_room_shutdown)
        c.signals.disconnected.connect(self.on_disconnected)
        c.signals.voice_channel_changed.connect(self.on_voice_channel_updated)
        logger.info("RoomPage: signals reconnected to new client_node.")

    def initialize_room_view(self):
        """Called upon entering the room window."""
        # Always rewire signals to the current client_node.
        self.reconnect_signals()

        self.fifo_users = []
        if session.user_id not in self.fifo_users:
            self.fifo_users.append(session.user_id)
        # Reset member cache — stale members from a previous room must not bleed in
        self.members_cache = {}
        self._update_owner_label()

        room = room_service.current_room
        # Show room name prominently in the header
        if room:
            room_name = room.get("name", "Room")
            self.room_title.setText(f"💬 general  —  {room_name}")
        # Reset to default channel and clear all cached messages from prior rooms
        self.current_text_channel = "general"
        self.messages_cache = {"general": []}
        self.clear_chat()
        
        self.is_mic_muted = False
        self.is_deafened = False
        self.is_camera_on = False
        self.btn_mic_toggle.setObjectName("controlButton")
        self.btn_deafen_toggle.setObjectName("controlButton")
        self.btn_camera_toggle.setObjectName("controlButton")
        self.btn_mic_toggle.style().unpolish(self.btn_mic_toggle)
        self.btn_mic_toggle.style().polish(self.btn_mic_toggle)
        self.btn_deafen_toggle.style().unpolish(self.btn_deafen_toggle)
        self.btn_deafen_toggle.style().polish(self.btn_deafen_toggle)
        self.btn_camera_toggle.style().unpolish(self.btn_camera_toggle)
        self.btn_camera_toggle.style().polish(self.btn_camera_toggle)
        
        self.voice_controls_box.setVisible(False)
        self.audio_status_lbl.setVisible(False)
        
        self.chat_container.setVisible(True)
        self.video_area.setVisible(False)
        
        # Video receiver signal is connected when user joins a voice channel
            
        # Clear video grid
        for lbl in self.video_labels.values():
            lbl.deleteLater()
        self.video_labels.clear()
        self.roster_list.clear()
        self.active_transfers.clear()
        
        self.user_name_label.setText(session.display_name or "Guest")
        if session.avatar_url and session.avatar_url.startswith("data:image"):
            try:
                import base64
                header, encoded = session.avatar_url.split(",", 1)
                data = base64.b64decode(encoded)
                pix = QPixmap()
                pix.loadFromData(data)
                
                target = QPixmap(36, 36)
                target.fill(Qt.transparent)
                from PySide6.QtGui import QPainter, QPainterPath
                painter = QPainter(target)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, 36, 36)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pix.scaled(36, 36, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                painter.end()
                
                self.avatar_label.setPixmap(target)
                self.avatar_label.setStyleSheet("background-color: transparent;")
                self.avatar_label.setText("")
            except Exception:
                pass
        else:
            self.avatar_label.setPixmap(QPixmap())
            self.avatar_label.setText(session.display_name[0].upper() if session.display_name else "?")
            self.avatar_label.setStyleSheet("background-color: rgba(138,180,248,0.15); border-radius: 18px; font-weight: bold; font-size: 14px;")
        
        # Clear transfer progress bar layout
        while self.transfers_layout.count():
            child = self.transfers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.refresh_roster()

        # Replay join_ack data (members list + chat history) that arrived while
        # the GUI signals were not yet connected to the new client_node.
        # This MUST happen after all the state-clear calls above so replayed
        # messages/members are not immediately wiped.
        room_service.client_node.replay_join_ack()

        # Show a "you joined" system message so the chat isn't blank on entry
        import datetime as _dt
        self.on_chat_received({
            "channel": "general",
            "sender_name": "System",
            "content": f"» You joined the room as {session.display_name}.",
            "timestamp": _dt.datetime.now().strftime("%H:%M"),
            "is_system": True
        })

    def refresh_roster(self):
        """Redraws the roster. We don't fetch from DB anymore as host syncs it."""
        self._redraw_roster()

    def _redraw_roster(self):
        """Redraws the roster list based on local members_cache without blocking."""
        self.roster_list.clear()
        for uid, info in self.members_cache.items():
            self.add_roster_item(uid, info["display_name"], info.get("muted", False), info.get("is_speaking", False), info.get("avatar_url"))
        self._redraw_voice_channels()

    def _redraw_voice_channels(self):
        from PySide6.QtWidgets import QTreeWidgetItem
        from PySide6.QtGui import QColor
        for i in range(self.voice_channels_tree.topLevelItemCount()):
            channel_item = self.voice_channels_tree.topLevelItem(i)
            channel_item.takeChildren()
            channel_name = channel_item.text(0).replace("🔊 ", "")
            
            for uid, info in self.members_cache.items():
                if info.get("voice_channel") == channel_name:
                    prefix = "🗣️ " if info.get("is_speaking") else "  ↳ "
                    user_item = QTreeWidgetItem(channel_item, [f"{prefix}{info['display_name']}"])
                    user_item.setData(0, Qt.UserRole, uid)
                    if info.get("is_speaking"):
                        user_item.setForeground(0, QColor("#4CAF50"))
                    elif info.get("muted"):
                        user_item.setForeground(0, QColor("#E87070"))
            channel_item.setExpanded(True)

    def add_roster_item(self, user_id, name, is_muted, is_speaking=False, avatar_url=None):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Avatar
        avatar = QLabel(widget)
        avatar.setFixedSize(28, 28)
        
        # Liquid glass green glow if speaking
        border_style = "border: 2px solid #4CAF50; box-shadow: 0 0 10px #4CAF50;" if is_speaking else "border: 1px solid rgba(255, 255, 255, 0.2);"
        
        has_avatar = False
        if avatar_url and avatar_url.startswith("data:image"):
            try:
                import base64
                header, encoded = avatar_url.split(",", 1)
                data = base64.b64decode(encoded)
                pix = QPixmap()
                pix.loadFromData(data)
                
                # Make circular mask
                target = QPixmap(28, 28)
                target.fill(Qt.transparent)
                from PySide6.QtGui import QPainter, QPainterPath, QBrush
                painter = QPainter(target)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, 28, 28)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pix.scaled(28, 28, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                painter.end()
                
                avatar.setPixmap(target)
                avatar.setStyleSheet(f"border-radius: 14px; qproperty-alignment: AlignCenter; {border_style}")
                has_avatar = True
            except Exception:
                pass
                
        if not has_avatar:
            avatar.setStyleSheet(f"""
                border-radius: 14px;
                background-color: #8ab4f8;
                color: white;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
                {border_style}
            """)
            avatar.setText(name[0].upper() if name else "?")
        
        # Name
        self_prefix = " (You)" if user_id == session.user_id else ""
        name_lbl = QLabel(name + self_prefix, widget)
        name_lbl.setStyleSheet("color: #e8eaed; font-size: 13px;")
        
        # Mute icon
        mute_lbl = QLabel("❌" if is_muted else "🎤", widget)
        
        layout.addWidget(avatar)
        layout.addWidget(name_lbl)
        layout.addStretch()
        layout.addWidget(mute_lbl)
        
        item = QListWidgetItem()
        item.setSizeHint(QSize(230, 48))
        item.setData(Qt.UserRole, user_id)
        self.roster_list.addItem(item)
        self.roster_list.setItemWidget(item, widget)

    # --- Video & Audio Toggles ---
    def toggle_mic(self):
        if not room_service.voice_sender: return
        self.is_mic_muted = not self.is_mic_muted
        room_service.voice_sender.set_muted(self.is_mic_muted)
        if self.is_mic_muted:
            self.btn_mic_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "off1.png")))
            self.btn_mic_toggle.setObjectName("dangerControlButton")
            self.btn_mic_toggle.setToolTip("Unmute")
        else:
            self.btn_mic_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "microphone.png")))
            self.btn_mic_toggle.setObjectName("controlButton")
            self.btn_mic_toggle.setToolTip("Mute")
        self.btn_mic_toggle.style().unpolish(self.btn_mic_toggle)
        self.btn_mic_toggle.style().polish(self.btn_mic_toggle)
        
    def toggle_deafen(self):
        if not room_service.voice_receiver: return
        self.is_deafened = not self.is_deafened
        room_service.voice_receiver.set_deafened(self.is_deafened)
        if room_service.video_receiver:
            room_service.video_receiver.set_deafened(self.is_deafened)
        if self.is_deafened:
            self.btn_deafen_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "deaf.png")))
            self.btn_deafen_toggle.setObjectName("dangerControlButton")
            self.btn_deafen_toggle.setToolTip("Undeafen")
        else:
            self.btn_deafen_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "music.png")))
            self.btn_deafen_toggle.setObjectName("controlButton")
            self.btn_deafen_toggle.setToolTip("Deafen")
        self.btn_deafen_toggle.style().unpolish(self.btn_deafen_toggle)
        self.btn_deafen_toggle.style().polish(self.btn_deafen_toggle)
        
    def toggle_chat(self):
        is_visible = self.chat_container.isVisible()
        
        # If it's "visible" but dragged so thin it's essentially closed (<5% width)
        sizes = self.center_content_splitter.sizes()
        total = sum(sizes)
        if total > 0 and is_visible and len(sizes) > 1:
            chat_width = sizes[1]
            if (chat_width / total) < 0.05:
                is_visible = False
                
        self.chat_container.setVisible(not is_visible)
        
        if not is_visible:
            self.btn_chat_toggle.setStyleSheet("border-radius: 20px; background-color: rgba(138,180,248,0.25); border: 1px solid rgba(138,180,248,0.5);")
            self.center_content_splitter.setSizes([700, 300])
        else:
            self.btn_chat_toggle.setStyleSheet("border-radius: 20px; background-color: rgba(138,180,248,0.10); border: 1px solid rgba(138,180,248,0.25);")
        
    def toggle_camera(self):
        if not room_service.video_sender: return
        
        # Connect local callback if not yet hooked up
        if not room_service.video_sender.local_callback:
            room_service.video_sender.local_callback = lambda jpeg: self.local_frame_signal.emit(jpeg)
            
        self.is_camera_on = not self.is_camera_on
        room_service.video_sender.set_camera_enabled(self.is_camera_on)
        
        if self.is_camera_on:
            self.btn_camera_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "video.png")))
            self.btn_camera_toggle.setObjectName("iconButton") # Blue transparent state for camera on
            self.btn_camera_toggle.setStyleSheet("background-color: rgba(138,180,248,0.15); border-radius: 20px;")
            self.btn_camera_toggle.setToolTip("Camera Off")
            self.video_area.setVisible(True)
            
            # Eagerly show the local video feed with a loading spinner
            uid = session.user_id
            if uid not in self.video_labels:
                name = "You"
                feed_widget = VideoFeedWidget(name=name, parent=self)
                self.video_labels[uid] = feed_widget
                self._reflow_video_grid()
        else:
            self.btn_camera_toggle.setIcon(QIcon(os.path.join(self.icon_dir, "media.png")))
            self.btn_camera_toggle.setStyleSheet("")
            self.btn_camera_toggle.setObjectName("controlButton")
            self.btn_camera_toggle.setToolTip("Camera On")
            # Remove our own local frame if camera turned off
            if session.user_id in self.video_labels:
                lbl = self.video_labels.pop(session.user_id)
                self.video_layout.removeWidget(lbl)
                lbl.deleteLater()
                self._reflow_video_grid()
                
            # If no cameras left at all, hide video area and chat toggle
            if not self.video_labels:
                self.video_area.setVisible(False)
                self.chat_container.setVisible(True)
                
        self.btn_camera_toggle.style().unpolish(self.btn_camera_toggle)
        self.btn_camera_toggle.style().polish(self.btn_camera_toggle)

    @Slot(bytes)
    def _on_local_frame(self, jpeg_bytes):
        self.on_video_frame(session.user_id, jpeg_bytes)
        
    @Slot(str, bytes)
    def on_video_frame(self, user_id, jpeg_bytes):
        try:
            # Use Qt's native JPEG decoder — much faster than numpy + cv2
            pixmap = QPixmap()
            if not pixmap.loadFromData(jpeg_bytes, "JPEG"):
                return
            
            if user_id not in self.video_labels:
                name = self.members_cache.get(user_id, {}).get("name", "Unknown") if user_id != session.user_id else "You"
                feed_widget = VideoFeedWidget(name=name, parent=self)
                self.video_labels[user_id] = feed_widget
                
                # Switch to show video area and chat toggle button on first camera
                if len(self.video_labels) == 1:
                    self.video_area.setVisible(True)
                
                # Reflow the entire grid using optimal math layout
                self._reflow_video_grid()
                
            self.video_labels[user_id].setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Error rendering video: {e}")

    def _reflow_video_grid(self):
        """Rearranges all video labels into an optimal grid using ceil(sqrt(n)) columns.
        
        Math strategy:
          n=1  → 1×1    n=2  → 1×2    n=3  → 2×2 (1 empty)
          n=4  → 2×2    n=5  → 2×3    n=6  → 2×3
          n=7  → 3×3    n=8  → 3×3    n=9  → 3×3
        """
        import math
        
        # Remove all widgets from grid first
        while self.video_layout.count():
            item = self.video_layout.takeAt(0)
            # Don't delete widget, just remove from layout
        
        labels = list(self.video_labels.values())
        n = len(labels)
        if n == 0:
            return
            
        # Calculate optimal columns: ceil(sqrt(n))
        cols = math.ceil(math.sqrt(n))
        
        for i, lbl in enumerate(labels):
            row = i // cols
            col = i % cols
            self.video_layout.addWidget(lbl, row, col)

    def create_text_channel(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Create Text Channel", "Channel Name:")
        if ok and name.strip():
            clean_name = name.strip().lower()
            self.text_channels_list.addItem(f"💬 {clean_name}")
            if clean_name not in self.messages_cache:
                self.messages_cache[clean_name] = []
                
    def delete_text_channel(self):
        row = self.text_channels_list.currentRow()
        if row > 0: # prevent deleting "general"
            item = self.text_channels_list.takeItem(row)
            if item:
                del item
            self.text_channels_list.setCurrentRow(0)
            self.on_text_channel_clicked(self.text_channels_list.item(0))
            
    def create_voice_channel(self):
        from PySide6.QtWidgets import QInputDialog, QTreeWidgetItem
        name, ok = QInputDialog.getText(self, "Create Voice Channel", "Channel Name:")
        if ok and name.strip():
            item = QTreeWidgetItem(self.voice_channels_tree, [f"🔊 {name.strip()}"])
            self.voice_channels_tree.addTopLevelItem(item)
            item.setExpanded(True)
            
    def delete_voice_channel(self):
        item = self.voice_channels_tree.currentItem()
        if item and not item.parent(): # Is top level channel
            if item.text(0) != "🔊 General VC":
                index = self.voice_channels_tree.indexOfTopLevelItem(item)
                self.voice_channels_tree.takeTopLevelItem(index)
            
    def on_text_channel_clicked(self, item):
        self.current_text_channel = item.text().replace("💬 ", "")
        # Keep the room name visible alongside the channel name
        room = room_service.current_room
        room_name = room.get("name", "") if room else ""
        suffix = f"  —  {room_name}" if room_name else ""
        self.room_title.setText(f"💬 {self.current_text_channel}{suffix}")
        
        # Show PiP and hide video area if in VC
        if room_service.voice_sender:
            self.pip.show()
            self.pip.snap_to_corner()
            self.video_area.setVisible(False)
            self.chat_container.setVisible(True)
            
        self.redraw_chat_display()
        
    def return_to_vc_screen(self):
        if self.current_voice_channel:
            self.room_title.setText(f"🔊 {self.current_voice_channel}")
            self.chat_container.setVisible(False)
            self.video_area.setVisible(True)
            
            self.voice_channels_tree.clearSelection()
            for i in range(self.voice_channels_tree.topLevelItemCount()):
                item = self.voice_channels_tree.topLevelItem(i)
                if item.text(0).replace("🔊 ", "") == self.current_voice_channel:
                    item.setSelected(True)
                    break

    def on_voice_channel_clicked(self, item, column=0):
        # Prevent clicking on users to trigger channel join
        if item.parent() is not None:
            return
            
        self.pip.hide()
        if self.video_labels:
            self.video_area.setVisible(True)
            if not self.chat_container.isVisible():
                pass # keep chat hidden if it was hidden
            
        self.current_voice_channel = item.text(0).replace("🔊 ", "")
        room_service.run_coro(room_service.client_node.join_channel("voice", self.current_voice_channel))
        
        self.voice_controls_box.setVisible(True)
        self.audio_status_lbl.setText(f"🔊 Connected: {self.current_voice_channel}")
        
        # We start audio + video sender/receiver only when a channel is clicked
        if not room_service.voice_sender:
            def handle_speaking_changed(is_speaking):
                room_service.run_coro(room_service.client_node.send_speaking_state(is_speaking))
                self.local_speaking_signal.emit(is_speaking)
            from voice.sender import VoiceSender
            from voice.receiver import VoiceReceiver
            from video.video_sender import VideoSender
            from video.video_receiver import VideoReceiver
            from utils.constants import DEFAULT_VIDEO_PORT
            room = room_service.current_room
            if room:
                # Start voice
                room_service.voice_sender = VoiceSender(room["host_ip"], room["voice_port"], on_speaking_changed=handle_speaking_changed)
                room_service.voice_sender.start()
                room_service.voice_receiver = VoiceReceiver(room["host_ip"], room["voice_port"], room_service.mixer)
                room_service.voice_receiver.start()
                
                # Start video
                room_service.video_sender = VideoSender(room["host_ip"], DEFAULT_VIDEO_PORT)
                room_service.video_sender.start()
                room_service.video_receiver = VideoReceiver(room["host_ip"], DEFAULT_VIDEO_PORT)
                room_service.video_receiver.start()
                room_service.video_receiver.signals.frame_received.connect(self.on_video_frame)
        
    def redraw_chat_display(self):
        self.clear_chat()
        messages = self.messages_cache.get(self.current_text_channel, [])
        for msg in messages:
            self._append_message_to_display(msg)

    def clear_chat(self):
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                row = child.layout()
                while row.count():
                    item = row.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                row.deleteLater()



    # --- Chat Handlers ---
    def send_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
            
        now = datetime.datetime.now().strftime("%H:%M")
        
        # Send via Client asyncio node
        room_service.run_coro(room_service.client_node.send_chat_message(text, now, self.current_text_channel))
        self.chat_input.clear()
        
    def send_image_in_chat(self):
        """Allows user to select an image, resizes it, and sends it inline as base64 via chat."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image to Send", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)")
        if not file_path:
            return
            
        try:
            # Load and resize image to prevent gigantic packet payload
            img = cv2.imread(file_path)
            if img is None:
                InfoBar.warning(title="Error", content="Failed to load image file.", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)
                return
                
            # Resize if too big (max 800px on longest side)
            h, w = img.shape[:2]
            max_dim = 800
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
                
            # Encode to JPEG with compression
            ret, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if not ret:
                InfoBar.warning(title="Error", content="Failed to compress image.", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)
                return
                
            import base64
            b64_str = base64.b64encode(buf).decode('utf-8')
            
            # Formulate the special image payload
            msg_text = f"[IMAGE:{b64_str}]"
            now = datetime.datetime.now().strftime("%H:%M")
            room_service.run_coro(room_service.client_node.send_chat_message(msg_text, now, self.current_text_channel))
            
        except Exception as e:
            logger.error(f"Failed to send image inline: {e}")
            InfoBar.error(title="Error", content=f"Failed to send image: {e}", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)

    @Slot(dict)
    def on_chat_received(self, msg):
        channel = msg.get("channel", "general")
        if channel not in self.messages_cache:
            self.messages_cache[channel] = []
        self.messages_cache[channel].append(msg)
        
        if channel == self.current_text_channel:
            self._append_message_to_display(msg)
            
        if (not self.chat_container.isVisible() or channel != self.current_text_channel) and not msg.get("is_system"):
            sender = msg.get("sender_name", "Unknown")
            InfoBar.info(
                title=f"New message in {channel}",
                content=f"From {sender}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            
    def _append_message_to_display(self, msg):
        sender = html.escape(msg.get("sender_name", "Unknown"))
        content = html.escape(msg.get("content", ""))
        time_str = html.escape(msg.get("timestamp", ""))
        
        bubble = QWidget()
        bubble_layout = QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 4, 12, 4)
        bubble_layout.setSpacing(12)
        
        is_own = msg.get("sender_id") == session.user_id or msg.get("sender_name") == session.display_name
        
        if msg.get("is_system"):
            text_color = "#ea4335" if msg.get("is_leave") else "#81c995"
            content_html = f"<span style='color: {text_color}; font-style: italic; font-weight: bold;'>{content}</span>"
            msg_lbl = QLabel(content_html)
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet("background: transparent;")
            bubble_layout.addWidget(msg_lbl)
        else:
            pfp_lbl = QLabel(sender[0].upper() if sender else "?", self)
            pfp_lbl.setFixedSize(40, 40)
            pfp_lbl.setAlignment(Qt.AlignCenter)
            pfp_lbl.setStyleSheet("background-color: rgba(138,180,248,0.15); border-radius: 20px; font-weight: bold; font-size: 16px; color: #e8eaed;")
            bubble_layout.addWidget(pfp_lbl, 0, Qt.AlignTop)
            
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(2)
            
            name_time_html = f"<span style='color: #e8eaed; font-weight: 800; font-size: 14px;'>{sender}</span> &nbsp;&nbsp;<span style='color: #5f6368; font-weight: 600; font-size: 10px;'>{time_str}</span>"
            name_time_lbl = QLabel(name_time_html)
            
            if content.startswith("[IMAGE:") and content.endswith("]"):
                b64_data = content[7:-1]
                content = f"<br><img src='data:image/jpeg;base64,{b64_data}' style='max-width:300px; max-height:300px;'><br>"
            
            msg_lbl = QLabel(f"<span style='color: #e8eaed; font-size: 13px;'>{content}</span>")
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet("background: transparent;")
            
            right_layout.addWidget(name_time_lbl)
            right_layout.addWidget(msg_lbl)
            bubble_layout.addWidget(right_widget)
            
        # Hover effect
        bubble.setStyleSheet("QWidget:hover { background-color: rgba(255,255,255,0.03); }")
            
        self.chat_layout.addWidget(bubble)
        
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum()))

    # --- Roster Updates ---
    @Slot(dict)
    def on_user_joined(self, user_info):
        msg = {
            "channel": self.current_text_channel,
            "sender_name": "System",
            "content": f"» {user_info['display_name']} has joined the room.",
            "timestamp": datetime.datetime.now().strftime("%H:%M"),
            "is_system": True
        }
        self.on_chat_received(msg)
        
        # Update local cache instead of blocking DB call
        self.members_cache[user_info["id"]] = {
            "display_name": user_info["display_name"],
            "avatar_url": user_info.get("avatar_url"),
            "bio": user_info.get("bio", ""),
            "links": user_info.get("links", ""),
            "muted": False,
            "is_speaking": False,
            "voice_channel": user_info.get("voice_channel", None)
        }
        if user_info["id"] not in self.fifo_users:
            self.fifo_users.append(user_info["id"])
        self._update_owner_label()
        self._redraw_roster()
        self._redraw_voice_channels()

    @Slot(str)
    def on_user_left(self, user_id):
        name = "Someone"
        if user_id in self.members_cache:
            name = self.members_cache[user_id]["display_name"]
            del self.members_cache[user_id]
            
        msg = {
            "channel": self.current_text_channel,
            "sender_name": "System",
            "content": f"« {name} has left the room.",
            "timestamp": datetime.datetime.now().strftime("%H:%M"),
            "is_system": True,
            "is_leave": True
        }
        self.on_chat_received(msg)
        if user_id in self.fifo_users:
            self.fifo_users.remove(user_id)
        self._update_owner_label()
        self._redraw_roster()
        self._redraw_voice_channels()
        
        # 1. Close/Reject any active file offer prompts from this user
        for file_id, packet in list(self.pending_offers.items()):
            if packet["sender_id"] == user_id:
                if file_id in self.active_offer_dialogs:
                    logger.info(f"Closing file offer dialog for {packet['file_name']} because sender left.")
                    self.active_offer_dialogs[file_id].reject()
                if file_id in self.pending_offers:
                    del self.pending_offers[file_id]
        
        # 2. Clean up voice decoders
        if room_service.voice_receiver:
            room_service.voice_receiver.remove_decoder(user_id)
        room_service.mixer.remove_speaker(user_id)

    @Slot(dict)
    def on_voice_channel_updated(self, packet):
        user_id = packet.get("user_id")
        channel = packet.get("channel_name")
        if user_id in self.members_cache:
            self.members_cache[user_id]["voice_channel"] = channel
            self._redraw_voice_channels()

    # --- Voice Handlers ---
    def on_mute_toggled(self, state):
        muted = (state == Qt.Checked.value)
        if room_service.voice_sender:
            room_service.voice_sender.set_muted(muted)
            
        # Broadcast mute state to other participants
        room_service.run_coro(room_service.client_node.send_voice_state(muted))
        
        # Update local roster state
        self.update_roster_mute(session.user_id, muted)

    @Slot(dict)
    def on_voice_state_changed(self, packet):
        uid = packet["user_id"]
        muted = packet["muted"]
        self.update_roster_mute(uid, muted)

    def update_roster_mute(self, user_id, is_muted):
        if user_id in self.members_cache:
            self.members_cache[user_id]["muted"] = is_muted
        self._redraw_roster()

    @Slot(list)
    def on_members_list(self, members):
        """Populates members cache with full details from the host server."""
        for user_info in members:
            self.members_cache[user_info["id"]] = {
                "display_name": user_info["display_name"],
                "avatar_url": user_info.get("avatar_url"),
                "bio": user_info.get("bio", ""),
                "links": user_info.get("links", ""),
                "muted": False,
                "is_speaking": False,
                "voice_channel": user_info.get("voice_channel", None)
            }
            if user_info["id"] not in self.fifo_users:
                self.fifo_users.append(user_info["id"])
        self._update_owner_label()
        self._redraw_roster()
        
    def _update_owner_label(self):
        if self.fifo_users:
            owner_id = self.fifo_users[0]
            # Since this could be us, check session if not in cache
            if owner_id == session.user_id:
                owner_name = session.display_name
            else:
                owner_info = self.members_cache.get(owner_id, {})
                owner_name = owner_info.get("display_name", "Unknown")
            self.owner_label.setText(f"OWNER : {owner_name}")
        else:
            self.owner_label.setText("OWNER : Unknown")

    def on_roster_double_clicked(self, item):
        user_id = item.data(Qt.UserRole)
        if user_id:
            self.open_profile(user_id)
            
    def open_profile(self, user_id):
        from gui.profile_window import ProfileDialog
        
        # Determine if viewing self or another user
        is_self = (user_id == session.user_id)
        if is_self:
            user_info = {
                "display_name": session.display_name,
                "avatar_url": session.avatar_url,
                "bio": session.bio,
                "links": session.links
            }
        else:
            user_info = self.members_cache.get(user_id)
            
        if user_info:
            dialog = ProfileDialog(user_id, user_info, is_self, self)
            if dialog.exec():
                # If they edited their own profile and saved
                if is_self:
                    self._redraw_roster()

    @Slot(dict)
    def on_speaking_state_changed(self, packet):
        uid = packet["user_id"]
        is_speaking = packet["is_speaking"]
        if uid in self.members_cache:
            self.members_cache[uid]["is_speaking"] = is_speaking
        self._redraw_roster()

    # --- File Sharing Implementation ---
    def send_file_to_room(self):
        self.initiate_file_transfer(recipient_id=None)

    def send_file_to_user(self):
        current_item = self.roster_list.currentItem()
        if not current_item:
            InfoBar.warning(title="Selection Error", content="Please select a member from the roster list first.", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)
            return
            
        uid = current_item.data(Qt.UserRole)
        if uid == session.user_id:
            InfoBar.warning(title="Selection Error", content="You cannot send a file to yourself.", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)
            return
            
        self.initiate_file_transfer(recipient_id=uid)

    def initiate_file_transfer(self, recipient_id=None):
        """Prompts user to pick a file, and broadcasts the offer via client TCP node."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Share")
        if not filepath:
            return
            
        path = Path(filepath)
        filename = path.name
        file_size = path.stat().st_size
        file_id = str(uuid.uuid4())
        
        # Cache file path locally so we can stream it if accepted
        self.outgoing_files[file_id] = filepath
        
        logger.info(f"Offering file {filename} ({file_size} bytes)")
        
        # Broadcast/Unicast offer signal
        room_service.run_coro(
            room_service.client_node.send_file_offer(file_id, filename, file_size, recipient_id)
        )
        
        # Add a progress bar in GUI in "Waiting..." status
        self.add_active_transfer(file_id, filename, "Offering file... (Expires in 60s)")
        
        # Start a 60-second countdown timer for this offer
        timer = QTimer(self)
        timer.setInterval(1000)
        remaining = 60
        
        def update_countdown():
            nonlocal remaining
            remaining -= 1
            if remaining <= 0:
                timer.stop()
                self.expire_file_offer(file_id, recipient_id)
            else:
                self.update_transfer_status(file_id, f"Offering file... (Expires in {remaining}s)")
                
        timer.timeout.connect(update_countdown)
        timer.start()
        self.offer_timers[file_id] = (timer, remaining)

    @Slot(dict)
    def on_file_accepted(self, packet):
        """Triggered on the sender's client. Starts uploading the file."""
        file_id = packet["file_id"]
        if file_id not in self.outgoing_files:
            return
            
        # Cancel the 60-second offer countdown timer since it was accepted
        if file_id in self.offer_timers:
            timer, _ = self.offer_timers[file_id]
            timer.stop()
            del self.offer_timers[file_id]
            
        filepath = self.outgoing_files[file_id]
        filename = Path(filepath).name
        
        # Update progress bar title
        self.update_transfer_status(file_id, "Uploading...")
        
        # Run upload stream coroutine on the background event loop
        host = room_service.current_room["host_ip"]
        port = room_service.current_room["file_port"]
        
        # We need a progress hook that emits thread-safe signals to Qt
        def progress_hook(sent, total):
            transfer_signals.progress.emit(file_id, sent, total)
            
        async def upload_task():
            success = await stream_file_to_host(host, port, file_id, filepath, progress_hook)
            msg = "Transfer complete!" if success else "Transfer failed."
            transfer_signals.finished.emit(file_id, success, msg)
            
        room_service.run_coro(upload_task())

    @Slot(dict)
    def on_file_declined(self, packet):
        """Triggered on sender's client. Removes active transfer UI."""
        file_id = packet["file_id"]
        
        # Cancel the 60-second offer countdown timer since it was declined
        if file_id in self.offer_timers:
            timer, _ = self.offer_timers[file_id]
            timer.stop()
            del self.offer_timers[file_id]
            
        if file_id in self.active_transfers:
            self.remove_transfer(file_id)
            InfoBar.info(title="File Declined", content="The recipient declined your file transfer.", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)

    # --- File Transfer Progress Callbacks (Qt Slots) ---
    @Slot(str, int, int)
    def on_transfer_progress(self, file_id, current, total):
        if file_id in self.active_transfers:
            _, bar, label = self.active_transfers[file_id]
            bar.setMaximum(total)
            bar.setValue(current)
            
            # Update label
            pct = int((current / total) * 100) if total > 0 else 0
            label.setText(f"{self.format_bytes(current)} / {self.format_bytes(total)} ({pct}%)")

    @Slot(str, bool, str)
    def on_transfer_finished(self, file_id, success, msg):
        # If recipient finished, make sure we run downloader
        if file_id in self.incoming_files and file_id not in self.active_transfers:
            # Wait, this means we received the accept trigger, now start download!
            pass
            
        # Check if this is the downloader side starting
        if file_id in self.incoming_files and not success and msg == "Accepting...":
            # This is not a failure, but our signal to start downloading!
            # Trigger downloader stream in background
            save_path = self.incoming_files[file_id]
            filename = Path(save_path).name
            
            self.update_transfer_status(file_id, "Downloading...")
            
            host = room_service.current_room["host_ip"]
            port = room_service.current_room["file_port"]
            total_size = 0
            
            # Since downloader needs total size, we should query/extract it
            # (or we stored it somewhere, or the downloader reads until EOF).
            # Wait! The downloader needs total size. How do we pass it?
            # We can cache it when the file offer is received!
            # Let's save it. Let's make sure we have cached sizes.
            # We will implement this details.
            
        if file_id in self.active_transfers:
            _, bar, label = self.active_transfers[file_id]
            if success:
                label.setText("Finished! Check downloads.")
                bar.setValue(bar.maximum())
            else:
                label.setText(f"Failed: {msg}")
                bar.setValue(0)
                
            # Auto remove after 5 seconds
            QTimer.singleShot(5000, lambda: self.remove_transfer(file_id))

    @Slot(dict)
    def on_file_offer(self, packet):
        """Displays Accept/Decline prompt to the receiving peer using a non-blocking dialog."""
        file_id = packet.get("file_id")
        filename = os.path.basename(packet.get("file_name", "unknown"))
        file_size = packet.get("file_size", 0)
        sender_name = packet.get("sender_name", "Unknown")
        sender_id = packet.get("sender_id")
        
        # Cache the pending offer details
        self.pending_offers[file_id] = packet
        
        # Create a non-blocking dialog box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Incoming File")
        msg_box.setText(f"User '{sender_name}' wants to share a file with you:\n\nName: {filename}\nSize: {self.format_bytes(file_size)}\n\nDo you want to accept this transfer?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        def handle_response(result):
            # Remove dialog from cache
            if file_id in self.active_offer_dialogs:
                del self.active_offer_dialogs[file_id]
                
            if result == QMessageBox.Yes:
                default_dir = get_setting("download_directory", str(Path.home() / "Downloads"))
                save_path, _ = QFileDialog.getSaveFileName(self, "Save File As", str(Path(default_dir) / filename))
                
                if save_path:
                    self.incoming_files[file_id] = save_path
                    self.add_active_transfer(file_id, filename, "Downloading...")
                    
                    # Start downloader thread in background immediately
                    host = room_service.current_room["host_ip"]
                    port = room_service.current_room["file_port"]
                    
                    def progress_hook(received, total):
                        transfer_signals.progress.emit(file_id, received, total)
                        
                    async def download_task():
                        success = await stream_file_from_host(host, port, file_id, save_path, file_size, progress_hook)
                        msg = "Download finished!" if success else "Download failed."
                        transfer_signals.finished.emit(file_id, success, msg)
                        
                    room_service.run_coro(download_task())
                    
                    # Send accept packet to notify the sender to upload
                    room_service.run_coro(room_service.client_node.send_file_accept(file_id, sender_id))
                else:
                    room_service.run_coro(room_service.client_node.send_file_decline(file_id, sender_id))
            else:
                # Declined
                room_service.run_coro(room_service.client_node.send_file_decline(file_id, sender_id))
                
        msg_box.finished.connect(handle_response)
        msg_box.show()
        self.active_offer_dialogs[file_id] = msg_box

    @Slot(dict)
    def on_file_expired(self, packet):
        """Triggered on the recipient's client when a file offer times out/expires."""
        file_id = packet["file_id"]
        
        # 1. Reject and close the non-blocking dialogue box if it's currently open
        if file_id in self.active_offer_dialogs:
            logger.info(f"Closing file offer dialog for expired File {file_id}")
            self.active_offer_dialogs[file_id].reject()
            
        # 2. Append expiration notice to chat display
        if file_id in self.pending_offers:
            offered = self.pending_offers[file_id]
            filename = offered["file_name"]
            sender = offered["sender_name"]
            
            msg = {
                "channel": self.current_text_channel,
                "sender_name": "System",
                "content": f"» File offer '{filename}' from {sender} has expired (60s timeout).",
                "timestamp": datetime.datetime.now().strftime("%H:%M"),
                "is_system": True
            }
            self.on_chat_received(msg)
            del self.pending_offers[file_id]

    def expire_file_offer(self, file_id: str, recipient_id: str = None):
        """Called on the sender's client when the 60-second timer runs out without acceptance."""
        if file_id in self.offer_timers:
            timer, _ = self.offer_timers[file_id]
            timer.stop()
            del self.offer_timers[file_id]
            
        # Update progress bar status
        self.update_transfer_status(file_id, "Failed: Offer expired (60s).")
        
        # Broadcast/Unicast file expiration packet to clear prompts on recipient side
        room_service.run_coro(
            room_service.client_node.send_file_expire(file_id, recipient_id)
        )
        
        # Auto-remove the transfer widget after 5 seconds
        QTimer.singleShot(5000, lambda: self.remove_transfer(file_id))

    # --- UI Helpers for progress bar ---
    def add_active_transfer(self, file_id, filename, initial_status):
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        name_lbl = QLabel(f"📄 {filename}", widget)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 11px; color: #e8eaed;")
        
        bar = QProgressBar(widget)
        bar.setFixedHeight(12)
        bar.setValue(0)
        
        status_lbl = QLabel(initial_status, widget)
        status_lbl.setStyleSheet("font-size: 10px; color: #9aa0a6;")
        
        layout.addWidget(name_lbl)
        layout.addWidget(bar)
        layout.addWidget(status_lbl)
        
        self.transfers_layout.addWidget(widget)
        self.active_transfers[file_id] = (widget, bar, status_lbl)

    def update_transfer_status(self, file_id, status):
        if file_id in self.active_transfers:
            _, _, label = self.active_transfers[file_id]
            label.setText(status)

    def remove_transfer(self, file_id):
        if file_id in self.active_transfers:
            widget, _, _ = self.active_transfers[file_id]
            widget.deleteLater()
            del self.active_transfers[file_id]

    # --- Helper methods ---
    @staticmethod
    def format_bytes(n):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    # --- Room Shutdown / Departure ---
    @Slot(str)
    def on_room_shutdown(self, msg):
        InfoBar.warning(title="Room Closed", content=f"The host has closed the room.\n{msg}", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self)
        self.leave_room()
        
    @Slot(str)
    def on_disconnected(self, msg):
        # Trigger P2P host migration instead of just leaving
        logger.warning("Lost connection to host TCP server. Initiating Host Migration...")
        # Show a transient loading overlay if possible, or just let room_service handle it
        room_service.handle_host_migration()

    def leave_room(self):
        """Cleans up the room connection and switches views back to lobby."""
        # Cancel any active countdown timers
        for file_id, (timer, _) in list(self.offer_timers.items()):
            timer.stop()
        self.offer_timers.clear()
        
        # Close any active offer dialogs
        for file_id, dialog in list(self.active_offer_dialogs.items()):
            dialog.reject()
        self.active_offer_dialogs.clear()
        
        room_service.leave_room()
        self.on_leave()
