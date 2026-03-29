#!/bin/bash
# 카카오톡 메시지 전송 빠른 수정

echo "🌸 Memory Garden - 카카오톡 전송 방법 선택"
echo ""
echo "현재 문제: 친구톡은 OAuth 액세스 토큰이 필요합니다"
echo ""
echo "해결 방법을 선택하세요:"
echo ""
echo "1️⃣  알림톡 사용 (권장 - OAuth 불필요)"
echo "   → 템플릿 등록 필요 (1-2일)"
echo "   → 코드 이미 수정 완료"
echo ""
echo "2️⃣  Mock 모드로 테스트 (즉시 가능)"
echo "   → 실제 메시지는 전송 안 됨"
echo "   → 전체 플로우 테스트 가능"
echo ""
echo "3️⃣  OAuth 로그인 구현 (2-3시간 소요)"
echo "   → 친구톡 사용 가능"
echo "   → 가장 정석적인 방법"
echo ""

read -p "선택하세요 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "✅ 알림톡 선택"
        echo ""
        echo "다음 단계:"
        echo "1. 템플릿 등록:"
        echo "   - https://business.kakao.com/ 접속"
        echo "   - 메시지 > 알림톡 관리 > 템플릿 추가"
        echo "   - 템플릿: /tmp/alimtalk_template.txt 참고"
        echo ""
        echo "2. 템플릿 코드 발급 후 (예: MEMORY_GARDEN_DAILY)"
        echo "   tasks/dialogue.py 952라인 확인:"
        echo "   template_code=\"MEMORY_GARDEN_DAILY\""
        echo ""
        echo "3. 서버 재시작 후 테스트"
        echo ""
        ;;
    2)
        echo ""
        echo "✅ Mock 모드 선택"
        echo ""
        # Mock 모드로 변경
        sed -i 's/KAKAO_MOCK_MODE=false/KAKAO_MOCK_MODE=true/' .env
        echo "✅ .env 수정 완료 (KAKAO_MOCK_MODE=true)"
        echo ""
        
        # 서버 재시작
        echo "서버 재시작 중..."
        pkill -f "uvicorn api.main"
        sleep 2
        nohup .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8001 > /tmp/fastapi_server_mock.log 2>&1 &
        sleep 3
        echo "✅ 서버 재시작 완료"
        echo ""
        
        echo "📋 다음 단계:"
        echo "1. 사용자 등록:"
        echo "   .venv/bin/python3.11 register_real_users.py"
        echo ""
        echo "2. 로그 확인:"
        echo "   tail -f /tmp/fastapi_server_mock.log"
        echo ""
        echo "⚠️  참고: Mock 모드에서는 실제 카카오톡 메시지가 전송되지 않습니다"
        echo "   로그에 '✅ [MOCK] Alimtalk sent' 메시지가 표시됩니다"
        echo ""
        ;;
    3)
        echo ""
        echo "✅ OAuth 로그인 선택"
        echo ""
        echo "다음 파일들을 구현해야 합니다:"
        echo "1. api/routes/auth.py - OAuth 로그인/콜백"
        echo "2. database/models.py - User 모델에 access_token 필드 추가"
        echo "3. tasks/dialogue.py - access_token 조회 및 사용"
        echo ""
        echo "예상 소요 시간: 2-3시간"
        echo ""
        ;;
    *)
        echo "잘못된 선택입니다"
        exit 1
        ;;
esac

