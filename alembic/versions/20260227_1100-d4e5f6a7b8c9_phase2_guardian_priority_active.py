"""Phase 2: Guardian.is_active + UserGuardian.priority 컬럼 추가

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-27 11:00:00

변경 내용:
- guardians 테이블: is_active 컬럼 추가 (비활성 보호자 제외 필터링)
- user_guardians 테이블: priority 컬럼 추가 (알림 발송 우선순위)

NOTE: 컬럼 추가에 IF NOT EXISTS 사용 (이미 생성된 경우 대비)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """컬럼 존재 여부 확인"""
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c)"
    ), {"t": table_name, "c": column_name})
    return result.scalar()


# revision identifiers
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ============================================
    # 1. guardians.is_active 컬럼 추가
    # ============================================
    if not _column_exists(conn, 'guardians', 'is_active'):
        op.add_column('guardians',
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False)
        )

    # ============================================
    # 2. user_guardians.priority 컬럼 추가
    # ============================================
    if not _column_exists(conn, 'user_guardians', 'priority'):
        op.add_column('user_guardians',
            sa.Column('priority', sa.Integer(), server_default='0', nullable=False)
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, 'user_guardians', 'priority'):
        op.drop_column('user_guardians', 'priority')

    if _column_exists(conn, 'guardians', 'is_active'):
        op.drop_column('guardians', 'is_active')
