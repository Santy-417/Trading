import io
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

from sklearn.pipeline import Pipeline

from app.core.logging_config import get_logger

logger = get_logger(__name__)

MODELS_DIR = Path(__file__).parent / "saved_models"
BUCKET_NAME = "ml-models"


class ModelRegistry:
    """
    Save, load, and manage trained ML models.

    Primary storage: Supabase Storage (bucket 'ml-models').
    Fallback: local filesystem under `saved_models/` (used when
    SUPABASE_SERVICE_ROLE_KEY is not configured or Storage is unreachable).

    An in-memory cache avoids re-downloading pipelines within the same process.
    """

    def __init__(self, models_dir: Path | None = None):
        self.models_dir = models_dir or MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Pipeline] = {}
        self._supabase = None  # Lazy-initialized on first use

    # ── Supabase client ───────────────────────────────────────────────────────

    def _get_supabase(self):
        """
        Return a configured supabase-py sync client, or None if the service
        role key is not set (triggers transparent local-filesystem fallback).
        """
        if self._supabase is not None:
            return self._supabase

        try:
            from app.core.config import get_settings
            settings = get_settings()
            if not settings.supabase_service_role_key:
                return None

            from supabase import create_client
            client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
            )

            # Ensure bucket exists (idempotent)
            try:
                client.storage.get_bucket(BUCKET_NAME)
            except Exception:
                client.storage.create_bucket(BUCKET_NAME, options={"public": False})

            self._supabase = client
            return self._supabase

        except Exception as e:
            logger.warning("Supabase client init failed — using local fallback: %s", e)
            return None

    # ── save ─────────────────────────────────────────────────────────────────

    def save(
        self,
        pipeline: Pipeline,
        name: str,
        metrics: dict,
        feature_importance: dict | None = None,
    ) -> str:
        """
        Persist a trained pipeline.

        With Supabase configured:
          - Serializes to BytesIO (no disk write)
          - Uploads to ml-models/{model_id}/{model_id}.pkl
          - Inserts a row in the ml_models table

        Without Supabase (fallback):
          - Writes .pkl + _meta.json to saved_models/ (previous behaviour)

        Returns:
            model_id (str)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        model_id = f"{name}_{timestamp}"

        buf = io.BytesIO()
        pickle.dump(pipeline, buf)
        pkl_bytes = buf.getvalue()

        sb = self._get_supabase()

        if sb:
            storage_path = f"{model_id}/{model_id}.pkl"
            try:
                sb.storage.from_(BUCKET_NAME).upload(
                    storage_path,
                    pkl_bytes,
                    {"content-type": "application/octet-stream"},
                )
            except Exception as e:
                logger.error("Storage upload failed for %s: %s", model_id, e)
                raise

            # Parse symbol / timeframe from name (e.g. "EURUSD_H1")
            parts = name.rsplit("_", 1)
            symbol = parts[0] if len(parts) == 2 else name
            timeframe = parts[1] if len(parts) == 2 else "H1"

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
                        "params": {"storage_path": storage_path},
                    }
                ).execute()
            except Exception as e:
                logger.error("DB insert failed for %s: %s — model is in Storage but not in DB", model_id, e)
                raise

            logger.info("Model saved to Supabase Storage: %s", model_id)

        else:
            # Local filesystem fallback
            model_path = self.models_dir / f"{model_id}.pkl"
            with open(model_path, "wb") as f:
                f.write(pkl_bytes)

            metadata = {
                "model_id": model_id,
                "name": name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
                "feature_importance": feature_importance,
            }
            meta_path = self.models_dir / f"{model_id}_meta.json"
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info("Model saved to local filesystem: %s", model_id)

        return model_id

    # ── load ─────────────────────────────────────────────────────────────────

    def load(self, model_id: str) -> Pipeline:
        """
        Load a trained pipeline by ID.

        Resolution order:
          1. In-memory cache
          2. Supabase Storage (download + cache)
          3. Local filesystem fallback (with warning)
        """
        if model_id in self._cache:
            return self._cache[model_id]

        sb = self._get_supabase()

        if sb:
            try:
                storage_path = f"{model_id}/{model_id}.pkl"
                data = sb.storage.from_(BUCKET_NAME).download(storage_path)
                pipeline = pickle.loads(data)
                self._cache[model_id] = pipeline
                logger.info("Model loaded from Supabase Storage: %s", model_id)
                return pipeline
            except Exception as e:
                logger.warning(
                    "Storage load failed for %s, trying local fallback: %s", model_id, e
                )

        # Local filesystem fallback
        model_path = self.models_dir / f"{model_id}.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_id}")

        with open(model_path, "rb") as f:
            pipeline = pickle.load(f)

        self._cache[model_id] = pipeline
        logger.info("Model loaded from local filesystem: %s", model_id)
        return pipeline

    # ── load_metadata ─────────────────────────────────────────────────────────

    def load_metadata(self, model_id: str) -> dict:
        """Load model metadata."""
        sb = self._get_supabase()

        if sb:
            try:
                res = (
                    sb.table("ml_models")
                    .select("*")
                    .eq("model_id", model_id)
                    .single()
                    .execute()
                )
                return res.data
            except Exception as e:
                logger.warning(
                    "DB metadata fetch failed for %s, trying local fallback: %s", model_id, e
                )

        # Local fallback
        meta_path = self.models_dir / f"{model_id}_meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found: {model_id}")

        with open(meta_path) as f:
            return json.load(f)

    # ── list_models ───────────────────────────────────────────────────────────

    def list_models(self) -> list[dict]:
        """List all saved models with metadata."""
        sb = self._get_supabase()

        if sb:
            try:
                res = (
                    sb.table("ml_models")
                    .select("*")
                    .order("created_at", desc=True)
                    .execute()
                )
                return res.data
            except Exception as e:
                logger.warning("DB list failed, using local fallback: %s", e)

        # Local fallback
        models = []
        for meta_file in sorted(self.models_dir.glob("*_meta.json"), reverse=True):
            try:
                with open(meta_file) as f:
                    models.append(json.load(f))
            except (json.JSONDecodeError, OSError) as err:
                logger.warning(
                    "Skipping corrupted model metadata: %s (%s)", meta_file.name, err
                )
        return models

    # ── get_latest ────────────────────────────────────────────────────────────

    def get_latest(self, name: str) -> str | None:
        """Get the latest model ID for a given name."""
        models = [m for m in self.list_models() if m.get("name") == name]
        if not models:
            return None
        return models[0]["model_id"]

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, model_id: str) -> bool:
        """
        Delete a model from Storage + DB + local filesystem + in-memory cache.
        Returns True if anything was deleted.
        """
        self._cache.pop(model_id, None)
        deleted = False

        sb = self._get_supabase()
        if sb:
            try:
                storage_path = f"{model_id}/{model_id}.pkl"
                sb.storage.from_(BUCKET_NAME).remove([storage_path])
                deleted = True
            except Exception as e:
                logger.warning("Storage delete failed for %s: %s", model_id, e)

            try:
                sb.table("ml_models").delete().eq("model_id", model_id).execute()
                deleted = True
            except Exception as e:
                logger.warning("DB delete failed for %s: %s", model_id, e)

        # Also remove local files if they exist (covers fallback + migrated models)
        for path in [
            self.models_dir / f"{model_id}.pkl",
            self.models_dir / f"{model_id}_meta.json",
        ]:
            if path.exists():
                path.unlink()
                deleted = True

        if deleted:
            logger.info("Model deleted: %s", model_id)
        return deleted


# Singleton
model_registry = ModelRegistry()
