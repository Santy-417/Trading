from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """
    Circuit breaker that stops trading when risk thresholds are breached.

    Monitors:
    - Maximum drawdown percentage
    - Daily loss cap
    - Overtrading (max trades per hour)
    """

    def __init__(self):
        settings = get_settings()
        self.max_drawdown_percent = settings.max_drawdown_percent
        self.max_daily_loss_percent = settings.max_daily_loss_percent
        self.max_trades_per_hour = settings.max_trades_per_hour
        self._tripped = False
        self._trip_reason: str | None = None
        self._trade_timestamps: list[datetime] = []

    @property
    def is_tripped(self) -> bool:
        return self._tripped

    @property
    def trip_reason(self) -> str | None:
        return self._trip_reason

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._tripped = False
        self._trip_reason = None
        logger.info("circuit_breaker_reset")

    def check_drawdown(self, balance: float, equity: float) -> bool:
        """
        Check if max drawdown threshold is breached.
        Returns True if trading is allowed, False if breached.
        """
        if balance <= 0:
            return False

        drawdown_percent = ((balance - equity) / balance) * 100

        if drawdown_percent >= self.max_drawdown_percent:
            self._tripped = True
            self._trip_reason = (
                f"Max drawdown breached: {drawdown_percent:.2f}% "
                f"(limit: {self.max_drawdown_percent}%)"
            )
            logger.critical(
                "circuit_breaker_drawdown: drawdown_percent=%s, threshold=%s",
                drawdown_percent, self.max_drawdown_percent,
            )
            return False
        return True

    def check_daily_loss(
        self, starting_balance: float, current_balance: float
    ) -> bool:
        """
        Check if daily loss cap is breached.
        Returns True if trading is allowed, False if breached.
        """
        if starting_balance <= 0:
            return False

        daily_loss_percent = (
            (starting_balance - current_balance) / starting_balance
        ) * 100

        if daily_loss_percent >= self.max_daily_loss_percent:
            self._tripped = True
            self._trip_reason = (
                f"Daily loss cap breached: {daily_loss_percent:.2f}% "
                f"(limit: {self.max_daily_loss_percent}%)"
            )
            logger.critical(
                "circuit_breaker_daily_loss: daily_loss_percent=%s, threshold=%s",
                daily_loss_percent, self.max_daily_loss_percent,
            )
            return False
        return True

    def check_overtrading(self) -> bool:
        """
        Check if max trades per hour is exceeded.
        Returns True if trading is allowed, False if limit reached.
        """
        now = datetime.now(timezone.utc)
        # Keep only trades from the last hour
        self._trade_timestamps = [
            ts for ts in self._trade_timestamps
            if (now - ts).total_seconds() < 3600
        ]

        if len(self._trade_timestamps) >= self.max_trades_per_hour:
            self._trip_reason = (
                f"Overtrading: {len(self._trade_timestamps)} trades in last hour "
                f"(limit: {self.max_trades_per_hour})"
            )
            logger.warning(
                "circuit_breaker_overtrading: trades_in_hour=%s, threshold=%s",
                len(self._trade_timestamps), self.max_trades_per_hour,
            )
            return False
        return True

    def record_trade(self) -> None:
        """Record a trade timestamp for overtrading detection."""
        self._trade_timestamps.append(datetime.now(timezone.utc))

    def check_all(
        self,
        balance: float,
        equity: float,
        starting_balance: float,
    ) -> tuple[bool, str | None]:
        """
        Run all circuit breaker checks.
        Returns (is_allowed, reason_if_blocked).
        """
        if self._tripped:
            return False, self._trip_reason

        if not self.check_drawdown(balance, equity):
            return False, self._trip_reason

        if not self.check_daily_loss(starting_balance, balance):
            return False, self._trip_reason

        if not self.check_overtrading():
            return False, self._trip_reason

        return True, None
