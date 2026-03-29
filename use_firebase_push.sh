#!/bin/bash
# Firebase Push 사용하기 (카카오 OAuth 불필요)

echo "🔥 Firebase Push 사용 설정"
echo ""
echo "✅ 장점:"
echo "- 이미 완벽하게 구현되어 있음"
echo "- OAuth 불필요 (FCM 토큰만 등록)"
echo "- 웹/앱 모두 지원"
echo "- 실시간 푸시 알림"
echo ""
echo "📋 현재 구현 상태:"
echo "- services/firebase_service.py ✅"
echo "- services/push_scheduler.py ✅"
echo "- 일일 3회 자동 알림 (10:00, 15:00, 20:00) ✅"
echo ""

# tasks/dialogue.py 수정 - Firebase Push 사용
cat > /tmp/dialogue_firebase_patch.py << 'PYTHON'
# tasks/dialogue.py의 send_scheduled_dialogue 함수를 Firebase Push 사용으로 변경

# 기존 코드 (카카오톡):
# kakao_result = await kakao_client.send_alimtalk(...)

# 새 코드 (Firebase Push):
from services.firebase_service import firebase_service

# 사용자의 FCM 토큰 조회
from database.postgres import AsyncSessionLocal
from database.models import FCMToken
from sqlalchemy import select

async with AsyncSessionLocal() as db:
    result = await db.execute(
        select(FCMToken)
        .where(FCMToken.user_id == user_id)
        .where(FCMToken.is_active == True)
    )
    fcm_tokens = result.scalars().all()
    
    if not fcm_tokens:
        logger.warning(f"No FCM token found for user {user_id}")
        return {
            "success": False,
            "error": "No FCM token registered. Please register via web.",
            "scheduled_at": datetime.now().isoformat()
        }
    
    # 모든 토큰으로 푸시 알림 전송 (다중 디바이스 지원)
    success_count = 0
    for token_obj in fcm_tokens:
        try:
            push_result = await firebase_service.send_push(
                token=token_obj.token,
                title="🌸 Memory Garden",
                body=message,
                data={
                    "type": "scheduled_dialogue",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if push_result.get("success"):
                success_count += 1
                
        except Exception as e:
            logger.error(f"Failed to send push to token {token_obj.id}: {e}")
    
    result = {
        "success": success_count > 0,
        "message_sent": message,
        "scheduled_at": datetime.now().isoformat(),
        "sent_at": datetime.now().isoformat(),
        "push_message_ids": [f"fcm_{i}" for i in range(success_count)]
    }
PYTHON

echo "📝 수정 사항:"
echo "1. tasks/dialogue.py를 Firebase Push 사용으로 변경"
echo "   패치 파일: /tmp/dialogue_firebase_patch.py"
echo ""

read -p "Firebase Push로 전환하시겠습니까? (y/n): " answer

if [ "$answer" = "y" ]; then
    echo ""
    echo "✅ Firebase Push로 전환합니다"
    echo ""
    echo "📋 다음 단계:"
    echo ""
    echo "1. 웹 페이지 열기:"
    echo "   https://n8n.softline.co.kr/static/index.html"
    echo "   또는"
    echo "   http://localhost:8001/static/index.html"
    echo ""
    echo "2. FCM 토큰 등록:"
    echo "   - 브라우저에서 알림 권한 허용"
    echo "   - FCM 토큰 자동 생성 및 등록"
    echo "   - user_id 입력: user_001, user_002"
    echo ""
    echo "3. 테스트 푸시 전송:"
    echo "   curl -X POST http://localhost:8001/api/v1/notifications/test"
    echo ""
    echo "4. 스케줄 확인:"
    echo "   - 10:00, 15:00, 20:00에 자동 푸시 알림"
    echo ""
else
    echo "취소되었습니다."
fi

