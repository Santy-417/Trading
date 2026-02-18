import pandas as pd
from sklearn.pipeline import Pipeline

from app.core.logging_config import get_logger
from app.ml.feature_engineering import FeatureEngineer
from app.ml.model_registry import model_registry

logger = get_logger(__name__)


class Predictor:
    """Make predictions using a trained ML model."""

    def __init__(self, model_id: str | None = None, pipeline: Pipeline | None = None):
        if pipeline:
            self._pipeline = pipeline
        elif model_id:
            self._pipeline = model_registry.load(model_id)
        else:
            raise ValueError("Provide either model_id or pipeline")

    def predict(self, df: pd.DataFrame) -> dict:
        """
        Predict on current market data.

        Args:
            df: OHLCV DataFrame (raw — features will be generated)

        Returns:
            Dict with prediction, probability, and confidence.
        """
        # Generate features
        featured = FeatureEngineer.add_all_features(df)
        featured = featured.dropna()

        if featured.empty:
            return {"prediction": 0, "probability": 0.0, "confidence": "low"}

        feature_cols = FeatureEngineer.get_feature_columns(featured)
        X = featured[feature_cols].iloc[[-1]].values  # Last row only

        prediction = int(self._pipeline.predict(X)[0])
        probability = float(self._pipeline.predict_proba(X)[0][1])

        # Confidence levels
        if probability > 0.75 or probability < 0.25:
            confidence = "high"
        elif probability > 0.65 or probability < 0.35:
            confidence = "medium"
        else:
            confidence = "low"

        logger.info(
            "Prediction: %d (prob=%.4f, confidence=%s)",
            prediction, probability, confidence,
        )

        return {
            "prediction": prediction,
            "probability": round(probability, 4),
            "confidence": confidence,
            "signal": "BUY" if prediction == 1 else "NEUTRAL",
        }
