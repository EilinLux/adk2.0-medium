# adk_agent_app/services/dlp_redaction_service.py
"""Google Cloud Sensitive Data Protection (Cloud DLP) Service for SostaApp (`07c-dlp-pii-redaction`).

Provides real-time inspection and de-identification of sensitive traveler PII:
  - Built-in Cloud DLP InfoTypes:
      * `CREDIT_CARD_NUMBER`
      * `PHONE_NUMBER`
      * `ITALY_FISCAL_CODE` (Codice Fiscale)
      * `IBAN_CODE`
      * `EMAIL_ADDRESS` (optional, configurable per context)
  - Custom Cloud DLP InfoType:
      * `ITALIAN_LICENSE_PLATE` (`\\b[A-Z]{2}\\s?\\d{3}\\s?[A-Z]{2}\\b`, e.g., `AB 123 CD`)
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

from google.cloud import dlp_v2

from ..config import PROJECT_ID

logger = logging.getLogger(__name__)

# Fast pre-filter regex so ordinary turns ("hello", "yes, I am usr_0a8f67") skip network calls
_PII_CANDIDATE_REGEX = re.compile(
    r"(?:"
    r"\b(?:\d[ -]*?){13,19}\b"  # Credit card candidate
    r"|(?:\+39|0039)?\s*3\d{2}[\s\-]?\d{6,7}\b"  # Italian mobile phone candidate
    r"|\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b"  # Italian Codice Fiscale
    r"|\bIT\d{2}[A-Z]\d{10}[0-9A-Z]{12}\b"  # Italian IBAN
    r"|\b[A-Z]{2}\s?\d{3}\s?[A-Z]{2}\b"  # Italian Vehicle License Plate (Targa)
    r")"
)

_dlp_client: Optional[dlp_v2.DlpServiceClient] = None


def get_dlp_client() -> dlp_v2.DlpServiceClient:
    """Returns a singleton Cloud DLP client."""
    global _dlp_client
    if _dlp_client is None:
        _dlp_client = dlp_v2.DlpServiceClient()
    return _dlp_client


@dataclass
class DlpRedactionResult:
    """Structured result returned by Cloud DLP inspection and de-identification."""

    original_text: str
    redacted_text: str
    was_redacted: bool
    info_types_found: List[str] = field(default_factory=list)
    findings_count: int = 0


def _build_inspect_config(include_email: bool = False) -> dict[str, Any]:
    """Builds the Cloud DLP InspectConfig combining built-in and custom SostaApp InfoTypes."""
    info_types = [
        {"name": "CREDIT_CARD_NUMBER"},
        {"name": "PHONE_NUMBER"},
        {"name": "ITALY_FISCAL_CODE"},
        {"name": "IBAN_CODE"},
    ]
    if include_email:
        info_types.append({"name": "EMAIL_ADDRESS"})

    custom_info_types = [
        {
            "info_type": {"name": "ITALIAN_LICENSE_PLATE"},
            "regex": {"pattern": r"\b[A-Z]{2}\s?\d{3}\s?[A-Z]{2}\b"},
            "likelihood": dlp_v2.Likelihood.POSSIBLE,
        }
    ]

    return {
        "info_types": info_types,
        "custom_info_types": custom_info_types,
        "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
        "include_quote": True,
    }


def _build_deidentify_config() -> dict[str, Any]:
    """Builds the Cloud DLP DeidentifyConfig replacing any matched InfoType with `[INFO_TYPE]`."""
    return {
        "info_type_transformations": {
            "transformations": [
                {
                    "primitive_transformation": {
                        "replace_with_info_type_config": {},
                    }
                }
            ]
        }
    }


def inspect_and_deidentify_text(
    text: str,
    *,
    include_email: bool = False,
    force_cloud_dlp: bool = False,
) -> DlpRedactionResult:
    """Inspects and de-identifies sensitive PII in `text` using Google Cloud DLP.

    Args:
        text: Input string to inspect and sanitize.
        include_email: Whether to also redact `EMAIL_ADDRESS` tokens.
        force_cloud_dlp: If True, always calls the Cloud DLP API even if the fast
            local regex pre-filter does not match.

    Returns:
        DlpRedactionResult containing the sanitized string and detected InfoTypes.
    """
    if not text or not text.strip():
        return DlpRedactionResult(
            original_text=text,
            redacted_text=text,
            was_redacted=False,
        )

    if not force_cloud_dlp and not _PII_CANDIDATE_REGEX.search(text):
        return DlpRedactionResult(
            original_text=text,
            redacted_text=text,
            was_redacted=False,
        )

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
    parent = f"projects/{project_id}/locations/{location}"

    inspect_config = _build_inspect_config(include_email=include_email)
    deidentify_config = _build_deidentify_config()
    item = {"value": text}

    client = get_dlp_client()

    # 1. Inspect content to list exact InfoTypes detected
    inspect_response = client.inspect_content(
        request={
            "parent": parent,
            "inspect_config": inspect_config,
            "item": item,
        }
    )
    findings = inspect_response.result.findings
    info_types_found = sorted({f.info_type.name for f in findings})

    if not findings:
        return DlpRedactionResult(
            original_text=text,
            redacted_text=text,
            was_redacted=False,
        )

    # 2. De-identify content via Cloud DLP
    deid_response = client.deidentify_content(
        request={
            "parent": parent,
            "inspect_config": inspect_config,
            "deidentify_config": deidentify_config,
            "item": item,
        }
    )
    redacted_text = deid_response.item.value

    logger.warning(
        f"[Cloud DLP] Redacted {len(findings)} PII finding(s) "
        f"({info_types_found}) via {parent}"
    )

    return DlpRedactionResult(
        original_text=text,
        redacted_text=redacted_text,
        was_redacted=(redacted_text != text),
        info_types_found=info_types_found,
        findings_count=len(findings),
    )
