import io
import base64
import string
import requests
import numpy as np
from PIL import Image, ImageOps, ImageFilter
import easyocr
import warnings
import os
import sys
import torch
import time

warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

reader = None
ocr_ready = False
ALLOWED_CHARS = string.ascii_letters + string.digits

def initialize_ocr_model(use_gpu=True):
    """Target function for background thread to initialize the OCR model."""
    global reader, ocr_ready
    if reader is None:
        print("Background OCR model loading started...")
        old_stdout, sys.stdout = sys.stdout, open(os.devnull, 'w')
        try:
            reader = easyocr.Reader(['en'], gpu=use_gpu)
            ocr_ready = True
            print("Background OCR model loading complete.")
        finally:
            sys.stdout = old_stdout

def _url_to_image(source, logger=None):
    source = source.strip()
    try:
        if source.lower().startswith("data:image/"):
            _, b64_data = source.split(",", 1)
            return Image.open(io.BytesIO(base64.b64decode(b64_data.strip()))).convert("RGB")
        elif source.lower().startswith("http"):
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        if logger: logger.error(f"Failed to convert source to image: {e}")
        return None
    return None

def _preprocess_image(pil_img):
    gray = pil_img.convert("L")
    contrast = ImageOps.autocontrast(gray, cutoff=2)
    sharpened = contrast.filter(ImageFilter.SHARPEN)
    return sharpened

def solve_captcha(image_source, use_gpu=True, logger=None):
    start_time = time.time()
    try:
        if not ocr_ready:
            if logger: logger.info("Waiting for OCR model to load...")
            while not ocr_ready:
                time.sleep(0.2)

        img = _url_to_image(image_source, logger)
        if not img: return ""

        processed_img = _preprocess_image(img)
        img_np = np.array(processed_img)
        result = reader.readtext(
            img_np,
            decoder='greedy', batch_size=1, detail=0, paragraph=True
        )

        if result:
            cleaned_text = ''.join(ch for ch in ''.join(result) if ch in ALLOWED_CHARS)
            if logger:
                duration = time.time() - start_time
                logger.info(f"OCR solved captcha as '{cleaned_text}' in {duration:.2f}s.")
            return cleaned_text

        if logger: logger.warning("OCR could not detect any text in the captcha.")
        return ""
    except Exception as e:
        if logger: logger.error(f"An exception occurred during captcha solving: {e}", exc_info=True)
        return ""
