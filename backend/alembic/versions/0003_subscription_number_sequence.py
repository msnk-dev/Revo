"""Add the database sequence used for subscription numbers."""

from alembic import op

revision = "0003_subscription_seq"
down_revision = "0002_auth_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE subscription_number_seq START WITH 1 INCREMENT BY 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE subscription_number_seq")
