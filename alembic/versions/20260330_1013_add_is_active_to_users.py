"""Add is_active to users

Revision ID: 20260330_1013
Revises: d4e5f6a7b8c9
Create Date: 2026-03-30 10:13:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_1013"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to users table with default True."""
    # 1. 컬럼 추가 (기존 레코드를 위해 nullable=True, server_default=True)
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=True,
            server_default="true"
        )
    )

    # 2. 기존 레코드 업데이트 (NULL인 경우 True로 설정)
    op.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")

    # 3. NOT NULL 제약조건 설정
    op.alter_column("users", "is_active", nullable=False)


def downgrade() -> None:
    """Remove is_active column from users table."""
    op.drop_column("users", "is_active")
