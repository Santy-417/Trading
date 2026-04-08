"""Add crash monitoring fields to bot_config

Revision ID: 002_crash_monitoring
Revises: 001_initial
Create Date: 2026-04-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_crash_monitoring"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bot_config",
        sa.Column("error_state", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "bot_config",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "bot_config",
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bot_config",
        sa.Column("crash_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("bot_config", "crash_count")
    op.drop_column("bot_config", "last_heartbeat")
    op.drop_column("bot_config", "last_error")
    op.drop_column("bot_config", "error_state")
