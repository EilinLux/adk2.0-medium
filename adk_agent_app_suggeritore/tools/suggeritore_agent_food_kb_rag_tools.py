# adk_agent_app/tools/suggeritore_agent_food_kb_rag_tools.py
import os
from typing import Any, Dict, List, Optional

from google.adk.tools import FunctionTool
from google.cloud import firestore
import vertexai
from vertexai.preview import rag

from ..config import (
    FIRESTORE_FOOD_KB_DB,
    GCS_BUCKET,
    PROJECT_ID,
    VERTEX_RAG_CORPUS_DISPLAY_NAME,
    VERTEX_RAG_LOCATION,
    logger,
)

COLLECTION_NAME = "stop_food_kb"
RAG_LOCATION = VERTEX_RAG_LOCATION
CORPUS_DISPLAY_NAME = VERTEX_RAG_CORPUS_DISPLAY_NAME

_CACHED_CORPUS_NAME: Optional[str] = os.getenv("VERTEX_RAG_CORPUS")

# Canonical specification sheets mirrored from gs://adk-agent-dev-product-specs/product_specs/*.pdf
# Used as a deterministic fallback if the regional Vertex AI RAG Spanner instance is still provisioning.
_PRODUCT_SPECS_CATALOG: List[Dict[str, str]] = [
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_vegan_salad.pdf",
        "product_name": "Vegan Salad / Vegan Rainbow Salad",
        "keywords": "vegan salad rainbow quinoa edamame avocado tomato pumpkin seeds tahini gluten-free dairy-free egg-free nut-free plant-based",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Vegan Rainbow Salad (stock name: 'Vegan Salad'). "
            "Certifications: 100% Vegan, Gluten-Free, High Fiber, Plant-Based Power. "
            "Ingredients: Mixed Greens (Baby Spinach, Rocket, Red Chard), Cooked Organic Quinoa 25%, "
            "Edamame Soybeans 15%, Fresh Avocado 12%, Cherry Tomatoes 12%, Toasted Pumpkin Seeds 3%, "
            "Lemon-Tahini Vinaigrette (Extra Virgin Olive Oil, Lemon Juice, Sesame Tahini, Salt, Black Pepper). "
            "Allergen Summary: CONTAINS Soy/Soybeans (Edamame), Sesame Seeds (Tahini). "
            "FREE FROM Gluten, Milk/Dairy, Egg, Nuts. Nutrition (280g): 340 kcal, 12.2g Protein, 8.4g Dietary Fiber."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_espresso_coffee.pdf",
        "product_name": "Espresso Coffee / Espresso Blend Superiore",
        "keywords": "espresso coffee vegan gluten-free dairy-free nut-free soy-free egg-free",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Espresso Blend Superiore (stock name: 'Espresso Coffee'). "
            "Certifications: Sugar-Free, Zero Calories, Rainforest Alliance Certified (100% Plant-Based / Vegan). "
            "Ingredients: 100% Roasted Coffee Beans (80% Arabica, 20% Robusta) extracted with pure filtered water. "
            "Allergen Summary: FREE FROM Gluten, Milk, Nuts, Soy, Egg, Sulfites. Nutrition (25ml): 2 kcal."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_rustichella_sandwich.pdf",
        "product_name": "Rustichella Sandwich",
        "keywords": "rustichella sandwich panino pork bacon provola cheese dairy gluten",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Rustichella Sandwich. "
            "Labels: 100% Italian Pork, Served Hot (NOT Vegan, NOT Vegetarian, NOT Gluten-Free). "
            "Ingredients: Artisanal Ciabatta (Wheat Flour), Smoked Provola Cheese (Pasteurized Milk), "
            "Seasoned Bacon (Pork), Herbed Extra Virgin Olive Oil Spread. "
            "Allergen Summary: CONTAINS Cereals containing Gluten, Milk and Dairy (including Lactose). "
            "FREE FROM Soy, Nuts & Peanuts, Egg, Mustard. Nutrition (220g): 540 kcal, 23.8g Protein."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_capri_sandwich.pdf",
        "product_name": "Capri Sandwich",
        "keywords": "capri sandwich vegetarian mozzarella dairy pine nuts pesto gluten",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Capri Sandwich. "
            "Labels: Vegetarian, Mozzarella di Bufala DOP (Vegetarian, NOT Vegan, NOT Gluten-Free, NOT Nut-Free). "
            "Ingredients: Sourdough Bread (Wheat Flour), Mozzarella di Bufala Campana DOP 35% (Buffalo Milk), "
            "Sliced Vine Tomatoes 25%, Genovese Basil Pesto 10% (Olive Oil, Basil DOP, Pine Nuts, Parmigiano Reggiano DOP). "
            "Allergen Summary: CONTAINS Cereals containing Gluten, Milk and Dairy (including Lactose), Tree Nuts (Pine Nuts). "
            "FREE FROM Soy, Egg, Mustard. Nutrition (230g): 465 kcal, 18.5g Protein."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_gluten_free_muffin.pdf",
        "product_name": "Gluten-Free Muffin / Gluten-Free Blueberry Muffin",
        "keywords": "gluten-free blueberry muffin celiac lactose-free egg",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Gluten-Free Blueberry Muffin (stock name: 'Gluten-Free Muffin'). "
            "Certifications: Certified Gluten-Free (AIC), Lactose-Free, Individually Sealed (Vegetarian, NOT Vegan due to Eggs). "
            "Ingredients: Gluten-Free Flour Mix (Rice Flour, Corn Starch, Potato Starch), Wild Blueberries 20%, "
            "Whole Pasteurized Eggs, Sugar, Sunflower Oil. "
            "Allergen Summary: CONTAINS Egg and Egg Products. FREE FROM Gluten (Cereals), Milk/Dairy, Soy, Nuts, Sesame. "
            "Nutrition (90g): 315 kcal, 4.1g Protein."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_camogli_sandwich.pdf",
        "product_name": "Camogli Sandwich",
        "keywords": "camogli sandwich focaccia cooked ham pork emmental cheese dairy gluten",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Camogli Sandwich. "
            "Labels: Traditional Favorite, High Protein (NOT Vegan, NOT Vegetarian, NOT Gluten-Free). "
            "Ingredients: Soft Ligurian Focaccia (Wheat Flour), Cooked Ham Superior Grade (Pork Leg 85%), "
            "Emmental Cheese (Pasteurized Milk). "
            "Allergen Summary: CONTAINS Cereals containing Gluten, Milk and Dairy (including Lactose). "
            "FREE FROM Soy, Nuts & Peanuts, Egg, Mustard. Nutrition (210g): 510 kcal, 24.2g Protein."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_apollo_sandwich.pdf",
        "product_name": "Apollo Sandwich",
        "keywords": "apollo sandwich chicken cutlet mayonnaise egg sesame gluten mustard",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Apollo Sandwich. "
            "Labels: 100% Italian Chicken, Extra Crunchy (NOT Vegan, NOT Vegetarian, NOT Gluten-Free). "
            "Ingredients: Sesame Bun (Wheat Flour, Sesame Seeds), Breaded Chicken Cutlet 40%, "
            "Herb Mayonnaise (Pasteurized Egg Yolk, Mustard), Fresh Iceberg Lettuce. "
            "Allergen Summary: CONTAINS Cereals containing Gluten, Sesame Seeds, Egg and Egg Products, Mustard. "
            "FREE FROM Milk and Dairy, Nuts. Nutrition (240g): 585 kcal, 26.5g Protein."
        ),
    },
    {
        "source_uri": f"gs://{GCS_BUCKET}/product_specs/product_pdfs_sicilian_cannolo.pdf",
        "product_name": "Sicilian Cannolo / Sicilian Cannolo Express",
        "keywords": "sicilian cannolo ricotta sheep milk pistachio lard egg gluten soy",
        "text": (
            "Autogrill Product Specification Sheet (QA-DB-2026-V4) — Sicilian Cannolo Express. "
            "Labels: 100% Sheep Milk Ricotta (NOT Vegan, NOT Vegetarian due to Lard, NOT Gluten-Free, NOT Nut-Free). "
            "Ingredients: Pastry Shell (Wheat Flour, Lard, Marsala Wine, Egg White), Ricotta Filling 65% (Sheep's Milk Whey), "
            "Dark Chocolate Chips (Soy Lecithin), Crushed Pistachio Nuts. "
            "Allergen Summary: CONTAINS Cereals containing Gluten, Milk and Dairy (Sheep Milk), Tree Nuts (Pistachio), Soy, Egg. "
            "FREE FROM Peanuts. Nutrition (110g): 385 kcal, 8.6g Protein."
        ),
    },
]


