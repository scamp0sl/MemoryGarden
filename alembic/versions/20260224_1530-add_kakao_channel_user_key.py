"""add kakao_channel_user_key to users table

Revision ID: a1b2c3d4e5f6
Revises: 6da46d0d1818
Create Date: 2026-02-24 15:30:00

카카오 채널 챗봇 사용자 식별을 위한 컬럼 추가.
plusfriendUserKey를 저장하여 채널 챗봇 사용자를 DB와 연결.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = '6da46d0d1818'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('kakao_channel_user_key', sa.String(255), nullable=True, unique=True, index=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'kakao_channel_user_key')
