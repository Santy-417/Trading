from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.schemas.backtest import (
    BacktestEstimateRequest,
    BacktestRequest,
    BacktestResponse,
    OptimizeRequest,
)
from app.services.backtest_service import BacktestService

router = APIRouter(prefix="/backtest", tags=["Backtesting"])


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    body: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = BacktestService(db)
    return await service.run_backtest(body)


@router.post("/estimate")
async def estimate_bars(
    body: BacktestEstimateRequest,
    _user: dict = Depends(get_current_user),
):
    """Estimate the number of bars for a given date range."""
    return BacktestService.estimate_bars(body)


@router.post("/optimize")
async def run_optimization(
    body: OptimizeRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = BacktestService(db)
    return await service.run_optimization(body)


@router.get("/results")
async def get_results(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = BacktestService(db)
    return await service.get_results(limit=limit)
