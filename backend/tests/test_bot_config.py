"""
Tests for GET /bot/config and PATCH /bot/config endpoints.

Strategy:
  - Tests call the endpoint handler functions directly with a mocked AsyncSession.
  - DB queries are mocked at the session.execute() level.
  - No real DB or HTTP server required.
  - Follows the same mock style as test_execution_engine.py.

Note: MetaTrader5 is not installed in CI / dev environments without MT5.
      We stub it in sys.modules before importing any app module that
      would otherwise trigger "import MetaTrader5" at module load time.
"""

import sys
from unittest.mock import MagicMock

# ── Stub non-installed packages (must come before any app import) ─────────────
# This environment has pandas/numpy/pytz but NOT MetaTrader5, sklearn, xgboost.
# Stub all of them so the import chain resolves cleanly.
_STUBS = [
    "MetaTrader5",
    "sklearn",
    "sklearn.pipeline",
    "sklearn.metrics",
    "sklearn.preprocessing",
    "sklearn.model_selection",
    "xgboost",
]
for _mod in _STUBS:
    sys.modules.setdefault(_mod, MagicMock())

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.routers.bot import get_bot_config, update_bot_config
from app.schemas.bot import BotConfigUpdateRequest, StrategyParamsUpdate


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_config(**overrides):
    """Return a mock BotConfig ORM object with sensible defaults."""
    config = MagicMock()
    config.id            = uuid.uuid4()
    config.name          = "default"
    config.is_active     = True
    config.strategy      = "bias"
    config.symbols       = ["EURUSD", "XAUUSD"]
    config.timeframe     = "H1"
    config.risk_per_trade = Decimal("1.00")
    config.lot_mode      = "percent_risk"
    config.fixed_lot     = Decimal("0.0100")
    config.max_trades_per_hour = 10
    config.strategy_params = {
        "entropy_threshold": 3.1,
        "choch_lookback": 60,
        "min_rr": 1.3,
        "sl_pips_base": 10.0,
        "sweep_tolerance_pips": 3.0,
    }
    config.error_state   = False
    config.last_error    = None
    config.last_heartbeat = None
    config.crash_count   = 0
    config.created_at    = datetime(2026, 1, 1, tzinfo=timezone.utc)
    config.updated_at    = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for k, v in overrides.items():
        setattr(config, k, v)
    return config


def _make_db(config_obj):
    """Return a mocked AsyncSession whose execute() returns config_obj."""
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = config_obj

    db = AsyncMock()
    db.execute.return_value = scalar_result
    db.flush = AsyncMock()
    return db


def _make_request(ip: str = "127.0.0.1"):
    req = MagicMock()
    req.client.host = ip
    return req


# ─── GET /bot/config ──────────────────────────────────────────────────────────


class TestGetBotConfig:
    @pytest.mark.asyncio
    async def test_returns_active_config(self):
        cfg = _make_config()
        db = _make_db(cfg)

        result = await get_bot_config(db=db, _user={})

        assert result.strategy == "bias"
        assert result.timeframe == "H1"
        assert result.symbols == ["EURUSD", "XAUUSD"]
        assert result.requires_restart is False

    @pytest.mark.asyncio
    async def test_falls_back_to_most_recent_when_no_active(self):
        """First query (is_active=True) returns None; second returns a config."""
        cfg = _make_config(is_active=False)

        none_result = MagicMock()
        none_result.scalar_one_or_none.return_value = None

        found_result = MagicMock()
        found_result.scalar_one_or_none.return_value = cfg

        db = AsyncMock()
        db.execute.side_effect = [none_result, found_result]

        result = await get_bot_config(db=db, _user={})

        assert result.strategy == "bias"
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_404_when_no_config_exists(self):
        none_result = MagicMock()
        none_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute.return_value = none_result

        with pytest.raises(HTTPException) as exc_info:
            await get_bot_config(db=db, _user={})

        assert exc_info.value.status_code == 404
        assert "No bot config found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_response_converts_decimal_to_float(self):
        cfg = _make_config(risk_per_trade=Decimal("1.50"), fixed_lot=Decimal("0.0200"))
        db = _make_db(cfg)

        result = await get_bot_config(db=db, _user={})

        assert isinstance(result.risk_per_trade, float)
        assert result.risk_per_trade == pytest.approx(1.5)
        assert isinstance(result.fixed_lot, float)


# ─── PATCH /bot/config ────────────────────────────────────────────────────────


