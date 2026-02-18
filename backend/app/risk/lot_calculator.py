from decimal import Decimal

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class LotCalculator:
    """Calculate position lot size based on risk parameters."""

    @staticmethod
    def fixed_lot(lot_size: float) -> float:
        """Return the fixed lot size directly."""
        return lot_size

    @staticmethod
    def percent_risk(
        balance: float,
        risk_percent: float,
        sl_pips: float,
        pip_value: float,
        volume_min: float = 0.01,
        volume_max: float = 100.0,
        volume_step: float = 0.01,
    ) -> float:
        """
        Calculate lot size based on percentage risk per trade.

        Args:
            balance: Account balance
            risk_percent: Risk percentage (e.g., 1.0 for 1%)
            sl_pips: Stop loss distance in pips
            pip_value: Value per pip per lot
            volume_min: Minimum allowed lot size
            volume_max: Maximum allowed lot size
            volume_step: Lot size step
        """
        if sl_pips <= 0:
            logger.warning("lot_calc_invalid_sl: sl_pips=%s", sl_pips)
            return volume_min

        risk_amount = balance * (risk_percent / 100.0)
        raw_lot = risk_amount / (sl_pips * pip_value)

        # Round to volume_step
        lot = max(volume_min, min(volume_max, raw_lot))
        lot = round(lot / volume_step) * volume_step
        lot = round(lot, 4)

        logger.info(
            "lot_calculated: balance=%s, risk_percent=%s, sl_pips=%s, pip_value=%s, calculated_lot=%s",
            balance, risk_percent, sl_pips, pip_value, lot,
        )
        return lot

    @staticmethod
    def dynamic_lot(
        balance: float,
        equity: float,
        risk_percent: float,
        sl_pips: float,
        pip_value: float,
        volume_min: float = 0.01,
        volume_max: float = 100.0,
        volume_step: float = 0.01,
    ) -> float:
        """
        Dynamic lot calculation based on equity (not just balance).
        More conservative when in drawdown.
        """
        # Use the minimum of balance and equity for extra safety
        effective_capital = min(balance, equity)
        return LotCalculator.percent_risk(
            balance=effective_capital,
            risk_percent=risk_percent,
            sl_pips=sl_pips,
            pip_value=pip_value,
            volume_min=volume_min,
            volume_max=volume_max,
            volume_step=volume_step,
        )
