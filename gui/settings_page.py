import base64
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFileDialog, QMessageBox, QFrame, QScrollArea,
                               QPushButton)
from PySide6.QtCore import Qt, QPoint, QPointF, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QPen
from qfluentwidgets import ComboBox, LineEdit, TextEdit, SmoothScrollArea

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


class DraggableAvatarWidget(QWidget):
    def __init__(self, size=96, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.size_val = size
        self._original_pixmap = None
        
        self.cx = 0.0
        self.cy = 0.0
        self.scale = 1.0
        self.rotation = 0.0
        
        self._dragging = False
        self._last_pos = QPoint()
        self.setCursor(Qt.OpenHandCursor)

    def set_image(self, pixmap: QPixmap):
        self._original_pixmap = pixmap
        self.cx = pixmap.width() / 2.0
        self.cy = pixmap.height() / 2.0
        self.scale = self.size_val / min(pixmap.width(), pixmap.height())
        self.rotation = 0.0
        self.update()
        
    def clear(self):
        self._original_pixmap = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._original_pixmap:
            self._dragging = True
            self._last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._dragging and self._original_pixmap:
            delta = event.pos() - self._last_pos
            self._last_pos = event.pos()
            
            import math
            rad = math.radians(-self.rotation)
            dx = delta.x() * math.cos(rad) - delta.y() * math.sin(rad)
            dy = delta.x() * math.sin(rad) + delta.y() * math.cos(rad)
            
            self.cx -= dx / self.scale
            self.cy -= dy / self.scale
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.OpenHandCursor)
            
    def wheelEvent(self, event):
        if not self._original_pixmap: return
        angle = event.angleDelta().y()
        if angle > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
            
        min_scale = self.size_val / min(self._original_pixmap.width(), self._original_pixmap.height())
        if self.scale < min_scale:
            self.scale = min_scale
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Draw circular background
        path = QPainterPath()
        path.addEllipse(0, 0, self.size_val, self.size_val)
        painter.setClipPath(path)
        painter.fillRect(0, 0, self.size_val, self.size_val, QColor(139, 92, 246, 40))
        
        if self._original_pixmap:
            painter.translate(self.size_val/2, self.size_val/2)
            painter.rotate(self.rotation)
            painter.scale(self.scale, self.scale)
            painter.translate(-self.cx, -self.cy)
            painter.drawPixmap(0, 0, self._original_pixmap)
        else:
            name = session.display_name or "?"
            initial = name[0].upper()
            painter.setPen(QColor(139, 92, 246))
            font = painter.font()
            font.setPixelSize(36)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(0, 0, self.size_val, self.size_val, Qt.AlignCenter, initial)
            
        # Draw border
        painter.setClipping(False)
        painter.resetTransform()
        painter.setPen(QPen(QColor(139, 92, 246), 2))
        painter.drawEllipse(1, 1, self.size_val-2, self.size_val-2)

    def get_cropped_base64(self) -> str:
        if not self._original_pixmap: return ""
        target = QPixmap(self.size_val, self.size_val)
        target.fill(Qt.transparent)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        path = QPainterPath()
        path.addEllipse(0, 0, self.size_val, self.size_val)
        painter.setClipPath(path)
        
        painter.translate(self.size_val/2, self.size_val/2)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
        painter.translate(-self.cx, -self.cy)
        painter.drawPixmap(0, 0, self._original_pixmap)
        painter.end()
        
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        target.save(buf, "PNG")
        import base64
        b64 = base64.b64encode(ba.data()).decode("utf-8")
        return f"data:image/png;base64,{b64}"


