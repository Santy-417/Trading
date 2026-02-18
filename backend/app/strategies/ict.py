import pandas as pd

from app.core.logging_config import get_logger
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)


class ICTStrategy(BaseStrategy):
    """
    ICT (Inner Circle Trader) strategy.

    Concepts used:
    - Order Blocks (OB): Last opposing candle before a strong move
    - Fair Value Gaps (FVG): Imbalance/gap between 3 candles
    - Liquidity sweeps: Price taking out previous highs/lows

    Entry: Price returns to an Order Block or FVG after a liquidity sweep.
    SL: Beyond the Order Block.
    TP: Opposite liquidity pool.
    """

    name = "ict"
    supported_timeframes = ["M5", "M15", "M30", "H1", "H4"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    def __init__(
        self,
        ob_lookback: int = 30,
        fvg_lookback: int = 20,
        liquidity_lookback: int = 50,
        rr_ratio: float = 2.0,
    ):
        self.ob_lookback = ob_lookback
        self.fvg_lookback = fvg_lookback
        self.liquidity_lookback = liquidity_lookback
        self.rr_ratio = rr_ratio

    def _find_order_blocks(
        self, df: pd.DataFrame
    ) -> list[dict]:
        """
        Identify Order Blocks: the last bearish candle before a bullish move
        (bullish OB) or last bullish candle before a bearish move (bearish OB).
        """
        order_blocks = []
        recent = df.tail(self.ob_lookback)

        for i in range(2, len(recent) - 1):
            curr = recent.iloc[i]
            prev = recent.iloc[i - 1]
            next_c = recent.iloc[i + 1] if i + 1 < len(recent) else None

            if next_c is None:
                continue

            # Bullish OB: bearish candle followed by strong bullish move
            if (
                prev["close"] < prev["open"]  # Previous was bearish
                and curr["close"] > curr["open"]  # Current is bullish
                and (curr["close"] - curr["open"]) > 1.5 * abs(prev["close"] - prev["open"])
            ):
                order_blocks.append({
                    "type": "bullish",
                    "high": prev["high"],
                    "low": prev["low"],
                    "index": i - 1,
                })

            # Bearish OB: bullish candle followed by strong bearish move
            if (
                prev["close"] > prev["open"]  # Previous was bullish
                and curr["close"] < curr["open"]  # Current is bearish
                and (curr["open"] - curr["close"]) > 1.5 * abs(prev["close"] - prev["open"])
            ):
                order_blocks.append({
                    "type": "bearish",
                    "high": prev["high"],
                    "low": prev["low"],
                    "index": i - 1,
                })

        return order_blocks

    def _find_fair_value_gaps(
        self, df: pd.DataFrame
    ) -> list[dict]:
        """
        Identify Fair Value Gaps (FVG): gaps between candle 1's high/low
        and candle 3's low/high.
        """
        fvgs = []
        recent = df.tail(self.fvg_lookback)

        for i in range(2, len(recent)):
            c1 = recent.iloc[i - 2]
            c3 = recent.iloc[i]

            # Bullish FVG: gap between c1 high and c3 low
            if c3["low"] > c1["high"]:
                fvgs.append({
                    "type": "bullish",
                    "top": c3["low"],
                    "bottom": c1["high"],
                    "index": i,
                })

            # Bearish FVG: gap between c3 high and c1 low
            if c3["high"] < c1["low"]:
                fvgs.append({
                    "type": "bearish",
                    "top": c1["low"],
                    "bottom": c3["high"],
                    "index": i,
                })

        return fvgs

    def _detect_liquidity_sweep(
        self, df: pd.DataFrame
    ) -> dict | None:
        """
        Detect if recent price action swept previous liquidity
        (took out a previous high/low then reversed).
        """
        recent = df.tail(self.liquidity_lookback)
        last_candle = recent.iloc[-1]
        prev_candle = recent.iloc[-2]

        # Find previous swing high and low (excluding last 5 candles)
        lookback = recent.iloc[:-5]
        if len(lookback) < 5:
            return None

        prev_high = lookback["high"].max()
        prev_low = lookback["low"].min()

        # Bullish sweep: price went below previous low then closed above
        if (
            last_candle["low"] < prev_low
            and last_candle["close"] > prev_low
            and last_candle["close"] > last_candle["open"]
        ):
            return {"type": "bullish_sweep", "level": prev_low}

        # Bearish sweep: price went above previous high then closed below
        if (
            last_candle["high"] > prev_high
            and last_candle["close"] < prev_high
            and last_candle["close"] < last_candle["open"]
        ):
            return {"type": "bearish_sweep", "level": prev_high}

        return None

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> TradeSignal | None:
        if len(df) < self.liquidity_lookback + 10:
            return None

        current_price = df["close"].iloc[-1]

        # Step 1: Check for liquidity sweep
        sweep = self._detect_liquidity_sweep(df)
        if sweep is None:
            return None

        # Step 2: Find Order Blocks
        order_blocks = self._find_order_blocks(df)

        # Step 3: Find FVGs
        fvgs = self._find_fair_value_gaps(df)

        signal_direction = None
        entry_zone = None

        if sweep["type"] == "bullish_sweep":
            # Look for bullish OB or FVG near current price
            for ob in reversed(order_blocks):
                if ob["type"] == "bullish" and ob["low"] <= current_price <= ob["high"]:
                    signal_direction = SignalDirection.BUY
                    entry_zone = ob
                    break

            if signal_direction is None:
                for fvg in reversed(fvgs):
                    if fvg["type"] == "bullish" and fvg["bottom"] <= current_price <= fvg["top"]:
                        signal_direction = SignalDirection.BUY
                        entry_zone = fvg
                        break

        elif sweep["type"] == "bearish_sweep":
            for ob in reversed(order_blocks):
                if ob["type"] == "bearish" and ob["low"] <= current_price <= ob["high"]:
                    signal_direction = SignalDirection.SELL
                    entry_zone = ob
                    break

            if signal_direction is None:
                for fvg in reversed(fvgs):
                    if fvg["type"] == "bearish" and fvg["bottom"] <= current_price <= fvg["top"]:
                        signal_direction = SignalDirection.SELL
                        entry_zone = fvg
                        break

        if signal_direction is None:
            return None

        sl, tp = self.calculate_sl_tp(df, signal_direction, current_price)

        signal = TradeSignal(
            direction=signal_direction,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.65,
            strategy_name=self.name,
            metadata={
                "sweep_type": sweep["type"],
                "sweep_level": sweep["level"],
                "entry_zone": entry_zone,
            },
        )

        if self.validate_signal(signal):
            logger.info(
                "ict_signal: symbol=%s, direction=%s, sweep=%s, entry=%s",
                symbol, signal_direction.value, sweep["type"], current_price,
            )
            return signal
        return None

    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
    ) -> tuple[float, float]:
        recent = df.tail(self.liquidity_lookback)
        atr = (recent["high"] - recent["low"]).mean()

        if direction == SignalDirection.BUY:
            sl = entry_price - (atr * 1.5)
            tp = entry_price + (atr * 1.5 * self.rr_ratio)
        else:
            sl = entry_price + (atr * 1.5)
            tp = entry_price - (atr * 1.5 * self.rr_ratio)

        return round(sl, 8), round(tp, 8)
