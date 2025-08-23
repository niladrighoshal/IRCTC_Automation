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
import time
import torch

# Suppress all warnings
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

ALLOWED_CHARS = string.ascii_letters + string.digits + string.punctuation

# Initialize reader as None, will be loaded when needed
reader = None

def check_gpu_available():
    """Check if GPU is available without printing warnings"""
    if torch.cuda.is_available():
        return True
    # Check for MPS (Apple Silicon)
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return True
    return False

def initialize_reader():
    """Initialize the OCR reader only when needed"""
    global reader
    if reader is None:
        # Check if GPU is available
        gpu_available = check_gpu_available()
        
        # Suppress stdout during OCR initialization
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        # Initialize reader with appropriate device
        reader = easyocr.Reader(['en'], gpu=gpu_available)
        
        # Restore stdout
        sys.stdout = old_stdout
        
        # Print device info (only once)
        if gpu_available:
            print("Using GPU acceleration", file=sys.stderr)
        else:
            print("Using CPU", file=sys.stderr)

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

def preprocess_image(pil_img):
    # Convert to grayscale
    gray = pil_img.convert("L")
    
    # Increase contrast (simpler than autocontrast+equalize)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    
    # Apply slight sharpening to enhance text
    gray = gray.filter(ImageFilter.SHARPEN)
    
    return gray

def run_ocr(pil_img):
    # Initialize reader if not already done
    initialize_reader()
    
    img_np = np.array(pil_img)  # Convert PIL -> numpy for EasyOCR
    
    # Use faster parameters for OCR
    result = reader.readtext(
        img_np, 
        decoder='greedy',  # Faster than beamsearch
        batch_size=1,      # Process as single image
        detail=0,          # Return only text, not details
        paragraph=True     # Treat as single paragraph
    )
    
    if result:
        text = ''.join(result)
        # Keep only allowed characters
        return ''.join(ch for ch in text if ch in ALLOWED_CHARS)
    return ""

# ----------------- Main Function -----------------
def process_image_url(image_url, show_time=False):
    # Start timing right at the beginning of the function
    start_time = time.time()
    
    try:
        # Convert URL to image
        img = url_to_image(image_url)
        
        # Preprocess image (simpler and faster)
        processed_img = preprocess_image(img)
        
        # Run OCR
        text = run_ocr(processed_img)
        
        if show_time:
            end_time = time.time()
            elapsed_time = end_time - start_time
            # Format time with seconds and milliseconds
            seconds = int(elapsed_time)
            milliseconds = int((elapsed_time - seconds) * 1000)
            print(f"Time taken: {seconds}s {milliseconds}ms", file=sys.stderr)
        
        return text
        
    except Exception as e:
        if show_time:
            end_time = time.time()
            elapsed_time = end_time - start_time
            seconds = int(elapsed_time)
            milliseconds = int((elapsed_time - seconds) * 1000)
            print(f"Time taken: {seconds}s {milliseconds}ms", file=sys.stderr)
        return ""

# ----------------- Main -----------------
if __name__ == "__main__":
    # Set this to True to show time taken, False to hide
    SHOW_TIME = True
    
    # Get image URL from command line argument or use default
    if len(sys.argv) > 1:
        image_url = sys.argv[1]
    else:
        # Default image URL if no argument provided
        image_url = input()
    
    # Process the image and get OCR result
    ocr_result = process_image_url(image_url, SHOW_TIME)
    
    # Print only the result
    print(ocr_result)