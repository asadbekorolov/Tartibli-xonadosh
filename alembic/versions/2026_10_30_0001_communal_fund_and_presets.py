"""communal_fund_and_multi_tenant_presets

Revision ID: 2026_10_30_0001
Revises: None
Create Date: 2026-10-30 12:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_10_30_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ensure Enum types exist
    conn = op.get_bind()
    
    # Template Type Enum
    template_type_enum = postgresql.ENUM(
        "LARGE_FLAT", "COMPACT_FLAT", "DORMITORY", "CUSTOM",
        name="flat_template_type_enum",
        create_type=False
    )
    template_type_enum.create(conn, checkfirst=True)

    # Rotation Type Enum
    rotation_type_enum = postgresql.ENUM(
        "ROUND_ROBIN", "FIXED_DAYS", "PAIR_ROTATION",
        name="rotation_type_enum",
        create_type=False
    )
    rotation_type_enum.create(conn, checkfirst=True)

    # Chore Status Enum
    chore_status_enum = postgresql.ENUM(
        "PENDING", "COMPLETED", "SKIPPED",
        name="chore_status_enum",
        create_type=False
    )
    chore_status_enum.create(conn, checkfirst=True)

    # Flat Role Enum
    flat_role_enum = postgresql.ENUM(
        "ADMIN", "MEMBER",
        name="flat_role_enum",
        create_type=False
    )
    flat_role_enum.create(conn, checkfirst=True)

    # Transaction Type Enum
    transaction_type_enum = postgresql.ENUM(
        "INCOME", "EXPENSE",
        name="transaction_type_enum",
        create_type=False
    )
    transaction_type_enum.create(conn, checkfirst=True)

    # 2. Users Table
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False, if_not_exists=True)

    # 3. Flats Table
    op.create_table(
        "flats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("invite_code", sa.String(length=32), nullable=False),
        sa.Column("created_by_id", sa.BigInteger(), nullable=False),
        sa.Column("max_members", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "template_type",
            sa.Enum("LARGE_FLAT", "COMPACT_FLAT", "DORMITORY", "CUSTOM", name="flat_template_type_enum"),
            server_default="LARGE_FLAT",
            nullable=False
        ),
        sa.Column("fund_balance", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=5), server_default="22:30", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_flats_invite_code"), "flats", ["invite_code"], unique=True, if_not_exists=True)

    # 4. Flat Members Table
    op.create_table(
        "flat_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "MEMBER", name="flat_role_enum"), server_default="MEMBER", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flat_id", "user_id", name="uq_flat_member"),
        if_not_exists=True,
    )

    # 5. Chores Table
    op.create_table(
        "chores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flat_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "rotation_type",
            sa.Enum("ROUND_ROBIN", "FIXED_DAYS", "PAIR_ROTATION", name="rotation_type_enum"),
            server_default="ROUND_ROBIN",
            nullable=False
        ),
        sa.Column("frequency_days", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("execution_time", sa.String(length=5), server_default="20:00", nullable=False),
        sa.Column("current_member_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=True),
        sa.Column("assignee_ids", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    # 6. Chore Assignments Table
    op.create_table(
        "chore_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chore_id", sa.Integer(), nullable=False),
        sa.Column("flat_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.BigInteger(), nullable=True),
        sa.Column("assignee_ids", sa.JSON(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "COMPLETED", "SKIPPED", name="chore_status_enum"), server_default="PENDING", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["chore_id"], ["chores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_chore_assignments_due_date"), "chore_assignments", ["due_date"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_chore_assignments_status"), "chore_assignments", ["status"], unique=False, if_not_exists=True)

    # 7. Fund Transactions Table
    op.create_table(
        "fund_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("flat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tx_type", sa.Enum("INCOME", "EXPENSE", name="transaction_type_enum"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_fund_transactions_created_at"), "fund_transactions", ["created_at"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_fund_transactions_flat_id"), "fund_transactions", ["flat_id"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_fund_transactions_user_id"), "fund_transactions", ["user_id"], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_table("fund_transactions", if_exists=True)
    op.drop_table("chore_assignments", if_exists=True)
    op.drop_table("chores", if_exists=True)
    op.drop_table("flat_members", if_exists=True)
    op.drop_table("flats", if_exists=True)
    op.drop_table("users", if_exists=True)

