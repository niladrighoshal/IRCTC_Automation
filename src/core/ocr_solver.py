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

# Suppress warnings from libraries
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Initialize reader as a global variable, to be loaded only once when first needed.
reader = None
ALLOWED_CHARS = string.ascii_letters + string.digits

def _initialize_reader(use_gpu=True, logger=None):
    """
    Initializes the EasyOCR reader instance. This is called 'lazily' (only when needed)
    to avoid loading the model into memory if OCR is not used.
    """
    global reader
    if reader is None:
        if logger:
            logger.info(f"Initializing EasyOCR reader... (GPU: {use_gpu})")
        else:
            print(f"Initializing EasyOCR reader... (GPU: {use_gpu})")

        # Suppress stdout during OCR initialization to keep console clean
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

        try:
            reader = easyocr.Reader(['en'], gpu=use_gpu)
        finally:
            # Restore stdout
            sys.stdout = old_stdout

        if logger:
            logger.info("EasyOCR reader initialized successfully.")
        else:
            print("EasyOCR reader initialized successfully.")

def _url_to_image(source, logger=None):
    """Converts an image URL or a base64 data URI to a PIL Image object."""
    source = source.strip()
    try:
        # Handle base64-encoded data URIs
        if source.lower().startswith("data:image/"):
            _, b64_data = source.split(",", 1)
            image_data = base64.b64decode(b64_data.strip())
            return Image.open(io.BytesIO(image_data)).convert("RGB")
        # Handle standard HTTP/HTTPS URLs
        elif source.lower().startswith("http"):
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        if logger:
            logger.error(f"Failed to convert source to image: {e}")
        else:
            print(f"Failed to convert source to image: {e}", file=sys.stderr)
        return None

    if logger:
        logger.error(f"Unsupported image source format: {source[:30]}...")
    return None

def _preprocess_image(pil_img):
    """Applies a series of filters to the image to make text more readable for OCR."""
    gray = pil_img.convert("L")
    contrast = ImageOps.autocontrast(gray, cutoff=2)
    sharpened = contrast.filter(ImageFilter.SHARPEN)
    return sharpened

def solve_captcha(image_source, use_gpu=True, logger=None):
    """
    Main function to solve a captcha from an image source (URL or data URI).

    Args:
        image_source (str): The URL or data URI of the captcha image.
        use_gpu (bool): Whether to use GPU for OCR processing.
        logger: An optional logger instance.

    Returns:
        The solved captcha text as a string, or an empty string if it fails.
    """
    start_time = time.time()
    try:
        # Step 1: Ensure the OCR reader is initialized
        _initialize_reader(use_gpu, logger)

        # Step 2: Download and convert the image
        img = _url_to_image(image_source, logger)
        if not img:
            return ""

        # Step 3: Preprocess the image for better OCR accuracy
        processed_img = _preprocess_image(img)

        # Step 4: Run OCR on the processed image
        img_np = np.array(processed_img)
        result = reader.readtext(
            img_np,
            decoder='greedy',
            batch_size=1,
            detail=0,
            paragraph=True
        )

        if result:
            text = ''.join(result)
            # Clean the text to keep only allowed characters
            cleaned_text = ''.join(ch for ch in text if ch in ALLOWED_CHARS)
            if logger:
                duration = time.time() - start_time
                logger.info(f"OCR solved captcha as '{cleaned_text}' in {duration:.2f}s.")
            return cleaned_text

        if logger:
            logger.warning("OCR could not detect any text in the captcha.")
        return ""

    except Exception as e:
        if logger:
            logger.error(f"An exception occurred during captcha solving: {e}", exc_info=True)
        else:
            print(f"An exception occurred during captcha solving: {e}", file=sys.stderr)
        return ""

if __name__ == '__main__':
    # Example usage for testing the module directly
    if len(sys.argv) > 1:
        test_image_url = sys.argv[1]
        print(f"Testing with URL from command line: {test_image_url}")
    else:
        # A public domain example of a captcha image for testing
        test_image_url = "https://www.fourmilab.ch/cgi-bin/Captchator?id=eb463a55e396294723934151743844885567304f"
        print(f"Testing with default URL: {test_image_url}")

    # Check if GPU is available on the system
    gpu_is_available = torch.cuda.is_available() or (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available())
    print(f"GPU available on this system: {gpu_is_available}")

    # Solve the captcha
    solved_text = solve_captcha(test_image_url, use_gpu=gpu_is_available)
    print(f"\nSolved Text: '{solved_text}'")
