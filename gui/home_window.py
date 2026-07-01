from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QMessageBox, QDialog, QStackedWidget,
                               QFrame)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from qfluentwidgets import SmoothScrollArea, PrimaryPushButton, PushButton, LineEdit

from auth.session import session
from database.rooms import list_active_rooms
from gui.create_room import CreateRoomDialog
from services.room_service import room_service
from utils.logger import logger


def _circular_pixmap(source, size: int) -> QPixmap | None:
    """Return a circular-cropped QPixmap from a file path or base64 data URI."""
    pix = QPixmap()
    if isinstance(source, str) and source.startswith("data:image"):
        try:
            import base64
            _, enc = source.split(",", 1)
            pix.loadFromData(base64.b64decode(enc))
        except Exception:
            return None
    elif isinstance(source, str):
        pix = QPixmap(source)
    else:
        return None
    if pix.isNull():
        return None
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
    p.end()
    return out


class _AvatarLabel(QLabel):
    """A circular avatar that shows a photo or a coloured initial."""
    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)

    def set_user(self, name: str, avatar_url: str = ""):
        if avatar_url and (avatar_url.startswith("data:image") or avatar_url.startswith("http")):
            pix = _circular_pixmap(avatar_url, self._size)
            if pix:
                self.setPixmap(pix)
                self.setStyleSheet(f"border-radius: {self._size // 2}px;")
                return
        # Fallback — coloured initial
        initial = (name or "?")[0].upper()
        self.setText(initial)
        self.setStyleSheet(
            f"background-color: rgba(91,138,240,0.18); "
            f"border-radius: {self._size // 2}px; "
            f"font-weight: 700; font-size: {self._size // 2}px; color: #5b8af0;"
        )


