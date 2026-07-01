import os
import sys
import time
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QMessageBox, QCheckBox, QGraphicsDropShadowEffect)
from PySide6.QtCore import QThread, Signal, Slot, Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath, QLinearGradient

from utils.constants import APPDATA_DIR
from utils.helpers import check_tailscale_status, get_tailscale_ip, run_tailscale_up
from auth.session import session
from utils.logger import logger

_ROOT = Path(__file__).parent.parent.resolve()

def _asset(rel: str) -> str:
    return str(_ROOT / rel)


# ── Worker threads ─────────────────────────────────────────────────────────────

class TailscalePollThread(QThread):
    connected = Signal(str)
    timed_out = Signal()

    def run(self):
        for _ in range(60):
            ip = get_tailscale_ip()
            if ip:
                self.connected.emit(ip)
                return
            time.sleep(1)
        self.timed_out.emit()


class LoginThread(QThread):
    finished = Signal(bool, str)

    def run(self):
        try:
            from auth.google_login import run_google_login
            from database.supabase import get_supabase
            tokens = run_google_login()
            if tokens:
                supabase = get_supabase()
                res = supabase.auth.get_user()
                auth_user = getattr(res, "user", None) or (
                    res.get("user") if isinstance(res, dict) else None
                )
                if auth_user:
                    session.access_token = tokens.get("access_token")
                    session.refresh_token = tokens.get("refresh_token")
                    ok = session.sync_to_supabase(auth_user)
                    self.finished.emit(ok, "" if ok else "Failed to sync profile.")
                else:
                    self.finished.emit(False, "Could not fetch user from Supabase.")
            else:
                self.finished.emit(False, "Google sign-in timed out or was cancelled.")
        except Exception as e:
            logger.error(f"Login thread error: {e}")
            self.finished.emit(False, str(e))


# ── Dot spinner ────────────────────────────────────────────────────────────────

class _Spinner(QLabel):
    _F = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._i = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("color: #5b8af0; font-size: 22px; background: transparent;")
        self.setVisible(False)

    def start(self):
        self._i = 0
        self._tick()
        self._t.start(80)
        self.setVisible(True)

    def stop(self):
        self._t.stop()
        self.setVisible(False)

    def _tick(self):
        self.setText(self._F[self._i % len(self._F)])
        self._i += 1


# ── Status badge widget ────────────────────────────────────────────────────────

class _Badge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setVisible(False)

    def show_info(self, text: str, color: str = "#5b8af0"):
        self.setText(text)
        self.setStyleSheet(f"""
            background-color: rgba(91,138,240,0.10);
            border: 1px solid rgba(91,138,240,0.30);
            border-radius: 12px;
            padding: 6px 18px;
            font-size: 13px;
            font-weight: 600;
            color: {color};
        """)
        self.setVisible(True)

    def show_success(self, text: str):
        self.show_info(text, "#4ade80")
        self.setStyleSheet(self.styleSheet().replace("rgba(91,138,240,0.10)", "rgba(74,222,128,0.10)")
                           .replace("rgba(91,138,240,0.30)", "rgba(74,222,128,0.30)"))

    def show_warning(self, text: str):
        self.show_info(text, "#fbbf24")
        self.setStyleSheet(self.styleSheet().replace("rgba(91,138,240,0.10)", "rgba(251,191,36,0.10)")
                           .replace("rgba(91,138,240,0.30)", "rgba(251,191,36,0.30)"))

    def show_error(self, text: str):
        self.show_info(text, "#f87171")
        self.setStyleSheet(self.styleSheet().replace("rgba(91,138,240,0.10)", "rgba(248,113,113,0.10)")
                           .replace("rgba(91,138,240,0.30)", "rgba(248,113,113,0.30)"))


# ── Login Page ──────────────────────────────────────────────────────────────────

