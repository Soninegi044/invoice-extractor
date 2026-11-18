import re
from decimal import Decimal, InvalidOperation
from typing import Optional

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EPS = Decimal("0.02")


def _d(v) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def validate_invoice(data: dict) -> list[str]:
    warnings: list[str] = []

    # --- Line items ---
    for i, item in enumerate(data.get("line_items") or []):
        qty = _d(item.get("quantity"))
        price = _d(item.get("unit_price"))
        disc = _d(item.get("discount")) or Decimal("0")
        tax = _d(item.get("tax_amount")) or Decimal("0")
        line_total = _d(item.get("line_total"))

        if qty is not None and price is not None:
            expected = qty * price - disc + tax
            if line_total is not None and abs(expected - line_total) > EPS:
                warnings.append(
                    f"line_items[{i}]: line_total {line_total} != expected {expected}"
                )
        if qty is None and price is not None and line_total is not None:
            warnings.append(f"line_items[{i}]: quantity is missing")

    # --- Tax consistency ---
    ts = data.get("tax_summary") or {}
    total_tax = _d(ts.get("total_tax"))
    components = sum(
        (_d(ts.get(k)) or Decimal("0")) for k in ("cgst", "sgst", "igst", "cess")
    )
    if total_tax is not None and abs(components - total_tax) > EPS:
        warnings.append(
            f"tax_summary: total_tax {total_tax} != sum of components {components}"
        )

    # --- Grand total ---
    amts = data.get("amounts") or {}
    subtotal = _d(ts.get("subtotal"))
    grand_total = _d(amts.get("grand_total"))
    if subtotal is not None and total_tax is not None and grand_total is not None:
        expected = subtotal + total_tax
        if abs(expected - grand_total) > EPS:
            warnings.append(
                f"amounts: grand_total {grand_total} != subtotal+total_tax {expected}"
            )

    # --- GSTIN format ---
    for party in ("supplier", "customer"):
        gstin = (data.get(party) or {}).get("gstin")
        if gstin and not GSTIN_RE.match(gstin.strip().upper()):
            warnings.append(f"{party}.gstin: '{gstin}' is not a valid GSTIN")

    # --- Date format ---
    details = data.get("invoice_details") or {}
    for field in ("invoice_date", "due_date"):
        val = details.get(field)
        if val and not DATE_RE.match(val):
            warnings.append(f"invoice_details.{field}: '{val}' is not YYYY-MM-DD")

    return warnings