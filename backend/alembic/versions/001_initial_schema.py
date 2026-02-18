"""Initial schema - all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-02-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- trades ---
    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("lot_size", sa.Numeric(10, 4), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(18, 8), nullable=True),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("profit", sa.Numeric(18, 4), nullable=True),
        sa.Column("commission", sa.Numeric(10, 4), server_default=sa.text("0")),
        sa.Column("swap", sa.Numeric(10, 4), server_default=sa.text("0")),
        sa.Column("strategy", sa.String(50), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("mt5_ticket", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trades_symbol", "trades", ["symbol"])
    op.create_index("ix_trades_status", "trades", ["status"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])
    op.create_index("ix_trades_strategy", "trades", ["strategy"])

    # --- bot_config ---
    op.create_table(
        "bot_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), server_default=sa.text("'default'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("strategy", sa.String(50), nullable=False, server_default=sa.text("'fibonacci'")),
        sa.Column("symbols", postgresql.ARRAY(sa.String()), server_default=sa.text("ARRAY['EURUSD','XAUUSD']")),
        sa.Column("timeframe", sa.String(10), server_default=sa.text("'H1'")),
        sa.Column("risk_per_trade", sa.Numeric(5, 2), server_default=sa.text("1.0")),
        sa.Column("lot_mode", sa.String(20), server_default=sa.text("'percent_risk'")),
        sa.Column("fixed_lot", sa.Numeric(10, 4), server_default=sa.text("0.01")),
        sa.Column("max_trades_per_hour", sa.Integer(), server_default=sa.text("10")),
        sa.Column("strategy_params", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- risk_events ---
    op.create_table(
        "risk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default=sa.text("'warning'")),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("current_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("threshold_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("action_taken", sa.String(50), server_default=sa.text("'none'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_events_type", "risk_events", ["event_type"])
    op.create_index("ix_risk_events_severity", "risk_events", ["severity"])
    op.create_index("ix_risk_events_created", "risk_events", ["created_at"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(50), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])

    # --- strategies ---
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("parameters", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("supported_symbols", postgresql.JSONB(), nullable=True),
        sa.Column("supported_timeframes", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- backtest_results ---
    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("total_trades", sa.Integer(), server_default=sa.text("0")),
        sa.Column("win_rate", sa.Numeric(6, 2), server_default=sa.text("0")),
        sa.Column("net_profit", sa.Numeric(18, 2), server_default=sa.text("0")),
        sa.Column("profit_factor", sa.Numeric(8, 2), server_default=sa.text("0")),
        sa.Column("sharpe_ratio", sa.Numeric(8, 2), server_default=sa.text("0")),
        sa.Column("max_drawdown_percent", sa.Numeric(6, 2), server_default=sa.text("0")),
        sa.Column("initial_balance", sa.Numeric(18, 2), server_default=sa.text("10000")),
        sa.Column("final_balance", sa.Numeric(18, 2), server_default=sa.text("0")),
        sa.Column("params", postgresql.JSONB(), nullable=True),
        sa.Column("full_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- ml_models ---
    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_id", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("feature_importance", postgresql.JSONB(), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ml_models")
    op.drop_table("backtest_results")
    op.drop_table("strategies")
    op.drop_table("audit_logs")
    op.drop_table("risk_events")
    op.drop_table("bot_config")
    op.drop_table("trades")
