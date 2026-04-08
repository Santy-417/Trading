"""Create ohlcv_bars table for persisted market data

Revision ID: 003_ohlcv_bars
Revises: 002_crash_monitoring
Create Date: 2026-04-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_ohlcv_bars"
down_revision: str | None = "002_crash_monitoring"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ohlcv_bars",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 5), nullable=False),
        sa.Column("high", sa.Numeric(18, 5), nullable=False),
        sa.Column("low", sa.Numeric(18, 5), nullable=False),
        sa.Column("close", sa.Numeric(18, 5), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_ohlcv_symbol_tf_ts"),
    )
    op.create_index("ix_ohlcv_symbol_tf_ts", "ohlcv_bars", ["symbol", "timeframe", "timestamp"])
    op.create_index("ix_ohlcv_symbol_tf", "ohlcv_bars", ["symbol", "timeframe"])


def downgrade() -> None:
    op.drop_index("ix_ohlcv_symbol_tf", table_name="ohlcv_bars")
    op.drop_index("ix_ohlcv_symbol_tf_ts", table_name="ohlcv_bars")
    op.drop_table("ohlcv_bars")
