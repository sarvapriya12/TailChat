import cv2
import base64
import numpy as np
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

class ImageCropper(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zoom & Crop Profile Picture")
        self.setFixedSize(400, 500)
        self.setWindowModality(Qt.WindowModal)
        
        self.original_img = cv2.imread(image_path)
        if self.original_img is None:
            raise ValueError("Failed to load image")
            
        self.original_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2RGB)
        
        # Make the original image square by cropping the center
        h, w = self.original_img.shape[:2]
        size = min(h, w)
        y = (h - size) // 2
        x = (w - size) // 2
        self.square_img = self.original_img[y:y+size, x:x+size]
        
        self.b64_result = None
        
        layout = QVBoxLayout(self)
        
        self.preview_label = QLabel(self)
        self.preview_label.setFixedSize(300, 300)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid #7C3AED; border-radius: 150px;")
        layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(100) # 1.0x
        self.zoom_slider.setMaximum(300) # 3.0x
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_preview)
        layout.addWidget(self.zoom_slider)
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_crop = QPushButton("Crop & Save")
        self.btn_crop.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_crop)
        layout.addLayout(btn_layout)
        
        self.update_preview()
        
    def update_preview(self):
        zoom = self.zoom_slider.value() / 100.0
        h, w = self.square_img.shape[:2]
        
        crop_size = int(h / zoom)
        y = (h - crop_size) // 2
        x = (w - crop_size) // 2
        
        cropped = self.square_img[y:y+crop_size, x:x+crop_size]
        preview = cv2.resize(cropped, (300, 300), interpolation=cv2.INTER_AREA)
        
        # Save high quality base64 string for final output
        # First convert back to BGR for imencode
        bgr = cv2.cvtColor(preview, cv2.COLOR_RGB2BGR)
        ret, buf = cv2.imencode('.jpg', bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            self.b64_result = "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')
        
        # Update preview pixmap
        h_p, w_p, ch = preview.shape
        bytes_per_line = ch * w_p
        qimg = QImage(preview.data, w_p, h_p, bytes_per_line, QImage.Format_RGB888)
        
        # Mask to circle
        pixmap = QPixmap.fromImage(qimg)
        
        # Optional: Actually clip the pixmap into a circle for preview
        target = QPixmap(300, 300)
        target.fill(Qt.transparent)
        from PySide6.QtGui import QPainter, QPainterPath
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, 300, 300)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        self.preview_label.setPixmap(target)
