from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/performance")
async def get_performance(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = MetricsService(db)
    return await service.get_performance()


@router.get("/equity-curve")
async def get_equity_curve(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = MetricsService(db)
    return await service.get_equity_curve()
