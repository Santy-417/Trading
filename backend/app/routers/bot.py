from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import trading_limiter
from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.schemas.bot import (
    BotKillRequest,
    BotKillResponse,
    BotStartRequest,
    BotStatusResponse,
)
from app.services.bot_service import BotService

router = APIRouter(prefix="/bot", tags=["Bot"])


def _get_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/start", response_model=BotStatusResponse)
@trading_limiter
async def start_bot(
    request: Request,
    body: BotStartRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = BotService(db)
    return await service.start(body, ip=_get_ip(request))


@router.post("/stop", response_model=BotStatusResponse)
@trading_limiter
async def stop_bot(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = BotService(db)
    return await service.stop(ip=_get_ip(request))


@router.post("/kill", response_model=BotKillResponse)
async def kill_bot(
    request: Request,
    body: BotKillRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    service = BotService(db)
    result = await service.kill(body, ip=_get_ip(request))
    return BotKillResponse(
        message="Kill switch activated",
        positions_closed=result.get("positions_closed", []),
        error=result.get("error"),
    )


@router.get("/status", response_model=BotStatusResponse)
async def bot_status(
    _user: dict = Depends(get_current_user),
):
    from app.execution.execution_engine import execution_engine

    return execution_engine.get_status()
