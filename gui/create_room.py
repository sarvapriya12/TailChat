from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QMessageBox, QWidget, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGraphicsDropShadowEffect, QColor


class CreateRoomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Host a New Room")
        self.setFixedSize(400, 320)
        self.setWindowModality(Qt.WindowModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #13151c;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 18px;
            }
        """)

        self.room_name     = ""
        self.room_password = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────
        hdr = QWidget(self)
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border-bottom: 1px solid rgba(255,255,255,0.07);
        """)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(24, 0, 20, 0)

        title = QLabel("🏠  Host a Room", hdr)
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #e8ecf4; background: transparent;"
        )
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        close_btn = QPushButton("✕", hdr)
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06); color: #8892a8;
                border: none; border-radius: 7px; font-size: 12px;
            }
            QPushButton:hover { background: rgba(248,113,113,0.15); color: #f87171; }
        """)
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(close_btn)
        outer.addWidget(hdr)

        # ── Body ───────────────────────────────────────────────────────
        body = QWidget(self)
        body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 8)
        body_lay.setSpacing(12)

        # Room name field
        name_lbl = QLabel("Room Name", body)
        name_lbl.setStyleSheet("font-size: 12px; color: #4a5168; background: transparent;")
        body_lay.addWidget(name_lbl)

        self.name_input = QLineEdit(body)
        self.name_input.setPlaceholderText("e.g.  Friday Night Gaming")
        self.name_input.setMaxLength(30)
        self.name_input.setMinimumHeight(44)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #1a1d27;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 11px;
                padding: 0px 14px;
                color: #e8ecf4;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(91,138,240,0.65);
                background: #1e2130;
            }
        """)
        body_lay.addWidget(self.name_input)

        # Password field
        pwd_lbl = QLabel("Room Password  (optional — leave blank for public)", body)
        pwd_lbl.setStyleSheet("font-size: 12px; color: #4a5168; background: transparent;")
        body_lay.addWidget(pwd_lbl)

        self.pwd_input = QLineEdit(body)
        self.pwd_input.setPlaceholderText("Password…")
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setMinimumHeight(44)
        self.pwd_input.setStyleSheet("""
            QLineEdit {
                background: #1a1d27;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 11px;
                padding: 0px 14px;
                color: #e8ecf4;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(91,138,240,0.65);
                background: #1e2130;
            }
        """)
        body_lay.addWidget(self.pwd_input)
        body_lay.addStretch()
        outer.addWidget(body, stretch=1)

        # ── Footer buttons ──────────────────────────────────────────────
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.06); max-height: 1px; border: none;")
        outer.addWidget(sep)

        btn_bar = QWidget(self)
        btn_bar.setStyleSheet("background: transparent;")
        btn_bar.setFixedHeight(60)
        bb = QHBoxLayout(btn_bar)
        bb.setContentsMargins(24, 0, 24, 0)
        bb.setSpacing(10)
        bb.addStretch()

        cancel_btn = QPushButton("Cancel", btn_bar)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06); color: #8892a8;
                border: 1px solid rgba(255,255,255,0.09); border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.10); color: #e8ecf4; }
        """)
        cancel_btn.clicked.connect(self.reject)
        bb.addWidget(cancel_btn)

        create_btn = QPushButton("✔  Create Room", btn_bar)
        create_btn.setMinimumHeight(40)
        create_btn.setMinimumWidth(130)
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4f7de8, stop:1 #6a9af6);
                color: #ffffff; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #5b8af0, stop:1 #7aabff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3d64c8, stop:1 #5079e0);
            }
        """)
        create_btn.clicked.connect(self._validate)
        bb.addWidget(create_btn)
        outer.addWidget(btn_bar)

        self.name_input.setFocus()
        self.name_input.returnPressed.connect(self._validate)
        self.pwd_input.returnPressed.connect(self._validate)

    def _validate(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Room name cannot be empty.")
            return
        if len(name) < 3:
            QMessageBox.warning(self, "Validation", "Room name must be at least 3 characters.")
            return
        self.room_name     = name
        self.room_password = self.pwd_input.text().strip()
        self.accept()
