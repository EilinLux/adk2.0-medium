import os
import sys
from pathlib import Path
from google.cloud import firestore
from google.cloud import bigquery
from google.cloud import storage

# ==========================================
# CONFIGURATION
# ==========================================
PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
ENVIRONMENT = "dev"

# Database & Bucket Identifiers
FIRESTORE_SESSION_DB = "adk-agent-dev-session-memory-fs"
FIRESTORE_FOOD_KB_DB = "adk-agent-dev-food-kb-dev-fs"
BIGQUERY_DATASET = "soste_app_dev"
BIGQUERY_TABLE = "db_soste"
GCS_BUCKET = f"adk-agent-dev-product-specs"


def test_firestore(db_name: str, label: str) -> bool:
    """Tests read connection to a specific Firestore database."""
    print(f"Testing Firestore ({label} -> '{db_name}')...", end=" ")
    try:
        db = firestore.Client(project=PROJECT_ID, database=db_name)
        # Fix: Fetch the first collection reference without using page_size
        col_iter = db.collections()
        _ = next(col_iter, None)
        print("✅ SUCCESS")
        return True
    except Exception as e:
        print(f"❌ FAILED\n   Error: {e}")
        return False

def test_bigquery() -> bool:
    """Tests query execution against the BigQuery dataset & table."""
    full_table = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    print(f"Testing BigQuery Table ('{full_table}')...", end=" ")
    try:
        client = bigquery.Client(project=PROJECT_ID)
        query = f"SELECT COUNT(1) as total_rows FROM `{full_table}`"
        query_job = client.query(query)
        results = list(query_job.result())
        row_count = results[0]["total_rows"] if results else 0
        print(f"✅ SUCCESS (Table accessible, found {row_count} rows)")
        return True
    except Exception as e:
        print(f"❌ FAILED\n   Error: {e}")
        return False


def test_gcs_bucket() -> bool:
    """Tests access permissions to the Cloud Storage bucket."""
    print(f"Testing Cloud Storage Bucket ('gs://{GCS_BUCKET}')...", end=" ")
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.get_bucket(GCS_BUCKET)
        blobs = list(bucket.list_blobs(max_results=5))
        print(f"✅ SUCCESS (Bucket accessible, found {len(blobs)} sample object(s))")
        return True
    except Exception as e:
        print(f"❌ FAILED\n   Error: {e}")
        return False

def run_all_tests() -> bool:
    print("=" * 60)
    print(f" RUNNING GCP RESOURCE CONNECTIVITY TESTS FOR: {PROJECT_ID}")
    print("=" * 60 + "\n")

    results = []

    # 1. Test Firestore Databases
    results.append(test_firestore(FIRESTORE_SESSION_DB, "Session Memory"))
    results.append(test_firestore(FIRESTORE_FOOD_KB_DB, "Food Knowledge Base"))

    # 2. Test BigQuery Data Warehouse
    #results.append(test_bigquery())

    # 3. Test Cloud Storage Bucket
    results.append(test_gcs_bucket())

    print("\n" + "=" * 60)
    is_success = all(results)
    
    if is_success:
        print("🎉 ALL GCP RESOURCES PASSED CONNECTIVITY CHECKS!")
    else:
        failed_count = results.count(False)
        print(f"⚠️ {failed_count} TEST(S) FAILED. Check IAM permissions or Terraform state.")
    print("=" * 60)

    # CRITICAL: Return the boolean status to agent.py
    return is_success

if __name__ == "__main__":
    run_all_tests()