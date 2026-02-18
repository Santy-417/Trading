import pandas as pd
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.core.logging_config import get_logger
from app.ml.feature_engineering import FeatureEngineer

logger = get_logger(__name__)


class HyperparameterOptimizer:
    """Optimize XGBoost hyperparameters via grid search with cross-validation."""

    DEFAULT_PARAM_GRID = {
        "classifier__n_estimators": [100, 200, 300],
        "classifier__max_depth": [4, 6, 8],
        "classifier__learning_rate": [0.01, 0.05, 0.1],
        "classifier__subsample": [0.7, 0.8, 0.9],
        "classifier__colsample_bytree": [0.7, 0.8, 0.9],
    }

    def __init__(self, param_grid: dict | None = None):
        self.param_grid = param_grid or self.DEFAULT_PARAM_GRID

    def optimize(
        self,
        train_data: pd.DataFrame,
        cv: int = 3,
        scoring: str = "f1",
        n_jobs: int = -1,
    ) -> dict:
        """
        Run grid search optimization.

        Returns:
            Dict with best_params, best_score, and all results.
        """
        feature_cols = FeatureEngineer.get_feature_columns(train_data)
        X = train_data[feature_cols].values
        y = train_data["target"].values

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", XGBClassifier(
                eval_metric="logloss",
                random_state=42,
            )),
        ])

        logger.info(
            "Starting hyperparameter optimization: %d combinations, cv=%d",
            self._count_combinations(),
            cv,
        )

        grid_search = GridSearchCV(
            pipeline,
            self.param_grid,
            cv=cv,
            scoring=scoring,
            n_jobs=n_jobs,
            verbose=0,
            refit=True,
        )

        grid_search.fit(X, y)

        best_params = {
            k.replace("classifier__", ""): v
            for k, v in grid_search.best_params_.items()
        }

        logger.info(
            "Optimization complete: best %s=%.4f, params=%s",
            scoring,
            grid_search.best_score_,
            best_params,
        )

        return {
            "best_params": best_params,
            "best_score": round(grid_search.best_score_, 4),
            "scoring": scoring,
            "cv_folds": cv,
            "best_pipeline": grid_search.best_estimator_,
        }

    def _count_combinations(self) -> int:
        count = 1
        for values in self.param_grid.values():
            count *= len(values)
        return count
