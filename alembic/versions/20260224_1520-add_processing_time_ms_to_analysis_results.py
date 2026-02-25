"""add processing_time_ms to analysis_results table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-24 15:20:00

analysis_results 테이블에 processing_time_ms 컬럼 추가.
MCDI 분석 처리 시간 기록용.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'analysis_results',
        sa.Column('processing_time_ms', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('analysis_results', 'processing_time_ms')
