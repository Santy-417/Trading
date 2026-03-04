from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.data_loader import DataLoader
from app.core.logging_config import get_logger
from app.ml.dataset_builder import DatasetBuilder
from app.ml.model_registry import model_registry
from app.ml.model_training import ModelTrainer
from app.ml.prediction import Predictor
from app.schemas.ml import PredictRequest, TrainRequest, ValidateRequest

logger = get_logger(__name__)


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string as tz-naive (MT5 data has tz-naive index)."""
    dt = datetime.fromisoformat(dt_str)
    return dt.replace(tzinfo=None)


class MLService:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    async def train(self, request: TrainRequest) -> dict:
        """Train a new ML model."""
        loader = DataLoader()
        if request.date_from and request.date_to:
            date_from = _parse_datetime(request.date_from)
            date_to = _parse_datetime(request.date_to)
            df, _ = await loader.load_with_warmup(
                request.symbol, request.timeframe,
                date_from, date_to, request.warmup_bars,
            )
        else:
            df = await loader.load_from_mt5(
                request.symbol, request.timeframe, count=request.bars
            )
        df = DataLoader.validate_data(df)

        # Build dataset
        builder = DatasetBuilder(forward_bars=request.forward_bars)
        dataset = builder.build(df)
        train_data, test_data = builder.split_train_test(dataset)

        # Train model
        trainer = ModelTrainer(model_params=request.model_params)
        trainer.train(train_data)
        metrics = trainer.evaluate(test_data)
        importance = trainer.get_feature_importance(train_data)

        # Save model
        model_name = f"{request.symbol}_{request.timeframe}"
        model_id = model_registry.save(
            pipeline=trainer.pipeline,
            name=model_name,
            metrics=metrics,
            feature_importance=importance,
        )

        return {
            "model_id": model_id,
            "metrics": metrics,
            "top_features": dict(list(importance.items())[:10]),
        }

    async def validate(self, request: ValidateRequest) -> dict:
        """Walk-forward validate a model."""
        loader = DataLoader()
        if request.date_from and request.date_to:
            date_from = _parse_datetime(request.date_from)
            date_to = _parse_datetime(request.date_to)
            df, _ = await loader.load_with_warmup(
                request.symbol, request.timeframe,
                date_from, date_to, request.warmup_bars,
            )
        else:
            df = await loader.load_from_mt5(
                request.symbol, request.timeframe, count=request.bars
            )
        df = DataLoader.validate_data(df)

        builder = DatasetBuilder()
        dataset = builder.build(df)
        splits = builder.walk_forward_split(dataset, n_splits=request.n_splits)

        trainer = ModelTrainer()
        results = trainer.walk_forward_validate(splits)

        return {
            "model_id": request.model_id,
            "n_splits": len(results),
            "results": results,
        }

    async def predict(self, request: PredictRequest) -> dict:
        """Make a prediction with a trained model."""
        loader = DataLoader()
        df = await loader.load_from_mt5(
            request.symbol, request.timeframe, count=request.bars
        )

        predictor = Predictor(model_id=request.model_id)
        return predictor.predict(df)

    def list_models(self) -> list[dict]:
        """List all saved models."""
        return model_registry.list_models()

    def delete_model(self, model_id: str) -> bool:
        """Delete a model and its metadata."""
        return model_registry.delete(model_id)
