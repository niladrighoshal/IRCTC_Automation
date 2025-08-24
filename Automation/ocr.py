# Automation/ocr.py
import easyocr
import torch
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import base64
import io
import string

ALLOWED_CHARS = string.ascii_letters + string.digits + string.punctuation

class CaptchaSolver:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

    def preprocess_image(self, pil_img):
        gray = pil_img.convert("L")
        gray = ImageOps.autocontrast(gray, cutoff=2)
        gray = gray.filter(ImageFilter.SHARPEN)
        return gray

    def solve_captcha(self, src):
        if "base64," in src:
            _, b64 = src.split(",", 1)
            img_data = base64.b64decode(b64)
            pil_img = Image.open(io.BytesIO(img_data))
        else:
            pil_img = Image.open(src)
        processed_img = self.preprocess_image(pil_img.convert("RGB"))
        result = self.reader.readtext(np.array(processed_img), detail=0)
        text = ''.join(ch for ch in ''.join(result) if ch in ALLOWED_CHARS)
        return text, processed_img
