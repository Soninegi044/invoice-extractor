from pathlib import Path

from fastapi import HTTPException, UploadFile

ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIMES = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}


def validate_file(file: UploadFile, size_bytes: int, max_mb: int) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported extension: {ext}")
    if (file.content_type or "") not in ALLOWED_MIMES:
        raise HTTPException(400, f"Unsupported MIME type: {file.content_type}")
    if size_bytes == 0:
        raise HTTPException(400, "Empty file")
    if size_bytes > max_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large (max {max_mb} MB)")