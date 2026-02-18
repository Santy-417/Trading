import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path

from sklearn.pipeline import Pipeline

from app.core.logging_config import get_logger

logger = get_logger(__name__)

MODELS_DIR = Path(__file__).parent / "saved_models"


class ModelRegistry:
    """Save, load, and manage trained ML models."""

    def __init__(self, models_dir: Path | None = None):
        self.models_dir = models_dir or MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        pipeline: Pipeline,
        name: str,
        metrics: dict,
        feature_importance: dict | None = None,
    ) -> str:
        """
        Save a trained model with metadata.

        Returns:
            Model ID (filename without extension).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        model_id = f"{name}_{timestamp}"

        # Save model
        model_path = self.models_dir / f"{model_id}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(pipeline, f)

        # Save metadata
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

        logger.info("Model saved: %s", model_id)
        return model_id

    def load(self, model_id: str) -> Pipeline:
        """Load a trained model by ID."""
        model_path = self.models_dir / f"{model_id}.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_id}")

        with open(model_path, "rb") as f:
            pipeline = pickle.load(f)

        logger.info("Model loaded: %s", model_id)
        return pipeline

    def load_metadata(self, model_id: str) -> dict:
        """Load model metadata."""
        meta_path = self.models_dir / f"{model_id}_meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found: {model_id}")

        with open(meta_path) as f:
            return json.load(f)

    def list_models(self) -> list[dict]:
        """List all saved models with metadata."""
        models = []
        for meta_file in sorted(self.models_dir.glob("*_meta.json"), reverse=True):
            with open(meta_file) as f:
                models.append(json.load(f))
        return models

    def get_latest(self, name: str) -> str | None:
        """Get the latest model ID for a given name."""
        models = [m for m in self.list_models() if m["name"] == name]
        if not models:
            return None
        return models[0]["model_id"]

    def delete(self, model_id: str) -> bool:
        """Delete a model and its metadata."""
        model_path = self.models_dir / f"{model_id}.pkl"
        meta_path = self.models_dir / f"{model_id}_meta.json"

        deleted = False
        for path in [model_path, meta_path]:
            if path.exists():
                path.unlink()
                deleted = True

        if deleted:
            logger.info("Model deleted: %s", model_id)
        return deleted


# Singleton
model_registry = ModelRegistry()
