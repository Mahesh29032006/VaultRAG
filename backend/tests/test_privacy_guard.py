import time
import pytest
from backend.privacy_guard import PrivacyGuard


def test_privacy_guard_empty_and_whitespace():
    res1 = PrivacyGuard.redact("")
    assert res1.redacted_text == ""
    assert res1.detected_entities == []

    res2 = PrivacyGuard.redact("   \n\t  ")
    assert res2.redacted_text == "   \n\t  "
    assert res2.detected_entities == []


def test_privacy_guard_null_byte_raises_value_error():
    with pytest.raises(ValueError, match="Null bytes"):
        PrivacyGuard.redact("Patient with \x00 in record")


def test_privacy_guard_e40_literal_collision_escaping():
    text = "The literal string [SAFE_SSN_1] should not collide with real SSN 123-45-6789."
    res = PrivacyGuard.redact(text)
    # The real SSN should receive a token that doesn't conflict with literal [SAFE_SSN_1]
    assert "[SAFE_SSN_1_X]" in res.redacted_text or "[SAFE_SSN_2]" in res.redacted_text
    assert "[SAFE_SSN_1]" in res.redacted_text  # literal was preserved


def test_privacy_guard_e41_repeated_entity_reuses_same_token():
    text = "SSN 987-65-4321 was noted. Later SSN 987-65-4321 was confirmed."
    res = PrivacyGuard.redact(text)
    tokens = [e.token for e in res.detected_entities if e.type == "SSN"]
    assert len(tokens) == 2
    assert tokens[0] == tokens[1]  # Same token reused


def test_privacy_guard_e42_overlapping_address_and_date():
    text = "Delivered to 124 5th Avenue New York NY 10001 on Jan 15, 2024."
    res = PrivacyGuard.redact(text)
    types = [e.type for e in res.detected_entities]
    assert "ADDRESS" in types
    assert "DATE" in types


def test_privacy_guard_e43_restore_missing_token_leaves_as_is():
    redacted = "Record for [SAFE_SSN_99] processed."
    restored = PrivacyGuard.restore(redacted, {"[SAFE_SSN_1]": "000-11-2222"})
    assert restored == redacted


def test_privacy_guard_e44_restore_extra_token_ignored():
    redacted = "Record for [SAFE_NAME_1] processed."
    token_map = {"[SAFE_NAME_1]": "Alice Smith", "[SAFE_DATE_1]": "2024-01-01"}
    restored = PrivacyGuard.restore(redacted, token_map)
    assert restored == "Record for Alice Smith processed."


def test_privacy_guard_e45_all_18_categories_redacted():
    sample_text = (
        "1. Patient Name: Jane Doe\n"
        "2. Address: 742 Evergreen Terrace Springfield IL 62704\n"
        "3. Date: 2024-05-12\n"
        "4. Phone: 555-234-5678\n"
        "5. Fax: (555) 345-6789\n"
        "6. Email: jane.doe@hospital.org\n"
        "7. SSN: 111-22-3333\n"
        "8. MRN: 48192-38192-AB12\n"
        "9. Health Plan ID: Member ID BCBS12345678\n"
        "10. Account: Acct #AC-99887766\n"
        "11. License: Lic #DL-98765432\n"
        "12. Vehicle ID: VIN 1HGCR2F83HA123456\n"
        "13. Device ID: Device Serial SN-9876543210\n"
        "14. URL: https://portal.hospital.org/patient/123\n"
        "15. IP Address: 192.168.1.105\n"
        "16. Biometric Ref: fingerprint BIO-FINGER-778899\n"
        "17. Provider ID: NPI 1234567890\n"
        "18. Financial: $4500-1234-5678-9012\n"
    )
    res = PrivacyGuard.redact(sample_text)
    detected_types = {e.type for e in res.detected_entities}
    all_18 = {
        "NAME", "ADDRESS", "DATE", "PHONE", "FAX", "EMAIL", "SSN", "MRN",
        "HEALTH_PLAN_ID", "ACCOUNT", "LICENSE", "VEHICLE_ID", "DEVICE_ID",
        "URL", "IP_ADDRESS", "BIOMETRIC_REF", "PROVIDER_ID", "FINANCIAL"
    }
    # Check that all 18 categories are detected and redacted
    assert detected_types == all_18

    # Verify complete reversibility
    restored = PrivacyGuard.restore(res.redacted_text, res.token_map)
    assert restored == sample_text


def test_privacy_guard_e46_one_megabyte_input_fast():
    one_mb_text = ("Regular EHR clinical note text line without sensitive data. " * 15 + "\n") * 1500
    t0 = time.perf_counter()
    res = PrivacyGuard.redact(one_mb_text)
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0  # Must complete in < 1 second


def test_privacy_guard_individual_ssn_redaction():
    text = "The patient's social security number is 456-78-1234."
    res = PrivacyGuard.redact(text)
    assert "456-78-1234" not in res.redacted_text
    assert "[SAFE_SSN_1]" in res.redacted_text


def test_privacy_guard_individual_mrn_redaction():
    text = "Medical record number MRN: 12345-67890-CD34 assigned."
    res = PrivacyGuard.redact(text)
    assert "12345-67890-CD34" not in res.redacted_text
    assert "[SAFE_MRN_1]" in res.redacted_text


def test_privacy_guard_individual_npi_provider_redaction():
    text = "Prescribing physician NPI 1982736450 authorized refill."
    res = PrivacyGuard.redact(text)
    assert "1982736450" not in res.redacted_text
    assert "[SAFE_PROVIDER_ID_1]" in res.redacted_text


def test_privacy_guard_clinical_lab_report_redaction():
    lab_text = (
        ":NAME Miss. HARSHITA  JAIN JPH00186102PATIENT ID:\n"
        ":AGE/SEX 19 Y/F PHONE/CELL NO. 9438332164:\n"
        ":NIT ROURKELA REPORTING DATE 18/04/2026 - 15:05:REFERRED BY\n"
        "SAMPLE RECEIVED DATE 18/04/2026 - 14:08:LAB NO. 26-BIO-468683:\n"
        "SAMPLE COLLECTED AT JP Hospital: SAMPLE COLLECTED DATE 18/04/2026 - 12:13:\n"
        "ACCESSION NO. : 26052947WARD : OPD\n"
        "Printed On : 18/04/2026 5:21:03PM sashikalasPrinted By :\n"
        "DR PRAGNYA PARAMITA MISHRA\n"
    )
    res = PrivacyGuard.redact(lab_text)

    # Assert no sensitive entities leak in the redacted text
    assert "HARSHITA" not in res.redacted_text
    assert "JAIN" not in res.redacted_text
    assert "JPH00186102" not in res.redacted_text
    assert "19 Y/F" not in res.redacted_text
    assert "9438332164" not in res.redacted_text
    assert "NIT ROURKELA" not in res.redacted_text
    assert "26-BIO-468683" not in res.redacted_text
    assert "JP Hospital" not in res.redacted_text
    assert "26052947" not in res.redacted_text
    assert "sashikalas" not in res.redacted_text
    assert "PRAGNYA PARAMITA MISHRA" not in res.redacted_text

    # Assert round-trip reversibility
    restored = PrivacyGuard.restore(res.redacted_text, res.token_map)
    assert restored == lab_text

