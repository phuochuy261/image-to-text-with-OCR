"""Named configurations shared by the local UI."""
CONFIGURATIONS = {
    "tesseract": ("Tesseract OCR", "tesseract", "small"),
    "tesseract_vietocr": ("Tesseract OCR + VietOCR", "tesseract_vietocr", "small"),
    "paddle_v5_vietocr": ("PaddleOCR v5 + VietOCR", "hybrid_v5", "small"),
    "v6_tiny_vietocr": ("PP-OCRv6 Tiny + VietOCR", "hybrid", "tiny"),
    "v6_small_vietocr": ("PP-OCRv6 Small + VietOCR", "hybrid", "small"),
    "v6_medium_vietocr": ("PP-OCRv6 Medium + VietOCR", "hybrid", "medium"),
    "v6_medium": ("PP-OCRv6 Medium", "ppocrv6", "medium"),
    "v6_small": ("PP-OCRv6 Small", "ppocrv6", "small"),
    "v6_tiny": ("PP-OCRv6 Tiny", "ppocrv6", "tiny"),
    "v5": ("PP-OCRv5 — Latin / tiếng Việt", "ppocrv5", "small"),
    "v3": ("PP-OCRv3 — Latin / tiếng Việt", "ppocrv3", "small"),
}
