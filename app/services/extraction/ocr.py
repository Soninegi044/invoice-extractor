from PIL import Image, ImageFilter, ImageOps
import fitz
import pytesseract

from app.core.config import settings

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _preprocess(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img


def ocr_image(image: Image.Image) -> tuple[str, float]:
    """Return (text, avg_word_confidence_in_0_1)."""
    img = _preprocess(image)
    data = pytesseract.image_to_data(
        img, lang=settings.ocr_lang, output_type=pytesseract.Output.DICT
    )
    words: list[str] = []
    confs: list[float] = []
    for i, raw in enumerate(data["text"]):
        w = (raw or "").strip()
        if not w:
            continue
        words.append(w)
        try:
            c = float(data["conf"][i])
            if c >= 0:
                confs.append(c)
        except (ValueError, TypeError):
            pass
    text = " ".join(words)
    avg_conf = (sum(confs) / len(confs)) / 100.0 if confs else 0.0
    return text, avg_conf


def ocr_image_file(file_path: str) -> tuple[str, float]:
    with Image.open(file_path) as img:
        return ocr_image(img)


def ocr_pdf_pages(file_path: str, dpi: int = 250) -> list[dict]:
    doc = fitz.open(file_path)
    pages: list[dict] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text, conf = ocr_image(img)
        pages.append({"page": i + 1, "text": text, "ocr_confidence": conf})
    doc.close()
    return pages