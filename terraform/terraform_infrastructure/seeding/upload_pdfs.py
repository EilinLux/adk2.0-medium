import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.storage import transfer_manager

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
BUCKET_NAME = os.getenv("GCS_BUCKET", f"adk-agent-{ENVIRONMENT}-product-specs")

# Locate 'product_pdfs' folder inside the current 'seeding' directory
SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_PDF_DIR = SCRIPT_DIR / "product_pdfs"
DESTINATION_PREFIX = "product_specs"

print(f"Connecting to Google Cloud Storage (Project: '{PROJECT_ID}')...")
storage_client = storage.Client(project=PROJECT_ID)

# ==========================================
# EXECUTION
# ==========================================
def upload_pdf_folder():
    if not LOCAL_PDF_DIR.exists() or not LOCAL_PDF_DIR.is_dir():
        print(f"❌ Error: Local directory '{LOCAL_PDF_DIR}' does not exist.")
        print(f"   Please create it and place your PDF files inside: {LOCAL_PDF_DIR}")
        sys.exit(1)

    print(f"Target Bucket: gs://{BUCKET_NAME}")
    print(f"Source Folder: {LOCAL_PDF_DIR}\n")

    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        if not bucket.exists():
            print(f"❌ Error: Bucket '{BUCKET_NAME}' does not exist. Ensure Terraform applied successfully.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to access bucket '{BUCKET_NAME}': {e}")
        sys.exit(1)

    # Collect all PDF files in seeding/product_pdfs/
    pdf_paths = [p for p in LOCAL_PDF_DIR.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"]

    if not pdf_paths:
        print(f"⚠️ No PDF files found in '{LOCAL_PDF_DIR}'.")
        return

    print(f"Uploading {len(pdf_paths)} file(s) using Transfer Manager...")

    results = transfer_manager.upload_many_from_filenames(
        bucket=bucket,
        filenames=[str(p) for p in pdf_paths],
        blob_name_prefix=f"{DESTINATION_PREFIX}/",
        source_directory=str(LOCAL_PDF_DIR),
        max_workers=8
    )

    success_count = 0
    for p, result in zip(pdf_paths, results):
        blob_name = f"{DESTINATION_PREFIX}/{p.relative_to(LOCAL_PDF_DIR).as_posix()}"
        if isinstance(result, Exception):
            print(f"  ❌ Failed to upload '{blob_name}': {result}")
        else:
            print(f"  -> Uploaded: gs://{BUCKET_NAME}/{blob_name}")
            success_count += 1

    print(f"\n✅ Successfully uploaded {success_count}/{len(pdf_paths)} PDF specification(s) to GCS!")

if __name__ == "__main__":
    upload_pdf_folder()