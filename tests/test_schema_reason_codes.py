from __future__ import annotations

from server.schema import canonical_reason_codes, normalize_reason_code


def test_normalize_reason_code_accepts_space_separated_variant():
    assert normalize_reason_code("sender domain spoof") == "sender_domain_spoof"
    assert normalize_reason_code("approval threshold evasion") == "approval_threshold_evasion"


def test_normalize_reason_code_maps_common_aliases():
    assert normalize_reason_code("shared remittance account") == "shared_bank_account"
    assert normalize_reason_code("invoice splitting") == "approval_threshold_evasion"


def test_canonical_reason_codes_dedupes_mixed_variants():
    assert canonical_reason_codes(
        [
            "sender_domain_spoof",
            "sender domain spoof",
            "invoice splitting",
            "approval_threshold_evasion",
            "shared remittance account",
        ]
    ) == [
        "sender_domain_spoof",
        "approval_threshold_evasion",
        "shared_bank_account",
    ]
