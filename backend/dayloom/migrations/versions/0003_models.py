import sqlalchemy as sa
from alembic import op

revision = "0003_models"
down_revision = "0002_accounts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_model"),
    )
    op.create_index("ix_model_connections_workspace_id", "model_connections", ["workspace_id"])
    op.create_table(
        "model_usage",
        sa.Column("day", sa.String(10), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("requests", sa.Integer(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Restore a verified backup before removing model connections")
