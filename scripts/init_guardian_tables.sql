-- ============================================
-- 보호자 관련 테이블 생성 스크립트
-- ============================================

-- 1. guardians 테이블
CREATE TABLE IF NOT EXISTS guardians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255),
    relationship VARCHAR(50),  -- 아들, 딸, 배우자, 기타
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE guardians IS '보호자 정보';
COMMENT ON COLUMN guardians.id IS '보호자 고유 ID';
COMMENT ON COLUMN guardians.name IS '보호자 이름';
COMMENT ON COLUMN guardians.phone IS '보호자 전화번호 (010-XXXX-XXXX)';
COMMENT ON COLUMN guardians.email IS '보호자 이메일 (선택)';
COMMENT ON COLUMN guardians.relationship IS '사용자와의 관계';
COMMENT ON COLUMN guardians.is_active IS '활성 상태';

-- 2. user_guardians 테이블 (사용자-보호자 연결)
CREATE TABLE IF NOT EXISTS user_guardians (
    user_id VARCHAR(50) NOT NULL,
    guardian_id UUID NOT NULL,
    priority INT DEFAULT 1,  -- 우선순위 (1이 가장 높음)
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, guardian_id),
    FOREIGN KEY (guardian_id) REFERENCES guardians(id) ON DELETE CASCADE
);

COMMENT ON TABLE user_guardians IS '사용자-보호자 연결 테이블';
COMMENT ON COLUMN user_guardians.user_id IS '사용자 ID';
COMMENT ON COLUMN user_guardians.guardian_id IS '보호자 ID';
COMMENT ON COLUMN user_guardians.priority IS '알림 우선순위 (1=최우선)';

-- 3. notification_logs 테이블 (알림 전송 로그)
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    guardian_id UUID NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    message_id VARCHAR(255),  -- 카카오톡 메시지 ID
    error TEXT,  -- 에러 메시지 (실패 시)
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (guardian_id) REFERENCES guardians(id) ON DELETE CASCADE
);

COMMENT ON TABLE notification_logs IS '알림 전송 로그';
COMMENT ON COLUMN notification_logs.user_id IS '사용자 ID';
COMMENT ON COLUMN notification_logs.guardian_id IS '보호자 ID';
COMMENT ON COLUMN notification_logs.risk_level IS '위험도 레벨';
COMMENT ON COLUMN notification_logs.message_id IS '카카오톡 메시지 ID';
COMMENT ON COLUMN notification_logs.error IS '에러 메시지 (실패 시)';
COMMENT ON COLUMN notification_logs.success IS '전송 성공 여부';

-- ============================================
-- 인덱스 생성
-- ============================================

-- guardians 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_guardians_phone ON guardians(phone);
CREATE INDEX IF NOT EXISTS idx_guardians_active ON guardians(is_active);

-- user_guardians 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_user_guardians_user ON user_guardians(user_id);
CREATE INDEX IF NOT EXISTS idx_user_guardians_guardian ON user_guardians(guardian_id);
CREATE INDEX IF NOT EXISTS idx_user_guardians_priority ON user_guardians(user_id, priority);

-- notification_logs 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_notification_logs_user ON notification_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_guardian ON notification_logs(guardian_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_success ON notification_logs(success, created_at DESC);

-- ============================================
-- 샘플 데이터 삽입 (테스트용)
-- ============================================

-- 샘플 보호자 1
INSERT INTO guardians (id, name, phone, email, relationship)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    '홍길동',
    '010-1234-5678',
    'hong@example.com',
    '아들'
) ON CONFLICT (phone) DO NOTHING;

-- 샘플 보호자 2
INSERT INTO guardians (id, name, phone, email, relationship)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '김영희',
    '010-9876-5432',
    'kim@example.com',
    '딸'
) ON CONFLICT (phone) DO NOTHING;

-- 테스트 사용자와 보호자 연결
INSERT INTO user_guardians (user_id, guardian_id, priority)
VALUES (
    'test_user',
    '00000000-0000-0000-0000-000000000001',
    1
) ON CONFLICT (user_id, guardian_id) DO NOTHING;

-- ============================================
-- 완료 메시지
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ Guardian tables created successfully';
    RAISE NOTICE '✅ Indexes created';
    RAISE NOTICE '✅ Sample data inserted';
END $$;
