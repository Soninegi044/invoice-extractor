import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.extraction import Extraction
from app.schemas.extraction import InvoiceExtraction
from app.services.document.validator import validate_file
from app.tasks.process_document import process_document

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.post("/upload")
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    validate_file(file, len(contents), settings.max_file_size_mb)

    doc_id = str(uuid.uuid4())
    ext = Path(file.filename or "").suffix.lower()
    dest = Path(settings.upload_dir) / f"{doc_id}{ext}"
    dest.write_bytes(contents)

    doc = Document(
        id=doc_id,
        original_filename=file.filename or "unknown",
        file_path=str(dest),
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        processing_status="queued",
    )
    db.add(doc)
    db.commit()

    background_tasks.add_task(process_document, doc_id)
    return {"document_id": doc_id, "status": "queued"}


@router.get("/{document_id}/status")
def get_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Not found")
    return {
        "document_id": doc.id,
        "processing_status": doc.processing_status,
        "document_type": doc.document_type,
        "error_message": doc.error_message,
    }


@router.get("/{document_id}/extraction")
def get_extraction(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Not found")
    if doc.processing_status not in ("completed", "needs_review"):
        raise HTTPException(409, f"Not ready: {doc.processing_status}")

    row = (
        db.query(Extraction)
        .filter_by(document_id=document_id)
        .order_by(Extraction.created_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(404, "No extraction found")

    return {
        "document_id": document_id,
        "extraction_id": row.id,
        "model_used": row.model_used,
        "confidence": row.confidence,
        "validation_status": row.validation_status,
        "data": row.extracted_json,
    }


@router.get("")
def list_invoices(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(Document)
        .order_by(Document.uploaded_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "document_id": d.id,
            "filename": d.original_filename,
            "status": d.processing_status,
            "type": d.document_type,
            "uploaded_at": d.uploaded_at,
        }
        for d in rows
    ]


@router.post("/{document_id}/reprocess")
def reprocess(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Not found")
    doc.processing_status = "queued"
    doc.error_message = None
    db.commit()
    background_tasks.add_task(process_document, document_id)
    return {"document_id": document_id, "status": "queued"}


@router.patch("/{document_id}/extraction")
def patch_extraction(
    document_id: str, payload: dict, db: Session = Depends(get_db)
):
    row = (
        db.query(Extraction)
        .filter_by(document_id=document_id)
        .order_by(Extraction.created_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(404, "No extraction found")

    merged = _deep_merge(row.extracted_json or {}, payload)
    try:
        merged = InvoiceExtraction(**merged).model_dump()
    except Exception as e:
        raise HTTPException(400, f"Invalid update: {e}")

    row.extracted_json = merged
    db.commit()
    return {"document_id": document_id, "updated": True}


def _deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out