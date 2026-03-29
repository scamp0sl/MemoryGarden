#!/bin/bash
# 실제 카카오톡 테스트 시작 스크립트

echo "🌸 Memory Garden - 실제 카카오톡 테스트 시작"
echo ""

# 1. 현재 설정 확인
echo "1️⃣ 현재 설정 확인"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "카카오 REST API Key: $(grep KAKAO_REST_API_KEY .env | tail -1 | cut -d= -f2)"
echo "카카오 Admin Key: $(grep KAKAO_ADMIN_KEY .env | tail -1 | cut -d= -f2)"
echo "Mock Mode: $(grep KAKAO_MOCK_MODE .env | cut -d= -f2)"
echo ""

# 2. 기존 서버 종료
echo "2️⃣ 기존 서버 종료 중..."
pkill -f "uvicorn api.main" 2>/dev/null
sleep 2
echo "✅ 서버 종료 완료"
echo ""

# 3. 서버 시작
echo "3️⃣ 서버 시작 중..."
nohup .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8001 > /tmp/fastapi_server_real.log 2>&1 &
SERVER_PID=$!
sleep 5

# 서버 확인
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ 서버 시작 완료 (PID: $SERVER_PID)"
else
    echo "❌ 서버 시작 실패"
    echo "로그 확인: tail -50 /tmp/fastapi_server_real.log"
    exit 1
fi
echo ""

# 4. 헬스 체크
echo "4️⃣ 서버 헬스 체크..."
sleep 2
curl -s http://localhost:8001/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 서버 정상 작동"
else
    echo "❌ 서버 응답 없음"
    exit 1
fi
echo ""

# 5. 다음 단계 안내
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 준비 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 다음 단계:"
echo "1. 사용자 정보 입력:"
echo "   nano register_real_users.py"
echo "   (REAL_USERS 섹션에 2명의 정보 입력)"
echo ""
echo "2. 사용자 등록 실행:"
echo "   .venv/bin/python3.11 register_real_users.py"
echo ""
echo "3. 로그 모니터링:"
echo "   tail -f /tmp/fastapi_server_real.log"
echo ""

