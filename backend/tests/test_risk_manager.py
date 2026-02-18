import pytest

from app.risk.circuit_breaker import CircuitBreaker
from app.risk.kill_switch import KillSwitch
from app.risk.lot_calculator import LotCalculator
from app.risk.risk_manager import RiskManager


class TestLotCalculator:
    def test_fixed_lot(self):
        assert LotCalculator.fixed_lot(0.05) == 0.05

    def test_percent_risk_basic(self):
        # $10,000 balance, 1% risk, 50 pips SL, $10/pip
        lot = LotCalculator.percent_risk(
            balance=10000, risk_percent=1.0, sl_pips=50, pip_value=10
        )
        # Risk = $100, lot = 100 / (50 * 10) = 0.2
        assert lot == 0.2

    def test_percent_risk_respects_min(self):
        lot = LotCalculator.percent_risk(
            balance=100, risk_percent=0.1, sl_pips=100, pip_value=10, volume_min=0.01
        )
        assert lot >= 0.01

    def test_percent_risk_respects_max(self):
        lot = LotCalculator.percent_risk(
            balance=10_000_000, risk_percent=5.0, sl_pips=1, pip_value=1, volume_max=100.0
        )
        assert lot <= 100.0

    def test_percent_risk_zero_sl(self):
        lot = LotCalculator.percent_risk(
            balance=10000, risk_percent=1.0, sl_pips=0, pip_value=10
        )
        assert lot == 0.01  # Returns volume_min

    def test_dynamic_lot_uses_min_of_balance_equity(self):
        # When in drawdown, equity < balance
        lot_normal = LotCalculator.percent_risk(
            balance=10000, risk_percent=1.0, sl_pips=50, pip_value=10
        )
        lot_dynamic = LotCalculator.dynamic_lot(
            balance=10000, equity=8000, risk_percent=1.0, sl_pips=50, pip_value=10
        )
        assert lot_dynamic < lot_normal


class TestKillSwitch:
    def test_default_state(self):
        ks = KillSwitch()
        assert not ks.is_activated
        allowed, reason = ks.check()
        assert allowed is True
        assert reason is None

    def test_activate(self):
        ks = KillSwitch()
        ks.activate("Test reason")
        assert ks.is_activated
        allowed, reason = ks.check()
        assert allowed is False
        assert "Test reason" in reason

    def test_deactivate(self):
        ks = KillSwitch()
        ks.activate("Test")
        ks.deactivate()
        assert not ks.is_activated
        allowed, _ = ks.check()
        assert allowed is True


class TestCircuitBreaker:
    def test_drawdown_within_limit(self):
        cb = CircuitBreaker()
        cb.max_drawdown_percent = 10.0
        assert cb.check_drawdown(balance=10000, equity=9500) is True

    def test_drawdown_breached(self):
        cb = CircuitBreaker()
        cb.max_drawdown_percent = 10.0
        assert cb.check_drawdown(balance=10000, equity=8900) is False
        assert cb.is_tripped

    def test_daily_loss_within_limit(self):
        cb = CircuitBreaker()
        cb.max_daily_loss_percent = 3.0
        assert cb.check_daily_loss(starting_balance=10000, current_balance=9800) is True

    def test_daily_loss_breached(self):
        cb = CircuitBreaker()
        cb.max_daily_loss_percent = 3.0
        assert cb.check_daily_loss(starting_balance=10000, current_balance=9600) is False
        assert cb.is_tripped

    def test_overtrading_within_limit(self):
        cb = CircuitBreaker()
        cb.max_trades_per_hour = 5
        for _ in range(4):
            cb.record_trade()
        assert cb.check_overtrading() is True

    def test_overtrading_breached(self):
        cb = CircuitBreaker()
        cb.max_trades_per_hour = 5
        for _ in range(5):
            cb.record_trade()
        assert cb.check_overtrading() is False

    def test_reset(self):
        cb = CircuitBreaker()
        cb.max_drawdown_percent = 10.0
        cb.check_drawdown(balance=10000, equity=8000)
        assert cb.is_tripped
        cb.reset()
        assert not cb.is_tripped


class TestRiskManager:
    def test_trade_allowed_when_no_issues(self):
        rm = RiskManager()
        rm.set_starting_balance(10000)
        result = rm.check_trade_allowed(balance=10000, equity=9900)
        assert result.allowed is True

    def test_trade_blocked_by_kill_switch(self):
        rm = RiskManager()
        rm.activate_kill_switch("Test")
        result = rm.check_trade_allowed(balance=10000, equity=9900)
        assert result.allowed is False
        assert "Kill switch" in result.reason

    def test_trade_blocked_by_drawdown(self):
        rm = RiskManager()
        rm.set_starting_balance(10000)
        rm.circuit_breaker.max_drawdown_percent = 5.0
        result = rm.check_trade_allowed(balance=10000, equity=9000)
        assert result.allowed is False

    def test_get_status(self):
        rm = RiskManager()
        rm.set_starting_balance(10000)
        status = rm.get_status()
        assert "kill_switch_active" in status
        assert "circuit_breaker_tripped" in status
        assert status["starting_balance"] == 10000
