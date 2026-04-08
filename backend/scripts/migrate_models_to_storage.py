"""
One-shot migration script: upload local ML model pickle files to Supabase Storage.

Usage (from backend/ directory):
    python scripts/migrate_models_to_storage.py

What it does:
  1. Scans backend/app/ml/saved_models/ for *.pkl files
  2. Uploads each to Supabase Storage bucket 'ml-models'
  3. Inserts a row in ml_models table if one doesn't exist yet
  4. Prints a summary: migrated / already_exists / errors

Requirements:
  - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY set in .env
  - Run from the backend/ directory so that .env is found
"""

import json
import sys
from pathlib import Path

# ── path setup ──────────────────────────────────────────────────────────────
# Allow imports from the backend package when running as a script
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ── imports ─────────────────────────────────────────────────────────────────
from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from app.core.config import get_settings
from app.ml.model_registry import BUCKET_NAME, MODELS_DIR

BUCKET = BUCKET_NAME
MODELS_PATH = MODELS_DIR


def run_migration() -> None:
    settings = get_settings()
    if not settings.supabase_service_role_key:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY is not set in .env — aborting.")
        sys.exit(1)

    from supabase import create_client

    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)

    # Ensure bucket exists
    try:
        sb.storage.get_bucket(BUCKET)
        print(f"Bucket '{BUCKET}' exists.")
    except Exception:
        sb.storage.create_bucket(BUCKET, options={"public": False})
        print(f"Bucket '{BUCKET}' created.")

    # Collect local pkl files
    pkl_files = [p for p in MODELS_PATH.glob("*.pkl") if not p.name.endswith("_meta.json")]

    if not pkl_files:
        print(f"No local .pkl files found in {MODELS_PATH} — nothing to migrate.")
        return

    print(f"Found {len(pkl_files)} local model(s) to process.\n")

    migrated = 0
    already_exists = 0
    errors = 0

    for pkl_path in sorted(pkl_files):
        model_id = pkl_path.stem  # filename without extension

        # Check if already in DB
        try:
            res = sb.table("ml_models").select("model_id").eq("model_id", model_id).execute()
            if res.data:
                print(f"  [SKIP]  {model_id} — already in DB")
                already_exists += 1
                continue
        except Exception as e:
            print(f"  [ERROR] {model_id} — DB check failed: {e}")
            errors += 1
            continue

        # Upload to Storage
        storage_path = f"{model_id}/{model_id}.pkl"
        try:
            pkl_bytes = pkl_path.read_bytes()
            sb.storage.from_(BUCKET).upload(
                storage_path,
                pkl_bytes,
                {"content-type": "application/octet-stream"},
            )
        except Exception as e:
            # Storage may return 409 if object already exists
            if "already exists" in str(e).lower() or "409" in str(e):
                print(f"  [SKIP]  {model_id} — already in Storage")
            else:
                print(f"  [ERROR] {model_id} — Storage upload failed: {e}")
                errors += 1
                continue

        # Read _meta.json if present
        meta_path = MODELS_PATH / f"{model_id}_meta.json"
        metadata: dict = {}
        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"  [WARN]  {model_id} — could not read meta.json: {e}")

        name = metadata.get("name", model_id)
        metrics = metadata.get("metrics", {})
        feature_importance = metadata.get("feature_importance")

        # Parse symbol / timeframe from name
        parts = name.rsplit("_", 1)
        symbol = parts[0] if len(parts) == 2 else name
        timeframe = parts[1] if len(parts) == 2 else "H1"

        # Insert into ml_models
        try:
            sb.table("ml_models").insert(
                {
                    "model_id": model_id,
                    "name": name,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "is_active": False,
                    "metrics": metrics,
                    "feature_importance": feature_importance,
                    "params": {"storage_path": storage_path, "migrated": True},
                }
            ).execute()
            print(f"  [OK]    {model_id} — uploaded & registered")
            migrated += 1
        except Exception as e:
            print(f"  [ERROR] {model_id} — DB insert failed: {e}")
            errors += 1

    # ── summary ──────────────────────────────────────────────────────────────
    print()
    print("=" * 50)
    print(f"Migration complete.")
    print(f"  Migrated      : {migrated}")
    print(f"  Already exists: {already_exists}")
    print(f"  Errors        : {errors}")
    print("=" * 50)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
