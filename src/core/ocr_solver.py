import io, base64, string, requests, numpy as np, easyocr, warnings, os, sys, torch, time
from PIL import Image, ImageOps, ImageFilter

warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

reader = None
ocr_ready = False
ALLOWED_CHARS = string.ascii_letters + string.digits

def initialize_ocr_model(use_gpu=True):
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

def _preprocess_image(pil_img):
    gray = pil_img.convert("L")
    contrast = ImageOps.autocontrast(gray, cutoff=2)
    return contrast.filter(ImageFilter.SHARPEN)

def solve_captcha(image_source, use_gpu=True, logger=None):
    start_time = time.time()
    try:
        # If OCR model is not ready, initialize it with the provided setting.
        # This ensures the model is loaded only once with the correct device.
        if not ocr_ready:
            if logger: logger.info(f"Initializing OCR model (GPU: {use_gpu})...")
            initialize_ocr_model(use_gpu=use_gpu)
            # Wait for the model to be ready after initialization
            while not ocr_ready: time.sleep(0.2)

        img = _url_to_image(image_source, logger)
        if not img: return ""

        processed_img = _preprocess_image(img)
        result = reader.readtext(np.array(processed_img), decoder='greedy', batch_size=1, detail=0, paragraph=True)

        if result:
            cleaned_text = ''.join(ch for ch in ''.join(result) if ch in ALLOWED_CHARS)
            if logger: logger.info(f"OCR solved as '{cleaned_text}' in {time.time() - start_time:.2f}s.")
            return cleaned_text

        if logger: logger.warning("OCR could not detect any text.")
        return ""
    except Exception as e:
        if logger: logger.error(f"Captcha solving exception: {e}", exc_info=True)
        return ""
