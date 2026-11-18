import fitz


def extract_text_from_pdf(file_path: str) -> list[dict]:
    doc = fitz.open(file_path)
    pages = [{"page": i + 1, "text": page.get_text("text")} for i, page in enumerate(doc)]
    doc.close()
    return pages