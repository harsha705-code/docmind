
import easyocr
import cv2
import numpy as np
import fitz
from PIL import Image
import io

# Load OCR reader
reader = easyocr.Reader(['en'], gpu=False)


def enhance_image(image):
    """Improve image quality before OCR."""
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    enhanced = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    return enhanced


def extract_text(image):
    """Extract text and confidence scores from an image."""
    enhanced = enhance_image(image)
    results = reader.readtext(enhanced)

    extracted = []
    for box, text, confidence in results:
        extracted.append({
            "text": text,
            "confidence": float(confidence),
            "box": box
        })

    return extracted


def process_document(uploaded_file):
    """Process an uploaded image or PDF."""
    filename = uploaded_file.name.lower()
    pages = []

    if filename.endswith(".pdf"):
        pdf_bytes = uploaded_file.read()
        document = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_number, page in enumerate(document, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

            results = extract_text(image)
            page_text = "\n".join(item["text"] for item in results)

            pages.append({
                "page_number": page_number,
                "text": page_text,
                "confidence": results
            })

    elif filename.endswith((".jpg", ".jpeg", ".png")):
        image = Image.open(uploaded_file).convert("RGB")
        results = extract_text(image)
        page_text = "\n".join(item["text"] for item in results)

        pages.append({
            "page_number": 1,
            "text": page_text,
            "confidence": results
        })

    else:
        return {
            "full_text": "",
            "pages": [],
            "confidence": [],
            "status": "unsupported"
        }

    full_text = "\n\n".join(page["text"] for page in pages)
    all_confidence = [
        item for page in pages for item in page["confidence"]
    ]

    return {
        "full_text": full_text,
        "pages": pages,
        "confidence": all_confidence,
        "status": "success"
    }
