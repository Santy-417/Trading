from dataclasses import dataclass

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.risk.circuit_breaker import CircuitBreaker
from app.risk.kill_switch import KillSwitch
from app.risk.lot_calculator import LotCalculator

logger = get_logger(__name__)


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str | None = None
    calculated_lot: float | None = None


class RiskManager:
    """
    Central risk management engine.

    Coordinates:
    - Kill switch
    - Circuit breaker (drawdown, daily loss, overtrading)
    - Lot size calculation
    """

    def __init__(self):
        self.kill_switch = KillSwitch()
        self.circuit_breaker = CircuitBreaker()
        self.lot_calculator = LotCalculator()
        self._starting_balance: float | None = None

    def set_starting_balance(self, balance: float) -> None:
        """Set the daily starting balance for loss tracking."""
        self._starting_balance = balance
        logger.info("risk_starting_balance_set: balance=%s", balance)

    def check_trade_allowed(
        self,
        balance: float,
        equity: float,
    ) -> RiskCheckResult:
        """
        Run all risk checks before allowing a trade.
        Returns whether trading is allowed and the reason if blocked.
        """
        # 1. Kill switch check
        allowed, reason = self.kill_switch.check()
        if not allowed:
            return RiskCheckResult(allowed=False, reason=reason)

        # 2. Circuit breaker checks
        starting = self._starting_balance or balance
        allowed, reason = self.circuit_breaker.check_all(
            balance=balance,
            equity=equity,
            starting_balance=starting,
        )
        if not allowed:
            return RiskCheckResult(allowed=False, reason=reason)

        return RiskCheckResult(allowed=True)

    def calculate_lot_size(
        self,
        balance: float,
        equity: float,
        sl_pips: float,
        pip_value: float,
        lot_mode: str = "percent_risk",
        fixed_lot: float = 0.01,
        risk_percent: float | None = None,
        volume_min: float = 0.01,
        volume_max: float = 100.0,
        volume_step: float = 0.01,
    ) -> float:
        """Calculate the appropriate lot size based on the selected mode."""
        settings = get_settings()
        risk_pct = risk_percent or settings.default_risk_per_trade

        if lot_mode == "fixed":
            return self.lot_calculator.fixed_lot(fixed_lot)
        elif lot_mode == "dynamic":
            return self.lot_calculator.dynamic_lot(
                balance=balance,
                equity=equity,
                risk_percent=risk_pct,
                sl_pips=sl_pips,
                pip_value=pip_value,
                volume_min=volume_min,
                volume_max=volume_max,
                volume_step=volume_step,
            )
        else:  # percent_risk (default)
            return self.lot_calculator.percent_risk(
                balance=balance,
                risk_percent=risk_pct,
                sl_pips=sl_pips,
                pip_value=pip_value,
                volume_min=volume_min,
                volume_max=volume_max,
                volume_step=volume_step,
            )

    def record_trade(self) -> None:
        """Record that a trade was executed (for overtrading detection)."""
        self.circuit_breaker.record_trade()

    def activate_kill_switch(self, reason: str = "Manual") -> None:
        """Activate emergency kill switch."""
        self.kill_switch.activate(reason)

    def deactivate_kill_switch(self) -> None:
        """Deactivate kill switch."""
        self.kill_switch.deactivate()

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after manual review."""
        self.circuit_breaker.reset()

    def get_status(self) -> dict:
        """Get current risk engine status."""
        return {
            "kill_switch_active": self.kill_switch.is_activated,
            "kill_switch_reason": self.kill_switch.reason,
            "circuit_breaker_tripped": self.circuit_breaker.is_tripped,
            "circuit_breaker_reason": self.circuit_breaker.trip_reason,
            "starting_balance": self._starting_balance,
            "max_drawdown_percent": self.circuit_breaker.max_drawdown_percent,
            "max_daily_loss_percent": self.circuit_breaker.max_daily_loss_percent,
            "max_trades_per_hour": self.circuit_breaker.max_trades_per_hour,
        }


# Singleton instance
risk_manager = RiskManager()
