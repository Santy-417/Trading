"""
NewsFilter — Block trading around High Impact news events.

Loads a JSON schedule of economic events and prevents order execution
within a configurable window (default ±5 minutes) around each event.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_SCHEDULE_PATH = Path(__file__).parent / "news_schedule.json"
_DEFAULT_WINDOW_MINUTES = 5

# Map symbols to their component currencies
_SYMBOL_CURRENCIES: dict[str, list[str]] = {
    "EURUSD": ["EUR", "USD"],
    "XAUUSD": ["XAU", "USD"],
    "DXY": ["USD"],
    "USDCAD": ["USD", "CAD"],
    "GBPUSD": ["GBP", "USD"],
    "AUDCAD": ["AUD", "CAD"],
    "EURJPY": ["EUR", "JPY"],
    "USDJPY": ["USD", "JPY"],
    "EURGBP": ["EUR", "GBP"],
}


class NewsFilter:
    """
    Filter trades around High Impact economic news events.

    Usage:
        filter = NewsFilter()
        if filter.is_restricted("EURUSD", datetime.now(timezone.utc)):
            # Skip trading — news event nearby
    """

    def __init__(
        self,
        schedule_path: str | Path | None = None,
        window_minutes: int = _DEFAULT_WINDOW_MINUTES,
    ):
        self.window_minutes = window_minutes
        self._schedule: list[dict] = []

        path = Path(schedule_path) if schedule_path else _DEFAULT_SCHEDULE_PATH
        self._load_schedule(path)

    def _load_schedule(self, path: Path) -> None:
        """Load news schedule from JSON file."""
        if not path.exists():
            logger.warning("news_schedule not found: %s — no news filtering active", path)
            return

        try:
            with open(path, encoding="utf-8") as f:
                self._schedule = json.load(f)
            logger.info("news_schedule loaded: %d events from %s", len(self._schedule), path)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("news_schedule load failed: %s", str(e))
            self._schedule = []

    def is_restricted(self, symbol: str, utc_time: datetime) -> bool:
        """
        Check if trading is restricted for the given symbol at the given UTC time.

        Returns True if there's a High Impact event for any of the symbol's
        currencies within ±window_minutes of utc_time.
        """
        if not self._schedule:
            return False

        currencies = self._get_currencies_for_symbol(symbol)
        if not currencies:
            return False

        window = timedelta(minutes=self.window_minutes)

        for event in self._schedule:
            if event.get("impact", "").lower() != "high":
                continue

            event_currency = event.get("currency", "")
            if event_currency not in currencies:
                continue

            # Parse event datetime
            event_dt = self._parse_event_time(event)
            if event_dt is None:
                continue

            # Check if current time is within the window
            if abs((utc_time - event_dt).total_seconds()) <= window.total_seconds():
                logger.info(
                    "news_filter_blocked: symbol=%s event=%s currency=%s time=%s",
                    symbol, event.get("event", "unknown"), event_currency,
                    event_dt.isoformat(),
                )
                return True

        return False

    @staticmethod
    def _get_currencies_for_symbol(symbol: str) -> list[str]:
        """Get the component currencies for a trading symbol."""
        return _SYMBOL_CURRENCIES.get(symbol, [])

    @staticmethod
    def _parse_event_time(event: dict) -> datetime | None:
        """Parse event date and time_utc into a UTC datetime."""
        try:
            date_str = event.get("date", "")
            time_str = event.get("time_utc", "")
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            return dt.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return None


# Singleton instance
news_filter = NewsFilter()
