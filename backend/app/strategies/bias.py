"""
BiasStrategy — Institutional-grade SMC strategy with ML filtering.

Based on Smart Money Concepts:
1. Daily Bias from previous D1 candle
2. London session manipulation (PDH/PDL sweep)
3. New York session entry after ChoCh on M5
4. Shannon entropy filter to avoid erratic markets
5. FVG (Fair Value Gap) as TP magnet
6. Hybrid risk adjustment (ML confidence + entropy Z-Score)

Supported symbols: EURUSD, XAUUSD
Sessions use America/Bogota (UTC-5) timezone.
"""

from math import log2

import numpy as np
import pandas as pd
import pytz

from app.core.logging_config import get_logger
from app.ml.prediction import Predictor
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)

# Pip definitions per symbol
PIP_SIZE = {
    "EURUSD": 0.0001,
    "XAUUSD": 0.01,
}

BOGOTA_TZ = pytz.timezone("America/Bogota")


class BiasStrategy(BaseStrategy):
    """
    Bias strategy: Daily bias + London manipulation + NY ChoCh entry.

    Flow:
    1. Determine daily bias (previous D1 close vs open)
    2. Detect London manipulation (PDH/PDL sweep during 07:00-11:00 Bogota)
    3. Check Shannon entropy — skip if market is erratic
    4. Detect Change of Character (ChoCh) on M5 during NY session (08:30-11:30 Bogota)
    5. ML filter (optional): skip if probability < min_ml_confidence
    6. Calculate SL/TP with FVG as primary TP target
    7. Compute hybrid risk percent based on ML confidence + entropy Z-Score
    """

    name = "bias"
    supported_timeframes = ["M5", "M15", "M30", "H1", "H4"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    # Used by ExecutionEngine for time-based close
    close_time_utc = (21, 30)  # 16:30 Bogota = 21:30 UTC
    choch_timeframe = "M5"  # ExecutionEngine loads M5 data for live trading

    def __init__(
        self,
        model_id: str | None = None,
        min_ml_confidence: float = 0.65,
        sl_pips_base: float = 10.0,
        min_rr: float = 1.3,  # Optimized post-SELL surgery (max Net Profit on 10k bars H1)
        london_start_hour: int = 2,      # 02:00 Bogotá (07:00 UTC London open)
        london_end_hour: int = 11,       # 11:30 Bogotá (covers full session + overlap)
        ny_start_hour: int = 8,
        ny_start_minute: int = 0,        # 08:00 Bogotá (13:00 UTC)
        ny_end_hour: int = 14,           # 14:00 Bogotá (19:00 UTC, full NY session)
        ny_end_minute: int = 0,
        choch_lookback: int = 60,        # Increased from 20 for more swing points
        entropy_threshold: float = 3.1,  # V1 optimization: upper bound of observed range (2.2-3.1)
        use_entropy_zscore: bool = True, # Enable Z-Score filter as alternative
        entropy_window: int = 50,
        fvg_lookback: int = 30,
        sweep_tolerance_pips: float = 3.0,  # V1.1: Allow near-miss sweeps (real market adjustment)
    ):
        self.min_ml_confidence = min_ml_confidence
        self.sl_pips_base = sl_pips_base
        self.min_rr = min_rr
        self.london_start_hour = london_start_hour
        self.london_end_hour = london_end_hour
        self.ny_start_hour = ny_start_hour
        self.ny_start_minute = ny_start_minute
        self.ny_end_hour = ny_end_hour
        self.ny_end_minute = ny_end_minute
        self.choch_lookback = choch_lookback
        self.entropy_threshold = entropy_threshold
        self.use_entropy_zscore = use_entropy_zscore
        self.entropy_window = entropy_window
        self.fvg_lookback = fvg_lookback
        self.sweep_tolerance_pips = sweep_tolerance_pips

        self._predictor: Predictor | None = None
        if model_id:
            self._predictor = Predictor(model_id=model_id)

        # Set by ExecutionEngine for live multi-timeframe data
        self._df_lower_tf: pd.DataFrame | None = None

        # State persistence: Manipulation detection across London → NY sessions
        self._last_manipulation: dict | None = None
        # Structure: {
        #   "type": "bullish_sweep_pdl" | "bearish_sweep_pdh",
        #   "level": float,
        #   "timestamp": pd.Timestamp,  # Bogotá timezone
        # }

        self._last_manipulation_day: pd.Timestamp | None = None
        # Date when manipulation was detected (resets each day)

        self._current_symbol: str | None = None
        # Symbol being traded (for ChoCh hybrid tolerance calculation)

        self._entropy_cache: dict[int, float | None] = {}
        # Cache entropy z-scores by DataFrame length to avoid recalculation during backtesting

        self._m5_resample_cache: dict[int, pd.DataFrame] = {}
        # Cache M5 resampled DataFrames by H1 DataFrame length for backtesting performance

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> TradeSignal | None:
        # Store symbol for ChoCh hybrid tolerance
        self._current_symbol = symbol

        if symbol not in self.supported_symbols:
            logger.info("bias: symbol %s not supported", symbol)
            return None
        if len(df) < 100:
            logger.info("bias: insufficient data (%d bars)", len(df))
            return None

        pip = PIP_SIZE.get(symbol, 0.0001)

        # State management: Reset manipulation state on new day
        current_time = self._get_bar_time_bogota(df)
        if current_time is None:
            logger.info("bias: cannot determine current time")
            return None

        current_day = current_time.normalize()  # Strip time, keep date only

        # Reset manipulation if day changed
        if self._last_manipulation_day is not None:
            if current_day > self._last_manipulation_day:
                logger.info(
                    "bias_state: New day detected, resetting manipulation (was %s)",
                    self._last_manipulation_day.strftime("%Y-%m-%d"),
                )
                self._last_manipulation = None
                self._last_manipulation_day = None

        # 1. Daily bias
        bias = self._get_daily_bias(df)
        if bias is None:
            logger.info("bias: no daily bias detected")
            return None
        logger.info("bias: daily_bias=%s", bias)

        # 2. Previous day levels
        pdh, pdl = self._get_previous_day_levels(df)
        if pdh is None or pdl is None:
            logger.info("bias: PDH/PDL not found")
            return None
        logger.info("bias: PDH=%.5f, PDL=%.5f", pdh, pdl)

        # 3. Check session timing — need London manipulation first
        current_time = self._get_bar_time_bogota(df)
        if current_time is None:
            logger.info("bias: cannot determine current time")
            return None

        # 4. Detect London manipulation
        # V1: For NEUTRAL bias (Doji), search sweeps in BOTH directions
        if bias == "NEUTRAL":
            logger.info("bias_neutral: NEUTRAL day detected, searching sweeps in both PDH and PDL")

            # Try both directions
            manipulation_bullish = self._detect_london_manipulation(df, pdh, pdl, "BULLISH", pip)
            manipulation_bearish = self._detect_london_manipulation(df, pdh, pdl, "BEARISH", pip)

            # Use whichever sweep was detected (prioritize most recent via timestamp if both)
            if manipulation_bullish is not None and manipulation_bearish is not None:
                # Both detected: use most recent
                if manipulation_bullish["timestamp"] > manipulation_bearish["timestamp"]:
                    bias = "BULLISH"
                    manipulation = manipulation_bullish
                    logger.info("bias_neutral: Both sweeps detected, using BULLISH (more recent)")
                else:
                    bias = "BEARISH"
                    manipulation = manipulation_bearish
                    logger.info("bias_neutral: Both sweeps detected, using BEARISH (more recent)")
            elif manipulation_bullish is not None:
                bias = "BULLISH"
                manipulation = manipulation_bullish
                logger.info("bias_neutral: PDL sweep detected, switching to BULLISH")
            elif manipulation_bearish is not None:
                bias = "BEARISH"
                manipulation = manipulation_bearish
                logger.info("bias_neutral: PDH sweep detected, switching to BEARISH")
            else:
                logger.info("bias_neutral: no sweeps detected in either direction")
                return None
        else:
            # Normal directional bias
            manipulation = self._detect_london_manipulation(df, pdh, pdl, bias, pip)
        if manipulation is None:
            logger.info("bias: no London manipulation detected")
            # Audit log for filtered signal
            logger.info(
                "[AUDIT] Bias=%s | Manipulation=NONE | Session=%s | PDH=%.5f | PDL=%.5f | Status=FILTERED",
                bias,
                "LONDON" if self._is_london_session(current_time) else "NY" if self._is_ny_session(current_time) else "OTHER",
                pdh,
                pdl,
            )
            return None
        logger.info("bias: manipulation=%s at %.5f", manipulation["type"], manipulation["level"])
        logger.debug("MANIPULATION DETECTED: %s at %.5f", manipulation['type'], manipulation['level'])

        # 5. Check if we're in NY session for entry
        # OPTIMIZATION: If manipulation was stored from earlier today (London session),
        # allow entry during extended hours (up to 6pm Bogota to capture NY close momentum)
        manipulation_is_stored = (
            self._last_manipulation is not None
            and current_time.normalize() == self._last_manipulation_day
        )

        if manipulation_is_stored:
            # Manipulation from today exists - allow entry until 18:00 Bogota (extended window)
            if current_time.hour >= 18:
                logger.info("bias: manipulation expired (after 18:00 Bogota)")
                logger.debug("BLOCKED: Manipulation expired (time: %d:00)", current_time.hour)
                return None
            logger.info("bias: using stored manipulation from %s (extended window active)",
                       manipulation["timestamp"].strftime("%H:%M"))
            logger.debug("PASSED: Using stored manipulation (extended window until 18:00)")
        else:
            # Fresh manipulation check - must be in NY session for immediate entry
            if not self._is_ny_session(current_time):
                logger.info("bias: not in NY session (current time: %s)", current_time)
                logger.debug("BLOCKED: Not in NY session (current time: %s)", current_time)
                return None
            logger.info("bias: in NY session")
            logger.debug("PASSED: NY session check (time: %s)", current_time)

        # 6. Shannon entropy filter (dual approach: Z-Score or absolute threshold)
        entropy = self._calculate_entropy(df, self.entropy_window)

        # Only calculate z-score if enabled (expensive operation)
        if self.use_entropy_zscore:
            entropy_zscore = self._calculate_entropy_zscore(df, entropy)
        else:
            entropy_zscore = None

        # Filter decision: use Z-Score if available and enabled, else absolute threshold
        if self.use_entropy_zscore and entropy_zscore is not None:
            if entropy_zscore > 1.5:  # 1.5 std devs above mean = statistically high
                logger.info(
                    "bias_entropy_zscore_filter: z_score=%.3f > 1.5, skipping (entropy=%.3f)",
                    entropy_zscore,
                    entropy,
                )
                return None
            logger.info(
                "bias_entropy: z_score=%.3f passed (entropy=%.3f)", entropy_zscore, entropy
            )
        else:
            # Fallback to absolute threshold
            if entropy > self.entropy_threshold:
                logger.info(
                    "bias_entropy_filter: entropy=%.3f > threshold=%.1f, skipping",
                    entropy,
                    self.entropy_threshold,
                )
                logger.debug("BLOCKED: Entropy %.3f > threshold %.1f", entropy, self.entropy_threshold)
                return None
            logger.info("bias_entropy: %.3f passed threshold (%.1f)", entropy, self.entropy_threshold)
            logger.debug("PASSED: Entropy check (%.3f <= %.1f)", entropy, self.entropy_threshold)

        # 7. Multi-timeframe ChoCh detection with fractal break fallback
        direction = SignalDirection.BUY if bias == "BULLISH" else SignalDirection.SELL

        # Performance optimization: only resample last N H1 bars needed for ChoCh (60 M5 bars = 5 H1 bars)
        # Using 10 H1 bars for safety margin
        if self._df_lower_tf is not None:
            df_m5 = self._df_lower_tf
        else:
            lookback_bars = 10  # Last 10 H1 bars = 120 M5 bars (2x the ChoCh lookback)
            df_recent = df.tail(lookback_bars) if len(df) > lookback_bars else df
            df_m5 = self._resample_to_m5(df_recent)

        choch_detected = self._detect_choch(df_m5, direction)

        if not choch_detected:
            # V1: Try fractal break as emergency fallback
            fractal_break = self._detect_fractal_break(df, direction)

            if not fractal_break:
                logger.info("bias: no ChoCh and no fractal break for %s", direction.value)
                logger.debug("BLOCKED: No ChoCh AND no fractal break for %s", direction.value)
                return None

            logger.info("bias: No ChoCh but FRACTAL BREAK detected for %s (fallback)", direction.value)
            logger.debug("PASSED: Fractal break detected for %s (ChoCh failed)", direction.value)
        else:
            logger.info("bias: ChoCh detected for %s", direction.value)

        # Audit log for successful signal generation path
        logger.info(
            "[AUDIT] Bias=%s | Manipulation=%s (%.5f) at %s | Session=NY | "
            "Entropy=%.3f (z=%.2f) | ChoCh=DETECTED | PDH=%.5f | PDL=%.5f",
            bias,
            manipulation["type"],
            manipulation["level"],
            manipulation.get("timestamp", pd.Timestamp.now(tz=BOGOTA_TZ)).strftime("%H:%M"),
            entropy,
            entropy_zscore if entropy_zscore is not None else 0.0,
            pdh,
            pdl,
        )

        # 8. ML filter
        ml_confidence = self._get_ml_confidence(df)
        if self._predictor is not None and ml_confidence is not None:
            if ml_confidence < self.min_ml_confidence:
                logger.info(
                    "bias_ml_filter: confidence=%.4f < threshold=%.2f, skipping",
                    ml_confidence, self.min_ml_confidence,
                )
                return None

        # 9. Hybrid risk calculation
        entropy_zscore = self._calculate_entropy_zscore(df, entropy)
        risk_percent = self._get_risk_percent(ml_confidence, entropy_zscore)

        # 10. Calculate SL/TP with FVG as magnet
        current_price = float(df["close"].iloc[-1])
        manipulated_level = manipulation["level"]
        sl, tp, fvg_tp = self._calculate_sl_tp_with_fvg(
            df, direction, current_price, manipulated_level, pip, ml_confidence,
        )

        signal = TradeSignal(
            direction=direction,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=ml_confidence if ml_confidence is not None else 0.6,
            strategy_name=self.name,
            metadata={
                "daily_bias": bias,
                "pdh": pdh,
                "pdl": pdl,
                "manipulation_type": manipulation["type"],
                "manipulation_level": manipulated_level,
                "choch_detected": choch_detected,
                "fractal_break_fallback": not choch_detected,
                "entropy": round(entropy, 4),
                "entropy_zscore": round(entropy_zscore, 4) if entropy_zscore is not None else None,
                "ml_confidence": round(ml_confidence, 4) if ml_confidence is not None else None,
                "risk_percent": risk_percent,
                "fvg_tp": fvg_tp,
            },
        )

        # Override base validation to use our min_rr
        if signal.direction == SignalDirection.NEUTRAL:
            logger.info("bias: signal direction is NEUTRAL")
            return None
        if signal.stop_loss <= 0 or signal.take_profit <= 0:
            logger.info("bias: invalid SL/TP (%.5f/%.5f)", signal.stop_loss, signal.take_profit)
            return None

        # RR validation with automatic retry using liquidity target
        if signal.risk_reward_ratio < self.min_rr:
            logger.info(
                "bias_rr_filter: Initial RR %.2f < %.1f, trying liquidity target",
                signal.risk_reward_ratio,
                self.min_rr,
            )

            # Attempt to find next liquidity level for better RR
            alternative_tp = self._find_liquidity_target(df, direction, current_price)

            # Recalculate RR with new TP
            if direction == SignalDirection.BUY:
                tp_distance = alternative_tp - current_price
                sl_distance = current_price - signal.stop_loss
            else:
                tp_distance = current_price - alternative_tp
                sl_distance = signal.stop_loss - current_price

            new_rr = tp_distance / sl_distance if sl_distance > 0 else 0

            if new_rr >= self.min_rr:
                # Update signal with new TP
                signal.take_profit = alternative_tp
                logger.info(
                    "bias_rr_retry: Alternative TP=%.5f, new RR=%.2f PASSED",
                    alternative_tp,
                    new_rr,
                )
            else:
                logger.info(
                    "bias_rr_filter: Even with alternative TP, RR=%.2f < %.1f, skipping",
                    new_rr,
                    self.min_rr,
                )
                return None

        logger.info(
            "bias: SIGNAL GENERATED %s at %.5f (SL=%.5f, TP=%.5f, RR=%.2f, risk=%.2f%%)",
            signal.direction.value, signal.entry_price, signal.stop_loss, signal.take_profit,
            signal.risk_reward_ratio, risk_percent,
        )

        logger.info(
            "bias_signal: symbol=%s direction=%s entry=%.5f sl=%.5f tp=%.5f "
            "rr=%.2f bias=%s entropy=%.3f risk=%.1f%%",
            symbol, direction.value, current_price, sl, tp,
            signal.risk_reward_ratio, bias, entropy, risk_percent,
        )
        return signal

    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
    ) -> tuple[float, float]:
        """Fallback SL/TP using ATR. Prefer _calculate_sl_tp_with_fvg in generate_signal."""
        pip = PIP_SIZE.get(df.attrs.get("symbol", "EURUSD"), 0.0001)
        sl_distance = self.sl_pips_base * pip

        if direction == SignalDirection.BUY:
            sl = entry_price - sl_distance
            tp = entry_price + (sl_distance * 2.0)
        else:
            sl = entry_price + sl_distance
            tp = entry_price - (sl_distance * 2.0)

        return round(sl, 8), round(tp, 8)

    # ------------------------------------------------------------------
    # Private: Daily Bias
    # ------------------------------------------------------------------

    def _get_daily_bias(self, df: pd.DataFrame) -> str | None:
        """
        Determine daily bias from previous D1 candle.
        Returns BULLISH/BEARISH/NEUTRAL (Doji detection).
        """
        if not hasattr(df.index, "date"):
            return None

        dates = df.index.date
        unique_dates = sorted(set(dates))
        if len(unique_dates) < 2:
            return None

        prev_date = unique_dates[-2]
        prev_day = df[dates == prev_date]
        if prev_day.empty:
            return None

        day_open = float(prev_day["open"].iloc[0])
        day_close = float(prev_day["close"].iloc[-1])
        day_high = float(prev_day["high"].max())
        day_low = float(prev_day["low"].min())

        # V1: Doji detection - body <20% of total range → NEUTRAL
        body = abs(day_close - day_open)
        total_range = day_high - day_low

        if total_range > 0:
            body_ratio = body / total_range

            if body_ratio < 0.20:  # Doji: indecision
                logger.info(
                    "bias_doji: D1 body_ratio=%.2f%% < 20%%, marking NEUTRAL "
                    "(O=%.5f, C=%.5f, H=%.5f, L=%.5f, range=%.5f)",
                    body_ratio * 100, day_open, day_close, day_high, day_low, total_range,
                )
                return "NEUTRAL"

        # Normal directional bias
        if day_close > day_open:
            return "BULLISH"
        elif day_close < day_open:
            return "BEARISH"
        return None

    def _get_previous_day_levels(self, df: pd.DataFrame) -> tuple[float | None, float | None]:
        """Get Previous Day High (PDH) and Previous Day Low (PDL)."""
        if not hasattr(df.index, "date"):
            return None, None

        dates = df.index.date
        unique_dates = sorted(set(dates))
        if len(unique_dates) < 2:
            return None, None

        prev_date = unique_dates[-2]
        prev_day = df[dates == prev_date]
        if prev_day.empty:
            return None, None

        pdh = float(prev_day["high"].max())
        pdl = float(prev_day["low"].min())
        return pdh, pdl

    # ------------------------------------------------------------------
    # Private: Session Timing (America/Bogota)
    # ------------------------------------------------------------------

    def _get_bar_time_bogota(self, df: pd.DataFrame) -> pd.Timestamp | None:
        """Get the last bar's time in Bogota timezone."""
        if df.index.empty:
            return None
        last_time = df.index[-1]
        return self._to_bogota_time(last_time)

    def _to_bogota_time(self, utc_time: pd.Timestamp) -> pd.Timestamp:
        """Convert UTC timestamp to America/Bogota."""
        if utc_time.tzinfo is None:
            utc_time = utc_time.tz_localize("UTC")
        return utc_time.astimezone(BOGOTA_TZ)

    def _is_london_session(self, bogota_time: pd.Timestamp) -> bool:
        """Check if time is in London manipulation window (Bogota time)."""
        hour = bogota_time.hour
        return self.london_start_hour <= hour < self.london_end_hour

    def _is_ny_session(self, bogota_time: pd.Timestamp) -> bool:
        """Check if time is in NY entry window (Bogota time)."""
        hour = bogota_time.hour
        minute = bogota_time.minute
        start_mins = self.ny_start_hour * 60 + self.ny_start_minute
        end_mins = self.ny_end_hour * 60 + self.ny_end_minute
        current_mins = hour * 60 + minute
        return start_mins <= current_mins <= end_mins

    # ------------------------------------------------------------------
    # Private: London Manipulation Detection
    # ------------------------------------------------------------------

    def _detect_london_manipulation(
        self,
        df: pd.DataFrame,
        pdh: float,
        pdl: float,
        bias: str,
        pip: float,
    ) -> dict | None:
        """
        Detect manipulation during London session (RELAXED for H1 bars).

        BULLISH: Sweep below PDL → close returns above within 3 candles
        BEARISH: Sweep above PDH → close returns below within 3 candles

        Uses timezone-aware conversion and stores manipulation state
        for persistence across London → NY sessions.
        """
        # 1. Check if manipulation already stored for today
        if self._last_manipulation is not None:
            current_time = self._get_bar_time_bogota(df)
            if current_time and current_time.normalize() == self._last_manipulation_day:
                logger.info(
                    "bias_state: Using stored manipulation from %s",
                    self._last_manipulation.get("timestamp", pd.Timestamp.now(tz=BOGOTA_TZ)).strftime("%H:%M"),
                )
                return self._last_manipulation

        if not hasattr(df.index, "hour"):
            return None

        recent = df.tail(50)

        # 2. Search for sweep with multi-candle validation window
        for i in range(len(recent) - 3):  # -3 to allow lookahead
            bar = recent.iloc[i]
            bar_time_utc = recent.index[i]

            # Convert to Bogotá timezone for session check
            bar_time_bogota = self._to_bogota_time(bar_time_utc)

            # Use existing session check method (already handles Bogotá correctly)
            if not self._is_london_session(bar_time_bogota):
                continue

            if bias == "BULLISH":
                # Step 1: Check if price swept below PDL (with tolerance for near-misses)
                bar_low = float(bar["low"])
                sweep_threshold = pdl + (self.sweep_tolerance_pips * pip)
                distance_to_pdl = (bar_low - pdl) / pip

                # Debug print: Show proximity to PDL
                if abs(distance_to_pdl) < 5.0:  # Within 5 pips
                    logger.debug(
                        "BULLISH: Bar low=%.5f, PDL=%.5f, distance=%.1f pips, threshold=%.1f pips",
                        bar_low, pdl, distance_to_pdl, self.sweep_tolerance_pips,
                    )
                    if distance_to_pdl > 0 and distance_to_pdl < self.sweep_tolerance_pips:
                        logger.debug("NEAR MISS PDL: Only %.1f pips away from PDL sweep", distance_to_pdl)

                if bar_low < sweep_threshold:
                    # Step 2: Validate close returns above PDL in same OR next 2 candles
                    validation_window = recent.iloc[i : i + 3]  # Current + next 2

                    for idx, val_bar in enumerate(validation_window.itertuples()):
                        if float(val_bar.close) > pdl:
                            # Manipulation confirmed!
                            manipulation = {
                                "type": "bullish_sweep_pdl",
                                "level": pdl,
                                "bar_low": bar_low,
                                "sweep_tolerance_used": self.sweep_tolerance_pips,
                            }

                            # Store manipulation state
                            current_time = self._get_bar_time_bogota(df)
                            manipulation["timestamp"] = current_time
                            self._last_manipulation = manipulation
                            self._last_manipulation_day = current_time.normalize()

                            logger.debug(
                                "BULLISH SWEEP CONFIRMED: low=%.5f, PDL=%.5f, distance=%.1f pips (tolerance=%.1f pips)",
                                bar_low, pdl, distance_to_pdl, self.sweep_tolerance_pips,
                            )

                            logger.info(
                                "bias_manip: BULLISH sweep at %s, low=%.5f (PDL=%.5f, tolerance=%.1f pips), "
                                "recovered in %d bars",
                                bar_time_bogota.strftime("%Y-%m-%d %H:%M"),
                                bar_low,
                                pdl,
                                self.sweep_tolerance_pips,
                                idx,
                            )
                            return manipulation

            elif bias == "BEARISH":
                # Step 1: Check if price swept above PDH (with tolerance for near-misses)
                bar_high = float(bar["high"])
                sweep_threshold = pdh - (self.sweep_tolerance_pips * pip)
                distance_to_pdh = (pdh - bar_high) / pip

                # Debug print: Show proximity to PDH
                if abs(distance_to_pdh) < 5.0:  # Within 5 pips
                    logger.debug(
                        "BEARISH: Bar high=%.5f, PDH=%.5f, distance=%.1f pips, threshold=%.1f pips",
                        bar_high, pdh, distance_to_pdh, self.sweep_tolerance_pips,
                    )
                    if distance_to_pdh > 0 and distance_to_pdh < self.sweep_tolerance_pips:
                        logger.debug("NEAR MISS PDH: Only %.1f pips away from PDH sweep", distance_to_pdh)

                if bar_high > sweep_threshold:
                    # Step 2: Validate close returns below PDH in same OR next 2 candles
                    validation_window = recent.iloc[i : i + 3]

                    for idx, val_bar in enumerate(validation_window.itertuples()):
                        if float(val_bar.close) < pdh:
                            # Manipulation confirmed!
                            manipulation = {
                                "type": "bearish_sweep_pdh",
                                "level": pdh,
                                "bar_high": bar_high,
                                "sweep_tolerance_used": self.sweep_tolerance_pips,
                            }

                            # Store manipulation state
                            current_time = self._get_bar_time_bogota(df)
                            manipulation["timestamp"] = current_time
                            self._last_manipulation = manipulation
                            self._last_manipulation_day = current_time.normalize()

                            logger.debug(
                                "BEARISH SWEEP CONFIRMED: high=%.5f, PDH=%.5f, distance=%.1f pips (tolerance=%.1f pips)",
                                bar_high, pdh, distance_to_pdh, self.sweep_tolerance_pips,
                            )

                            logger.info(
                                "bias_manip: BEARISH sweep at %s, high=%.5f (PDH=%.5f, tolerance=%.1f pips), "
                                "recovered in %d bars",
                                bar_time_bogota.strftime("%Y-%m-%d %H:%M"),
                                bar_high,
                                pdh,
                                self.sweep_tolerance_pips,
                                idx,
                            )
                            return manipulation

        return None

    # ------------------------------------------------------------------
    # Private: Shannon Entropy
    # ------------------------------------------------------------------

    def _calculate_entropy(self, df: pd.DataFrame, window: int) -> float:
        """
        Calculate Shannon entropy of recent price returns.
        High entropy = erratic/noisy market → skip ChoCh.
        """
        returns = df["close"].pct_change().dropna().tail(window)
        if len(returns) < 10:
            return 0.0

        # Discretize returns into 10 bins
        counts, _ = np.histogram(returns.values, bins=10)
        total = counts.sum()
        if total == 0:
            return 0.0

        probs = counts / total
        # Shannon entropy: H = -sum(p * log2(p)) for p > 0
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * log2(p)

        return entropy

    def _calculate_entropy_zscore(self, df: pd.DataFrame, current_entropy: float) -> float | None:
        """Calculate Z-Score of current entropy vs rolling mean."""
        # Cache key: use DataFrame length (assumes sequential backtesting)
        cache_key = len(df)

        # Check cache first
        if cache_key in self._entropy_cache:
            return self._entropy_cache[cache_key]

        returns = df["close"].pct_change().dropna()
        if len(returns) < self.entropy_window * 2:
            self._entropy_cache[cache_key] = None
            return None

        # Optimized: only calculate last 100 entropies for rolling mean/std
        # This reduces O(n²) to O(n) for backtesting
        max_lookback = min(100, len(returns) - self.entropy_window)
        start_idx = len(returns) - max_lookback

        entropies = []
        for i in range(start_idx, len(returns)):
            window_returns = returns.iloc[i - self.entropy_window : i]
            counts, _ = np.histogram(window_returns.values, bins=10)
            total = counts.sum()
            if total == 0:
                entropies.append(0.0)
                continue
            probs = counts / total
            h = sum(-p * log2(p) for p in probs if p > 0)
            entropies.append(h)

        if len(entropies) < 2:
            self._entropy_cache[cache_key] = None
            return None

        mean_entropy = np.mean(entropies)
        std_entropy = np.std(entropies)
        if std_entropy < 1e-10:
            self._entropy_cache[cache_key] = 0.0
            return 0.0

        z_score = (current_entropy - mean_entropy) / std_entropy
        self._entropy_cache[cache_key] = z_score
        return z_score

    # ------------------------------------------------------------------
    # Private: Multi-Timeframe ChoCh
    # ------------------------------------------------------------------

    def _resample_to_m5(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Interpolate H1 data to approximate M5 bars for backtesting.
        Each H1 bar becomes 12 M5 bars with linear interpolation.
        """
        if len(df) < 2:
            return df

        # Check cache first (critical for backtesting performance with 10k+ bars)
        cache_key = len(df)
        if cache_key in self._m5_resample_cache:
            return self._m5_resample_cache[cache_key]

        m5_rows = []
        for i in range(len(df)):
            bar = df.iloc[i]
            bar_time = df.index[i]
            o = float(bar["open"])
            h, lo, c = float(bar["high"]), float(bar["low"]), float(bar["close"])
            vol = float(bar.get("tick_volume", 0))

            # Create 12 synthetic M5 bars within the H1 candle
            for j in range(12):
                frac = j / 11.0
                # Simulate price path: open → low/high → close
                if frac < 0.3:
                    # First third: move towards extreme
                    if c > o:  # Bullish candle: dip to low first
                        mid = o + (lo - o) * (frac / 0.3)
                    else:  # Bearish: push to high first
                        mid = o + (h - o) * (frac / 0.3)
                elif frac < 0.7:
                    # Middle: transition
                    inner_frac = (frac - 0.3) / 0.4
                    if c > o:
                        mid = lo + (h - lo) * inner_frac
                    else:
                        mid = h + (lo - h) * inner_frac
                else:
                    # Final third: approach close
                    inner_frac = (frac - 0.7) / 0.3
                    if c > o:
                        mid = h + (c - h) * inner_frac
                    else:
                        mid = lo + (c - lo) * inner_frac

                noise = (h - lo) * 0.05
                m5_rows.append({
                    "open": mid - noise * 0.5,
                    "high": mid + noise,
                    "low": mid - noise,
                    "close": mid + noise * 0.5,
                    "tick_volume": vol / 12.0,
                    "time": bar_time + pd.Timedelta(minutes=5 * j),
                })

        m5_df = pd.DataFrame(m5_rows)
        m5_df.set_index("time", inplace=True)

        # Cache result for future calls (backtesting optimization)
        self._m5_resample_cache[cache_key] = m5_df

        return m5_df

    def _detect_choch(self, df_m5: pd.DataFrame, direction: SignalDirection) -> bool:
        """
        Detect Change of Character (ChoCh) on M5 timeframe with SYMMETRIC logic.

        Key improvements:
        - Uses configurable lookback (self.choch_lookback)
        - Filters swing points by temporal proximity (last 15 bars)
        - Symmetric tolerance and threshold logic for BUY/SELL
        - Dynamic tolerance based on recent volatility
        """
        if len(df_m5) < self.choch_lookback:
            logger.info("bias_choch: insufficient M5 bars (%d < %d)", len(df_m5), self.choch_lookback)
            return False

        recent = df_m5.tail(self.choch_lookback)  # Use configurable parameter
        highs = recent["high"].values
        lows = recent["low"].values
        closes = recent["close"].values

        # Find ALL swing points (3-bar method)
        swing_highs = []
        swing_lows = []

        for i in range(1, len(recent) - 1):
            if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
                swing_highs.append((i, highs[i]))
            if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
                swing_lows.append((i, lows[i]))

        if not swing_highs or not swing_lows:
            logger.info("bias_choch: no swings found")
            return False

        # NUEVO: Filter swings by temporal proximity (last 15 bars = 1.25 hours)
        local_window = 15
        recent_swing_highs = [(idx, price) for idx, price in swing_highs if idx >= len(recent) - local_window]
        recent_swing_lows = [(idx, price) for idx, price in swing_lows if idx >= len(recent) - local_window]

        # Fallback: If no recent swings, use all
        if not recent_swing_highs:
            recent_swing_highs = swing_highs
        if not recent_swing_lows:
            recent_swing_lows = swing_lows

        logger.info(
            "bias_choch: M5_bars=%d, total_swings=(highs=%d, lows=%d), local_swings=(highs=%d, lows=%d), direction=%s",
            len(recent),
            len(swing_highs),
            len(swing_lows),
            len(recent_swing_highs),
            len(recent_swing_lows),
            direction.value,
        )

        last_close = closes[-1]

        # Use recent 10-bar range for dynamic tolerance (more stable than 5)
        recent_10_high = highs[-10:].max()
        recent_10_low = lows[-10:].min()
        recent_range = recent_10_high - recent_10_low

        if direction == SignalDirection.BUY:
            # Bullish ChoCh: price breaks above RECENT swing high
            last_swing_high = recent_swing_highs[-1][1]

            pip = PIP_SIZE.get(self._current_symbol, 0.0001)
            tolerance = max(recent_range * 0.15, pip * 2.0)
            threshold = last_swing_high - tolerance
            is_break = last_close >= threshold

            logger.info(
                "bias_choch_buy: close=%.5f, swing_high=%.5f (local), threshold=%.5f, "
                "tolerance=%.5f (DYNAMIC: max(range*0.15=%.5f, pip*2.0=%.5f)), range=%.5f, break=%s",
                last_close,
                last_swing_high,
                threshold,
                tolerance,
                recent_range * 0.15,
                pip * 2.0,
                recent_range,
                is_break,
            )
            return is_break

        elif direction == SignalDirection.SELL:
            # Bearish ChoCh: price breaks below RECENT swing low
            last_swing_low = recent_swing_lows[-1][1]

            pip = PIP_SIZE.get(self._current_symbol, 0.0001)
            tolerance = max(recent_range * 0.15, pip * 2.0)

            # CRITICAL: Liquidity grab threshold (1.5 pips above swing) - calibrated for balance
            threshold = last_swing_low + (pip * 1.5)
            is_break = last_close <= threshold

            logger.info(
                "bias_choch_sell: close=%.5f, swing_low=%.5f (local), threshold=%.5f, "
                "tolerance=%.5f (DYNAMIC: max(range*0.15=%.5f, pip*2.0=%.5f)), range=%.5f, break=%s",
                last_close,
                last_swing_low,
                threshold,
                tolerance,
                recent_range * 0.15,
                pip * 2.0,
                recent_range,
                is_break,
            )
            return is_break

        return False

    # ================================================================
    # SIMETRÍA VERIFICADA (BUY vs SELL):
    # ================================================================
    #
    # | Aspecto              | BUY Logic                          | SELL Logic                         |
    # |----------------------|------------------------------------|------------------------------------|
    # | Swing Selection      | recent_swing_highs[-1]             | recent_swing_lows[-1]              |
    # | Temporal Filter      | Últimos 15 bars M5                 | Últimos 15 bars M5                 |
    # | Tolerance Formula    | max(range * 0.15, pip * 2.0)       | max(range * 0.15, pip * 2.0)       |
    # | Threshold Calc       | swing_high - tolerance             | swing_low + (pip * 0.5)            |
    # | Break Condition      | close >= threshold                 | close <= threshold                 |
    # | Fractal Threshold    | fractal_high - (pip * 3.0)         | fractal_low + (pip * 3.0)          |
    # | Fractal Break        | close > threshold                  | close < threshold                  |
    # ================================================================

    def _detect_fractal_break(self, df: pd.DataFrame, direction: SignalDirection) -> bool:
        """
        Fractal Break de Emergencia: Fallback if no ChoCh detected.

        SMC Liquidity Grab Logic:
        - Allows "touching" of fractal zones with 3-pip tolerance
        - Symmetric for BUY/SELL to ensure balanced detection

        Only active after London sweep detected (manipulation exists).
        """
        if len(df) < 3:
            logger.info("bias_fractal: insufficient H1 bars (%d < 3)", len(df))
            return False

        last_3_bars = df.tail(3)
        current_close = float(df.iloc[-1]["close"])
        pip = PIP_SIZE.get(self._current_symbol, 0.0001)

        if direction == SignalDirection.BUY:
            # Bullish fractal: close breaks above max of last 3 H1 highs (con tolerancia)
            fractal_high = last_3_bars["high"].max()

            # SMC: Permitir "roce" de zona de liquidez (3 pips abajo del fractal)
            threshold = fractal_high - (pip * 3.0)
            is_break = current_close > threshold

            logger.info(
                "bias_fractal_buy: close=%.5f, fractal_high=%.5f (3H1), threshold=%.5f (-3.0 pips), break=%s",
                current_close, fractal_high, threshold, is_break,
            )
            return is_break

        elif direction == SignalDirection.SELL:
            # Bearish fractal: close breaks below min of last 3 H1 lows (con tolerancia)
            fractal_low = last_3_bars["low"].min()

            # SMC: Permitir "roce" de zona de liquidez (1.0 pips arriba del fractal) - calibrated
            threshold = fractal_low + (pip * 1.0)
            is_break = current_close < threshold

            logger.info(
                "bias_fractal_sell: close=%.5f, fractal_low=%.5f (3H1), threshold=%.5f (+1.0 pips), break=%s",
                current_close, fractal_low, threshold, is_break,
            )
            return is_break

        return False

    # ------------------------------------------------------------------
    # Private: FVG Detection & TP Calculation
    # ------------------------------------------------------------------

    def _find_unfilled_fvg(
        self, df: pd.DataFrame, direction: SignalDirection, entry_price: float,
    ) -> float | None:
        """
        Find the nearest unfilled Fair Value Gap as TP magnet.
        Bullish FVG: Candle3.Low > Candle1.High (gap up)
        Bearish FVG: Candle3.High < Candle1.Low (gap down)
        """
        recent = df.tail(self.fvg_lookback)
        if len(recent) < 3:
            return None

        best_fvg = None
        best_distance = float("inf")

        for i in range(2, len(recent)):
            c1 = recent.iloc[i - 2]
            c3 = recent.iloc[i]

            if direction == SignalDirection.BUY:
                # Bullish FVG above entry: gap between c1.high and c3.low
                if float(c3["low"]) > float(c1["high"]):
                    fvg_bottom = float(c1["high"])
                    fvg_top = float(c3["low"])
                    # FVG must be above entry price
                    if fvg_bottom > entry_price:
                        distance = fvg_bottom - entry_price
                        if distance < best_distance:
                            best_distance = distance
                            best_fvg = fvg_bottom  # TP at bottom of FVG

            elif direction == SignalDirection.SELL:
                # Bearish FVG below entry: gap between c3.high and c1.low
                if float(c3["high"]) < float(c1["low"]):
                    fvg_top = float(c1["low"])
                    fvg_bottom = float(c3["high"])
                    # FVG must be below entry price
                    if fvg_top < entry_price:
                        distance = entry_price - fvg_top
                        if distance < best_distance:
                            best_distance = distance
                            best_fvg = fvg_top  # TP at top of FVG

        return best_fvg

    def _find_liquidity_target(
        self, df: pd.DataFrame, direction: SignalDirection, entry_price: float,
    ) -> float:
        """Fallback TP: nearest swing high/low as liquidity target."""
        recent = df.tail(50)
        if direction == SignalDirection.BUY:
            # Target the highest swing high above entry
            highs = recent["high"].values
            targets = [h for h in highs if h > entry_price]
            return float(max(targets)) if targets else entry_price * 1.005
        else:
            lows = recent["low"].values
            targets = [low for low in lows if low < entry_price]
            return float(min(targets)) if targets else entry_price * 0.995

    def _calculate_sl_tp_with_fvg(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
        manipulated_level: float,
        pip: float,
        ml_confidence: float | None,
    ) -> tuple[float, float, float | None]:
        """
        Calculate SL and TP.
        SL: based on manipulated level + dynamic pips by ML confidence.
        TP: FVG as primary target, then liquidity as fallback.
        Returns: (sl, tp, fvg_tp_or_none)
        """
        # Dynamic SL based on ML confidence
        if ml_confidence is not None and ml_confidence > 0.85:
            sl_pips = 8.0
        elif ml_confidence is not None and ml_confidence < 0.75:
            sl_pips = 12.0
        else:
            sl_pips = self.sl_pips_base

        sl_distance = sl_pips * pip

        if direction == SignalDirection.BUY:
            sl = manipulated_level - sl_distance
        else:
            sl = manipulated_level + sl_distance

        # TP: FVG as primary magnet
        fvg_tp = self._find_unfilled_fvg(df, direction, entry_price)

        if fvg_tp is not None:
            tp = fvg_tp
        else:
            tp = self._find_liquidity_target(df, direction, entry_price)

        return round(sl, 8), round(tp, 8), round(fvg_tp, 8) if fvg_tp else None

    # ------------------------------------------------------------------
    # Private: ML Integration
    # ------------------------------------------------------------------

    def _get_ml_confidence(self, df: pd.DataFrame) -> float | None:
        """Get ML prediction probability. Returns None if no model loaded."""
        if self._predictor is None:
            return None
        try:
            result = self._predictor.predict(df)
            return result.get("probability", 0.0)
        except Exception as e:
            logger.warning("bias_ml_error: %s", str(e))
            return None

    def _get_risk_percent(
        self, ml_confidence: float | None, entropy_zscore: float | None,
    ) -> float:
        """
        Hybrid risk adjustment: ML confidence + entropy Z-Score.

        - Confidence > 0.85 AND low entropy (Z < 0) → 1.5% (organized market, high confidence)
        - Confidence > 0.85 AND high entropy (Z > 0) → 0.5% (precaution)
        - Confidence 0.65-0.85 → 0.5%
        - No ML → 0.5% default
        """
        if ml_confidence is None:
            return 0.5

        if ml_confidence > 0.85:
            if entropy_zscore is not None and entropy_zscore < 0:
                return 1.5  # High confidence + organized market
            return 0.5  # High confidence but erratic market

        return 0.5  # Medium confidence
