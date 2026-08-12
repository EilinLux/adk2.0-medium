# terraform/terraform_infrastructure/seeding/vertex_rag_seed.py
import concurrent.futures
import os
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions
import vertexai
from vertexai.preview import rag

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
LOCATION = os.getenv("VERTEX_RAG_LOCATION", "europe-west3")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
BUCKET_NAME = os.getenv("GCS_BUCKET", f"adk-agent-{ENVIRONMENT}-product-specs")
GCS_PDF_URI = f"gs://{BUCKET_NAME}/product_specs/"
CORPUS_DISPLAY_NAME = os.getenv(
    "VERTEX_RAG_CORPUS_DISPLAY_NAME", "sosta-product-specs-corpus"
)


def ensure_rag_corpus() -> str:
    """Creates or retrieves the Vertex AI RAG Corpus and imports product specification PDFs from GCS."""
    print(
        f"Initializing Vertex AI RAG in project='{PROJECT_ID}', location='{LOCATION}'..."
    )
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Check if the RAG Corpus already exists
    existing_corpora = list(rag.list_corpora())
    target_corpus = None
    for corpus in existing_corpora:
        if corpus.display_name == CORPUS_DISPLAY_NAME:
            target_corpus = corpus
            print(f"✅ Found existing RAG Corpus: {corpus.name} ({corpus.display_name})")
            break

    # 2. Create the RAG Corpus if it does not exist
    if target_corpus is None:
        print(f"🚀 Creating new Vertex AI RAG Corpus '{CORPUS_DISPLAY_NAME}'...")
        print(
            "   (Note: First-time regional Spanner backing store provisioning in GCP can take 10–20 minutes.)"
        )
        embedding_model_config = rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        )
        try:
            target_corpus = rag.create_corpus(
                display_name=CORPUS_DISPLAY_NAME,
                description="Autogrill & Sosta highway stop product specification sheets (ingredients, allergens, nutrition).",
                embedding_model_config=embedding_model_config,
                timeout=600,
            )
            print(f"✅ Created RAG Corpus: {target_corpus.name}")
        except (concurrent.futures.TimeoutError, google_exceptions.RetryError):
            print(
                "⏳ CreateRagCorpus operation is still provisioning the regional Spanner instance in the background."
            )
            print(
                "   Re-run `uv run python terraform/terraform_infrastructure/seeding/vertex_rag_seed.py` in a few minutes to import the PDFs."
            )
            return ""

    # 3. Check existing files in the corpus; import from GCS if empty
    existing_files = list(rag.list_files(corpus_name=target_corpus.name))
    if existing_files:
        print(
            f"✅ RAG Corpus already contains {len(existing_files)} file(s). Skipping re-import."
        )
    else:
        print(f"📄 Importing PDFs from '{GCS_PDF_URI}' into '{target_corpus.name}'...")
        import_response = rag.import_files(
            corpus_name=target_corpus.name,
            paths=[GCS_PDF_URI],
            chunk_size=512,
            chunk_overlap=100,
        )
        print(
            f"✅ Successfully imported {import_response.imported_rag_files_count} PDF file(s) into Vertex AI RAG Corpus!"
        )

    print(f"\n📌 VERTEX_RAG_CORPUS={target_corpus.name}")
    return target_corpus.name


if __name__ == "__main__":
    ensure_rag_corpus()
