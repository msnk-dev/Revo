"""add token version for revocable refresh sessions"""

from alembic import op
import sqlalchemy as sa

revision = "0002_auth_token_version"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=160), nullable=True))
    op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "token_version")
    op.drop_column("users", "name")

