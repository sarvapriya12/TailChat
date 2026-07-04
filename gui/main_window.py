import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
                                QLabel, QSizePolicy, QFrame, QPushButton)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QIcon
from qframelesswindow import FramelessWindow
from qfluentwidgets import setTheme, Theme, TransparentPushButton, PrimaryPushButton

from gui.styles import DARK_STYLESHEET
from gui.login_window import LoadingPage
from gui.home_window import HomePage
from gui.room_window import RoomPage
from gui.about_page import AboutPage
from gui.settings_page import SettingsPage
from auth.session import session

_ROOT = Path(__file__).parent.parent.resolve()


def _circular_pixmap(source, size: int) -> QPixmap | None:
    """Return a circular-cropped QPixmap from a file path or base64 data-URI."""
    pix = QPixmap()
    if isinstance(source, str) and source.startswith("data:image"):
        try:
            import base64
            _, enc = source.split(",", 1)
            pix.loadFromData(base64.b64decode(enc))
        except Exception:
            return None
    elif isinstance(source, str) and source:
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


class SidebarWidget(QWidget):
    def __init__(self, parent, on_navigate, on_install_tailscale, on_open_settings):
        super().__init__(parent)
        self.setObjectName("leftPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(220)
        self.on_navigate = on_navigate
        self.on_install_tailscale = on_install_tailscale
        self.on_open_settings = on_open_settings

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 28, 16, 20)
        lay.setSpacing(4)

        # ── App brand ──────────────────────────────────────────────────
        brand = QLabel("TailChat", self)
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #8B5CF6; "
            "letter-spacing: -0.3px; margin-bottom: 20px; background: transparent;"
        )
        lay.addWidget(brand)

        # ── Avatar ─────────────────────────────────────────────────────
        self.avatar_lbl = QLabel(self)
        self.avatar_lbl.setFixedSize(80, 80)
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        self.avatar_lbl.setStyleSheet(
            "background-color: rgba(139,92,246,0.15); border-radius: 40px; "
            "font-weight: 700; font-size: 30px; color: #8B5CF6;"
        )
        self.avatar_lbl.setCursor(Qt.PointingHandCursor)
        self.avatar_lbl.mousePressEvent = lambda _: self.on_open_settings()

        av_row = QHBoxLayout()
        av_row.addStretch()
        av_row.addWidget(self.avatar_lbl)
        av_row.addStretch()
        lay.addLayout(av_row)
        lay.addSpacing(10)

        # ── Display name ───────────────────────────────────────────────
        self.name_lbl = QLabel("Loading…", self)
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #F8F8F2; background: transparent;"
        )
        lay.addWidget(self.name_lbl)

        # ── Email / status ─────────────────────────────────────────────
        self.email_lbl = QLabel("", self)
        self.email_lbl.setAlignment(Qt.AlignCenter)
        self.email_lbl.setWordWrap(True)
        self.email_lbl.setStyleSheet(
            "font-size: 11px; color: #98A0C6; background: transparent; margin-bottom: 4px;"
        )
        lay.addWidget(self.email_lbl)

        # Online status dot + text
        status_row = QHBoxLayout()
        status_row.setAlignment(Qt.AlignCenter)
        status_row.setSpacing(6)
        dot = QLabel("●", self)
        dot.setStyleSheet("color: #4ade80; font-size: 9px; background: transparent;")
        status_row.addWidget(dot)
        status_lbl = QLabel("Online", self)
        status_lbl.setStyleSheet("font-size: 12px; color: #98A0C6; background: transparent;")
        status_row.addWidget(status_lbl)
        lay.addLayout(status_row)
        lay.addSpacing(16)

        # ── Divider ────────────────────────────────────────────────────
        div = QFrame(self)
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background: rgba(80,86,120,0.08); max-height: 1px; border: none;")
        lay.addWidget(div)
        lay.addSpacing(8)

        # ── Nav section label ──────────────────────────────────────────
        nav_lbl = QLabel("NAVIGATE", self)
        nav_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1.5px; "
            "color: #98A0C6; background: transparent; margin-top: 4px;"
        )
        lay.addWidget(nav_lbl)
        lay.addSpacing(4)

        # ── Nav buttons ────────────────────────────────────────────────
        self.btn_home = self._nav_btn("🏠  Lobby", lambda: self.on_navigate(1))
        lay.addWidget(self.btn_home)

        self.btn_settings = self._nav_btn("⚙  Settings & Profile", self.on_open_settings)
        lay.addWidget(self.btn_settings)

        self.btn_about = self._nav_btn("ℹ  About", self.on_open_about)
        lay.addWidget(self.btn_about)

        lay.addStretch()

        # ── Tailscale install (shown conditionally) ────────────────────
        self.btn_tailscale = QPushButton("⬇  Install Tailscale", self)
        self.btn_tailscale.setMinimumHeight(40)
        self.btn_tailscale.clicked.connect(self.on_install_tailscale)
        self.btn_tailscale.setVisible(False)
        lay.addWidget(self.btn_tailscale)
        lay.addSpacing(4)

        # ── Sign out ───────────────────────────────────────────────────
        self.btn_signout = QPushButton("Sign Out", self)
        self.btn_signout.setObjectName("dangerButton")
        self.btn_signout.setMinimumHeight(36)
        self.btn_signout.clicked.connect(self._sign_out)
        lay.addWidget(self.btn_signout)

    def _nav_btn(self, text: str, slot) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setObjectName("transparentButton")
        btn.setMinimumHeight(40)
        btn.setStyleSheet("""
            QPushButton#transparentButton {
                background: transparent;
                color: #98A0C6;
                border: none;
                text-align: left;
                padding: 0px 12px;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton#transparentButton:hover {
                background: rgba(80,86,120,0.08);
                color: #F8F8F2;
            }
            QPushButton#transparentButton:pressed {
                background: rgba(139,92,246,0.14);
                color: #8B5CF6;
            }
        """)
        btn.clicked.connect(slot)
        return btn

    def on_open_about(self):
        self.on_navigate(3)

    def _sign_out(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Sign Out", "Sign out of TailChat?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            session.clear()
            self.on_navigate(0)

    def update_profile(self):
        """Refresh avatar + name from the current session."""
        name = session.display_name or "Guest"
        self.name_lbl.setText(name)
        self.email_lbl.setText(session.email or "")

        av = session.avatar_url
        if av:
            pix = _circular_pixmap(av, 80)
            if pix:
                self.avatar_lbl.setPixmap(pix)
                self.avatar_lbl.setStyleSheet("border-radius: 40px; background: transparent;")
                self.avatar_lbl.setToolTip("Click to edit profile")
                return

        # Fallback — coloured initial
        self.avatar_lbl.setPixmap(QPixmap())
        self.avatar_lbl.setText((name or "?")[0].upper())
        self.avatar_lbl.setStyleSheet(
            "background-color: rgba(139,92,246,0.18); border-radius: 40px; "
            "font-weight: 700; font-size: 30px; color: #8B5CF6;"
        )
        self.avatar_lbl.setToolTip("Click to edit profile")


class TailChatMainWindow(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TailChat")
        self.resize(1200, 720)
        self.setMinimumSize(900, 560)

        setTheme(Theme.DARK)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("mainWindow")
        self.setStyleSheet(DARK_STYLESHEET + "\n#mainWindow { background-color: #121212; }")

        # ── Titlebar ───────────────────────────────────────────────────
        if hasattr(self, "titleBar"):
            from PySide6.QtGui import QColor
            self.titleBar.setAttribute(Qt.WA_StyledBackground, True)
            self.titleBar.setStyleSheet(
                "TitleBar { background-color: #121212; "
                "border-bottom: 1px solid rgba(80,86,120,0.06); } "
                "QLabel { color: #F8F8F2; font-size: 13px; font-weight: 600; }"
            )
            for btn in [
                getattr(self.titleBar, "minBtn", None),
                getattr(self.titleBar, "maxBtn", None),
                getattr(self.titleBar, "closeBtn", None),
            ]:
                if btn:
                    btn.setNormalColor(QColor('#F8F8F2'))
                    if btn is not getattr(self.titleBar, "closeBtn", None):
                        btn.setHoverColor(QColor('#F8F8F2'))
                        btn.setPressedColor(QColor('#F8F8F2'))
                        btn.setHoverBackgroundColor(QColor(88, 101, 242, 20))
                        btn.setPressedBackgroundColor(QColor(88, 101, 242, 40))

        # ── App icon ───────────────────────────────────────────────────
        logo_path = _ROOT / "assets" / "images" / "app_logo.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # ── Root layout ────────────────────────────────────────────────
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 32, 0, 0)
        root.setSpacing(0)

        self.sidebar = SidebarWidget(
            self, self.navigate_to, self.install_tailscale, self.open_settings
        )
        root.addWidget(self.sidebar)

        # Thin separator between sidebar and content
        sep = QFrame(self)
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background: rgba(80,86,120,0.05); max-width: 1px; border: none;")
        root.addWidget(sep)

        self.stack = QStackedWidget(self)
        self.stack.setAttribute(Qt.WA_StyledBackground, True)
        self.stack.setStyleSheet("background-color: transparent;")
        root.addWidget(self.stack, stretch=1)

        self.loading_page = LoadingPage(self.on_login_success, self)
        self.home_page    = HomePage(self.on_logout, self.on_enter_room, self)
        self.room_page    = RoomPage(self.on_leave_room, self)
        self.about_page   = AboutPage(self)
        self.settings_page= SettingsPage(self.close_settings, self)

        self.stack.addWidget(self.loading_page)  # 0
        self.stack.addWidget(self.home_page)     # 1
        self.stack.addWidget(self.room_page)     # 2
        self.stack.addWidget(self.about_page)    # 3
        self.stack.addWidget(self.settings_page) # 4

        self.navigate_to(0)
        self._previous_index = 1

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to(self, index: int):
        self.stack.setCurrentIndex(index)

    def on_login_success(self):
        self.sidebar.update_profile()
        self.navigate_to(1)
        self.home_page.status_ready()
        self.home_page.refresh_rooms()
        self.home_page.refresh_timer.start(10_000)

    def on_logout(self):
        self.navigate_to(0)

    def on_enter_room(self):
        self.sidebar.setVisible(False)
        self.navigate_to(2)
        self.room_page.initialize_room_view()

    def on_leave_room(self):
        self.sidebar.setVisible(True)
        self.navigate_to(1)
        self.home_page.status_ready()
        self.home_page.refresh_rooms()
        self.home_page.refresh_timer.start(10_000)

    # ── Tailscale install ───────────────────────────────────────────────────────

    def install_tailscale(self):
        installer = _ROOT / "resources" / "tailscale-setup.exe"
        try:
            if installer.exists():
                import os
                os.startfile(str(installer))
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Not Found",
                    "Installer not found in /resources.\n"
                    "Download from https://tailscale.com/download"
                )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to run installer:\n{e}")

    # ── Settings ──────────────────────────────────────────────────────────

    def open_settings(self):
        self._previous_index = self.stack.currentIndex()
        if self._previous_index not in (1, 2):
            self._previous_index = 1
        self.navigate_to(4)
        
    def close_settings(self):
        self.sidebar.update_profile()
        if self._previous_index == 2:
            self.room_page.update_profile()
        self.navigate_to(self._previous_index)
