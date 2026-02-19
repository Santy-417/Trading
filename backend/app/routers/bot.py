from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import trading_limiter
from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.repositories.audit_repository import AuditRepository
from app.schemas.bot import (
    AccountInfoResponse,
    BotKillRequest,
    BotKillResponse,
    BotLogEntry,
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


@router.post("/reset-kill")
async def reset_kill_switch(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Deactivate the kill switch and reset circuit breaker."""
    from app.risk.risk_manager import risk_manager

    was_active = risk_manager.kill_switch.is_activated
    risk_manager.deactivate_kill_switch()
    risk_manager.reset_circuit_breaker()

    audit_repo = AuditRepository(db)
    await audit_repo.create(
        action="kill_switch_reset",
        entity_type="bot",
        details={"was_active": was_active},
        ip_address=_get_ip(request),
    )

    return {"message": "Kill switch deactivated", "was_active": was_active}


@router.get("/status", response_model=BotStatusResponse)
async def bot_status(
    _user: dict = Depends(get_current_user),
):
    from app.execution.execution_engine import execution_engine

    return execution_engine.get_status()


@router.get("/account", response_model=AccountInfoResponse)
async def get_account_info(
    _user: dict = Depends(get_current_user),
):
    from app.integrations.metatrader.mt5_client import mt5_client

    await mt5_client.initialize()
    info = await mt5_client.get_account_info()
    return AccountInfoResponse(
        balance=info.get("balance", 0),
        equity=info.get("equity", 0),
        profit=info.get("profit", 0),
        margin=info.get("margin", 0),
        free_margin=info.get("free_margin", 0),
        leverage=info.get("leverage", 0),
        currency=info.get("currency", "USD"),
        name=info.get("name", ""),
        server=info.get("server", ""),
    )


@router.get("/logs", response_model=list[BotLogEntry])
async def get_bot_logs(
    limit: int = Query(default=50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
):
    from app.execution.execution_engine import execution_engine

    return execution_engine.get_logs(limit=limit)