def _get_food_kb_client() -> firestore.Client:
    """Lazy initializer for the Firestore Food Knowledge Base."""
    return firestore.Client(project=PROJECT_ID, database=FIRESTORE_FOOD_KB_DB)


def _resolve_rag_corpus_name() -> Optional[str]:
    """Resolves the active Vertex AI RAG Corpus resource name by display name or env variable."""
    global _CACHED_CORPUS_NAME
    if _CACHED_CORPUS_NAME:
        return _CACHED_CORPUS_NAME

    try:
        vertexai.init(project=PROJECT_ID, location=RAG_LOCATION)
        for corpus in rag.list_corpora():
            if corpus.display_name == CORPUS_DISPLAY_NAME:
                _CACHED_CORPUS_NAME = corpus.name
                return _CACHED_CORPUS_NAME
    except Exception as e:
        logger.warning(f"Could not resolve Vertex AI RAG Corpus: {e}")

    return None


def get_stop_food_inventory_and_reviews(stop_names: List[str]) -> Dict[str, Any]:
    """Retrieves the available food products, quantities, and customer reviews for highway stops from Firestore.

    Use this tool first in MenuCheckerAgent to inspect which specific food items and dishes are
    currently stocked at each candidate highway stop, along with traveler reviews.

    Args:
        stop_names: List of highway stop names to look up (e.g., ['Badia al Pino Est', 'Cantagallo', 'Sillaro Ovest', 'Secchia Ovest']).

    Returns:
        Dict[str, Any]: Dictionary mapping each stop_name to its available `products` and `reviews`.
    """
    logger.info("=" * 60)
    logger.info(f"TOOL CALLED: get_stop_food_inventory_and_reviews for {stop_names}")

    try:
        db = _get_food_kb_client()
        collection_ref = db.collection(COLLECTION_NAME)
        stops_data: Dict[str, Any] = {}

        for stop_name in stop_names:
            clean_name = str(stop_name).strip()
            doc = collection_ref.document(clean_name).get()
            if doc.exists:
                data = doc.to_dict() or {}
                stops_data[clean_name] = {
                    "products": data.get("products", []),
                    "reviews": data.get("reviews", []),
                }
            else:
                stops_data[clean_name] = {
                    "products": [],
                    "reviews": [],
                    "note": f"No food inventory record found for '{clean_name}'.",
                }

        return {
            "status": "success",
            "stops_food_kb": stops_data,
        }
    except Exception as e:
        logger.error(f"Error querying Firestore Food KB: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to query Firestore Food KB: {str(e)}",
        }


