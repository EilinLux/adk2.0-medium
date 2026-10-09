# adk_agent_app/test_connections.py
import os
from pathlib import Path
import sys

# Ensure project root is on sys.path when run directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import firestore

from adk_agent_app.config import (
    FIRESTORE_APP_DB,
    FIRESTORE_SESSION_DB,
    PROJECT_ID,
)


def test_firestore(db_name: str, label: str) -> bool:
    """Tests read connection to a specific Firestore database."""
    print(f"Testing Firestore ({label} -> '{db_name}')...", end=" ")
    try:
        db = firestore.Client(project=PROJECT_ID, database=db_name)
        col_iter = db.collections()
        _ = next(col_iter, None)
        print("✅ SUCCESS")
        return True
    except Exception as e:
        print(f"❌ FAILED\n   Error: {e}")
        return False


def run_all_tests() -> bool:
    os.environ["_ADK_PREFLIGHT_RAN"] = "1"
    print("=" * 60)
    print(f" RUNNING GCP RESOURCE CONNECTIVITY TESTS FOR SOSTA_APP: {PROJECT_ID}")
    print("=" * 60 + "\n")

    results = [
        test_firestore(FIRESTORE_APP_DB, "Application DB"),
        test_firestore(FIRESTORE_SESSION_DB, "Session Memory"),
    ]

    print("\n" + "=" * 60)
    is_success = all(results)

    if is_success:
        print("🎉 ALL SOSTA_APP GCP RESOURCES PASSED CONNECTIVITY CHECKS!")
    else:
        failed_count = results.count(False)
        print(f"⚠️ {failed_count} TEST(S) FAILED. Check IAM permissions or Terraform state.")
    print("=" * 60)

    return is_success


if __name__ == "__main__":
    if not os.getenv("_ADK_PREFLIGHT_RAN"):
        run_all_tests()