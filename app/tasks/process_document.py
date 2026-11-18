import logging
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.schemas.extraction import InvoiceExtraction
from app.services.document.classifier import classify_document
from app.services.extraction.ocr import ocr_image_file, ocr_pdf_pages
from app.services.llm.groq_client import semantic_check
from app.services.validation.invoice_validator import validate_invoice
from app.services.vision.gemini import (
    extract_invoice_from_image,
    extract_invoice_from_pdf,
)
# 🔥 ChromaDB ki jagah NuDB import kiya hai
from app.services.database.nuclia_db import push_to_nuclia

logger = logging.getLogger(__name__)


def process_document(document_id: str) -> None:
    # 🔥 STEP 1: Connection kholo, status update karo, aur band kar do
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            return
        doc.processing_status = "processing"
        doc.error_message = None
        db.commit()
        
        # Important variables copy kar lo
        file_path = doc.file_path
        doc_type = classify_document(file_path)
    except Exception as e:
        logger.error(f"Error in initial DB setup: {e}")
        db.close()
        return
    finally:
        db.close() # AI processing se pehle DB connection free kar do

    # 🔥 STEP 2: AI Processing (Bina DB connection ke)
    ocr_conf: float | None = None
    ext = Path(file_path).suffix.lower()
    model_used = "unknown"
    extracted = None

    try:
        if doc_type["type"] == "image":
            _, ocr_conf = ocr_image_file(file_path)
            mime = "image/png" if ext == ".png" else "image/jpeg"
            with open(file_path, "rb") as f:
                extracted, model_used = extract_invoice_from_image(f.read(), mime)

        elif doc_type["type"] == "scanned_pdf":
            pages = ocr_pdf_pages(file_path)
            if pages:
                ocr_conf = sum(p["ocr_confidence"] for p in pages) / len(pages)
            extracted, model_used = extract_invoice_from_pdf(file_path)

        else:  # digital_pdf
            extracted, model_used = extract_invoice_from_pdf(file_path)
            
    except Exception as e:
        logger.error(f"AI Extraction failed: {e}")

    # Agar saare Gemini models fail ho jayein
    if extracted is None:
        extracted = {}
        model_used = "gemini_failed"

    try:
        parsed = InvoiceExtraction(**extracted)
    except Exception as e:
        logger.warning("Schema coercion failed: %s", e)
        parsed = InvoiceExtraction()

    data = parsed.model_dump()

    # Math & Validation Fixes
    for item in data.get("line_items", []):
        qty = item.get("quantity")
        total = item.get("line_total")
        unit_price = item.get("unit_price")
        if total and qty and qty > 0 and not unit_price:
            item["unit_price"] = round(total / qty, 2)

    warnings = validate_invoice(data)
    line_items_sum = sum((item.get("line_total") or 0) for item in data.get("line_items", []))
    extracted_total = data.get("amounts", {}).get("grand_total")

    if extracted_total and line_items_sum > 0:
        if abs(extracted_total - line_items_sum) > 10: 
            warnings.append(f"Math Error: Line items sum ({line_items_sum}) does not match Grand Total ({extracted_total}).")
            
    if model_used == "gemini_failed":
        warnings.insert(0, "AI extraction completely failed. Please check API keys or try reprocessing.")

    warnings.extend(semantic_check(data, warnings))
    missing = _find_missing(data)
    confidence = _estimate_confidence(data, ocr_conf)

    status = "completed"
    if warnings or missing or confidence < 0.6:
        status = "needs_review"
    if model_used == "gemini_failed" and not data.get("invoice_details", {}).get("invoice_number"):
        status = "failed"

    data["extraction_metadata"] = {
        "status": status,
        "confidence": round(confidence, 2),
        "missing_fields": missing,
        "warnings": warnings,
    }

    # 🔥 NuDB (Nuclia) mein save karein
    success = push_to_nuclia(document_id, data)

    # 🔥 STEP 3: Naya Connection kholo aur status update karke save karo
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc:
            if success:
                doc.processing_status = status
                doc.error_message = "Data saved in NuDB"
            else:
                doc.processing_status = "failed"
                doc.error_message = "Failed to save in NuDB"
            db.commit()
    except Exception as e:
        logger.exception(f"Failed to save final status to DB: {e}")
        db.rollback()
    finally:
        db.close()


def _find_missing(data: dict) -> list[str]:
    missing: list[str] = []
    details = data.get("invoice_details") or {}
    if not details.get("invoice_number"): missing.append("invoice_details.invoice_number")
    if not details.get("invoice_date"): missing.append("invoice_details.invoice_date")
    if not details.get("currency"): missing.append("invoice_details.currency")
    if not (data.get("supplier") or {}).get("name"): missing.append("supplier.name")
    if (data.get("amounts") or {}).get("grand_total") is None: missing.append("amounts.grand_total")
    if not data.get("line_items"): missing.append("line_items")
    return missing

def _estimate_confidence(data: dict, ocr_conf: float | None) -> float:
    score = 0
    total = 5
    if (data.get("invoice_details") or {}).get("invoice_number"): score += 1
    if (data.get("invoice_details") or {}).get("invoice_date"): score += 1
    if (data.get("supplier") or {}).get("name"): score += 1
    if (data.get("amounts") or {}).get("grand_total") is not None: score += 1
    if data.get("line_items"): score += 1
    field_score = score / total
    if ocr_conf is not None:
        return round(field_score * 0.7 + ocr_conf * 0.3, 4)
    return round(field_score, 4)