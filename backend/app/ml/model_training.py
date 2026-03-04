import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.core.logging_config import get_logger
from app.ml.feature_engineering import FeatureEngineer

logger = get_logger(__name__)


class ModelTrainer:
    """Train and evaluate ML models for trade signal prediction."""

    def __init__(self, model_params: dict | None = None):
        self.model_params = model_params or {
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "eval_metric": "logloss",
            "random_state": 42,
        }
        self.pipeline: Pipeline | None = None

    def train(self, train_data: pd.DataFrame) -> Pipeline:
        """
        Train an XGBoost classifier pipeline.

        Args:
            train_data: DataFrame with features and 'target' column
        """
        feature_cols = FeatureEngineer.get_feature_columns(train_data)
        X_train = train_data[feature_cols].values
        y_train = train_data["target"].values

        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", XGBClassifier(**self.model_params)),
        ])

        self.pipeline.fit(X_train, y_train)

        # Training metrics
        train_pred = self.pipeline.predict(X_train)
        train_acc = accuracy_score(y_train, train_pred)

        logger.info(
            "Model trained: %d samples, accuracy=%.4f, features=%d",
            len(X_train), train_acc, len(feature_cols),
        )

        return self.pipeline

    def evaluate(self, test_data: pd.DataFrame) -> dict:
        """Evaluate the trained model on test data."""
        if self.pipeline is None:
            raise RuntimeError("Model not trained yet. Call train() first.")

        feature_cols = FeatureEngineer.get_feature_columns(test_data)
        X_test = test_data[feature_cols].values
        y_test = test_data["target"].values

        y_pred = self.pipeline.predict(X_test)
        y_proba = self.pipeline.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
            "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
            "test_samples": len(y_test),
            "positive_rate": round(y_test.mean(), 4),
            "predicted_positive_rate": round(y_pred.mean(), 4),
        }

        logger.info(
            "Model evaluation: acc=%.4f, precision=%.4f, recall=%.4f, f1=%.4f",
            metrics["accuracy"], metrics["precision"],
            metrics["recall"], metrics["f1_score"],
        )

        return metrics

    def get_feature_importance(self, train_data: pd.DataFrame) -> dict[str, float]:
        """Get feature importance from the trained model."""
        if self.pipeline is None:
            raise RuntimeError("Model not trained yet.")

        feature_cols = FeatureEngineer.get_feature_columns(train_data)
        classifier = self.pipeline.named_steps["classifier"]
        importances = classifier.feature_importances_

        importance_dict = {col: float(imp) for col, imp in zip(feature_cols, importances)}
        # Sort by importance descending
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

    def walk_forward_validate(
        self, splits: list[tuple[pd.DataFrame, pd.DataFrame]]
    ) -> list[dict]:
        """Run walk-forward validation across multiple splits."""
        results = []

        for i, (train, test) in enumerate(splits):
            self.train(train)
            metrics = self.evaluate(test)
            metrics["split"] = i
            results.append(metrics)
            logger.info("Walk-forward split %d: acc=%.4f", i, metrics["accuracy"])

        # Average metrics
        avg_metrics = {
            key: round(np.mean([r[key] for r in results]), 4)
            for key in ["accuracy", "precision", "recall", "f1_score"]
        }
        logger.info(
            "Walk-forward avg: acc=%.4f, f1=%.4f",
            avg_metrics["accuracy"], avg_metrics["f1_score"],
        )

        return results
