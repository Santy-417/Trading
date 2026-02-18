from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.execution.execution_engine import execution_engine
from app.repositories.audit_repository import AuditRepository
from app.schemas.bot import BotKillRequest, BotStartRequest

logger = get_logger(__name__)


class BotService:
    def __init__(self, session: AsyncSession):
        self.audit_repo = AuditRepository(session)

    async def start(self, request: BotStartRequest, ip: str | None = None) -> dict:
        await execution_engine.start(
            strategy_name=request.strategy,
            symbols=request.symbols,
            timeframe=request.timeframe,
            strategy_params=request.strategy_params,
            loop_interval=request.loop_interval,
        )
        await self.audit_repo.create(
            action="bot_start",
            entity_type="bot",
            details={
                "strategy": request.strategy,
                "symbols": request.symbols,
                "timeframe": request.timeframe,
            },
            ip_address=ip,
        )
        return execution_engine.get_status()

    async def stop(self, ip: str | None = None) -> dict:
        await execution_engine.stop()
        await self.audit_repo.create(
            action="bot_stop",
            entity_type="bot",
            ip_address=ip,
        )
        return execution_engine.get_status()

    async def kill(self, request: BotKillRequest, ip: str | None = None) -> dict:
        result = await execution_engine.kill(close_positions=request.close_positions)
        await self.audit_repo.create(
            action="kill_switch",
            entity_type="bot",
            details={
                "reason": request.reason,
                "close_positions": request.close_positions,
                "positions_closed": result.get("positions_closed", []),
            },
            ip_address=ip,
        )
        return result

    def get_status(self) -> dict:
        return execution_engine.get_status()
