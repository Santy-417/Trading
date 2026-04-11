from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import trading_limiter
from app.core.security import get_current_user
from app.integrations.supabase.client import get_db
from app.models.bot_config import BotConfig
from app.repositories.audit_repository import AuditRepository
from app.schemas.bot import (
    AccountInfoResponse,
    BotConfigResponse,
    BotConfigUpdateRequest,
    BotKillRequest,
    BotKillResponse,
    BotLogEntry,
    BotStartRequest,
    BotStatusResponse,
    SignalStatusResponse,
    _VALID_LOT_MODES,
    _VALID_STRATEGIES,
    _VALID_SYMBOLS,
    _VALID_TIMEFRAMES,
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


@router.get("/signal-status", response_model=SignalStatusResponse)
async def get_signal_status(
    _user: dict = Depends(get_current_user),
):
    """
    Returns the current internal state of the strategy and execution engine.
    Used by the LastSignalBadge component on the Trading page.
    """
    from app.execution.execution_engine import execution_engine

    status = execution_engine.get_status()
    bot_state_raw = status["state"]  # e.g. "running", "stopped", "error"

    is_running = bot_state_raw == "running"
    bot_display_state = (
        "ACTIVO" if bot_state_raw == "running"
        else "ERROR" if bot_state_raw == "error"
        else "DETENIDO"
    )

    # Pull internal strategy state (only available for BiasStrategy)
    block_reason: str | None = None
    block_detail: str | None = None
    daily_bias: str | None = None
    sweep_detected: bool = False

    strategy = getattr(execution_engine, "_strategy", None)
    if strategy is not None:
        block_reason = getattr(strategy, "_last_block_reason", None)
        block_detail = getattr(strategy, "_last_block_detail", None)
        daily_bias = getattr(strategy, "_daily_bias", None)
        sweep_detected = bool(getattr(strategy, "_sweep_detected", False))

    last_trade = getattr(execution_engine, "_last_executed_trade", None)

    # Session calculation (UTC-based)
    now_utc = datetime.now(timezone.utc)
    hour_utc = now_utc.hour
    minute_utc = now_utc.minute
    minutes_since_midnight = hour_utc * 60 + minute_utc

    # Session windows in UTC minutes
    LONDON_START = 7 * 60        # 07:00 UTC
    LONDON_END   = 16 * 60       # 16:00 UTC
    NY_START     = 13 * 60       # 13:00 UTC
    NY_END       = 19 * 60       # 19:00 UTC

    in_london = LONDON_START <= minutes_since_midnight < LONDON_END
    in_ny     = NY_START     <= minutes_since_midnight < NY_END

    if in_london and in_ny:
        current_session = "overlap"
    elif in_london:
        current_session = "london"
    elif in_ny:
        current_session = "ny"
    else:
        current_session = "closed"

    # Minutes until NY opens (None if already open or past)
    ny_open_minutes: int | None = None
    if not in_ny:
        if minutes_since_midnight < NY_START:
            ny_open_minutes = NY_START - minutes_since_midnight
        else:
            # After NY close — calculate time until next day's NY open
            ny_open_minutes = (24 * 60 - minutes_since_midnight) + NY_START

    return SignalStatusResponse(
        bot_state=bot_display_state,
        is_running=is_running,
        block_reason=block_reason,
        block_detail=block_detail,
        daily_bias=daily_bias,
        sweep_detected=sweep_detected,
        last_trade=last_trade,
        current_session=current_session,
        ny_open_minutes=ny_open_minutes,
    )


# ── Bot Config ─────────────────────────────────────────────────────────────────

async def _get_active_config(db: AsyncSession) -> BotConfig:
    """
    Return the active bot_config row.

    Lookup order:
      1. WHERE is_active = True  ORDER BY created_at DESC LIMIT 1
      2. Most recent row (any)   ORDER BY created_at DESC LIMIT 1
      3. HTTPException 404
    """
    result = await db.execute(
        select(BotConfig)
        .where(BotConfig.is_active.is_(True))
        .order_by(BotConfig.created_at.desc())
        .limit(1)
    )
    config = result.scalar_one_or_none()

    if config is None:
        result = await db.execute(
            select(BotConfig).order_by(BotConfig.created_at.desc()).limit(1)
        )
        config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(status_code=404, detail="No bot config found")

    return config


@router.get("/config", response_model=BotConfigResponse)
async def get_bot_config(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Return the active bot configuration."""
    config = await _get_active_config(db)
    response = BotConfigResponse.model_validate(config)
    response.requires_restart = False  # Only PATCH can set this
    return response


@router.patch("/config", response_model=BotConfigResponse)
async def update_bot_config(
    request: Request,
    body: BotConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Partially update the active bot configuration.

    Only the fields present in the request body are updated.
    strategy_params are merged into the existing JSONB dict.
    Returns requires_restart=True when strategy, symbols, or timeframe change.
    """
    config = await _get_active_config(db)

    # Track which high-impact fields change to signal the frontend
    _RESTART_FIELDS = {"strategy", "symbols", "timeframe"}
    requires_restart = False

    # ── Validate enum fields ──────────────────────────────────────────────────
    if body.strategy is not None and body.strategy not in _VALID_STRATEGIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid strategy '{body.strategy}'. Valid: {sorted(_VALID_STRATEGIES)}",
        )
    if body.timeframe is not None and body.timeframe not in _VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid timeframe '{body.timeframe}'. Valid: {sorted(_VALID_TIMEFRAMES)}",
        )
    if body.lot_mode is not None and body.lot_mode not in _VALID_LOT_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid lot_mode '{body.lot_mode}'. Valid: {sorted(_VALID_LOT_MODES)}",
        )
    if body.symbols is not None:
        invalid = set(body.symbols) - _VALID_SYMBOLS
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid symbols: {sorted(invalid)}. Valid: {sorted(_VALID_SYMBOLS)}",
            )

    # ── Apply scalar fields ───────────────────────────────────────────────────
    scalar_fields = (
        "strategy", "symbols", "timeframe",
        "risk_per_trade", "lot_mode", "fixed_lot", "max_trades_per_hour",
    )
    for field in scalar_fields:
        value = getattr(body, field)
        if value is not None:
            if field in _RESTART_FIELDS and getattr(config, field) != value:
                requires_restart = True
            setattr(config, field, value)

    # ── Merge strategy_params (JSONB) ─────────────────────────────────────────
    if body.strategy_params is not None:
        current_params: dict = dict(config.strategy_params or {})
        update_dict = body.strategy_params.model_dump(exclude_none=True)
        current_params.update(update_dict)
        config.strategy_params = current_params

    await db.flush()

    # Audit log
    audit_repo = AuditRepository(db)
    changed = body.model_dump(exclude_none=True)
    await audit_repo.create(
        action="bot_config_update",
        entity_type="bot_config",
        details={"changed_fields": list(changed.keys()), "requires_restart": requires_restart},
        ip_address=request.client.host if request.client else None,
    )

    response = BotConfigResponse.model_validate(config)
    response.requires_restart = requires_restart
    return response
