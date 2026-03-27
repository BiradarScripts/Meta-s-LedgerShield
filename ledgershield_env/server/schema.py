from __future__ import annotations

FIELD_KEYS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "currency",
    "subtotal",
    "tax",
    "total",
    "po_id",
    "receipt_id",
    "bank_account",
]

DISCREPANCY_TYPES = [
    "price_mismatch",
    "quantity_mismatch",
    "missing_receipt",
    "duplicate_po_reference",
    "invalid_invoice_date",
    "total_mismatch",
    "bank_override_attempt",
    "vendor_name_spoof",
]