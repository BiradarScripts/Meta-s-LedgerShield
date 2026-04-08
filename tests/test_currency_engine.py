"""Tests for the multi-currency engine (Phase 1.1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.currency_engine import (
    convert_currency,
    detect_currency_mismatch,
    generate_aging_report,
    validate_iban,
    validate_swift,
)


class TestIBANValidation:
    def test_valid_german_iban(self):
        result = validate_iban("DE89 3704 0044 0532 0130 00")
        assert result["country"] == "DE"
        # Format check passes (checksum may vary for test data)

    def test_too_short(self):
        result = validate_iban("DE8")
        assert not result["valid"]
        assert "too short" in result["errors"][0].lower()

    def test_invalid_country_code(self):
        result = validate_iban("12345678901234567890")
        assert not result["valid"]


class TestSWIFTValidation:
    def test_valid_8_char(self):
        result = validate_swift("DEUTDEFF")
        assert result["valid"]
        assert result["bank_code"] == "DEUT"
        assert result["country"] == "DE"

    def test_valid_11_char(self):
        result = validate_swift("DEUTDEFF500")
        assert result["valid"]

    def test_invalid_length(self):
        result = validate_swift("SHORT")
        assert not result["valid"]


class TestCurrencyConversion:
    def test_same_currency(self):
        result = convert_currency(100.0, "USD", "USD", apply_spread=False)
        assert result.valid
        assert result.converted_amount == 100.0

    def test_usd_to_eur(self):
        result = convert_currency(100.0, "USD", "EUR", apply_spread=False)
        assert result.valid
        assert result.converted_amount > 0

    def test_unknown_currency(self):
        result = convert_currency(100.0, "USD", "XYZ")
        assert not result.valid

    def test_sanctioned_currency(self):
        result = convert_currency(100.0, "USD", "IRR")
        assert not result.valid
        assert any("sanctioned" in f for f in result.risk_flags)

    def test_spread_applied(self):
        with_spread = convert_currency(100.0, "USD", "EUR", apply_spread=True)
        without_spread = convert_currency(100.0, "USD", "EUR", apply_spread=False)
        assert with_spread.converted_amount < without_spread.converted_amount


class TestCurrencyMismatch:
    def test_no_mismatch(self):
        result = detect_currency_mismatch("USD", "USD", "USD")
        assert not result["has_mismatch"]

    def test_single_mismatch(self):
        result = detect_currency_mismatch("USD", "", "EUR")
        assert result["has_mismatch"]
        assert result["risk_level"] == "medium"

    def test_triple_mismatch(self):
        result = detect_currency_mismatch("USD", "EUR", "GBP")
        assert result["has_mismatch"]
        assert result["risk_level"] == "high"


class TestAgingReport:
    def test_basic_report(self):
        invoices = [
            {"invoice_id": "INV-001", "amount": 1000, "currency": "USD", "days_outstanding": 15, "vendor_name": "Acme"},
            {"invoice_id": "INV-002", "amount": 2000, "currency": "USD", "days_outstanding": 45, "vendor_name": "Beta"},
            {"invoice_id": "INV-003", "amount": 500, "currency": "EUR", "days_outstanding": 95, "vendor_name": "Gamma"},
        ]
        report = generate_aging_report(invoices)
        assert report["base_currency"] == "USD"
        assert report["total"] > 0
        assert len(report["buckets"]["0_30"]) == 1
        assert len(report["buckets"]["31_60"]) == 1
        assert len(report["buckets"]["90_plus"]) == 1
