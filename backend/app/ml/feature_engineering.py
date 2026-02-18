import numpy as np
import pandas as pd


class FeatureEngineer:
    """Generate technical indicator features for ML models."""

    @staticmethod
    def add_all_features(df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical features to a DataFrame."""
        df = df.copy()
        df = FeatureEngineer.add_returns(df)
        df = FeatureEngineer.add_rsi(df)
        df = FeatureEngineer.add_macd(df)
        df = FeatureEngineer.add_bollinger_bands(df)
        df = FeatureEngineer.add_atr(df)
        df = FeatureEngineer.add_ema(df)
        df = FeatureEngineer.add_volume_features(df)
        df = FeatureEngineer.add_candle_patterns(df)
        df = FeatureEngineer.add_momentum(df)
        return df

    @staticmethod
    def add_returns(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
        periods = periods or [1, 3, 5, 10, 20]
        for p in periods:
            df[f"return_{p}"] = df["close"].pct_change(p)
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.inf)
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def add_macd(
        df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> pd.DataFrame:
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]
        return df

    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        sma = df["close"].rolling(period).mean()
        rolling_std = df["close"].rolling(period).std()
        df["bb_upper"] = sma + (rolling_std * std)
        df["bb_lower"] = sma - (rolling_std * std)
        df["bb_middle"] = sma
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / sma
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
        return df

    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(period).mean()
        df["atr_percent"] = df["atr"] / df["close"] * 100
        return df

    @staticmethod
    def add_ema(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
        periods = periods or [9, 21, 50, 200]
        for p in periods:
            df[f"ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()
        return df

    @staticmethod
    def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
        if "tick_volume" in df.columns:
            df["volume_sma_20"] = df["tick_volume"].rolling(20).mean()
            df["volume_ratio"] = df["tick_volume"] / df["volume_sma_20"]
        return df

    @staticmethod
    def add_candle_patterns(df: pd.DataFrame) -> pd.DataFrame:
        body = df["close"] - df["open"]
        range_ = df["high"] - df["low"]

        df["candle_body_ratio"] = body.abs() / range_.replace(0, np.inf)
        df["upper_shadow"] = df["high"] - df[["open", "close"]].max(axis=1)
        df["lower_shadow"] = df[["open", "close"]].min(axis=1) - df["low"]
        df["is_bullish"] = (body > 0).astype(int)
        return df

    @staticmethod
    def add_momentum(df: pd.DataFrame) -> pd.DataFrame:
        df["momentum_10"] = df["close"] - df["close"].shift(10)
        df["momentum_20"] = df["close"] - df["close"].shift(20)
        df["roc_10"] = df["close"].pct_change(10) * 100
        return df

    @staticmethod
    def get_feature_columns(df: pd.DataFrame) -> list[str]:
        """Get list of feature column names (excludes OHLCV and target)."""
        exclude = {"open", "high", "low", "close", "tick_volume", "real_volume", "spread", "target"}
        return [c for c in df.columns if c not in exclude]