class TestPatchBotConfig:
    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_updates_scalar_field(self, MockAuditRepo):
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config(risk_per_trade=Decimal("1.00"))
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(risk_per_trade=2.5)
        result = await update_bot_config(
            request=_make_request(), body=body, db=db, _user={}
        )

        assert cfg.risk_per_trade == 2.5
        assert result.requires_restart is False

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_requires_restart_on_strategy_change(self, MockAuditRepo):
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config(strategy="bias")
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(strategy="fibonacci")
        result = await update_bot_config(
            request=_make_request(), body=body, db=db, _user={}
        )

        assert result.requires_restart is True
        assert cfg.strategy == "fibonacci"

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_requires_restart_on_symbols_change(self, MockAuditRepo):
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config(symbols=["EURUSD", "XAUUSD"])
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(symbols=["EURUSD"])
        result = await update_bot_config(
            request=_make_request(), body=body, db=db, _user={}
        )

        assert result.requires_restart is True

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_requires_restart_on_timeframe_change(self, MockAuditRepo):
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config(timeframe="H1")
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(timeframe="H4")
        result = await update_bot_config(
            request=_make_request(), body=body, db=db, _user={}
        )

        assert result.requires_restart is True

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_no_restart_when_same_value(self, MockAuditRepo):
        """Sending the same strategy that's already set must NOT trigger restart."""
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config(strategy="bias")
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(strategy="bias")
        result = await update_bot_config(
            request=_make_request(), body=body, db=db, _user={}
        )

        assert result.requires_restart is False

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_merges_strategy_params(self, MockAuditRepo):
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config(strategy_params={
            "entropy_threshold": 3.1,
            "choch_lookback": 60,
            "min_rr": 1.3,
            "sl_pips_base": 10.0,
            "sweep_tolerance_pips": 3.0,
        })
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(
            strategy_params=StrategyParamsUpdate(min_rr=1.5, sl_pips_base=15.0)
        )
        await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        updated = cfg.strategy_params
        # Changed fields
        assert updated["min_rr"] == 1.5
        assert updated["sl_pips_base"] == 15.0
        # Unchanged fields preserved
        assert updated["entropy_threshold"] == 3.1
        assert updated["choch_lookback"] == 60
        assert updated["sweep_tolerance_pips"] == 3.0

    @pytest.mark.asyncio
    async def test_rejects_invalid_strategy(self):
        cfg = _make_config()
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(strategy="nonexistent")
        with pytest.raises(HTTPException) as exc_info:
            await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        assert exc_info.value.status_code == 422
        assert "strategy" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_invalid_timeframe(self):
        cfg = _make_config()
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(timeframe="W1")
        with pytest.raises(HTTPException) as exc_info:
            await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_invalid_lot_mode(self):
        cfg = _make_config()
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(lot_mode="magic")
        with pytest.raises(HTTPException) as exc_info:
            await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_invalid_symbol(self):
        cfg = _make_config()
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(symbols=["EURUSD", "BTCUSD"])
        with pytest.raises(HTTPException) as exc_info:
            await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        assert exc_info.value.status_code == 422
        assert "BTCUSD" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_404_when_no_config(self):
        none_result = MagicMock()
        none_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute.return_value = none_result

        body = BotConfigUpdateRequest(risk_per_trade=2.0)
        with pytest.raises(HTTPException) as exc_info:
            await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_empty_body_changes_nothing(self, MockAuditRepo):
        """PATCH with no fields should not mutate anything and not restart."""
        MockAuditRepo.return_value.create = AsyncMock()

        cfg = _make_config()
        original_strategy = cfg.strategy
        db = _make_db(cfg)

        body = BotConfigUpdateRequest()  # all None
        result = await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        assert cfg.strategy == original_strategy
        assert result.requires_restart is False

    @pytest.mark.asyncio
    @patch("app.routers.bot.AuditRepository")
    async def test_audit_log_written(self, MockAuditRepo):
        mock_audit = AsyncMock()
        MockAuditRepo.return_value.create = mock_audit

        cfg = _make_config()
        db = _make_db(cfg)

        body = BotConfigUpdateRequest(risk_per_trade=1.5, max_trades_per_hour=5)
        await update_bot_config(request=_make_request(), body=body, db=db, _user={})

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["action"] == "bot_config_update"
        assert "risk_per_trade" in call_kwargs["details"]["changed_fields"]
        assert "max_trades_per_hour" in call_kwargs["details"]["changed_fields"]
