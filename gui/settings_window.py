from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QFileDialog, QMessageBox, QFrame, QScrollArea,
                               QWidget, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPainterPath
from qfluentwidgets import ComboBox, LineEdit, PushButton, PrimaryPushButton, TextEdit

from config.settings import load_settings, save_settings
from voice.microphone import MicrophoneReader
from voice.speaker import SpeakerMixer
from services.room_service import room_service
from auth.session import session
from utils.logger import logger


def _section(text: str, parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet(
        "font-size: 11px; font-weight: 700; letter-spacing: 1.2px; "
        "color: #98A0C6; text-transform: uppercase; "
        "background: transparent; margin-top: 8px; margin-bottom: 2px;"
    )
    return lbl


def _divider(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("background: rgba(80,86,120,0.06); max-height: 1px; border: none;")
    return f


def _field_label(text: str, parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet("font-size: 13px; color: #98A0C6; background: transparent;")
    return lbl


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Profile")
        self.setMinimumSize(540, 680)
        self.resize(540, 720)
        self.setWindowModality(Qt.WindowModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #13151c;
                border: 1px solid rgba(80,86,120,0.09);
                border-radius: 18px;
            }
        """)

        self._settings = load_settings()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Title bar ──────────────────────────────────────────────────
        title_bar = QWidget(self)
        title_bar.setAttribute(Qt.WA_StyledBackground, True)
        title_bar.setStyleSheet("""
            background-color: rgba(80,86,120,0.03);
            border-bottom: 1px solid rgba(80,86,120,0.07);
            border-radius: 0px;
        """)
        title_bar.setFixedHeight(56)
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(28, 0, 20, 0)
        title_lbl = QLabel("Settings & Profile", title_bar)
        title_lbl.setStyleSheet(
            "font-size: 17px; font-weight: 700; color: #F8F8F2; background: transparent;"
        )
        tb_lay.addWidget(title_lbl)
        tb_lay.addStretch()
        close_btn = QPushButton("✕", title_bar)
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(80,86,120,0.06); color: #98A0C6;
                border: none; border-radius: 8px; font-size: 13px;
            }
            QPushButton:hover { background: rgba(248,113,113,0.15); color: #f87171; }
        """)
        close_btn.clicked.connect(self.reject)
        tb_lay.addWidget(close_btn)
        outer.addWidget(title_bar)

        # ── Scroll body ────────────────────────────────────────────────
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        body.setAttribute(Qt.WA_StyledBackground, True)
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(28, 24, 28, 12)
        lay.setSpacing(10)
        scroll.setWidget(body)

        # ══════════════════════════════════════════════════════════ PROFILE
        lay.addWidget(_section("Profile", body))
        lay.addWidget(_divider(body))

        # ── Big avatar ─────────────────────────────────────────────────
        av_area = QWidget(body)
        av_area.setAttribute(Qt.WA_StyledBackground, True)
        av_area.setStyleSheet("""
            background: rgba(139,92,246,0.05);
            border: 1px dashed rgba(139,92,246,0.25);
            border-radius: 14px;
        """)
        av_lay = QVBoxLayout(av_area)
        av_lay.setContentsMargins(20, 20, 20, 16)
        av_lay.setSpacing(12)
        av_lay.setAlignment(Qt.AlignCenter)

        self._avatar_lbl = QLabel(av_area)
        self._avatar_lbl.setFixedSize(96, 96)
        self._avatar_lbl.setAlignment(Qt.AlignCenter)
        self._render_avatar()
        av_lay.addWidget(self._avatar_lbl, alignment=Qt.AlignCenter)

        av_hint = QLabel("Profile photo visible to other members", av_area)
        av_hint.setStyleSheet("font-size: 12px; color: #98A0C6; background: transparent;")
        av_hint.setAlignment(Qt.AlignCenter)
        av_lay.addWidget(av_hint)

        av_btns = QHBoxLayout()
        av_btns.setSpacing(8)
        self._change_av_btn = QPushButton("📷  Upload Photo", av_area)
        self._change_av_btn.setMinimumHeight(38)
        self._change_av_btn.clicked.connect(self._pick_avatar)
        av_btns.addWidget(self._change_av_btn)

        self._remove_av_btn = QPushButton("Remove", av_area)
        self._remove_av_btn.setObjectName("secondaryButton")
        self._remove_av_btn.setMinimumHeight(38)
        self._remove_av_btn.clicked.connect(self._remove_avatar)
        av_btns.addWidget(self._remove_av_btn)
        av_lay.addLayout(av_btns)
        lay.addWidget(av_area)
        lay.addSpacing(6)

        # ── Name ───────────────────────────────────────────────────────
        lay.addWidget(_field_label("Display Name", body))
        self._name_input = LineEdit(body)
        self._name_input.setText(
            self._settings.get("profile_name", "") or session.display_name
        )
        self._name_input.setPlaceholderText("Your visible name in rooms")
        lay.addWidget(self._name_input)

        # ── Bio ────────────────────────────────────────────────────────
        lay.addWidget(_field_label("Bio", body))
        self._bio_input = TextEdit(body)
        self._bio_input.setPlainText(self._settings.get("profile_bio", ""))
        self._bio_input.setPlaceholderText("Tell others a bit about yourself…")
        self._bio_input.setFixedHeight(76)
        lay.addWidget(self._bio_input)

        # ── Links ──────────────────────────────────────────────────────
        lay.addWidget(_field_label("Links (one per line)", body))
        self._links_input = TextEdit(body)
        self._links_input.setPlainText(self._settings.get("profile_links", ""))
        self._links_input.setPlaceholderText("https://github.com/you\nhttps://twitter.com/you")
        self._links_input.setFixedHeight(64)
        lay.addWidget(self._links_input)

        # ══════════════════════════════════════════════════════════ AUDIO
        lay.addSpacing(6)
        lay.addWidget(_section("Audio", body))
        lay.addWidget(_divider(body))

        lay.addWidget(_field_label("Microphone", body))
        self._mic_combo = ComboBox(body)
        lay.addWidget(self._mic_combo)

        lay.addWidget(_field_label("Speaker / Playback Device", body))
        self._spk_combo = ComboBox(body)
        lay.addWidget(self._spk_combo)
        self._populate_devices()

        # ══════════════════════════════════════════════════════════ FILES
        lay.addSpacing(6)
        lay.addWidget(_section("Files", body))
        lay.addWidget(_divider(body))

        lay.addWidget(_field_label("Download Folder", body))
        dir_row = QHBoxLayout()
        self._dir_input = LineEdit(body)
        self._dir_input.setText(self._settings.get("download_directory", ""))
        browse_btn = QPushButton("Browse…", body)
        browse_btn.setObjectName("secondaryButton")
        browse_btn.setMinimumHeight(38)
        browse_btn.clicked.connect(self._browse_folder)
        dir_row.addWidget(self._dir_input)
        dir_row.addWidget(browse_btn)
        lay.addLayout(dir_row)

        # ══════════════════════════════════════════════════════ APPEARANCE
        lay.addSpacing(6)
        lay.addWidget(_section("Appearance", body))
        lay.addWidget(_divider(body))

        lay.addWidget(_field_label("Theme", body))
        self._theme_combo = ComboBox(body)
        self._theme_combo.addItem("Dark  (default)", userData="dark")
        self._theme_combo.addItem("Light", userData="light")
        current_theme = self._settings.get("theme", "dark")
        self._theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        lay.addWidget(self._theme_combo)

        lay.addStretch()

        # ── Save / cancel ──────────────────────────────────────────────
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(80,86,120,0.06); max-height: 1px; border: none;")
        outer.addWidget(sep)

        btn_bar = QWidget(self)
        btn_bar.setAttribute(Qt.WA_StyledBackground, True)
        btn_bar.setStyleSheet("background: transparent;")
        btn_bar.setFixedHeight(64)
        btn_lay = QHBoxLayout(btn_bar)
        btn_lay.setContentsMargins(28, 0, 28, 0)
        btn_lay.setSpacing(10)
        btn_lay.addStretch()

        cancel = QPushButton("Cancel", btn_bar)
        cancel.setObjectName("secondaryButton")
        cancel.setMinimumHeight(40)
        cancel.setMinimumWidth(90)
        cancel.clicked.connect(self.reject)
        btn_lay.addWidget(cancel)

        save = QPushButton("Save Changes", btn_bar)
        save.setMinimumHeight(40)
        save.setMinimumWidth(130)
        save.clicked.connect(self._save)
        btn_lay.addWidget(save)
        outer.addWidget(btn_bar)

    # ── Avatar helpers ──────────────────────────────────────────────────────────

    def _render_avatar(self):
        av = self._settings.get("profile_picture", "") or session.avatar_url
        if av and av.startswith("data:image"):
            try:
                import base64
                _, enc = av.split(",", 1)
                pix = QPixmap()
                pix.loadFromData(base64.b64decode(enc))
                out = QPixmap(96, 96)
                out.fill(Qt.transparent)
                p = QPainter(out)
                p.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, 96, 96)
                p.setClipPath(path)
                p.drawPixmap(0, 0, pix.scaled(96, 96, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                p.end()
                self._avatar_lbl.setPixmap(out)
                self._avatar_lbl.setStyleSheet("border-radius: 48px; background: transparent;")
                return
            except Exception:
                pass
        name = self._settings.get("profile_name", "") or session.display_name or "?"
        self._avatar_lbl.setText(name[0].upper())
        self._avatar_lbl.setStyleSheet(
            "background: rgba(139,92,246,0.18); border-radius: 48px; "
            "font-weight: 700; font-size: 36px; color: #8B5CF6;"
        )

    def _pick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Photo", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        try:
            from gui.image_cropper import ImageCropper
            cropper = ImageCropper(path, self)
            if cropper.exec() == QDialog.Accepted and cropper.b64_result:
                self._settings["profile_picture"] = cropper.b64_result
                self._render_avatar()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load image:\n{e}")

    def _remove_avatar(self):
        self._settings["profile_picture"] = ""
        self._render_avatar()

    # ── Audio ───────────────────────────────────────────────────────────────────

    def _populate_devices(self):
        mics = MicrophoneReader.get_input_devices()
        self._mic_combo.addItem("Default Microphone", userData=None)
        sel_mic = self._settings.get("microphone_index")
        for m in mics:
            self._mic_combo.addItem(f"{m['name']} ({m['channels']} ch)", userData=m["index"])
            if sel_mic is not None and m["index"] == sel_mic:
                self._mic_combo.setCurrentIndex(self._mic_combo.count() - 1)

        speakers = SpeakerMixer.get_output_devices()
        self._spk_combo.addItem("Default Speaker", userData=None)
        sel_spk = self._settings.get("speaker_index")
        for s in speakers:
            self._spk_combo.addItem(s["name"], userData=s["index"])
            if sel_spk is not None and s["index"] == sel_spk:
                self._spk_combo.setCurrentIndex(self._spk_combo.count() - 1)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Downloads Folder", self._dir_input.text()
        )
        if folder:
            self._dir_input.setText(folder)

    # ── Save ─────────────────────────────────────────────────────────────────────

    def _save(self):
        download_dir = self._dir_input.text().strip()
        if not download_dir:
            QMessageBox.warning(self, "Settings", "Download folder cannot be empty.")
            return

        name  = self._name_input.text().strip()
        bio   = self._bio_input.toPlainText().strip()
        links = self._links_input.toPlainText().strip()

        self._settings["profile_name"]       = name
        self._settings["profile_bio"]        = bio
        self._settings["profile_links"]      = links
        self._settings["microphone_index"]   = self._mic_combo.currentData()
        self._settings["speaker_index"]      = self._spk_combo.currentData()
        self._settings["download_directory"] = download_dir

        new_theme    = self._theme_combo.currentData()
        theme_changed = self._settings.get("theme") != new_theme
        self._settings["theme"] = new_theme

        if theme_changed:
            import PySide6.QtWidgets as _qw
            from gui.styles import LIGHT_STYLESHEET, DARK_STYLESHEET
            app = _qw.QApplication.instance()
            stylesheet = LIGHT_STYLESHEET if new_theme == "light" else DARK_STYLESHEET
            app.setStyleSheet(stylesheet)
            for w in app.topLevelWidgets():
                w.setStyleSheet(stylesheet)

        save_settings(self._settings)

        if name:    session.display_name = name
        if bio:     session.bio = bio
        if links:   session.links = links
        av = self._settings.get("profile_picture", "")
        if av:      session.avatar_url = av
        session.update_profile()

        try:
            room_service.mixer.set_device(self._settings["speaker_index"])
            if room_service.voice_sender and room_service.voice_sender.mic:
                room_service.voice_sender.mic.set_device(self._settings["microphone_index"])
        except Exception as e:
            logger.debug(f"Audio hot-swap: {e}")

        self.accept()
