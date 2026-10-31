"""Store invoice line variant and discount snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0004_invoice_line_snapshots"
down_revision = "0003_subscription_number_sequence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoice_lines", sa.Column("variant_extra", sa.Numeric(12, 2), nullable=False, server_default="0.00"))
    op.add_column("invoice_lines", sa.Column("discount_name", sa.String(160), nullable=True))
    op.add_column("invoice_lines", sa.Column("discount_reason", sa.String(240), nullable=True))


def downgrade() -> None:
    op.drop_column("invoice_lines", "discount_reason")
    op.drop_column("invoice_lines", "discount_name")
    op.drop_column("invoice_lines", "variant_extra")
