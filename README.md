# Invoice Extractor MVP

Simplified MVP of the AI invoice-extraction system.

## Dependencies

- Python 3.11+
- PostgreSQL 14+
- Tesseract OCR (with `eng` language data)

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill API keys + DB URL
uvicorn app.main:app --reload