from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="train_model")
def train_model_task(
    self,
    symbol: str,
    timeframe: str,
    bars: int = 5000,
    model_params: dict | None = None,
    forward_bars: int = 10,
):
    """Train an ML model as a background Celery task."""
    import asyncio

    from app.backtesting.data_loader import DataLoader
    from app.ml.dataset_builder import DatasetBuilder
    from app.ml.model_registry import model_registry
    from app.ml.model_training import ModelTrainer

    async def _run():
        # Load data
        loader = DataLoader()
        df = await loader.load_from_mt5(symbol, timeframe, count=bars)
        df = DataLoader.validate_data(df)

        # Build dataset
        builder = DatasetBuilder(forward_bars=forward_bars)
        dataset = builder.build(df)
        train, test = builder.split_train_test(dataset)

        # Train
        trainer = ModelTrainer(model_params=model_params)
        trainer.train(train)
        metrics = trainer.evaluate(test)
        importance = trainer.get_feature_importance(train)

        # Save
        model_name = f"{symbol}_{timeframe}"
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

    return asyncio.run(_run())


@celery_app.task(bind=True, name="validate_model")
def validate_model_task(
    self,
    model_id: str,
    symbol: str,
    timeframe: str,
    bars: int = 5000,
    n_splits: int = 5,
):
    """Walk-forward validate a model as a background task."""
    import asyncio

    from app.backtesting.data_loader import DataLoader
    from app.ml.dataset_builder import DatasetBuilder
    from app.ml.model_training import ModelTrainer

    async def _run():
        loader = DataLoader()
        df = await loader.load_from_mt5(symbol, timeframe, count=bars)
        df = DataLoader.validate_data(df)

        builder = DatasetBuilder()
        dataset = builder.build(df)
        splits = builder.walk_forward_split(dataset, n_splits=n_splits)

        trainer = ModelTrainer()
        results = trainer.walk_forward_validate(splits)

        return {
            "model_id": model_id,
            "n_splits": len(results),
            "results": results,
        }

    return asyncio.run(_run())
