import sqlalchemy as sa
from alembic import op

revision = "0002_accounts"
down_revision = "0001_workspaces"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("issuer", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("issuer", "subject", name="uq_identity_subject"),
    )
    op.create_table(
        "account_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "identity_id", sa.String(36), sa.ForeignKey("account_identities.id"), nullable=False
        ),
        sa.Column("access_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("refresh_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("access_expires_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("device", sa.String(200), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_account_sessions_identity_id", "account_sessions", ["identity_id"])
    op.create_table(
        "login_flows",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_login_flows_expires_at", "login_flows", ["expires_at"])


def downgrade():
    raise RuntimeError("Restore a verified backup before removing account isolation")
