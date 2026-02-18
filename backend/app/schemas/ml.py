from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    symbol: str = Field(default="EURUSD")
    timeframe: str = Field(default="H1")
    bars: int = Field(default=5000, ge=500, le=50000)
    forward_bars: int = Field(default=10, ge=3, le=50)
    model_params: dict | None = None


class ValidateRequest(BaseModel):
    model_id: str
    symbol: str = Field(default="EURUSD")
    timeframe: str = Field(default="H1")
    bars: int = Field(default=5000, ge=500, le=50000)
    n_splits: int = Field(default=5, ge=2, le=10)


class PredictRequest(BaseModel):
    model_id: str
    symbol: str = Field(default="EURUSD")
    timeframe: str = Field(default="H1")
    bars: int = Field(default=200, ge=50, le=1000)


class TrainResponse(BaseModel):
    model_id: str
    metrics: dict
    top_features: dict


class ValidateResponse(BaseModel):
    model_id: str
    n_splits: int
    results: list[dict]


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    confidence: str
    signal: str


class ModelListResponse(BaseModel):
    models: list[dict]