class SettingsPage(QWidget):
    def __init__(self, on_close, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #121212;")
        self.on_close = on_close

        self._settings = load_settings()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        header = QWidget(self)
        header.setFixedHeight(64)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(32, 0, 32, 0)
        title = QLabel("⚙  Settings & Profile")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8F8F2; background: transparent;")
        h_lay.addWidget(title)
        h_lay.addStretch()
        outer.addWidget(header)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background: rgba(255,255,255,0.05); max-height: 1px; border: none;")
        outer.addWidget(sep1)

        # ── Scroll body ────────────────────────────────────────────────
        scroll = SmoothScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        body.setAttribute(Qt.WA_StyledBackground, True)
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(40, 24, 40, 40)
        lay.setSpacing(10)
        scroll.setWidget(body)

        # ══════════════════════════════════════════════════════════ PROFILE
        lay.addWidget(_section("Profile", body))
        lay.addWidget(_divider(body))

        # ── Big avatar ─────────────────────────────────────────────────
        av_area = QWidget(body)
        av_area.setAttribute(Qt.WA_StyledBackground, True)
        av_area.setStyleSheet("""
            QWidget {
                background: rgba(139,92,246,0.05);
                border: 1px dashed rgba(139,92,246,0.25);
                border-radius: 14px;
            }
        """)
        av_lay = QVBoxLayout(av_area)
        av_lay.setContentsMargins(20, 20, 20, 16)
        av_lay.setSpacing(12)
        av_lay.setAlignment(Qt.AlignCenter)

        self._avatar_widget = DraggableAvatarWidget(96, av_area)
        self._render_avatar()
        av_lay.addWidget(self._avatar_widget, alignment=Qt.AlignCenter)

        av_hint = QLabel("Profile photo visible to other members. Scroll to zoom, drag to pan.", av_area)
        av_hint.setStyleSheet("font-size: 12px; color: #98A0C6; background: transparent; border: none;")
        av_hint.setAlignment(Qt.AlignCenter)
        av_lay.addWidget(av_hint)

        from PySide6.QtWidgets import QSlider
        self.rot_slider = QSlider(Qt.Horizontal, av_area)
        self.rot_slider.setRange(0, 360)
        self.rot_slider.setValue(0)
        self.rot_slider.setToolTip("Rotate Photo")
        self.rot_slider.setStyleSheet("QSlider::handle:horizontal { background: #8B5CF6; border-radius: 6px; width: 12px; margin: -4px 0; } QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; }")
        self.rot_slider.valueChanged.connect(self._on_avatar_rotate)
        
        rot_lay = QHBoxLayout()
        rot_icon = QLabel("↻")
        rot_icon.setStyleSheet("color: #98A0C6; background: transparent; font-size: 16px;")
        rot_lay.addWidget(rot_icon)
        rot_lay.addWidget(self.rot_slider)
        av_lay.addLayout(rot_lay)


        av_btns = QHBoxLayout()
        av_btns.setSpacing(8)
        self._change_av_btn = QPushButton("📷  Upload Photo", av_area)
        self._change_av_btn.setMinimumHeight(38)
        self._change_av_btn.setStyleSheet("""
            QPushButton {
                background: #252526; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; color: white; font-weight: bold; border: none;
            }
            QPushButton:hover { background: #2D2D30; border: 1px solid white; }
        """)
        self._change_av_btn.clicked.connect(self._pick_avatar)
        av_btns.addWidget(self._change_av_btn)

        self._remove_av_btn = QPushButton("Remove", av_area)
        self._remove_av_btn.setMinimumHeight(38)
        self._remove_av_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248,113,113,0.1); color: #f87171;
                border-radius: 6px; font-weight: bold; border: none;
            }
            QPushButton:hover { background: rgba(248,113,113,0.2); }
        """)
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
        browse_btn.setMinimumHeight(38)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: #252526; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; color: white; font-weight: bold;
            }
            QPushButton:hover { background: #2D2D30; border: 1px solid white; }
        """)
        browse_btn.clicked.connect(self._browse_folder)
        dir_row.addWidget(self._dir_input)
        dir_row.addWidget(browse_btn)
        lay.addLayout(dir_row)

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
        btn_lay.setContentsMargins(32, 0, 32, 0)
        btn_lay.setSpacing(10)
        btn_lay.addStretch()
        
        cancel = QPushButton("Cancel", btn_bar)
        cancel.setMinimumHeight(40)
        cancel.setMinimumWidth(90)
        cancel.setStyleSheet("""
            QPushButton {
                background: #252526; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; color: white; font-weight: bold;
            }
            QPushButton:hover { background: #2D2D30; border: 1px solid white; }
        """)
        cancel.clicked.connect(self.on_close)
        btn_lay.addWidget(cancel)

        save = QPushButton("Save Changes", btn_bar)
        save.setMinimumHeight(40)
        save.setMinimumWidth(130)
        save.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; color: white; font-weight: bold;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        save.clicked.connect(self._save)
        btn_lay.addWidget(save)
        outer.addWidget(btn_bar)

    # ── Avatar helpers ──────────────────────────────────────────────────────────

    def _render_avatar(self):
        av_data = self._settings.get("profile_avatar", "") or session.avatar_url
        if av_data and av_data.startswith("data:image"):
            try:
                _, enc = av_data.split(",", 1)
                b = base64.b64decode(enc)
                pix = QPixmap()
                pix.loadFromData(b)
                if not pix.isNull():
                    self._avatar_widget.set_image(pix)
            except Exception as e:
                logger.error(f"Failed to load avatar data: {e}")
                self._avatar_widget.clear()
        else:
            self._avatar_widget.clear()

    def _on_avatar_rotate(self, val):
        self._avatar_widget.rotation = float(val)
        self._avatar_widget.update()

    def _pick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Picture", "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            pix = QPixmap(path)
            if pix.isNull():
                QMessageBox.warning(self, "Invalid Image", "Could not load the selected image.")
                return
            self._avatar_widget.set_image(pix)

    def _remove_avatar(self):
        self._avatar_widget.clear()


    # ── Audio helpers ───────────────────────────────────────────────────────────

    def _populate_devices(self):
        # Mics
        try:
            mics = MicrophoneReader.list_devices()
            self._mic_combo.clear()
            self._mic_combo.addItem("Default Microphone", userData="")
            current_mic = self._settings.get("mic_device", "")
            idx_to_select = 0
            for i, m in enumerate(mics, start=1):
                self._mic_combo.addItem(m, userData=m)
                if m == current_mic:
                    idx_to_select = i
            self._mic_combo.setCurrentIndex(idx_to_select)
        except Exception as e:
            logger.error(f"Error listing mics: {e}")

        # Speakers
        try:
            spks = SpeakerMixer.list_devices()
            self._spk_combo.clear()
            self._spk_combo.addItem("Default Speaker", userData="")
            current_spk = self._settings.get("speaker_device", "")
            idx_to_select = 0
            for i, s in enumerate(spks, start=1):
                self._spk_combo.addItem(s, userData=s)
                if s == current_spk:
                    idx_to_select = i
            self._spk_combo.setCurrentIndex(idx_to_select)
        except Exception as e:
            logger.error(f"Error listing speakers: {e}")

    # ── Folder helpers ──────────────────────────────────────────────────────────

    def _browse_folder(self):
        import os
        start_dir = self._dir_input.text() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Select Download Folder", start_dir)
        if path:
            self._dir_input.setText(path)

    # ── Save ────────────────────────────────────────────────────────────────────

    def _save(self):
        # Update settings dict
        self._settings["profile_name"] = self._name_input.text().strip()
        self._settings["profile_bio"] = self._bio_input.toPlainText().strip()
        self._settings["profile_links"] = self._links_input.toPlainText().strip()
        self._settings["download_directory"] = self._dir_input.text().strip()
        self._settings["mic_device"] = self._mic_combo.currentData()
        self._settings["speaker_device"] = self._spk_combo.currentData()
        
        # Save cropped avatar
        if self._avatar_widget.pixmap:
            self._settings["profile_avatar"] = self._avatar_widget.get_cropped_base64()
        else:
            self._settings["profile_avatar"] = ""

        # Commit to disk
        save_settings(self._settings)

        # Update session immediately
        session.display_name = self._settings["profile_name"]
        session.avatar_url = self._settings["profile_avatar"]

        # Push presence to host if currently in a room
        if room_service.current_room_id:
            logger.info("Pushing profile update to host...")
            from network.client import chat_client
            chat_client.send_presence_update()
            
        self.on_close()
