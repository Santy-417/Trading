"""
SMC Feature Extractor - Smart Money Concepts features for ML models.

Extracts features specific to BiasStrategy and SMC analysis:
- PDH/PDL distances and sweep probabilities
- Session classification (London/NY/Other)
- Manipulation detection indicators
- ChoCh occurrence flags
- Entropy and volatility regimes
- Fractal break patterns
"""

from math import log2

import numpy as np
import pandas as pd
import pytz

from app.core.logging_config import get_logger

logger = get_logger(__name__)

BOGOTA_TZ = pytz.timezone("America/Bogota")

PIP_SIZE = {
    "EURUSD": 0.0001,
    "XAUUSD": 0.01,
}


class SMCFeatureExtractor:
    """Extract Smart Money Concepts features from OHLCV data."""

    @staticmethod
    def add_all_smc_features(df: pd.DataFrame, symbol: str = "EURUSD") -> pd.DataFrame:
        """Add all SMC features to DataFrame."""
        df = df.copy()
        df = SMCFeatureExtractor.add_pdh_pdl_features(df)
        df = SMCFeatureExtractor.add_session_features(df)
        df = SMCFeatureExtractor.add_sweep_probability(df, symbol)
        df = SMCFeatureExtractor.add_fractal_features(df)
        df = SMCFeatureExtractor.add_entropy_features(df)
        df = SMCFeatureExtractor.add_bias_features(df)
        return df

    @staticmethod
    def add_pdh_pdl_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Previous Day High/Low features.

        Features:
        - distance_to_pdh: Distance from close to PDH (pips)
        - distance_to_pdl: Distance from close to PDL (pips)
        - pdh_pdl_range: Total range between PDH and PDL
        - position_in_pdh_pdl: Normalized position (0-1) within PDH/PDL range
        """
        if not hasattr(df.index, "date"):
            df["distance_to_pdh"] = 0.0
            df["distance_to_pdl"] = 0.0
            df["pdh_pdl_range"] = 0.0
            df["position_in_pdh_pdl"] = 0.5
            return df

        distances_pdh = []
        distances_pdl = []
        ranges = []
        positions = []

        dates = df.index.date
        unique_dates = sorted(set(dates))

        for current_date in unique_dates:
            current_day_data = df[dates == current_date]

            # Get previous day
            date_index = unique_dates.index(current_date)
            if date_index == 0:
                # First day: no previous day
                for _ in range(len(current_day_data)):
                    distances_pdh.append(0.0)
                    distances_pdl.append(0.0)
                    ranges.append(0.0)
                    positions.append(0.5)
                continue

            prev_date = unique_dates[date_index - 1]
            prev_day = df[dates == prev_date]

            if prev_day.empty:
                for _ in range(len(current_day_data)):
                    distances_pdh.append(0.0)
                    distances_pdl.append(0.0)
                    ranges.append(0.0)
                    positions.append(0.5)
                continue

            pdh = float(prev_day["high"].max())
            pdl = float(prev_day["low"].min())
            pdh_pdl_range = pdh - pdl

            for _, row in current_day_data.iterrows():
                close = float(row["close"])
                dist_pdh = close - pdh
                dist_pdl = close - pdl

                distances_pdh.append(dist_pdh)
                distances_pdl.append(dist_pdl)
                ranges.append(pdh_pdl_range)

                # Position: 0 = at PDL, 1 = at PDH
                if pdh_pdl_range > 0:
                    position = (close - pdl) / pdh_pdl_range
                else:
                    position = 0.5
                positions.append(position)

        df["distance_to_pdh"] = distances_pdh
        df["distance_to_pdl"] = distances_pdl
        df["pdh_pdl_range"] = ranges
        df["position_in_pdh_pdl"] = positions

        return df

    @staticmethod
    def add_session_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add session classification features (Bogotá timezone).

        Features:
        - is_london_session: 1 if London session (02:00-11:30 Bogotá), else 0
        - is_ny_session: 1 if NY session (08:00-14:00 Bogotá), else 0
        - session_overlap: 1 if both sessions overlap (08:00-11:30 Bogotá), else 0
        """
        if not hasattr(df.index, "tz_localize") and not hasattr(df.index, "tz_convert"):
            df["is_london_session"] = 0
            df["is_ny_session"] = 0
            df["session_overlap"] = 0
            return df

        london_flags = []
        ny_flags = []
        overlap_flags = []

        for timestamp in df.index:
            # Convert to Bogotá time
            if timestamp.tz is None:
                ts_bogota = timestamp.tz_localize("UTC").tz_convert(BOGOTA_TZ)
            else:
                ts_bogota = timestamp.tz_convert(BOGOTA_TZ)

            hour = ts_bogota.hour

            # London: 02:00-11:30 Bogotá (07:00-16:30 UTC)
            is_london = 2 <= hour < 12
            # NY: 08:00-14:00 Bogotá (13:00-19:00 UTC)
            is_ny = 8 <= hour < 14
            # Overlap: 08:00-11:30 Bogotá
            is_overlap = 8 <= hour < 12

            london_flags.append(1 if is_london else 0)
            ny_flags.append(1 if is_ny else 0)
            overlap_flags.append(1 if is_overlap else 0)

        df["is_london_session"] = london_flags
        df["is_ny_session"] = ny_flags
        df["session_overlap"] = overlap_flags

        return df

    @staticmethod
    def add_sweep_probability(df: pd.DataFrame, symbol: str = "EURUSD") -> pd.DataFrame:
        """
        Add sweep probability features.

        Features:
        - swept_pdl: 1 if low swept below PDL, else 0
        - swept_pdh: 1 if high swept above PDH, else 0
        - sweep_magnitude_pdl: Distance of sweep below PDL (in pips)
        - sweep_magnitude_pdh: Distance of sweep above PDH (in pips)
        """
        pip = PIP_SIZE.get(symbol, 0.0001)

        if "distance_to_pdl" not in df.columns:
            df = SMCFeatureExtractor.add_pdh_pdl_features(df)

        swept_pdl_flags = []
        swept_pdh_flags = []
        sweep_mag_pdl = []
        sweep_mag_pdh = []

        if not hasattr(df.index, "date"):
            for _ in range(len(df)):
                swept_pdl_flags.append(0)
                swept_pdh_flags.append(0)
                sweep_mag_pdl.append(0.0)
                sweep_mag_pdh.append(0.0)
        else:
            dates = df.index.date
            unique_dates = sorted(set(dates))

            for current_date in unique_dates:
                current_day_data = df[dates == current_date]

                date_index = unique_dates.index(current_date)
                if date_index == 0:
                    for _ in range(len(current_day_data)):
                        swept_pdl_flags.append(0)
                        swept_pdh_flags.append(0)
                        sweep_mag_pdl.append(0.0)
                        sweep_mag_pdh.append(0.0)
                    continue

                prev_date = unique_dates[date_index - 1]
                prev_day = df[dates == prev_date]

                if prev_day.empty:
                    for _ in range(len(current_day_data)):
                        swept_pdl_flags.append(0)
                        swept_pdh_flags.append(0)
                        sweep_mag_pdl.append(0.0)
                        sweep_mag_pdh.append(0.0)
                    continue

                pdh = float(prev_day["high"].max())
                pdl = float(prev_day["low"].min())

                for _, row in current_day_data.iterrows():
                    low = float(row["low"])
                    high = float(row["high"])

                    # PDL sweep
                    if low < pdl:
                        swept_pdl_flags.append(1)
                        sweep_mag_pdl.append((pdl - low) / pip)
                    else:
                        swept_pdl_flags.append(0)
                        sweep_mag_pdl.append(0.0)

                    # PDH sweep
                    if high > pdh:
                        swept_pdh_flags.append(1)
                        sweep_mag_pdh.append((high - pdh) / pip)
                    else:
                        swept_pdh_flags.append(0)
                        sweep_mag_pdh.append(0.0)

        df["swept_pdl"] = swept_pdl_flags
        df["swept_pdh"] = swept_pdh_flags
        df["sweep_magnitude_pdl"] = sweep_mag_pdl
        df["sweep_magnitude_pdh"] = sweep_mag_pdh

        return df

    @staticmethod
    def add_fractal_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add fractal break features (3-bar patterns).

        Features:
        - fractal_break_high: 1 if close breaks max of last 3 highs, else 0
        - fractal_break_low: 1 if close breaks min of last 3 lows, else 0
        """
        fractal_high_flags = []
        fractal_low_flags = []

        for i in range(len(df)):
            if i < 3:
                fractal_high_flags.append(0)
                fractal_low_flags.append(0)
                continue

            last_3 = df.iloc[i - 3 : i]
            current_close = float(df.iloc[i]["close"])

            fractal_high = last_3["high"].max()
            fractal_low = last_3["low"].min()

            fractal_high_flags.append(1 if current_close > fractal_high else 0)
            fractal_low_flags.append(1 if current_close < fractal_low else 0)

        df["fractal_break_high"] = fractal_high_flags
        df["fractal_break_low"] = fractal_low_flags

        return df

    @staticmethod
    def add_entropy_features(df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
        """
        Add Shannon entropy features for market regime detection.

        Features:
        - market_entropy: Shannon entropy of returns
        - entropy_zscore: Z-Score of entropy vs rolling mean
        - high_entropy_regime: 1 if z-score > 1.5 (erratic market), else 0
        """
        returns = df["close"].pct_change()
        entropy_values = []

        for i in range(len(df)):
            if i < window:
                entropy_values.append(0.0)
                continue

            window_returns = returns.iloc[i - window : i].dropna().values
            if len(window_returns) < 10:
                entropy_values.append(0.0)
                continue

            counts, _ = np.histogram(window_returns, bins=10)
            total = counts.sum()
            if total == 0:
                entropy_values.append(0.0)
                continue

            probs = counts / total
            h = sum(-p * log2(p) for p in probs if p > 0)
            entropy_values.append(h)

        df["market_entropy"] = entropy_values

        # Z-Score
        entropy_series = pd.Series(entropy_values, index=df.index)
        rolling_mean = entropy_series.rolling(100).mean()
        rolling_std = entropy_series.rolling(100).std()
        df["entropy_zscore"] = (entropy_series - rolling_mean) / rolling_std.replace(0, np.inf)

        # High entropy regime flag
        df["high_entropy_regime"] = (df["entropy_zscore"] > 1.5).astype(int)

        return df

    @staticmethod
    def add_bias_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add daily bias features.

        Features:
        - daily_bias_bullish: 1 if previous D1 closed bullish, else 0
        - daily_bias_bearish: 1 if previous D1 closed bearish, else 0
        - daily_bias_neutral: 1 if previous D1 is Doji (body <20% of range), else 0
        - d1_body_ratio: Body size / total range of previous D1
        """
        if not hasattr(df.index, "date"):
            df["daily_bias_bullish"] = 0
            df["daily_bias_bearish"] = 0
            df["daily_bias_neutral"] = 0
            df["d1_body_ratio"] = 0.0
            return df

        bias_bullish = []
        bias_bearish = []
        bias_neutral = []
        body_ratios = []

        dates = df.index.date
        unique_dates = sorted(set(dates))

        for current_date in unique_dates:
            current_day_data = df[dates == current_date]

            date_index = unique_dates.index(current_date)
            if date_index == 0:
                for _ in range(len(current_day_data)):
                    bias_bullish.append(0)
                    bias_bearish.append(0)
                    bias_neutral.append(0)
                    body_ratios.append(0.0)
                continue

            prev_date = unique_dates[date_index - 1]
            prev_day = df[dates == prev_date]

            if prev_day.empty:
                for _ in range(len(current_day_data)):
                    bias_bullish.append(0)
                    bias_bearish.append(0)
                    bias_neutral.append(0)
                    body_ratios.append(0.0)
                continue

            day_open = float(prev_day["open"].iloc[0])
            day_close = float(prev_day["close"].iloc[-1])
            day_high = float(prev_day["high"].max())
            day_low = float(prev_day["low"].min())

            body = abs(day_close - day_open)
            total_range = day_high - day_low
            body_ratio = body / total_range if total_range > 0 else 0.0

            # Doji detection
            is_neutral = body_ratio < 0.20
            is_bullish = day_close > day_open and not is_neutral
            is_bearish = day_close < day_open and not is_neutral

            for _ in range(len(current_day_data)):
                bias_bullish.append(1 if is_bullish else 0)
                bias_bearish.append(1 if is_bearish else 0)
                bias_neutral.append(1 if is_neutral else 0)
                body_ratios.append(body_ratio)

        df["daily_bias_bullish"] = bias_bullish
        df["daily_bias_bearish"] = bias_bearish
        df["daily_bias_neutral"] = bias_neutral
        df["d1_body_ratio"] = body_ratios

        return df

    @staticmethod
    def get_smc_feature_columns(df: pd.DataFrame) -> list[str]:
        """Get list of SMC feature column names (excludes OHLCV)."""
        exclude = {"open", "high", "low", "close", "tick_volume", "real_volume", "spread", "target"}
        smc_features = [
            "distance_to_pdh", "distance_to_pdl", "pdh_pdl_range", "position_in_pdh_pdl",
            "is_london_session", "is_ny_session", "session_overlap",
            "swept_pdl", "swept_pdh", "sweep_magnitude_pdl", "sweep_magnitude_pdh",
            "fractal_break_high", "fractal_break_low",
            "market_entropy", "entropy_zscore", "high_entropy_regime",
            "daily_bias_bullish", "daily_bias_bearish", "daily_bias_neutral", "d1_body_ratio",
        ]
        return [c for c in df.columns if c in smc_features]
