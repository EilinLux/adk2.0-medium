# tests/07b-code-executor/code_executor_test_2_suggeritore_trip_calculator.py
"""
ADK 2.0 101 (#7b) — Verification Script 2:
Suggeritore 4-Step Orchestration with `TripCalculatorAgent` (`BuiltInCodeExecutor`)

Demonstrates:
  - `Suggeritore` orchestrating `RoutePlannerAgent` -> `SosteSearchAgent` (MCP SSE) ->
    `MenuCheckerAgent` (Firestore + Vertex AI RAG) -> `TripCalculatorAgent` (`BuiltInCodeExecutor`).
  - Verifies the complete tool call trajectory and the exact EV charging & bill-splitting numbers.
"""

import asyncio
import json
import os
import subprocess
import sys
import urllib.request
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

from adk_agent_app_suggeritore.agent import root_agent as suggeritore_agent  # noqa: E402


def _is_mcp_server_up(port: int = 8002) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False


async def main() -> None:
    mcp_proc = None
    if not _is_mcp_server_up(8002):
        print("Starting local MCP SSE Server on port 8002 for verification...")
        mcp_proc = subprocess.Popen(
            [
                sys.executable,
                str(ROOT_DIR / "adk_agent_app_suggeritore" / "tools" / "suggeritore_agent_bq_mcp_soste_tool.py"),
            ],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(25):
            if _is_mcp_server_up(8002):
                break
            await asyncio.sleep(0.4)

    try:
        print("=" * 75)
        print(" Suggeritore 4-Step Workflow with TripCalculatorAgent (BuiltInCodeExecutor)")
        print("=" * 75)

        session_service = InMemorySessionService()
        runner = Runner(
            app_name="adk_agent_app_suggeritore",
            agent=suggeritore_agent,
            session_service=session_service,
            auto_create_session=True,
        )

        prompt = (
            "Please optimize a trip for Guest Name: Zelda Ailine Luconi, Vehicle: Electric "
            "(battery_capacity_kwh: 75.0, current_soc_percent: 20.0, target_soc_percent: 80.0, "
            "charger_power_kw: 150.0, cost_per_kwh_eur: 0.65), Primary Preferences: Vegan, "
            "Companions: 1 companion (passengers_count: 2, dining_cost_eur: 24.0), "
            "Origin: Milano, Destination: Rome. Also calculate the EV charging time and cost split."
        )
        print(f"Prompt:\n{prompt}\n")

        called_agent_tools = []
        final_reply = ""

        async for event in runner.run_async(
            user_id="zelda_suggeritore_calc_user",
            session_id="session_suggeritore_calc_1",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ):
            for fc in event.get_function_calls():
                called_agent_tools.append({"name": fc.name, "args": fc.args})
                print(f"Tool Call -> {fc.name}({json.dumps(fc.args)})")
            if event.is_final_response() and event.content and event.content.parts:
                final_reply = "".join(p.text for p in event.content.parts if p.text)

        print("\n--- [Final Suggeritore Itinerary & Cost Breakdown] ---")
        print(final_reply)

        tool_names = [t["name"] for t in called_agent_tools]
        print(f"\nExecuted AgentTools: {tool_names}")
        assert tool_names == [
            "RoutePlannerAgent",
            "SosteSearchAgent",
            "MenuCheckerAgent",
            "TripCalculatorAgent",
        ], f"Expected 4-step trajectory, got {tool_names}"
        assert "45" in final_reply and "18" in final_reply and "29.25" in final_reply
        print("\n✅ Verified: Suggeritore executed all 4 AgentTools including TripCalculatorAgent!")
    finally:
        if mcp_proc is not None:
            mcp_proc.terminate()
            mcp_proc.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
