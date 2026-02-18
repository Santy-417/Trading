from app.core.logging_config import get_logger

logger = get_logger(__name__)


class KillSwitch:
    """
    Emergency kill switch that immediately stops all trading
    and optionally closes all open positions.
    """

    def __init__(self):
        self._activated = False
        self._reason: str | None = None

    @property
    def is_activated(self) -> bool:
        return self._activated

    @property
    def reason(self) -> str | None:
        return self._reason

    def activate(self, reason: str = "Manual activation") -> None:
        """Activate the kill switch."""
        self._activated = True
        self._reason = reason
        logger.critical("kill_switch_activated: reason=%s", reason)

    def deactivate(self) -> None:
        """Deactivate the kill switch (requires explicit action)."""
        self._activated = False
        self._reason = None
        logger.info("kill_switch_deactivated")

    def check(self) -> tuple[bool, str | None]:
        """
        Check kill switch status.
        Returns (is_trading_allowed, reason_if_blocked).
        """
        if self._activated:
            return False, f"Kill switch active: {self._reason}"
        return True, None
