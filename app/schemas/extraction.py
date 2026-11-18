from typing import List, Optional

from pydantic import BaseModel, Field


class InvoiceDetails(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    purchase_order_number: Optional[str] = None
    invoice_type: Optional[str] = None
    currency: Optional[str] = None
    payment_terms: Optional[str] = None


class Party(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class LineItem(BaseModel):
    description: Optional[str] = None
    product_name: Optional[str] = None
    hsn_sac: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    discount: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    line_total: Optional[float] = None


class TaxSummary(BaseModel):
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    cess: Optional[float] = None
    total_tax: Optional[float] = None
    discount: Optional[float] = None
    shipping: Optional[float] = None


class Amounts(BaseModel):
    taxable_amount: Optional[float] = None
    grand_total: Optional[float] = None
    amount_paid: Optional[float] = None
    balance_due: Optional[float] = None
    amount_in_words: Optional[str] = None


class PaymentInfo(BaseModel):
    bank_name: Optional[str] = None
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    upi_id: Optional[str] = None
    instructions: Optional[str] = None


class ExtractionMetadata(BaseModel):
    status: str = "needs_review"
    confidence: float = 0.0
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class InvoiceExtraction(BaseModel):
    document_type: str = "invoice"
    invoice_details: InvoiceDetails = Field(default_factory=InvoiceDetails)
    supplier: Party = Field(default_factory=Party)
    customer: Party = Field(default_factory=Party)
    line_items: List[LineItem] = Field(default_factory=list)
    tax_summary: TaxSummary = Field(default_factory=TaxSummary)
    amounts: Amounts = Field(default_factory=Amounts)
    payment: PaymentInfo = Field(default_factory=PaymentInfo)
    extraction_metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)