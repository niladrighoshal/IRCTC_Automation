import sys
import io
import base64
import string
import requests
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QScrollArea, QLineEdit, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from PIL import Image, ImageOps
import easyocr
import pyperclip

ALLOWED_CHARS = string.ascii_letters + string.digits + string.punctuation

# ----------------- Helpers -----------------
def url_to_image(source):
    source = source.strip()
    # Data URI
    if source.lower().startswith("data:image/"):
        _, b64 = source.split(",", 1)
        return Image.open(io.BytesIO(base64.b64decode(b64.strip()))).convert("RGB")
    # HTTP/HTTPS
    if source.lower().startswith("http://") or source.lower().startswith("https://"):
        r = requests.get(source)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    raise ValueError("Unsupported URL. Must be HTTP/HTTPS or data URI.")

def enhance_grayscale(pil_img):
    gray = pil_img.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = ImageOps.equalize(gray)
    return gray

def run_ocr(pil_img):
    reader = easyocr.Reader(['en'])
    img_np = np.array(pil_img)  # Convert PIL -> numpy for EasyOCR
    result = reader.readtext(img_np)
    text = ''.join([res[1] for res in result])
    # Keep only allowed characters, remove spaces
    return ''.join(ch for ch in text if ch in ALLOWED_CHARS)

def pil_to_qpixmap(pil_img, max_side=800):
    w, h = pil_img.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        pil_img = pil_img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    buf = io.BytesIO()
    pil_img.save(buf, format='PNG')
    qt_img = QImage.fromData(buf.getvalue())
    return QPixmap.fromImage(qt_img)

# ----------------- GUI -----------------
class OCRApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("URL OCR")
        self.setGeometry(100, 100, 1000, 800)

        # URL input + Paste & OCR button
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter image URL or data URI...")
        self.btn_paste = QPushButton("Paste & OCR")
        self.btn_paste.clicked.connect(self.paste_and_ocr)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.url_input)
        top_layout.addWidget(self.btn_paste)

        # Scroll area for images
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)

        # OCR text display
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.scroll_area, stretch=3)
        layout.addWidget(QLabel("OCR Text:"))
        layout.addWidget(self.text_area, stretch=1)

        self.setLayout(layout)
        self._images = []

    def clear_images(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self._images = []

    def add_image(self, pil_img, caption):
        pixmap = pil_to_qpixmap(pil_img)
        self._images.append(pixmap)
        self.scroll_layout.addWidget(QLabel(caption))
        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignLeft)
        self.scroll_layout.addWidget(label)

    def paste_and_ocr(self):
        try:
            url = pyperclip.paste()
            self.url_input.setText(url)
            img = url_to_image(url)
            self.clear_images()
            self.add_image(img, "Original")
            gray = enhance_grayscale(img)
            self.add_image(gray, "Grayscale")
            text = run_ocr(gray)
            self.text_area.setPlainText(text)
            print("OCR Result:", text)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# ----------------- Main -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OCRApp()
    window.show()
    sys.exit(app.exec_())
