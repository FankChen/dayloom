import sqlalchemy as sa
from alembic import op

revision = "0001_workspaces"
down_revision = None
branch_labels = None
depends_on = None

LEGACY = "00000000-0000-0000-0000-000000000000"
OWNED = ("tasks", "memories", "messages", "actions", "audit", "calendar_events", "preferences")


def upgrade():
    connection = op.get_bind()
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.execute(
        sa.text(
            "INSERT INTO workspaces (id, name, created_at) VALUES (:id, :name, :created)"
        ).bindparams(id=LEGACY, name="Local workspace", created="2026-10-30T00:00:00+00:00")
    )
    naming = {"pk": "pk_%(table_name)s"}
    existing = set(sa.inspect(connection).get_table_names())
    for table in OWNED:
        if table not in existing:
            continue
        with op.batch_alter_table(table, naming_convention=naming) as batch:
            batch.add_column(
                sa.Column("workspace_id", sa.String(36), nullable=False, server_default=LEGACY)
            )
            batch.create_foreign_key(
                f"fk_{table}_workspace", "workspaces", ["workspace_id"], ["id"]
            )
            if table in {"calendar_events", "preferences"}:
                primary = sa.inspect(connection).get_pk_constraint(table)
                batch.drop_constraint(primary["name"] or f"pk_{table}", type_="primary")
                batch.create_primary_key(
                    f"pk_{table}", [*primary["constrained_columns"], "workspace_id"]
                )
            else:
                batch.create_index(f"ix_{table}_workspace_id", ["workspace_id"])
        with op.batch_alter_table(table) as batch:
            batch.alter_column("workspace_id", server_default=None)


def downgrade():
    raise RuntimeError("Restore a verified backup instead of discarding workspace ownership")