class HomePage(QWidget):
    def __init__(self, on_logout, on_enter_room, parent=None):
        super().__init__(parent)
        self.on_logout = on_logout
        self.on_enter_room = on_enter_room
        self.selected_room_id = None
        self.active_rooms_cache = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header bar ─────────────────────────────────────────────
        header = QWidget(self)
        header.setObjectName("homeHeader")
        header.setFixedHeight(64)
        header.setStyleSheet("""
            QWidget#homeHeader {
                background-color: rgba(24,27,36,0.95);
                border-bottom: 1px solid rgba(255,255,255,0.06);
            }
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)
        h_lay.setSpacing(12)

        logo_lbl = QLabel("TailChat", header)
        logo_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #ffffff; "
            "letter-spacing: -0.3px; background: transparent;"
        )
        h_lay.addWidget(logo_lbl)

        dot = QLabel("•", header)
        dot.setStyleSheet("color: #3a3f52; font-size: 14px; background: transparent;")
        h_lay.addWidget(dot)

        self.header_status = QLabel("Lobby", header)
        self.header_status.setStyleSheet("font-size: 14px; color: #6b7489; background: transparent;")
        h_lay.addWidget(self.header_status)

        h_lay.addStretch()

        # Header avatar
        self.header_avatar = _AvatarLabel(32, header)
        h_lay.addWidget(self.header_avatar)

        self.header_name = QLabel("", header)
        self.header_name.setStyleSheet("font-size: 13px; font-weight: 600; color: #e8ecf4; background: transparent;")
        h_lay.addWidget(self.header_name)

        root.addWidget(header)

        # ── Main area ──────────────────────────────────────────────────
        main_area = QWidget(self)
        main_lay = QHBoxLayout(main_area)
        main_lay.setContentsMargins(24, 24, 24, 24)
        main_lay.setSpacing(18)
        root.addWidget(main_area, stretch=1)

        # ── LEFT: Room list ────────────────────────────────────────────
        rooms_col = QWidget(main_area)
        rooms_col.setObjectName("roomsPanel")
        rooms_col.setStyleSheet("""
            QWidget#roomsPanel {
                background-color: rgba(24,27,36,0.60);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 18px;
            }
        """)
        rooms_lay = QVBoxLayout(rooms_col)
        rooms_lay.setContentsMargins(20, 20, 20, 20)
        rooms_lay.setSpacing(12)

        # Header row
        rooms_hdr = QHBoxLayout()
        rooms_title = QLabel("Active Rooms", rooms_col)
        rooms_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #e8ecf4; background: transparent;"
        )
        rooms_hdr.addWidget(rooms_title)
        rooms_hdr.addStretch()

        self.refresh_btn = QPushButton("⟳", rooms_col)
        self.refresh_btn.setObjectName("iconButton")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setToolTip("Refresh rooms")
        self.refresh_btn.clicked.connect(self._refresh_clicked)
        rooms_hdr.addWidget(self.refresh_btn)
        rooms_lay.addLayout(rooms_hdr)

        # Search
        self.search_input = LineEdit(rooms_col)
        self.search_input.setPlaceholderText("🔍  Search rooms…")
        self.search_input.textChanged.connect(self.filter_rooms)
        rooms_lay.addWidget(self.search_input)

        # Scroll area for cards
        self.room_scroll = SmoothScrollArea(rooms_col)
        self.room_scroll.setWidgetResizable(True)
        self.room_scroll.setStyleSheet("background: transparent; border: none;")
        self.room_content = QWidget()
        self.room_content.setStyleSheet("background: transparent;")
        self.room_layout = QVBoxLayout(self.room_content)
        self.room_layout.setAlignment(Qt.AlignTop)
        self.room_layout.setContentsMargins(0, 0, 4, 0)
        self.room_layout.setSpacing(8)
        self.room_scroll.setWidget(self.room_content)
        rooms_lay.addWidget(self.room_scroll, stretch=1)

        # Footer
        sep = QFrame(rooms_col)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.06); max-height: 1px; border: none;")
        rooms_lay.addWidget(sep)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.host_room_btn = QPushButton("＋  Host a Room", rooms_col)
        self.host_room_btn.setMinimumHeight(42)
        self.host_room_btn.clicked.connect(self.host_room)
        footer.addWidget(self.host_room_btn)

        self.join_room_btn = QPushButton("→  Join Selected", rooms_col)
        self.join_room_btn.setObjectName("secondaryButton")
        self.join_room_btn.setMinimumHeight(42)
        self.join_room_btn.clicked.connect(self.join_selected_room)
        footer.addWidget(self.join_room_btn)
        rooms_lay.addLayout(footer)

        main_lay.addWidget(rooms_col, stretch=3)

        # ── RIGHT: Peers panel ─────────────────────────────────────────
        peers_col = QWidget(main_area)
        peers_col.setObjectName("peersPanel")
        peers_col.setStyleSheet("""
            QWidget#peersPanel {
                background-color: rgba(24,27,36,0.60);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 18px;
            }
        """)
        peers_col.setFixedWidth(240)
        peers_lay = QVBoxLayout(peers_col)
        peers_lay.setContentsMargins(16, 20, 16, 20)
        peers_lay.setSpacing(10)

        peers_title = QLabel("Online Peers", peers_col)
        peers_title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #e8ecf4; background: transparent;"
        )
        peers_lay.addWidget(peers_title)

        sep2 = QFrame(peers_col)
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: rgba(255,255,255,0.06); max-height: 1px; border: none;")
        peers_lay.addWidget(sep2)

        self.peers_scroll = SmoothScrollArea(peers_col)
        self.peers_scroll.setWidgetResizable(True)
        self.peers_scroll.setStyleSheet("background: transparent; border: none;")
        self.peers_content = QWidget()
        self.peers_content.setStyleSheet("background: transparent;")
        self.peers_layout = QVBoxLayout(self.peers_content)
        self.peers_layout.setAlignment(Qt.AlignTop)
        self.peers_layout.setContentsMargins(0, 0, 0, 0)
        self.peers_layout.setSpacing(4)
        self.peers_scroll.setWidget(self.peers_content)
        peers_lay.addWidget(self.peers_scroll, stretch=1)
        main_lay.addWidget(peers_col)

        # ── Loading overlay ────────────────────────────────────────────
        self.content_stack = QStackedWidget(self)
        main_area_widget = main_area

        loading_widget = QWidget(self)
        loading_lay = QVBoxLayout(loading_widget)
        loading_lay.setAlignment(Qt.AlignCenter)
        self.loading_icon = QLabel("⠋", loading_widget)
        self.loading_icon.setStyleSheet(
            "font-size: 52px; color: #5b8af0; background: transparent;"
        )
        self.loading_icon.setAlignment(Qt.AlignCenter)
        loading_lay.addWidget(self.loading_icon)
        self.loading_text = QLabel("Connecting…", loading_widget)
        self.loading_text.setStyleSheet(
            "font-size: 16px; color: #6b7489; margin-top: 16px; background: transparent;"
        )
        self.loading_text.setAlignment(Qt.AlignCenter)
        loading_lay.addWidget(self.loading_text)

        # Use a proper stacked layout
        from PySide6.QtWidgets import QStackedLayout
        self._stack = QStackedWidget(self)
        self._stack.addWidget(main_area)       # 0 — lobby
        self._stack.addWidget(loading_widget)  # 1 — loading
        root.addWidget(self._stack, stretch=1)
        root.removeWidget(main_area)  # already owned by stack

        # Timers
        self._spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self._spinner_idx = 0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_anim)

        room_service.signals.room_joined.connect(self.on_room_joined)
        room_service.signals.error_occurred.connect(self.on_room_error)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_rooms)
        self.refresh_timer.start(10_000)

        self.refresh_rooms()
        self._update_header()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _tick_anim(self):
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
        self.loading_icon.setText(self._spinner_frames[self._spinner_idx])

    def _update_header(self):
        name = session.display_name or "Guest"
        self.header_name.setText(name)
        self.header_avatar.set_user(name, session.avatar_url or "")

    # ── Room list ───────────────────────────────────────────────────────────────

    def filter_rooms(self, q: str = ""):
        self._clear(self.room_layout)
        self.selected_room_id = None
        q = q.lower()
        shown = 0
        for r in self.active_rooms_cache:
            host_info = r.get("users") or {}
            host_name = host_info.get("display_name", "")
            if q and q not in r["name"].lower() and q not in host_name.lower():
                continue
            self._add_room_card(r)
            shown += 1
        if shown == 0:
            lbl = QLabel("No active rooms.\nHost one to get started! 🚀", self.room_content)
            lbl.setStyleSheet("color: #4a5168; font-size: 14px; background: transparent;")
            lbl.setAlignment(Qt.AlignCenter)
            self.room_layout.addWidget(lbl)

    def _refresh_clicked(self):
        self.refresh_btn.setEnabled(False)
        QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self):
        self.refresh_rooms()
        self.refresh_btn.setEnabled(True)

    def refresh_rooms(self):
        self.active_rooms_cache = list_active_rooms()
        self.filter_rooms(self.search_input.text())
        self.refresh_users()
        self._update_header()

    def _add_room_card(self, room):
        host_info = room.get("users") or {}
        host_name = host_info.get("display_name", "Unknown")
        host_avatar = host_info.get("avatar_url", "")
        room_name = room["name"]
        is_private = bool(room.get("password"))
        is_mine = (room.get("host_id") == session.user_id)
        members = room.get("room_members", [])
        member_count = len(members) if isinstance(members, list) else 0

        card = QWidget(self.room_content)
        card.setObjectName("roomCard")
        card.setCursor(Qt.PointingHandCursor)
        _NORMAL = """
            QWidget#roomCard {
                background-color: rgba(30,33,48,0.70);
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 14px;
            }
            QWidget#roomCard:hover {
                background-color: rgba(91,138,240,0.08);
                border: 1px solid rgba(91,138,240,0.28);
            }
        """
        _SELECTED = """
            QWidget#roomCard {
                background-color: rgba(91,138,240,0.14);
                border: 1px solid rgba(91,138,240,0.50);
                border-radius: 14px;
                border-left: 3px solid #5b8af0;
            }
        """
        card.setStyleSheet(_NORMAL)

        cl = QHBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(14)

        # Lock / house icon
        icon_lbl = QLabel("🔒" if is_private else "🏠", card)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        cl.addWidget(icon_lbl)

        # Info
        info = QVBoxLayout()
        info.setSpacing(3)
        name_lbl = QLabel(room_name, card)
        name_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #e8ecf4; background: transparent;"
        )
        host_lbl = QLabel(f"Host: {host_name}  ·  {room.get('host_ip','')}", card)
        host_lbl.setStyleSheet("font-size: 12px; color: #4a5168; background: transparent;")
        info.addWidget(name_lbl)
        info.addWidget(host_lbl)
        cl.addLayout(info)
        cl.addStretch()

        # Badges row
        badges = QHBoxLayout()
        badges.setSpacing(6)
        if member_count > 0:
            b = QLabel(f"👥 {member_count}", card)
            b.setStyleSheet("""
                background: rgba(91,138,240,0.12);
                border: 1px solid rgba(91,138,240,0.28);
                border-radius: 8px; padding: 2px 8px;
                font-size: 12px; font-weight: 600; color: #5b8af0;
            """)
            badges.addWidget(b)
        if is_mine:
            b2 = QLabel("★ You", card)
            b2.setStyleSheet("""
                background: rgba(74,222,128,0.12);
                border: 1px solid rgba(74,222,128,0.28);
                border-radius: 8px; padding: 2px 8px;
                font-size: 12px; font-weight: 600; color: #4ade80;
            """)
            badges.addWidget(b2)
        cl.addLayout(badges)

        def _select(_, rid=room["id"], c=card):
            self.selected_room_id = rid
            for i in range(self.room_layout.count()):
                w = self.room_layout.itemAt(i).widget()
                if w and w.objectName() == "roomCard":
                    w.setStyleSheet(_NORMAL)
            c.setStyleSheet(_SELECTED)

        def _dbl(_, rid=room["id"], c=card):
            _select(None, rid=rid, c=c)
            self.join_selected_room()

        card.mousePressEvent = _select
        card.mouseDoubleClickEvent = _dbl
        self.room_layout.addWidget(card)

    # ── Peers panel ─────────────────────────────────────────────────────────────

    def refresh_users(self):
        try:
            import subprocess, json as _json
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode != 0:
                return
            data = _json.loads(result.stdout)
            self._clear(self.peers_layout)
            peers = data.get("Peer", {})
            users = data.get("User", {})
            online = 0
            for peer in peers.values():
                if not peer.get("Online", False):
                    continue
                uid = str(peer.get("UserID", ""))
                uinfo = users.get(uid, {})
                name = uinfo.get("DisplayName", peer.get("HostName", "Unknown"))
                ips = peer.get("TailscaleIPs", [])
                ip = next((x for x in ips if "." in x), "")

                row = QHBoxLayout()
                row.setSpacing(8)
                dot = QLabel("●", self.peers_content)
                dot.setStyleSheet("color: #4ade80; font-size: 9px; background: transparent;")
                row.addWidget(dot)
                info = QVBoxLayout()
                info.setSpacing(0)
                n = QLabel(name, self.peers_content)
                n.setStyleSheet("font-size: 13px; font-weight: 600; color: #e8ecf4; background: transparent;")
                i = QLabel(ip, self.peers_content)
                i.setStyleSheet("font-size: 11px; color: #4a5168; background: transparent;")
                info.addWidget(n)
                info.addWidget(i)
                row.addLayout(info)
                row.addStretch()

                wrapper = QWidget(self.peers_content)
                wrapper.setStyleSheet("background: transparent;")
                wrapper.setLayout(row)
                self.peers_layout.addWidget(wrapper)
                online += 1

            if online == 0:
                lbl = QLabel("No peers online", self.peers_content)
                lbl.setStyleSheet("color: #4a5168; font-size: 13px; background: transparent;")
                lbl.setAlignment(Qt.AlignCenter)
                self.peers_layout.addWidget(lbl)
        except Exception as e:
            logger.debug(f"Peer list error: {e}")

    # ── Room actions ────────────────────────────────────────────────────────────

    def host_room(self):
        dialog = CreateRoomDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status_loading("Starting host servers & publishing room…")
            room_service.host_room(dialog.room_name, dialog.room_password)

    def join_selected_room(self, *_):
        if not self.selected_room_id:
            QMessageBox.warning(self, "No Room Selected", "Click a room in the list first.")
            return
        room_id = self.selected_room_id

        if room_service.current_room and room_service.current_room["id"] == room_id:
            self.on_enter_room()
            return

        if room_service.current_room:
            reply = QMessageBox.question(
                self, "Leave Current Room?",
                "You're already in a room. Leave it and join this one?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                room_service.leave_room()
            else:
                return

        target = next((r for r in self.active_rooms_cache if r["id"] == room_id), None)
        pwd = None
        if target and target.get("password"):
            from PySide6.QtWidgets import QInputDialog, QLineEdit as _LE
            entered, ok = QInputDialog.getText(
                self, "🔒 Private Room", "Enter room password:", _LE.Password
            )
            if not ok:
                return
            if entered != target["password"]:
                QMessageBox.warning(self, "Access Denied", "Incorrect password.")
                return
            pwd = entered

        self.status_loading("Connecting to host servers…")
        room_service.join_room(room_id, password=pwd)

    # ── State control ────────────────────────────────────────────────────────────

    def status_loading(self, message: str):
        self.host_room_btn.setEnabled(False)
        self.join_room_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.loading_text.setText(message)
        self._stack.setCurrentIndex(1)
        self.anim_timer.start(80)

    def status_ready(self):
        self.host_room_btn.setEnabled(True)
        self.join_room_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.anim_timer.stop()
        self._stack.setCurrentIndex(0)
        self._update_header()

    @Slot()
    def on_room_joined(self):
        self.status_ready()
        self.refresh_timer.stop()
        self.on_enter_room()

    @Slot(str)
    def on_room_error(self, err: str):
        self.status_ready()
        QMessageBox.critical(self, "Connection Error", f"Action failed:\n\n{err}")

    def logout(self):
        self.refresh_timer.stop()
        session.clear()
        self.on_logout()
