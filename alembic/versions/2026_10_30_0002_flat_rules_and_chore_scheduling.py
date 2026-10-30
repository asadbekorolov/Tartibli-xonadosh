"""flat_rules_and_chore_scheduling

Revision ID: 2026_10_30_0002
Revises: 2026_10_30_0001
Create Date: 2026-10-30 13:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_10_30_0002"
down_revision: Union[str, None] = "2026_10_30_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Chore Frequency Type Enum
    chore_freq_enum = postgresql.ENUM(
        "DAILY", "WEEKLY", "CUSTOM",
        name="chore_frequency_type_enum",
        create_type=False
    )
    chore_freq_enum.create(conn, checkfirst=True)

    # 2. Add columns to chores table
    op.add_column(
        "chores",
        sa.Column(
            "frequency_type",
            sa.Enum("DAILY", "WEEKLY", "CUSTOM", name="chore_frequency_type_enum"),
            server_default="DAILY",
            nullable=False
        )
    )
    op.add_column("chores", sa.Column("assigned_weekdays", sa.JSON(), nullable=True))
    op.add_column("chores", sa.Column("assigned_pairs", sa.JSON(), nullable=True))

    # 3. Create flat_rules table
    op.create_table(
        "flat_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flat_id", sa.Integer(), nullable=False),
        sa.Column("order_num", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_flat_rules_flat_id"), "flat_rules", ["flat_id"], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_flat_rules_flat_id"), table_name="flat_rules", if_exists=True)
    op.drop_table("flat_rules", if_exists=True)
    op.drop_column("chores", "assigned_pairs")
    op.drop_column("chores", "assigned_weekdays")
    op.drop_column("chores", "frequency_type")
