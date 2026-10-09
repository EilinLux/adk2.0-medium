# tests/07c-dlp-pii-redaction/dlp_test_2_agent_callback_pii_shield.py
"""
ADK 2.0 101 (#7c) — Verification Script 2:
End-to-End Agent PII Shield via `before_model_guardrail` + Google Cloud DLP

Demonstrates:
  - When a traveler (`usr_0a8f67`) accidentally shares sensitive PII (Visa Credit Card,
    Phone Number, Italian License Plate) during a trip planning turn, `before_model_guardrail`
    intercepts the `LlmRequest`, calls Google Cloud DLP (`deidentify_content`) in-place,
    and records the DLP audit telemetry (`dlp:redaction_count`, `dlp:redacted_info_types`,
    `dlp:last_redacted_text`) in ADK session state before Gemini ever sees the prompt.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

if os.getenv("GOOGLE_CLOUD_PROJECT"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

from adk_agent_app.agent import root_agent  # noqa: E402


async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="sosta_dlp_callback_test",
        agent=root_agent,
        session_service=session_service,
        auto_create_session=True,
    )

    user_id = "zelda_dlp_shield_user"
    session_id = "session_dlp_shield_1"

    print("=" * 75)
    print(" TURN 1: Authenticate Registered User (usr_0a8f67)")
    print("=" * 75)
    turn1 = "Hi! I am already registered, my user ID is usr_0a8f67."
    print(f"User Input : {turn1}")
    reply1 = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=turn1)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            reply1 = "".join(p.text for p in event.content.parts if p.text)
    print(f"Agent Reply: {reply1}\n")

    print("=" * 75)
    print(" TURN 2: Traveler Overshares Credit Card, Phone & License Plate")
    print("=" * 75)
    turn2 = (
        "Let's continue in English! I am traveling alone to Roma in my electric car "
        "(license plate AB 123 CD). In case you need to pre-book a fast charger, "
        "my Visa card is 4532 0151 1283 0366 and my phone is +39 347 1234567."
    )
    print(f"User Input : {turn2}")
    reply2 = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=turn2)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            reply2 = "".join(p.text for p in event.content.parts if p.text)

    print(f"\nAgent Reply:\n{reply2}\n")

    session = await session_service.get_session(
        app_name="sosta_dlp_callback_test",
        user_id=user_id,
        session_id=session_id,
    )
    dlp_state = {
        k: v for k, v in session.state.items() if k.startswith("dlp:")
    }
    print("DLP Audit Telemetry in Session State:")
    print(json.dumps(dlp_state, indent=2))

    assert dlp_state.get("dlp:redaction_count", 0) >= 3
    assert "CREDIT_CARD_NUMBER" in dlp_state.get("dlp:redacted_info_types", [])
    assert "PHONE_NUMBER" in dlp_state.get("dlp:redacted_info_types", [])
    assert "ITALIAN_LICENSE_PLATE" in dlp_state.get("dlp:redacted_info_types", [])
    assert "4532 0151 1283 0366" not in dlp_state.get("dlp:last_redacted_text", "")
    assert "4532 0151 1283 0366" not in reply2
    print("\n✅ Verified: before_model_guardrail redacted Credit Card, Phone, and License Plate via Cloud DLP before calling Gemini!")


if __name__ == "__main__":
    asyncio.run(main())
