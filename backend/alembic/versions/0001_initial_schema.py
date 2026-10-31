"""create the initial Revo schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.models import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("agent", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("plan", postgresql.JSONB(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=160)),
        sa.Column("provider", sa.String(length=40)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("tokens_in", sa.Integer()),
        sa.Column("tokens_out", sa.Integer()),
        sa.Column("status", sa.String(length=24), nullable=False),
    )
    op.create_index("ix_ai_runs_created_at", "ai_runs", ["created_at"])
    op.create_table(
        "briefs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("brief_date", sa.Date(), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=160)),
        sa.Column("provider", sa.String(length=40)),
        sa.Column("used_fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("briefs")
    op.drop_index("ix_ai_runs_created_at", table_name="ai_runs")
    op.drop_table("ai_runs")
    Base.metadata.drop_all(bind=op.get_bind())

