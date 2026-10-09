# tests/07c-dlp-pii-redaction/dlp_test_1_cloud_dlp_service.py
"""
ADK 2.0 101 (#7c) — Verification Script 1:
Direct Google Cloud Sensitive Data Protection (Cloud DLP) Inspection & De-identification

Demonstrates:
  1. Built-in Cloud DLP InfoTypes (`CREDIT_CARD_NUMBER`, `PHONE_NUMBER`, `ITALY_FISCAL_CODE`).
  2. Custom Regex InfoType (`ITALIAN_LICENSE_PLATE` -> `AB 123 CD`).
  3. Zero-latency pass-through for clean conversational turns (`usr_0a8f67`).
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from adk_agent_app.services.dlp_redaction_service import inspect_and_deidentify_text  # noqa: E402


def main() -> None:
    print("=" * 75)
    print(" PART A: Cloud DLP Inspection & Redaction of Traveler PII")
    print("=" * 75)

    raw_message = (
        "Hi! I am usr_0a8f67 driving my electric car (targa AB 123 CD) to Roma. "
        "Please charge my Telepass or Visa 4532 0151 1283 0366 and text my phone "
        "+39 347 1234567 (Codice Fiscale LCNZLD90A41F205X)."
    )
    print(f"Original Text :\n  {raw_message}\n")

    result = inspect_and_deidentify_text(raw_message, force_cloud_dlp=True)

    print(f"Redacted Text :\n  {result.redacted_text}\n")
    print(f"Was Redacted     : {result.was_redacted}")
    print(f"Findings Count   : {result.findings_count}")
    print(f"InfoTypes Found  : {result.info_types_found}")

    assert result.was_redacted is True
    assert "4532 0151 1283 0366" not in result.redacted_text
    assert "347 1234567" not in result.redacted_text
    assert "AB 123 CD" not in result.redacted_text
    assert "CREDIT_CARD_NUMBER" in result.info_types_found
    assert "PHONE_NUMBER" in result.info_types_found
    assert "ITALIAN_LICENSE_PLATE" in result.info_types_found
    assert "usr_0a8f67" in result.redacted_text, "SostaApp user_id must NOT be redacted!"
    print("\n✅ Verified: Cloud DLP masked Credit Card, Phone Number, Codice Fiscale, and License Plate while preserving usr_0a8f67!")

    print("\n" + "=" * 75)
    print(" PART B: Fast Pre-Filter Pass-Through on Clean Messages")
    print("=" * 75)
    clean_message = "yes, I am usr_0a8f67 and I am traveling alone to Roma"
    clean_result = inspect_and_deidentify_text(clean_message)
    print(f"Clean Message : {clean_result.redacted_text}")
    assert clean_result.was_redacted is False
    assert clean_result.findings_count == 0
    print("✅ Verified: Clean conversational messages bypass Cloud DLP with 0 findings!")


if __name__ == "__main__":
    main()
