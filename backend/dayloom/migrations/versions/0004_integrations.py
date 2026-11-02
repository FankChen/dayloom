import sqlalchemy as sa
from alembic import op

revision = "0004_integrations"
down_revision = "0003_models"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_integrations_workspace_id", "integrations", ["workspace_id"])
    op.create_table(
        "integration_usage",
        sa.Column("day", sa.String(10), primary_key=True),
        sa.Column("kind", sa.String(80), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("requests", sa.Integer(), nullable=False),
    )
    if "actions" in sa.inspect(op.get_bind()).get_table_names():
        op.add_column("actions", sa.Column("effect_started_at", sa.Float(), nullable=True))


def downgrade():
    raise RuntimeError("Restore a verified backup before removing external-effect state")
