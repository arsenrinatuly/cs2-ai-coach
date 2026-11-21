"""Add durable worker retry state."""

import sqlalchemy as sa
from alembic import op

revision = "2d6369ad4f80"
down_revision = "0395a64b70c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "matches",
        sa.Column(
            "next_attempt_at", sa.BigInteger(), server_default="0", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("matches", "next_attempt_at")
    op.drop_column("matches", "attempts")
