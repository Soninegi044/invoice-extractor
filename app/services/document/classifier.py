from pathlib import Path

import fitz


def classify_document(file_path: str) -> dict:
    """Return {'type': 'digital_pdf' | 'scanned_pdf' | 'image', 'page_count': int}"""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(file_path)
        page_count = doc.page_count
        total_text = sum(len(page.get_text("text").strip()) for page in doc)
        doc.close()
        kind = "digital_pdf" if total_text > 100 else "scanned_pdf"
        return {"type": kind, "page_count": page_count}
    return {"type": "image", "page_count": 1}