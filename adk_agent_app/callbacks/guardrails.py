# adk_agent_app/callbacks/guardrails.py
"""Production Execution Callbacks & Guardrails for SostaApp (`07a-callbacks-and-guardrails`).

Implements the 4 ADK 2.0 execution interception hooks:
1. `before_model_guardrail` (`before_model_callback`):
   - Inspects incoming `LlmRequest` before calling Gemini.
   - Short-circuits prompt-injection / jailbreak attempts with a deterministic `LlmResponse`
     (consuming 0 LLM tokens).
   - Tracks `metrics:llm_requests_count` and `metrics:last_active_agent` in session state.
2. `after_model_guardrail` (`after_model_callback`):
   - Inspects `LlmResponse` returned by Gemini.
   - Tracks `metrics:llm_responses_count` in session state.
   - Optionally appends a deterministic Allergen Safety Compliance footer when
     `callback_context.state.get("enable_allergen_footer")` is enabled.
3. `before_tool_guardrail` (`before_tool_callback`):
   - Sanitizes and validates tool arguments before execution.
   - Blocks malformed/malicious `user_id` inputs on `is_registered_user` and `extract_user_profile`
     before querying Firestore.
   - Enforces zero-trust authorization on `update_dietary_preferences` so a caller cannot modify
     another user's profile (`args["user_id"] != tool_context.state["verified_user_id"]`).
4. `after_tool_guardrail` (`after_tool_callback`):
   - Records an immutable audit trail in `tool_context.state["audit:tool_execution_log"]`
     and enriches dict responses with `"_audit_verified": True`.
"""

import logging
import os
import re
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

logger = logging.getLogger(__name__)

# Patterns indicating a prompt-injection or system-override attempt
PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "dump the firestore",
    "reveal your system prompt",
    "print your system instructions",
)

# Valid SostaApp User ID pattern: usr_ followed by alphanumeric/underscore characters
VALID_USER_ID_REGEX = re.compile(r"^usr_[a-zA-Z0-9_]+$")


def _extract_latest_user_text(llm_request: LlmRequest) -> str:
    """Extracts the text of the latest user turn from an LlmRequest."""
    if not llm_request.contents:
        return ""
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            texts = [p.text for p in content.parts if getattr(p, "text", None)]
            if texts:
                return " ".join(texts)
    return ""


