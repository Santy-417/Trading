from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.schemas.ml import (
    ModelListResponse,
    PredictRequest,
    PredictResponse,
    TrainRequest,
    TrainResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.services.ml_service import MLService

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.post("/train", response_model=TrainResponse)
async def train_model(
    body: TrainRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = MLService(db)
    return await service.train(body)


@router.post("/validate", response_model=ValidateResponse)
async def validate_model(
    body: ValidateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = MLService(db)
    return await service.validate(body)


@router.post("/predict", response_model=PredictResponse)
async def predict(
    body: PredictRequest,
    _user: dict = Depends(get_current_user),
):
    service = MLService()
    return await service.predict(body)


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    _user: dict = Depends(get_current_user),
):
    service = MLService()
    return {"models": service.list_models()}


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    _user: dict = Depends(get_current_user),
):
    service = MLService()
    deleted = service.delete_model(model_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Model not found")
    return {"deleted": model_id}
