import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Extraction(Base):
    __tablename__ = "invoice_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    extracted_json: Mapped[dict] = mapped_column(JSON)
    model_used: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)