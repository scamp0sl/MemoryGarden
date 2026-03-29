"""Phase 1: Guardian, GardenStatus, MemoryEvent, Notification 테이블 추가 + User 온보딩 컬럼

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-27 10:00:00

변경 내용:
- users 테이블: garden_name, onboarding_day, last_interaction_at 컬럼 추가
- guardians 테이블 신규 생성 (SPEC §4.1.2) - IF NOT EXISTS
- user_guardians 테이블 신규 생성 (사용자-보호자 M:N) - IF NOT EXISTS
- notifications 테이블 신규 생성 (알림 이력) - IF NOT EXISTS
- memory_events 테이블 신규 생성 (모순 탐지 이력) - IF NOT EXISTS
- garden_status 테이블 신규 생성 (게이미피케이션) - IF NOT EXISTS

NOTE: 테이블 생성에 IF NOT EXISTS 사용 (이미 생성된 경우 대비)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text, inspect


def _table_exists(conn, table_name: str) -> bool:
    """테이블 존재 여부 확인"""
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=:t)"
    ), {"t": table_name})
    return result.scalar()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """컬럼 존재 여부 확인"""
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c)"
    ), {"t": table_name, "c": column_name})
    return result.scalar()


# revision identifiers
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ============================================
    # 1. users 테이블 컬럼 추가 (없는 경우에만)
    # ============================================
    if not _column_exists(conn, 'users', 'garden_name'):
        op.add_column('users',
            sa.Column('garden_name', sa.String(100), nullable=True)
        )

    if not _column_exists(conn, 'users', 'onboarding_day'):
        op.add_column('users',
            sa.Column('onboarding_day', sa.Integer(), nullable=False, server_default='0')
        )

    if not _column_exists(conn, 'users', 'last_interaction_at'):
        op.add_column('users',
            sa.Column('last_interaction_at', sa.DateTime(), nullable=True)
        )

    # ============================================
    # 2. guardians 테이블 생성 (없는 경우에만)
    # ============================================
    if not _table_exists(conn, 'guardians'):
        op.create_table(
            'guardians',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text('gen_random_uuid()')),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('phone', sa.String(20), nullable=True),
            sa.Column('email', sa.String(100), nullable=True),
            sa.Column('kakao_id', sa.String(100), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        )
        op.create_index('idx_guardians_phone', 'guardians', ['phone'])
        op.create_index('idx_guardians_email', 'guardians', ['email'])

    # ============================================
    # 3. user_guardians 테이블 생성 (없는 경우에만)
    # ============================================
    if not _table_exists(conn, 'user_guardians'):
        op.create_table(
            'user_guardians',
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('guardian_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('guardians.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('relation', sa.String(50), nullable=True),
            sa.Column('notification_enabled', sa.Boolean(), server_default='true'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        )
        op.create_index('idx_user_guardians_user', 'user_guardians', ['user_id'])
        op.create_index('idx_user_guardians_guardian', 'user_guardians', ['guardian_id'])

    # ============================================
    # 4. notifications 테이블 생성 (없는 경우에만)
    # ============================================
    if not _table_exists(conn, 'notifications'):
        op.create_table(
            'notifications',
            sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column('guardian_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('guardians.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('risk_level', sa.String(20), nullable=True),
            sa.Column('analysis_snapshot', postgresql.JSONB(), nullable=True),
            sa.Column('sent_at', sa.DateTime(), server_default=sa.text('NOW()')),
            sa.Column('read_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_notifications_guardian_sent', 'notifications', ['guardian_id', 'sent_at'])
        op.create_index('idx_notifications_user_sent', 'notifications', ['user_id', 'sent_at'])

    # ============================================
    # 5. memory_events 테이블 생성 (없는 경우에만)
    # ============================================
    if not _table_exists(conn, 'memory_events'):
        op.create_table(
            'memory_events',
            sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('event_type', sa.String(50), nullable=False),
            sa.Column('entity', sa.String(100), nullable=True),
            sa.Column('old_value', sa.Text(), nullable=True),
            sa.Column('new_value', sa.Text(), nullable=True),
            sa.Column('severity', sa.String(20), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('conversation_id', sa.BigInteger(),
                      sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        )
        op.create_index('idx_memory_events_user_type', 'memory_events', ['user_id', 'event_type'])
        op.create_index('idx_memory_events_severity', 'memory_events', ['severity'])

    # ============================================
    # 6. garden_status 테이블 생성 (없는 경우에만)
    # ============================================
    if not _table_exists(conn, 'garden_status'):
        op.create_table(
            'garden_status',
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('flower_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('butterfly_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('consecutive_days', sa.Integer(), server_default='0', nullable=False),
            sa.Column('total_conversations', sa.Integer(), server_default='0', nullable=False),
            sa.Column('garden_level', sa.Integer(), server_default='1', nullable=False),
            sa.Column('last_interaction_at', sa.DateTime(), nullable=True),
            sa.Column('season_badge', sa.String(50), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()')),
        )
    else:
        # 테이블이 이미 존재할 경우 누락된 컬럼 추가
        if not _column_exists(conn, 'garden_status', 'garden_level'):
            op.add_column('garden_status',
                sa.Column('garden_level', sa.Integer(), server_default='1', nullable=False)
            )


def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, 'garden_status'):
        op.drop_table('garden_status')

    if _table_exists(conn, 'memory_events'):
        op.drop_index('idx_memory_events_severity', 'memory_events')
        op.drop_index('idx_memory_events_user_type', 'memory_events')
        op.drop_table('memory_events')

    if _table_exists(conn, 'notifications'):
        op.drop_index('idx_notifications_user_sent', 'notifications')
        op.drop_index('idx_notifications_guardian_sent', 'notifications')
        op.drop_table('notifications')

    if _table_exists(conn, 'user_guardians'):
        op.drop_index('idx_user_guardians_guardian', 'user_guardians')
        op.drop_index('idx_user_guardians_user', 'user_guardians')
        op.drop_table('user_guardians')

    if _table_exists(conn, 'guardians'):
        op.drop_index('idx_guardians_email', 'guardians')
        op.drop_index('idx_guardians_phone', 'guardians')
        op.drop_table('guardians')

    if _column_exists(conn, 'users', 'last_interaction_at'):
        op.drop_column('users', 'last_interaction_at')
    if _column_exists(conn, 'users', 'onboarding_day'):
        op.drop_column('users', 'onboarding_day')
    if _column_exists(conn, 'users', 'garden_name'):
        op.drop_column('users', 'garden_name')
