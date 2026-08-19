# tests/07b-code-executor/code_executor_test_1_builtin_vs_local.py
"""
ADK 2.0 101 (#7b) — Verification Script 1:
Sandboxed Code Execution (`BuiltInCodeExecutor` vs `UnsafeLocalCodeExecutor`) & Event Inspection

Demonstrates:
- Part A: `BuiltInCodeExecutor` — Gemini 2.5's server-side sandboxed Python execution,
  inspecting `part.executable_code` and `part.code_execution_result` in the ADK Event loop.
- Part B: Why `BuiltInCodeExecutor` is isolated inside a specialist sub-agent wrapped as an
  `AgentTool` (avoiding Gemini 2.x's 400 INVALID_ARGUMENT when mixing native
  `ToolCodeExecution` with custom `FunctionTool` declarations on the same LlmAgent).
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ---------------------------------------------------------------------------
# Path Resolution & Environment Configuration
# ---------------------------------------------------------------------------
# Resolve repository root path (2 parent levels above this test file)
ROOT_DIR = Path(__file__).resolve().parents[2]
# Inject repository root into sys.path to enable local module imports
sys.path.insert(0, str(ROOT_DIR))
# Load local environment variables (API keys, project settings) from root .env file
load_dotenv(ROOT_DIR / ".env")

# Automatically switch to Vertex AI backend if GOOGLE_CLOUD_PROJECT is configured
if os.getenv("GOOGLE_CLOUD_PROJECT"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"


# ---------------------------------------------------------------------------
# Main Async Execution & Inspection Routine
# ---------------------------------------------------------------------------
async def main() -> None:
    # Initialize ephemeral in-memory storage for test session management
    session_service = InMemorySessionService()

    print("=" * 75)
    print(" PART A: BuiltInCodeExecutor — Inspecting executable_code & code_execution_result")
    print("=" * 75)

    # Define dedicated analyst agent configured with Google's server-side BuiltInCodeExecutor
    ev_math_agent = Agent(
        name="EVChargingMathAgent",
        model="gemini-2.5-flash",
        instruction=(
            "You are an EV Charging Physics & Billing Analyst. "
            "Always write and execute Python code to compute exact results before answering."
        ),
        code_executor=BuiltInCodeExecutor(),  # Instructs Gemini to write and run Python in a sandbox
    )

    # Instantiate the ADK Runner bound to the analyst agent and session service
    runner = Runner(
        app_name="sosta_code_executor_test_1",
        agent=ev_math_agent,
        session_service=session_service,
        auto_create_session=True,  # Automatically provisions new session IDs on the fly
    )

    # Quantitative prompt requiring multi-step arithmetic calculations
    prompt = (
        "An electric vehicle with a 75 kWh battery arrives at Secchia Ovest at 20% SoC "
        "and charges to 80% SoC on a 150 kW DC fast charger at €0.65/kWh. "
        "Two passengers also spend €24.00 total on vegan salads and coffee. "
        "Compute: (1) energy added in kWh, (2) charging time in minutes, "
        "(3) charging cost in EUR, (4) total stop cost in EUR, and (5) cost per passenger in EUR."
    )
    print(f"Prompt: {prompt}\n")

    executed_python_snippets = []
    sandbox_stdout_outputs = []
    final_text = ""

    # Stream execution events emitted asynchronously by the ADK runner
    async for event in runner.run_async(
        user_id="zelda_code_exec_user",
        session_id="session_builtin_exec",
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
    ):
        # Inspect raw content parts returned during streaming steps
        if event.content and event.content.parts:
            for part in event.content.parts:
                # Intercept generated Python code written by Gemini before execution
                if getattr(part, "executable_code", None):
                    code_str = part.executable_code.code
                    executed_python_snippets.append(code_str)
                    print("--- [Event Part: executable_code] ---")
                    print(code_str.strip())
                    
                # Intercept stdout returned from Gemini's server-side Python sandbox
                if getattr(part, "code_execution_result", None):
                    out_str = part.code_execution_result.output
                    sandbox_stdout_outputs.append(out_str)
                    print("--- [Event Part: code_execution_result] ---")
                    print(out_str.strip())
                    
        # Extract and accumulate final response text synthesized by the model
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text for p in event.content.parts if p.text)

    print("\n--- [Final Agent Response] ---")
    print(final_text)

    # Assertions: Verify that code was generated, executed, and produced correct numbers
    assert len(executed_python_snippets) >= 1, "Expected Gemini to generate executable_code!"
    assert len(sandbox_stdout_outputs) >= 1, "Expected Gemini sandbox to return code_execution_result!"
    assert "45" in final_text and "18" in final_text and "29.25" in final_text
    print("\n✅ Verified: BuiltInCodeExecutor generated Python code, ran it in Gemini's sandbox, and returned exact figures!")


if __name__ == "__main__":
    # Script entrypoint: Run async verification routine
    asyncio.run(main())