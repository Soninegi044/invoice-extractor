import json
import logging
import fitz
from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_log

from app.core.config import settings

logger = logging.getLogger(__name__)
_client = None

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in .env file")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client

# 🔥 UPDATED PROMPT: Hindi, Handwritten aur Local bills ke liye smart rules add kar diye gaye hain
EXTRACTION_PROMPT = """You are an expert invoice and bill data extraction system.
Extract structured data from the provided image/document.

Rules:
- Return ONLY valid JSON matching the schema below.
- Use null for missing values. DO NOT invent data.
- Dates should be in YYYY-MM-DD format if possible.
- Extract ALL line items.
- **STRICT TRANSLATION:** If the item descriptions are in Hindi or any regional language, you MUST translate them into English. (e.g., 'मशरूम' -> 'Mushroom', 'आलू' -> 'Potato').
- **SCRIBBLES & CORRECTIONS:** Handwritten bills often have crossed-out numbers or scribbles. If a number (like rate) is crossed out or messy, DO NOT guess it. Instead, look at the rightmost 'Total/Amount' column for that row. Extract the clear final amount (e.g., 400) and leave the 'unit_price' as null if you cannot read it.
- **HANDWRITTEN MATH CHECK:** Before outputting the 'grand_total', cross-check it with the line items. 
- **EXTRA CHARGES:** If there is an extra amount written before the total (like '+1990' or 'Previous Balance'), add it as a new line item with the description "Extra Charge".
- **ROW ALIGNMENT:** Pay extreme attention to the table rows and columns. Do not mix numbers from one row into another. Ensure the total belongs to the correct item.
- If the visual total contradicts the math, prefer the mathematically correct number from the bottom of the bill.

Schema:
{
  "document_type": "invoice" | "bill" | "receipt" | "other",
  "invoice_details": {"invoice_number": str|null, "invoice_date": str|null, "currency": str|null},
  "supplier": {"name": str|null, "address": str|null},
  "line_items": [
    {
      "description": str|null, 
      "quantity": number|null, 
      "unit": str|null, 
      "unit_price": number|null, 
      "line_total": number|null
    }
  ],
  "amounts": {"grand_total": number|null}
}
"""

def _parse(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)

# Custom Exception to handle only retryable errors
class RetryableAPIError(Exception):
    pass

@retry(
    retry=retry_if_exception_type(RetryableAPIError),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3), # Har model par max 3 baar try karega
    before=before_log(logger, logging.WARNING),
    reraise=True
)
def _call_single_model(client, model_name: str, parts: list) -> dict:
    try:
        logger.info(f"Attempting extraction with model: {model_name}")
        resp = client.models.generate_content(
            model=model_name,
            contents=parts + [EXTRACTION_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        return _parse(resp.text)
        
    except APIError as e:
        status = getattr(e, 'status_code', getattr(e, 'code', 0))
        
        # 503: High Demand, 429: Rate Limit, 504: Timeout
        if status in [503, 429, 504]:
            logger.warning(f"Model {model_name} gave retryable error {status}. Retrying with backoff...")
            raise RetryableAPIError(f"Temporary error {status} on {model_name}")
        
        # 400: Bad Request, 403: Auth Error (No retry)
        elif status in [400, 403]:
            logger.error(f"Permanent error {status} on {model_name}. Not retrying. {e}")
            raise e 
            
        else:
            logger.error(f"Unknown API error on {model_name}: {e}")
            raise e

def _call(parts: list):
    client = _get_client()
    models_to_try = [m.strip() for m in settings.gemini_models.split(",")]
    
    for model_name in models_to_try:
        try:
            # Yeh function andar hi retry aur backoff handle karega
            result = _call_single_model(client, model_name, parts)
            logger.info(f"Successfully extracted using: {model_name}")
            return result, model_name
            
        except Exception as e:
            # Agar retries khatam ho gaye (ya permanent error aaya), toh next model par jao
            logger.warning(f"Model {model_name} completely failed. Moving to next fallback.")
            continue

    logger.error(f"All Gemini models failed completely.")
    return None, None


def extract_invoice_from_image(image_bytes: bytes, mime_type: str):
    return _call([types.Part.from_bytes(data=image_bytes, mime_type=mime_type)])

def extract_invoice_from_pdf(file_path: str, max_pages: int = 5):
    doc = fitz.open(file_path)
    parts: list = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=200)
        parts.append(types.Part.from_bytes(data=pix.tobytes("png"), mime_type="image/png"))
    doc.close()
    return _call(parts)