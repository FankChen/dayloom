import sqlalchemy as sa
from alembic import op

revision = "0006_agents"
down_revision = "0005_automation"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "agent_runs" not in tables:
        op.create_table(
            "agent_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False
            ),
            sa.Column("goal", sa.Text(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("allowed_tools", sa.JSON(), nullable=False),
            sa.Column("model_binding", sa.JSON(), nullable=False),
            sa.Column("allow_external", sa.Integer(), nullable=False),
            sa.Column("auto_readonly", sa.Integer(), nullable=False),
            sa.Column("steps", sa.Integer(), nullable=False),
            sa.Column("max_steps", sa.Integer(), nullable=False),
            sa.Column("expires_at", sa.Float(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("lease_until", sa.Float(), nullable=True),
            sa.Column("claim_token", sa.String(36), nullable=True),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.Column("updated_at", sa.String(40), nullable=False),
        )
        op.create_index("ix_agent_runs_workspace_id", "agent_runs", ["workspace_id"])
        op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    if "agent_steps" not in tables:
        op.create_table(
            "agent_steps",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False
            ),
            sa.Column(
                "agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False
            ),
            sa.Column("ordinal", sa.Integer(), nullable=False),
            sa.Column("decision", sa.String(30), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("action_id", sa.String(36), sa.ForeignKey("actions.id"), nullable=True),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.UniqueConstraint("agent_run_id", "ordinal", name="uq_agent_step_order"),
        )
        op.create_index("ix_agent_steps_workspace_id", "agent_steps", ["workspace_id"])
        op.create_index("ix_agent_steps_agent_run_id", "agent_steps", ["agent_run_id"])
    if "artifacts" not in tables:
        op.create_table(
            "artifacts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False
            ),
            sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("sources", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
        )
        op.create_index("ix_artifacts_workspace_id", "artifacts", ["workspace_id"])
    if "actions" in tables and "agent_run_id" not in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("actions")
    }:
        with op.batch_alter_table("actions") as batch:
            batch.add_column(sa.Column("agent_run_id", sa.String(36), nullable=True))
            batch.create_foreign_key("fk_action_agent_run", "agent_runs", ["agent_run_id"], ["id"])
            batch.create_index("ix_actions_agent_run_id", ["agent_run_id"])


def downgrade():
    raise RuntimeError("Restore a verified backup before removing Agent execution records")
