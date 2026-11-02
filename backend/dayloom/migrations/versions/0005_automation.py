import sqlalchemy as sa
from alembic import op

revision = "0005_automation"
down_revision = "0004_integrations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("tool", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("approved_digest", sa.String(64), nullable=False),
        sa.Column("starts_at", sa.Float(), nullable=False),
        sa.Column("next_run_at", sa.Float(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("max_runs", sa.Integer(), nullable=False),
        sa.Column("runs_created", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_automation_rules_workspace_id", "automation_rules", ["workspace_id"])
    op.create_index("ix_automation_rules_next_run_at", "automation_rules", ["next_run_at"])
    if "actions" in sa.inspect(op.get_bind()).get_table_names():
        with op.batch_alter_table("actions") as batch:
            batch.add_column(sa.Column("automation_id", sa.String(36), nullable=True))
            batch.create_foreign_key(
                "fk_action_automation", "automation_rules", ["automation_id"], ["id"]
            )


def downgrade():
    raise RuntimeError("Restore a verified backup before removing automation authority")
