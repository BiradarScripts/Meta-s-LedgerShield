"""
Multi-currency processing engine for LedgerShield.

Provides FX rate conversion, IBAN/SWIFT validation, currency mismatch
detection, and multi-currency aging report generation.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any
from .schema import normalize_text, safe_float

FX_RATES: dict[str, float] = {
    "USD": 1.0, "EUR": 1.085, "GBP": 1.265, "JPY": 0.0067, "CHF": 1.12,
    "CAD": 0.74, "AUD": 0.655, "INR": 0.012, "CNY": 0.138, "SGD": 0.745,
    "HKD": 0.128, "KRW": 0.00075, "MXN": 0.058, "BRL": 0.20, "ZAR": 0.055,
    "AED": 0.2723, "SAR": 0.2667, "THB": 0.028, "SEK": 0.096, "NOK": 0.094,
    "DKK": 0.1455, "NZD": 0.61, "TRY": 0.031, "PLN": 0.25, "CZK": 0.044,
}
SANCTIONED_CURRENCIES: set[str] = {"KPW", "SYP", "IRR", "CUP"}
FX_SPREAD_BPS = 50

_IBAN_LENGTHS: dict[str, int] = {
    "DE": 22, "GB": 22, "FR": 27, "IT": 27, "ES": 24, "NL": 18,
    "BE": 16, "AT": 20, "CH": 21, "SE": 24, "NO": 15, "DK": 18,
    "PL": 28, "CZ": 24, "IE": 22, "PT": 25, "FI": 18, "LU": 20,
    "GR": 27, "HU": 28, "RO": 24, "BG": 22, "HR": 21, "SK": 24,
    "SI": 19, "LT": 20, "LV": 21, "EE": 20, "AE": 23, "SA": 24,
}


@dataclass
class CurrencyResult:
    """Result of a currency conversion/validation operation."""
    valid: bool = True
    source_currency: str = ""
    target_currency: str = ""
    source_amount: float = 0.0
    converted_amount: float = 0.0
    fx_rate: float = 1.0
    spread_applied: bool = False
    warnings: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)


def validate_iban(iban: str) -> dict[str, Any]:
    """Validate IBAN format: length check + MOD-97 checksum."""
    cleaned = re.sub(r"\s+", "", str(iban or "")).upper()
    errors: list[str] = []
    if len(cleaned) < 5:
        return {"valid": False, "country": "", "errors": ["IBAN too short"]}
    country_code = cleaned[:2]
    if not country_code.isalpha():
        errors.append(f"Invalid country code: {country_code}")
    expected = _IBAN_LENGTHS.get(country_code)
    if expected and len(cleaned) != expected:
        errors.append(f"Expected {expected} chars for {country_code}, got {len(cleaned)}")
    rearranged = cleaned[4:] + cleaned[:4]
    numeric_str = ""
    for ch in rearranged:
        if ch.isdigit():
            numeric_str += ch
        elif ch.isalpha():
            numeric_str += str(ord(ch) - ord("A") + 10)
        else:
            errors.append(f"Invalid character: {ch}")
    if numeric_str and not errors:
        try:
            if int(numeric_str) % 97 != 1:
                errors.append("IBAN checksum failed (MOD-97)")
        except (ValueError, OverflowError):
            errors.append("IBAN numeric conversion failed")
    return {"valid": len(errors) == 0, "country": country_code, "errors": errors}


def validate_swift(swift_code: str) -> dict[str, Any]:
    """Validate SWIFT/BIC code format (8 or 11 chars)."""
    cleaned = re.sub(r"\s+", "", str(swift_code or "")).upper()
    errors: list[str] = []
    if len(cleaned) not in (8, 11):
        return {"valid": False, "bank_code": "", "country": "",
                "errors": [f"Must be 8 or 11 chars, got {len(cleaned)}"]}
    bank_code, country_code = cleaned[:4], cleaned[4:6]
    if not bank_code.isalpha():
        errors.append(f"Bank code must be alphabetic: {bank_code}")
    if not country_code.isalpha():
        errors.append(f"Country code must be alphabetic: {country_code}")
    return {"valid": len(errors) == 0, "bank_code": bank_code,
            "country": country_code, "errors": errors}


def convert_currency(amount: float, from_currency: str, to_currency: str,
                     apply_spread: bool = True) -> CurrencyResult:
    """Convert between currencies using static FX rates."""
    from_code = str(from_currency or "").upper().strip()
    to_code = str(to_currency or "").upper().strip()
    warnings, risk_flags = [], []
    from_rate = FX_RATES.get(from_code)
    to_rate = FX_RATES.get(to_code)
    for code in (from_code, to_code):
        if code in SANCTIONED_CURRENCIES:
            risk_flags.append(f"sanctioned_currency_{code.lower()}")
    if from_rate is None:
        return CurrencyResult(valid=False, source_currency=from_code,
                              target_currency=to_code, source_amount=amount,
                              warnings=[f"Unknown currency: {from_code}"],
                              risk_flags=risk_flags)
    if to_rate is None:
        return CurrencyResult(valid=False, source_currency=from_code,
                              target_currency=to_code, source_amount=amount,
                              warnings=[f"Unknown currency: {to_code}"],
                              risk_flags=risk_flags)
    raw_rate = to_rate / from_rate if from_rate > 0 else 0.0
    if apply_spread:
        effective_rate = raw_rate * (1.0 - FX_SPREAD_BPS / 10000.0)
        warnings.append(f"Spread of {FX_SPREAD_BPS}bps applied")
    else:
        effective_rate = raw_rate
    converted = round(amount * effective_rate, 2)
    usd_amount = amount * from_rate
    if usd_amount > 100_000:
        warnings.append("Large-value cross-border payment: enhanced due diligence")
    return CurrencyResult(valid=True, source_currency=from_code,
                          target_currency=to_code, source_amount=amount,
                          converted_amount=converted, fx_rate=round(effective_rate, 6),
                          spread_applied=apply_spread, warnings=warnings,
                          risk_flags=risk_flags)


def detect_currency_mismatch(invoice_currency: str, po_currency: str,
                             payment_currency: str) -> dict[str, Any]:
    """Detect currency mismatches across invoice, PO, and payment."""
    inv = normalize_text(invoice_currency).upper()
    po = normalize_text(po_currency).upper()
    pay = normalize_text(payment_currency).upper()
    mismatches = []
    if inv and po and inv != po:
        mismatches.append(f"Invoice ({inv}) != PO ({po})")
    if inv and pay and inv != pay:
        mismatches.append(f"Invoice ({inv}) != Payment ({pay})")
    if po and pay and po != pay:
        mismatches.append(f"PO ({po}) != Payment ({pay})")
    risk = "high" if len(mismatches) >= 2 else ("medium" if mismatches else "none")
    return {"has_mismatch": bool(mismatches), "mismatches": mismatches,
            "risk_level": risk, "currencies_seen": sorted({c for c in (inv, po, pay) if c})}


def generate_aging_report(invoices: list[dict[str, Any]],
                          base_currency: str = "USD") -> dict[str, Any]:
    """Generate multi-currency aging report with 30/60/90/90+ buckets."""
    buckets: dict[str, list[dict[str, Any]]] = {
        "0_30": [], "31_60": [], "61_90": [], "90_plus": []}
    total = 0.0
    for inv in invoices:
        days = int(inv.get("days_outstanding", 0) or 0)
        amount = safe_float(inv.get("amount", 0))
        curr = str(inv.get("currency", base_currency) or base_currency).upper()
        result = convert_currency(amount, curr, base_currency, apply_spread=False)
        base_amt = result.converted_amount if result.valid else amount
        entry = {"invoice_id": inv.get("invoice_id", ""), "vendor": inv.get("vendor_name", ""),
                 "original_amount": amount, "currency": curr,
                 "base_amount": round(base_amt, 2), "days": days}
        key = "0_30" if days <= 30 else "31_60" if days <= 60 else "61_90" if days <= 90 else "90_plus"
        buckets[key].append(entry)
        total += base_amt
    return {"base_currency": base_currency, "total": round(total, 2),
            "bucket_totals": {k: round(sum(e["base_amount"] for e in v), 2)
                              for k, v in buckets.items()},
            "buckets": buckets}
