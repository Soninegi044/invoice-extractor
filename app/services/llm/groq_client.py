import json
import logging

from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)
_client: Groq | None = None


def _get_client() -> Groq | None:
    global _client
    if not settings.groq_api_key:
        return None
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def semantic_check(extracted: dict, existing_warnings: list[str]) -> list[str]:
    """Optional semantic-inconsistency pass. Returns extra warnings (may be empty)."""
    client = _get_client()
    if client is None:
        return []
    prompt = f"""Review this extracted invoice JSON and flag ONLY clear semantic inconsistencies
(e.g. supplier/customer swapped, GSTIN country mismatch, impossible dates, missing totals).

Return JSON: {{"warnings": ["..."]}}. Empty list if nothing is wrong.
Be conservative — do not invent issues.

Invoice JSON:
{json.dumps(extracted)[:8000]}

Deterministic warnings already found (do not repeat):
{json.dumps(existing_warnings)}
"""
    try:
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return json.loads(resp.choices[0].message.content).get("warnings", []) or []
    except Exception:
        logger.warning("Groq semantic check failed; skipping", exc_info=True)
        return []