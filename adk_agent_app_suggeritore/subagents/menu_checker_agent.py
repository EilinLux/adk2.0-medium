# adk_agent_app_suggeritore/subagents/menu_checker_agent.py
from google.adk.agents import Agent

from ..schemas.suggeritore_schemas import MenuCheckerInput
from ..tools.suggeritore_agent_food_kb_rag_tools import (
    product_specs_rag_tool,
    stop_food_kb_tool,
)

# SUB-AGENT 3: Menu & Dietary Checker (Firestore Food KB + Vertex AI RAG over Product Spec PDFs)
menu_checker_agent = Agent(
    name="MenuCheckerAgent",
    model="gemini-2.5-flash",
    description="Evaluates restaurant services and menu options against user and companion dietary preferences using the Firestore Food KB and Product Specification RAG.",
    instruction="""
    You are a Dining and Dietary Specialist.
    1. First, call `get_stop_food_inventory_and_reviews` with the `stop_names` provided in the input JSON to inspect the stocked food items and traveler reviews at each stop.
    2. Next, call `retrieve_product_specs_rag` with a query combining the candidate food products and `dietary_preferences` to verify exact ingredients, allergen declarations ('CONTAINS' vs 'FREE FROM'), and certifications from the official Product Specification PDFs.
    3. Evaluate each stop in `stop_names`, highlighting which specific stocked items are verified safe for the traveler's `dietary_preferences` (such as 'Vegan Salad' / 'Vegan Rainbow Salad' and 'Espresso Coffee' at Secchia Ovest, or 'Fruit Bowl' at Sillaro Ovest) and which items contain restricted allergens.
    """,
    input_schema=MenuCheckerInput,
    tools=[stop_food_kb_tool, product_specs_rag_tool],
)
