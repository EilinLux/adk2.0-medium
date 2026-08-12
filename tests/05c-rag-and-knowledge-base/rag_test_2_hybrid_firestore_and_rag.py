# tests/05c-rag-and-knowledge-base/rag_test_2_hybrid_firestore_and_rag.py
"""Test 2: Hybrid Grounding with Firestore Food KB + Vertex AI RAG (`MenuCheckerAgent`).

Demonstrates:
1. How `MenuCheckerAgent` combines two `FunctionTool`s in sequence:
   - `get_stop_food_inventory_and_reviews`: Queries Firestore (`adk-agent-dev-food-kb-fs` / `stop_food_kb`)
     for live product inventory and customer reviews at each candidate highway stop.
   - `retrieve_product_specs_rag`: Queries Vertex AI RAG (`rag.retrieval_query` / GCS Product Spec PDFs)
     for exact ingredient lists, allergen summaries ('CONTAINS' vs 'FREE FROM'), and certifications.
2. How this eliminates LLM hallucination: instead of guessing generic highway food, `MenuCheckerAgent`
   proves that `Secchia Ovest` stocks the 100% Vegan & Gluten-Free `Vegan Salad` ('Vegan Rainbow Salad'),
   whereas `Rustichella Sandwich` and `Capri Sandwich` contain dairy/pork.
"""

import asyncio
import json
import os
from pathlib import Path
import sys

# Ensure project root is on sys.path when invoked directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION

from adk_agent_app.subagents.suggeritore_soste_subagents import menu_checker_agent


async def main() -> None:
    print("=" * 80)
    print(
        "TEST 2: HYBRID FIRESTORE FOOD KB + VERTEX AI RAG IN `MenuCheckerAgent`"
    )
    print("=" * 80)

    session_service = InMemorySessionService()
    runner = Runner(
        app_name="hybrid_rag_demo",
        agent=menu_checker_agent,
        session_service=session_service,
    )
    await session_service.create_session(
        app_name="hybrid_rag_demo",
        user_id="demo_user",
        session_id="session_hybrid_rag",
    )

    payload = {
        "stop_names": [
            "Badia al Pino Est",
            "Cantagallo",
            "Sillaro Ovest",
            "Secchia Ovest",
        ],
        "dietary_preferences": ["Vegan"],
    }
    print(f"\n[Input to MenuCheckerAgent]:\n{json.dumps(payload, indent=2)}\n")

    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=json.dumps(payload))],
    )

    async for event in runner.run_async(
        user_id="demo_user",
        session_id="session_hybrid_rag",
        new_message=msg,
    ):
        for call in event.get_function_calls():
            print(f"  -> [Tool Call] {call.name}({call.args})")
        if event.is_final_response() and event.content and event.content.parts:
            print(
                f"\n[MenuCheckerAgent Grounded Output]:\n{event.content.parts[0].text}\n"
            )


if __name__ == "__main__":
    asyncio.run(main())