class LoadingPage(QWidget):
    def __init__(self, on_login_success, parent=None):
        super().__init__(parent)
        self.on_login_success = on_login_success
        self.poll_thread = None
        self.login_thread = None

        # Full-page centring layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Glass card ─────────────────────────────────────────────────
        card = QWidget(self)
        card.setObjectName("loginCard")
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QWidget#loginCard {
                background-color: rgba(30, 33, 48, 0.92);
                border: 1px solid rgba(255,255,255,0.08);
                border-top: 1px solid rgba(255,255,255,0.14);
                border-radius: 24px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(60)
        shadow.setXOffset(0)
        shadow.setYOffset(12)
        shadow.setColor(QColor(0, 0, 0, 120))
        card.setGraphicsEffect(shadow)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(48, 48, 48, 48)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignTop)

        # ── Logo ───────────────────────────────────────────────────────
        logo_lbl = QLabel(card)
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = _asset("assets/images/app_logo.png")
        if Path(logo_path).exists():
            pix = QPixmap(logo_path).scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("💬")
            logo_lbl.setStyleSheet("font-size: 56px; background: transparent;")
        lay.addWidget(logo_lbl)
        lay.addSpacing(20)

        # ── App name ───────────────────────────────────────────────────
        title = QLabel("TailChat", card)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 30px; font-weight: 700; color: #ffffff; "
            "letter-spacing: -0.5px; background: transparent;"
        )
        lay.addWidget(title)
        lay.addSpacing(6)

        sub = QLabel("Private chat & voice over your Tailscale network", card)
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 13px; color: #6b7489; background: transparent;")
        lay.addWidget(sub)
        lay.addSpacing(32)

        # ── Spinner ────────────────────────────────────────────────────
        self.spinner = _Spinner(card)
        lay.addWidget(self.spinner, alignment=Qt.AlignCenter)
        lay.addSpacing(8)

        # ── Status badge (IP / device) ─────────────────────────────────
        self.badge = _Badge(card)
        lay.addWidget(self.badge, alignment=Qt.AlignCenter)
        lay.addSpacing(6)

        # ── Status text ────────────────────────────────────────────────
        self.status_lbl = QLabel("Checking Tailscale status…", card)
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet(
            "color: #6b7489; font-size: 13px; min-height: 40px; "
            "line-height: 1.5; background: transparent;"
        )
        lay.addWidget(self.status_lbl)
        lay.addSpacing(24)

        # ── Remember-me ────────────────────────────────────────────────
        self.remember_cb = QCheckBox("Keep me signed in for 7 days", card)
        self.remember_cb.setChecked(True)
        self.remember_cb.setVisible(False)
        self.remember_cb.setStyleSheet(
            "color: #6b7489; font-size: 13px; spacing: 8px; background: transparent;"
        )
        lay.addWidget(self.remember_cb, alignment=Qt.AlignCenter)
        lay.addSpacing(12)

        # ── Primary action button ──────────────────────────────────────
        self.action_btn = QPushButton("Check Status", card)
        self.action_btn.setMinimumHeight(50)
        self.action_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4f7de8, stop:1 #6a9af6);
                color: #ffffff;
                border: none;
                border-radius: 14px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #5b8af0, stop:1 #7aabff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3d64c8, stop:1 #5079e0);
            }
            QPushButton:disabled {
                background: rgba(91,138,240,0.20);
                color: rgba(255,255,255,0.35);
            }
        """)
        self.action_btn.clicked.connect(self.check_status)
        lay.addWidget(self.action_btn)
        lay.addSpacing(10)

        # ── Retry link button ──────────────────────────────────────────
        self.retry_btn = QPushButton("↺  Re-check Tailscale", card)
        self.retry_btn.setObjectName("secondaryButton")
        self.retry_btn.setMinimumHeight(38)
        self.retry_btn.clicked.connect(self.check_status)
        self.retry_btn.setVisible(False)
        lay.addWidget(self.retry_btn)

        # ── Version / footer ───────────────────────────────────────────
        lay.addSpacing(20)
        ver = QLabel("v1.0 · Secured by Tailscale", card)
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("font-size: 11px; color: #3a3f52; background: transparent;")
        lay.addWidget(ver)

        # Centre card
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card)
        row.addStretch()
        outer.addStretch()
        outer.addLayout(row)
        outer.addStretch()

        QTimer.singleShot(0, self.check_status)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _status(self, text: str, color: str = "#6b7489"):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; min-height: 40px; "
            f"line-height: 1.5; background: transparent;"
        )

    def _busy(self, on: bool):
        self.action_btn.setEnabled(not on)
        self.retry_btn.setEnabled(not on)
        if on:
            self.spinner.start()
        else:
            self.spinner.stop()

    def _rewire(self, slot):
        try:
            self.action_btn.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.action_btn.clicked.connect(slot)

    # ── Flow ───────────────────────────────────────────────────────────────────

    def check_status(self):
        self._busy(False)
        self.retry_btn.setVisible(False)
        self.badge.setVisible(False)
        self.remember_cb.setVisible(False)
        self._status("Checking Tailscale status…")
        self.spinner.start()
        QTimer.singleShot(100, self._do_check)

    def _do_check(self):
        self.spinner.stop()
        is_conn, status = check_tailscale_status()

        if status == "not_installed":
            self.badge.show_error("Tailscale Not Found")
            self._status(
                "Tailscale VPN is required but wasn't found on this machine.",
                "#f87171"
            )
            self.action_btn.setText("⬇  Download & Install Tailscale")
            self._rewire(self._install_tailscale)

        elif status in ("stopped", "logged_out", "disconnected"):
            self.badge.show_warning("Not Connected")
            self._status(
                "Tailscale is installed but not connected.\n"
                "Opening Tailscale authentication in your browser…",
                "#fbbf24"
            )
            self.action_btn.setText("🔗  Connect to Tailscale")
            self._rewire(self._connect_tailscale)
            self.retry_btn.setVisible(True)
            QTimer.singleShot(600, self._connect_tailscale)

        elif is_conn:
            if session.try_load_local_session():
                self.on_login_success()
                return

            import socket
            device = socket.gethostname()
            self.badge.show_success(f"🟢  {status}   ·   {device}")
            self._status(
                "Connected to Tailscale.\nSign in with your Google account to continue.",
                "#4ade80"
            )
            self.action_btn.setText("   Sign in with Google")
            self._rewire(self._start_login)
            self.remember_cb.setVisible(True)
            QTimer.singleShot(400, self._start_login)

        else:
            self.badge.show_warning("Resolving…")
            self._status("Tailscale detected — resolving IP address…", "#fbbf24")
            self.action_btn.setText("↺  Retry")
            self._rewire(self.check_status)
            QTimer.singleShot(1200, self.check_status)

    def _install_tailscale(self):
        installer = _ROOT / "resources" / "tailscale-setup.exe"
        try:
            if installer.exists():
                os.startfile(str(installer))
                QMessageBox.information(
                    self, "Tailscale Setup",
                    "Installer launched!\n\nAfter setup is complete and you've "
                    "signed in, click 'Re-check Tailscale'."
                )
            else:
                QMessageBox.warning(
                    self, "Installer Not Found",
                    "Bundled installer not found.\n"
                    "Download Tailscale from https://tailscale.com/download"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch installer:\n{e}")
        self.check_status()

    def _connect_tailscale(self):
        self._busy(True)
        self._status("Opening Tailscale authentication in your browser…", "#5b8af0")
        if run_tailscale_up():
            self._status("Waiting for Tailscale to connect…", "#5b8af0")
            self.poll_thread = TailscalePollThread()
            self.poll_thread.connected.connect(self._on_ts_connected)
            self.poll_thread.timed_out.connect(self._on_ts_timeout)
            self.poll_thread.start()
        else:
            self._status("Could not launch Tailscale CLI.", "#f87171")
            self._busy(False)

    @Slot(str)
    def _on_ts_connected(self, ip):
        self._busy(False)
        self.check_status()

    @Slot()
    def _on_ts_timeout(self):
        self._busy(False)
        self.badge.show_error("Timed Out")
        self._status(
            "Timed out waiting for Tailscale.\nConnect manually then re-check.",
            "#f87171"
        )
        self.retry_btn.setVisible(True)

    def _start_login(self):
        self._busy(True)
        self.action_btn.setText("Waiting for browser…")
        self._status(
            "A Google sign-in tab has opened in your browser.\n"
            "Complete the login and return here.",
            "#5b8af0"
        )
        self.login_thread = LoginThread()
        self.login_thread.finished.connect(self._on_login_done)
        self.login_thread.start()

    @Slot(bool, str)
    def _on_login_done(self, success: bool, error: str):
        self._busy(False)
        self.action_btn.setText("   Sign in with Google")
        if success:
            if self.remember_cb.isChecked():
                session.save_local_session()
            self.badge.show_success("Signed in!")
            self._status("Loading your rooms…", "#4ade80")
            self.on_login_success()
        else:
            self.badge.show_error("Sign-in Failed")
            self._status(f"Could not complete sign-in.\n{error}", "#f87171")
            self._rewire(self._start_login)
            QMessageBox.warning(
                self, "Login Failed",
                f"Could not complete sign-in:\n\n{error}\n\nPlease try again."
            )
