"""enable row level security policies

Revision ID: 20260316_0003
Revises: 20260316_0002
Create Date: 2026-03-16 00:30:00
"""

from __future__ import annotations

from alembic import op


revision = "20260316_0003"
down_revision = "20260316_0002"
branch_labels = None
depends_on = None


TABLES = [
    "projects",
    "chapters",
    "chapter_versions",
    "requirements",
    "runs",
    "run_artifacts",
    "memories",
    "characters",
    "memory_deltas",
    "merge_decisions",
]


def _policy_sql(table: str) -> str:
    return f"""
    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};

    CREATE POLICY tenant_isolation_{table}
      ON {table}
      FOR ALL
      USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
      WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """


def upgrade() -> None:
    for table in TABLES:
        op.execute(_policy_sql(table))


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
