from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import trading_limiter
from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.schemas.order import (
    ClosePositionRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    ModifyPositionRequest,
    OrderResponse,
)
from app.schemas.trade import TradeListResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def _get_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/market", response_model=OrderResponse)
@trading_limiter
async def market_order(
    request: Request,
    body: MarketOrderRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.market_order(body, ip=_get_ip(request))


@router.post("/limit", response_model=OrderResponse)
@trading_limiter
async def limit_order(
    request: Request,
    body: LimitOrderRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.limit_order(body, ip=_get_ip(request))


@router.post("/close", response_model=OrderResponse)
@trading_limiter
async def close_position(
    request: Request,
    body: ClosePositionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.close_position(body.ticket, ip=_get_ip(request))


@router.post("/modify", response_model=OrderResponse)
@trading_limiter
async def modify_position(
    request: Request,
    body: ModifyPositionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.modify_position(
        ticket=body.ticket,
        sl=body.stop_loss,
        tp=body.take_profit,
        volume=body.volume,
        ip=_get_ip(request),
    )


@router.get("/symbol-info")
async def get_symbol_info(
    symbol: str = Query(default="EURUSD"),
    _user: dict = Depends(get_current_user),
):
    """Get symbol info including current bid/ask and stops level."""
    from app.integrations.metatrader.mt5_client import mt5_client

    await mt5_client.initialize()
    return await mt5_client.get_symbol_info(symbol)


@router.get("/open")
async def get_open_positions(
    _user: dict = Depends(get_current_user),
):
    service = OrderService(None)
    return await service.get_open_positions()


@router.get("/pending")
async def get_pending_orders(
    _user: dict = Depends(get_current_user),
):
    service = OrderService(None)
    return await service.get_pending_orders()


@router.post("/cancel", response_model=OrderResponse)
@trading_limiter
async def cancel_order(
    request: Request,
    body: ClosePositionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.cancel_order(body.ticket, ip=_get_ip(request))


@router.get("/history", response_model=TradeListResponse)
async def get_trade_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    symbol: str | None = Query(default=None),
    strategy: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.get_trade_history(
        page=page, page_size=page_size, symbol=symbol, strategy=strategy
    )