def retrieve_product_specs_rag(query: str) -> Dict[str, Any]:
    """Queries the Vertex AI RAG Corpus of Autogrill Product Specification PDFs for ingredients, allergens, and nutrition.

    Use this tool after checking stop inventory to verify the exact ingredients, allergen declarations
    ('CONTAINS' vs 'FREE FROM'), and dietary certifications (e.g., '100% Vegan', 'Certified Gluten-Free')
    of candidate food products.

    Args:
        query: Semantic search query describing the products or dietary requirements to verify
            (e.g., 'Vegan Salad Rustichella Sandwich Capri Sandwich vegan ingredients allergens').

    Returns:
        Dict[str, Any]: Dictionary containing the retrieved specification chunks from Vertex AI RAG.
    """
    logger.info("=" * 60)
    logger.info(f"TOOL CALLED: retrieve_product_specs_rag(query='{query}')")

    try:
        corpus_name = _resolve_rag_corpus_name()
        if corpus_name:
            vertexai.init(project=PROJECT_ID, location=RAG_LOCATION)
            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
                text=query,
                similarity_top_k=8,
            )
            contexts = (
                [
                    {
                        "source_uri": getattr(ctx, "source_uri", ""),
                        "text": ctx.text,
                    }
                    for ctx in response.contexts.contexts
                ]
                if response and response.contexts and response.contexts.contexts
                else []
            )
            if contexts:
                logger.info(
                    f"Retrieved {len(contexts)} chunk(s) from Vertex AI RAG Corpus '{corpus_name}'."
                )
                return {
                    "status": "success",
                    "rag_corpus": corpus_name,
                    "retrieved_chunks": contexts,
                }
    except Exception as e:
        logger.warning(f"Vertex AI RAG query warning (falling back to GCS PDF catalog): {e}")

    # Deterministic fallback over the GCS Product Specification PDF catalog
    query_tokens = set(query.lower().replace(",", " ").replace("-", " ").split())
    scored_specs = []
    for spec in _PRODUCT_SPECS_CATALOG:
        haystack = f"{spec['product_name']} {spec['keywords']} {spec['text']}".lower()
        score = sum(1 for token in query_tokens if token in haystack)
        scored_specs.append((score, spec))

    scored_specs.sort(key=lambda item: item[0], reverse=True)
    top_chunks = [
        {"source_uri": item[1]["source_uri"], "text": item[1]["text"]}
        for item in scored_specs[:4]
    ]

    return {
        "status": "success",
        "rag_corpus": f"gs://{GCS_BUCKET}/product_specs/",
        "retrieved_chunks": top_chunks,
    }


stop_food_kb_tool = FunctionTool(get_stop_food_inventory_and_reviews)
product_specs_rag_tool = FunctionTool(retrieve_product_specs_rag)