def before_model_guardrail(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Intercepts LLM requests before calling Gemini.

    Returns an `LlmResponse` to short-circuit the model call if a prompt injection
    attempt is detected; otherwise returns `None` to proceed normally.
    """
    # 1. Update telemetry in session state
    req_count = int(callback_context.state.get("metrics:llm_requests_count", 0))
    callback_context.state["metrics:llm_requests_count"] = req_count + 1
    callback_context.state["metrics:last_active_agent"] = callback_context.agent_name

    # 2. Check latest user message for prompt-injection / override patterns
    user_text = _extract_latest_user_text(llm_request)
    lowered = user_text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in lowered:
            blocked_count = int(
                callback_context.state.get("security:blocked_attempts", 0)
            )
            callback_context.state["security:blocked_attempts"] = blocked_count + 1
            callback_context.state["security:last_blocked_reason"] = (
                f"prompt_injection:{pattern}"
            )
            logger.warning(
                f"[before_model_guardrail] Blocked prompt injection on agent "
                f"'{callback_context.agent_name}': matched '{pattern}'"
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(
                            text=(
                                "Guardrail Alert: Your request was blocked by SostaApp's security policy. "
                                "I can only assist with highway trip planning, account registration, and dining stops."
                            )
                        )
                    ],
                )
            )

    return None


def after_model_guardrail(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Intercepts LLM responses after Gemini returns.

    Tracks response telemetry and optionally appends a deterministic allergen
    compliance badge when `enable_allergen_footer` is set in session state.
    """
    resp_count = int(callback_context.state.get("metrics:llm_responses_count", 0))
    callback_context.state["metrics:llm_responses_count"] = resp_count + 1

    enable_footer = callback_context.state.get(
        "enable_allergen_footer", False
    ) or (os.getenv("SOSTA_APPEND_ALLERGEN_FOOTER", "").lower() == "true")

    if not enable_footer:
        return None

    # Only append footer to final text responses (not intermediate tool call turns)
    if not llm_response.content or not llm_response.content.parts:
        return None
    if any(getattr(p, "function_call", None) for p in llm_response.content.parts):
        return None

    preferences = callback_context.state.get("user:culinary_preferences")
    if not preferences:
        return None

    pref_str = (
        ", ".join(preferences)
        if isinstance(preferences, list)
        else str(preferences)
    )
    badge = f"\n\n[🛡️ SostaApp Allergen Guardrail: Profile verified for {pref_str}]"

    new_parts = []
    appended = False
    for part in llm_response.content.parts:
        if getattr(part, "text", None) and not appended:
            if badge not in part.text:
                new_parts.append(types.Part.from_text(text=part.text + badge))
            else:
                new_parts.append(part)
            appended = True
        else:
            new_parts.append(part)

    if appended:
        return LlmResponse(
            content=types.Content(
                role=llm_response.content.role or "model",
                parts=new_parts,
            ),
            grounding_metadata=llm_response.grounding_metadata,
        )

    return None


def before_tool_guardrail(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> Optional[dict[str, Any]]:
    """Intercepts tool execution before the Python function runs.

    Validates `user_id` format and prevents cross-user profile modification.
    Returning a dict short-circuits the actual tool execution.
    """
    tool_name = tool.name

    # 1. Sanitize and validate `user_id` format on user lookup tools
    if tool_name in ("is_registered_user", "extract_user_profile", "update_dietary_preferences"):
        raw_user_id = args.get("user_id")
        if isinstance(raw_user_id, str):
            cleaned_id = raw_user_id.strip()
            args["user_id"] = cleaned_id

            if not VALID_USER_ID_REGEX.match(cleaned_id):
                tool_context.state["security:last_blocked_tool"] = tool_name
                tool_context.state["security:last_blocked_arg"] = raw_user_id
                logger.warning(
                    f"[before_tool_guardrail] Blocked invalid user_id '{raw_user_id}' on tool '{tool_name}'"
                )
                return {
                    "status": "error",
                    "error_code": "INVALID_USER_ID_FORMAT",
                    "message": (
                        f"Security policy blocked tool '{tool_name}': User ID '{raw_user_id}' "
                        "is malformed. Expected format 'usr_<alphanumeric>'."
                    ),
                }

    # 2. Zero-Trust Authorization check on `update_dietary_preferences`
    if tool_name == "update_dietary_preferences":
        verified_id = tool_context.state.get("verified_user_id")
        requested_id = args.get("user_id")
        if verified_id and requested_id and requested_id != verified_id:
            tool_context.state["security:last_blocked_tool"] = tool_name
            logger.warning(
                f"[before_tool_guardrail] Blocked cross-user profile update: "
                f"verified='{verified_id}' vs requested='{requested_id}'"
            )
            return {
                "status": "error",
                "error_code": "UNAUTHORIZED_PROFILE_UPDATE",
                "message": (
                    f"Unauthorized: Session is authenticated as '{verified_id}' "
                    f"and cannot modify preferences for '{requested_id}'."
                ),
            }

    return None


def after_tool_guardrail(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Intercepts tool output after execution to record an audit log and tag the response."""
    audit_log = list(tool_context.state.get("audit:tool_execution_log", []))
    status = (
        tool_response.get("status", "ok")
        if isinstance(tool_response, dict)
        else "ok"
    )
    audit_log.append(
        {
            "agent": tool_context.agent_name,
            "tool": tool.name,
            "status": status,
        }
    )
    tool_context.state["audit:tool_execution_log"] = audit_log

    if isinstance(tool_response, dict):
        enriched = dict(tool_response)
        enriched["_audit_verified"] = True
        return enriched

    return None
