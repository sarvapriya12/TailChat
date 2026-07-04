import base64
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QTextEdit, QPushButton, QMessageBox,
                                QFileDialog, QFrame, QWidget, QScrollArea)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QPainter, QPainterPath

from config.settings import load_settings, save_settings
from auth.session import session


def _circular_pixmap(b64_or_path: str, size: int) -> QPixmap | None:
    pix = QPixmap()
    if b64_or_path.startswith("data:image"):
        try:
            _, enc = b64_or_path.split(",", 1)
            pix.loadFromData(base64.b64decode(enc))
        except Exception:
            return None
    else:
        pix = QPixmap(b64_or_path)
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


class ProfileDialog(QDialog):
    def __init__(self, user_id, user_info: dict, is_self: bool = False, parent=None):
        super().__init__(parent)
        self.user_id   = user_id
        self.user_info = user_info
        self.is_self   = is_self

        self.setWindowTitle("My Profile" if is_self else "User Profile")
        self.setMinimumSize(440, 560)
        self.resize(440, 600)
        self.setWindowModality(Qt.WindowModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #13151c;
                border: 1px solid rgba(80,86,120,0.09);
                border-radius: 18px;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Hero banner ────────────────────────────────────────────────
        banner = QWidget(self)
        banner.setAttribute(Qt.WA_StyledBackground, True)
        banner.setFixedHeight(110)
        banner.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(61,100,200,0.60),
                stop:0.5 rgba(139,92,246,0.40),
                stop:1 rgba(124,159,244,0.50));
            border-radius: 0px;
        """)
        outer.addWidget(banner)

        # ── Avatar overlapping banner/body ─────────────────────────────
        av_wrap = QHBoxLayout()
        av_wrap.setContentsMargins(28, 0, 28, 0)
        av_wrap.setSpacing(0)
        self.avatar_lbl = QLabel(self)
        self.avatar_lbl.setFixedSize(96, 96)
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        self.avatar_lbl.setStyleSheet("""
            background-color: #13151c;
            border: 3px solid #13151c;
            border-radius: 48px;
        """)
        self._render_avatar(96)
        av_wrap.addWidget(self.avatar_lbl)
        av_wrap.addStretch()

        # Change photo button (self only) — floats in top-right of avatar
        if is_self:
            self.change_av_btn = QPushButton("📷", self)
            self.change_av_btn.setFixedSize(30, 30)
            self.change_av_btn.setToolTip("Change profile photo")
            self.change_av_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8B5CF6; color: #F8F8F2;
                    border: 2px solid #13151c; border-radius: 15px;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #6b97f2; }
            """)
            self.change_av_btn.clicked.connect(self._change_avatar)
            av_wrap.addWidget(self.change_av_btn, alignment=Qt.AlignBottom)

        outer.addLayout(av_wrap)

        # ── Scroll body ────────────────────────────────────────────────
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        body.setAttribute(Qt.WA_StyledBackground, True)
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(28, 12, 28, 20)
        lay.setSpacing(10)
        scroll.setWidget(body)

        # ── Name ───────────────────────────────────────────────────────
        if is_self:
            name_lbl = QLabel("Display Name", body)
            name_lbl.setStyleSheet("font-size: 12px; color: #98A0C6; background: transparent;")
            lay.addWidget(name_lbl)
            self.name_input = QLineEdit(body)
            self.name_input.setText(user_info.get("display_name", ""))
            self.name_input.setStyleSheet("""
                background: #1a1d27; border: 1px solid rgba(80,86,120,0.09);
                border-radius: 10px; padding: 9px 14px; color: #F8F8F2; font-size: 14px;
            """)
            lay.addWidget(self.name_input)
        else:
            name_lbl = QLabel(user_info.get("display_name", "Unknown User"), body)
            name_lbl.setStyleSheet(
                "font-size: 22px; font-weight: 700; color: #F8F8F2; background: transparent;"
            )
            lay.addWidget(name_lbl)

            if user_info.get("email"):
                email_lbl = QLabel(user_info["email"], body)
                email_lbl.setStyleSheet(
                    "font-size: 13px; color: #98A0C6; background: transparent;"
                )
                lay.addWidget(email_lbl)

        # ── Bio ────────────────────────────────────────────────────────
        lay.addSpacing(4)
        bio_title = QLabel("Bio", body)
        bio_title.setStyleSheet("font-size: 12px; color: #98A0C6; background: transparent;")
        lay.addWidget(bio_title)

        self.bio_input = QTextEdit(body)
        self.bio_input.setPlainText(user_info.get("bio", ""))
        self.bio_input.setReadOnly(not is_self)
        self.bio_input.setFixedHeight(90)
        self.bio_input.setStyleSheet("""
            background: #1a1d27; border: 1px solid rgba(80,86,120,0.09);
            border-radius: 10px; padding: 8px 12px; color: #F8F8F2; font-size: 14px;
        """)
        lay.addWidget(self.bio_input)

        # ── Links ──────────────────────────────────────────────────────
        lay.addSpacing(4)
        links_title = QLabel("Links", body)
        links_title.setStyleSheet("font-size: 12px; color: #98A0C6; background: transparent;")
        lay.addWidget(links_title)

        if is_self:
            self.links_input = QTextEdit(body)
            self.links_input.setPlainText(user_info.get("links", ""))
            self.links_input.setFixedHeight(72)
            self.links_input.setStyleSheet("""
                background: #1a1d27; border: 1px solid rgba(80,86,120,0.09);
                border-radius: 10px; padding: 8px 12px; color: #F8F8F2; font-size: 14px;
            """)
            lay.addWidget(self.links_input)
        else:
            links_text = user_info.get("links", "")
            links_list = [l.strip() for l in links_text.splitlines() if l.strip()]
            if links_list:
                for link in links_list:
                    btn = QPushButton(link, body)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.setStyleSheet("""
                        QPushButton {
                            background: rgba(139,92,246,0.08);
                            border: 1px solid rgba(139,92,246,0.22);
                            border-radius: 8px; padding: 6px 12px;
                            color: #8B5CF6; font-size: 13px; text-align: left;
                        }
                        QPushButton:hover {
                            background: rgba(139,92,246,0.16);
                            border-color: rgba(139,92,246,0.45);
                            color: #7aabff;
                        }
                    """)
                    btn.clicked.connect(lambda _, l=link: self._open_link(l))
                    lay.addWidget(btn)
            else:
                no_links = QLabel("No links added.", body)
                no_links.setStyleSheet("font-size: 13px; color: #98A0C6; background: transparent;")
                lay.addWidget(no_links)

        lay.addStretch()

        # ── Action button ──────────────────────────────────────────────
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(80,86,120,0.06); max-height: 1px; border: none;")
        outer.addWidget(sep)

        btn_bar = QWidget(self)
        btn_bar.setAttribute(Qt.WA_StyledBackground, True)
        btn_bar.setStyleSheet("background: transparent;")
        btn_bar.setFixedHeight(60)
        bb_lay = QHBoxLayout(btn_bar)
        bb_lay.setContentsMargins(28, 0, 28, 0)
        bb_lay.addStretch()

        if is_self:
            save_btn = QPushButton("Save Profile", btn_bar)
            save_btn.setMinimumHeight(40)
            save_btn.setMinimumWidth(130)
            save_btn.clicked.connect(self._save_profile)
            bb_lay.addWidget(save_btn)
        else:
            close_btn = QPushButton("Close", btn_bar)
            close_btn.setObjectName("secondaryButton")
            close_btn.setMinimumHeight(40)
            close_btn.setMinimumWidth(90)
            close_btn.clicked.connect(self.accept)
            bb_lay.addWidget(close_btn)

        outer.addWidget(btn_bar)

    # ── Avatar ──────────────────────────────────────────────────────────────────

    def _render_avatar(self, size: int = 96):
        av = self.user_info.get("avatar_url", "")
        if av:
            pix = _circular_pixmap(av, size)
            if pix:
                self.avatar_lbl.setPixmap(pix)
                self.avatar_lbl.setStyleSheet(
                    f"border: 3px solid #13151c; border-radius: {size // 2}px; background: transparent;"
                )
                return
        name = self.user_info.get("display_name", "?")
        self.avatar_lbl.setText((name or "?")[0].upper())
        self.avatar_lbl.setStyleSheet(
            f"background: rgba(139,92,246,0.18); border: 3px solid #13151c; "
            f"border-radius: {size // 2}px; font-weight: 700; "
            f"font-size: {size // 2 - 4}px; color: #8B5CF6;"
        )

    def _change_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Photo", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        try:
            from gui.image_cropper import ImageCropper
            cropper = ImageCropper(path, self)
            if cropper.exec() == QDialog.Accepted and cropper.b64_result:
                self.user_info["avatar_url"] = cropper.b64_result
                self._render_avatar(96)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load photo:\n{e}")

    # ── Links ────────────────────────────────────────────────────────────────────

    def _open_link(self, url: str):
        if not url.startswith("http"):
            url = "https://" + url
        QDesktopServices.openUrl(QUrl(url))

    # ── Save ─────────────────────────────────────────────────────────────────────

    def _save_profile(self):
        bio   = self.bio_input.toPlainText().strip()
        links = self.links_input.toPlainText().strip()
        name  = self.name_input.text().strip()
        av    = self.user_info.get("avatar_url", "")

        session.bio    = bio
        session.links  = links
        if name:  session.display_name = name
        if av:    session.avatar_url   = av

        settings = load_settings()
        settings["profile_bio"]    = bio
        settings["profile_links"]  = links
        if name:  settings["profile_name"]    = name
        if av:    settings["profile_picture"] = av

        if save_settings(settings):
            QMessageBox.information(
                self, "Saved",
                "Profile saved! Other users will see your updated info next time you join a room."
            )
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to save profile.")
