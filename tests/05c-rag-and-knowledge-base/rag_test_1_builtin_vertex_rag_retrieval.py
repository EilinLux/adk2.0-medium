# tests/05c-rag-and-knowledge-base/rag_test_1_builtin_vertex_rag_retrieval.py
"""Test 1: Built-in `VertexAiRagRetrieval` vs. Custom `FunctionTool` Mixing Constraint.

Demonstrates:
1. Part A: How Google ADK's built-in `VertexAiRagRetrieval` works when used as the SOLE tool
   on a dedicated RAG Agent (attaching a native Gemini 2.x `types.Retrieval(vertex_rag_store=...)`
   grounding configuration when the LLM and RAG Corpus share the same region).
2. Part B: Why mixing `VertexAiRagRetrieval` (a built-in Gemini Grounding/Retrieval tool) with a custom
   Python `FunctionTool` (such as `lookup_stop_inventory`) inside the same `Agent` raises a Gemini API
   `400 INVALID_ARGUMENT` error — motivating the `FunctionTool(retrieve_product_specs_rag)` wrapper
   used in `MenuCheckerAgent` (see Test 2).
"""

import asyncio
import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.genai import types
import vertexai
from vertexai.preview import rag

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
RAG_LOCATION = os.getenv("VERTEX_RAG_LOCATION", "europe-west3")
CORPUS_DISPLAY_NAME = os.getenv(
    "VERTEX_RAG_CORPUS_DISPLAY_NAME", "sosta-product-specs-corpus"
)

# For native VertexAiRagRetrieval grounding, Gemini and the Vertex AI RAG Corpus must run in the same region
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = RAG_LOCATION


def resolve_rag_corpus() -> str:
    """Finds the active Vertex AI RAG Corpus resource name in `RAG_LOCATION`."""
    vertexai.init(project=PROJECT_ID, location=RAG_LOCATION)
    for corpus in rag.list_corpora():
        if corpus.display_name == CORPUS_DISPLAY_NAME:
            return corpus.name
    raise RuntimeError(
        f"RAG Corpus '{CORPUS_DISPLAY_NAME}' not found in {RAG_LOCATION}. "
        "Run `uv run python terraform/terraform_infrastructure/seeding/vertex_rag_seed.py` first."
    )


def lookup_stop_inventory(stop_name: str) -> dict:
    """Mock Firestore Food KB lookup for a single highway stop."""
    return {
        "stop_name": stop_name,
        "products": ["Rustichella Sandwich", "Vegan Salad", "Espresso Coffee"],
    }


async def main() -> None:
    corpus_name = resolve_rag_corpus()
    print(f"Using Vertex AI RAG Corpus: {corpus_name}\n")

    builtin_rag_tool = VertexAiRagRetrieval(
        name="product_specs_rag",
        description="Retrieves Autogrill product specification sheets from Vertex AI RAG.",
        rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
        similarity_top_k=4,
    )

    # =========================================================================
    # PART A: Pure `VertexAiRagRetrieval` Agent (Single Built-in Retrieval Tool)
    # =========================================================================
    print("=" * 80)
    print("PART A: STANDALONE `VertexAiRagRetrieval` AGENT (SINGLE RETRIEVAL TOOL)")
    print("=" * 80)

    pure_rag_agent = Agent(
        name="PureProductSpecsRagAgent",
        model="gemini-2.5-flash",
        description="Answers product ingredient and allergen questions using built-in VertexAiRagRetrieval.",
        instruction="""
        You are a Product Quality & Allergen Specialist.
        Use your retrieval tool to answer questions about ingredients, certifications, and allergens
        from the official Autogrill Product Specification Sheets.
        """,
        tools=[builtin_rag_tool],
    )

    session_service = InMemorySessionService()
    runner_pure = Runner(
        app_name="rag_builtin_demo",
        agent=pure_rag_agent,
        session_service=session_service,
    )
    await session_service.create_session(
        app_name="rag_builtin_demo",
        user_id="demo_user",
        session_id="session_pure_rag",
    )

    msg_pure = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text="What are the exact ingredients and allergens of the Vegan Rainbow Salad?"
            )
        ],
    )

    async for event in runner_pure.run_async(
        user_id="demo_user",
        session_id="session_pure_rag",
        new_message=msg_pure,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            print(f"\n[PureProductSpecsRagAgent]:\n{event.content.parts[0].text}\n")

    # =========================================================================
    # PART B: Mixing `VertexAiRagRetrieval` + Custom `FunctionTool` (Anti-Pattern)
    # =========================================================================
    print("=" * 80)
    print(
        "PART B: MIXING BUILT-IN `VertexAiRagRetrieval` + `FunctionTool` IN ONE AGENT"
    )
    print("=" * 80)

    stop_inventory_tool = FunctionTool(lookup_stop_inventory)
    conflicted_rag_agent = Agent(
        name="ConflictedMenuChecker",
        model="gemini-2.5-flash",
        description="Attempts to mix built-in VertexAiRagRetrieval and a custom FunctionTool in one Agent.",
        instruction="""
        First call `lookup_stop_inventory` for 'Secchia Ovest', then retrieve product specs from RAG.
        """,
        tools=[stop_inventory_tool, builtin_rag_tool],
    )

    runner_conflict = Runner(
        app_name="rag_builtin_demo",
        agent=conflicted_rag_agent,
        session_service=session_service,
    )
    await session_service.create_session(
        app_name="rag_builtin_demo",
        user_id="demo_user",
        session_id="session_conflict_rag",
    )

    msg_conflict = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text="Check what vegan food is available at Secchia Ovest."
            )
        ],
    )

    try:
        async for event in runner_conflict.run_async(
            user_id="demo_user",
            session_id="session_conflict_rag",
            new_message=msg_conflict,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                print(f"[ConflictedMenuChecker]: {event.content.parts[0].text}")
    except Exception as exc:
        print("\n[Expected Gemini 2.x API Error Caught]:")
        print(f"  {type(exc).__name__}: {exc}")
        print(
            "\nArchitectural Takeaway:\n"
            "  On Gemini 2.x models, `VertexAiRagRetrieval` attaches a native `Retrieval` grounding tool\n"
            "  to `GenerateContentConfig.tools`, which cannot be combined in the same LLM request with\n"
            "  custom `FunctionTool` declarations (`400 INVALID_ARGUMENT: Multiple tools are supported\n"
            "  only when they are all search tools`).\n"
            "  Furthermore, native `VertexAiRagRetrieval` requires the Gemini endpoint and RAG Corpus\n"
            "  to reside in the exact same GCP region.\n"
            "  By wrapping `rag.retrieval_query()` inside a standard `FunctionTool` (see Test 2),\n"
            "  `MenuCheckerAgent` can seamlessly combine Firestore Food KB queries (`europe-west1`)\n"
            "  and Vertex AI RAG queries (`europe-west3`) in a single agent!"
        )


if __name__ == "__main__":
    asyncio.run(main())
