# 📱 카카오톡 채널 테스트 가이드

Memory Garden 프로젝트의 카카오톡 채널 통합 테스트 방법을 안내합니다.

---

## 📋 목차

1. [테스트 환경 설정](#1-테스트-환경-설정)
2. [Mock 모드 테스트](#2-mock-모드-테스트)
3. [실제 API 테스트](#3-실제-api-테스트)
4. [E2E 시나리오 테스트](#4-e2e-시나리오-테스트)
5. [통합 테스트](#5-통합-테스트)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. 테스트 환경 설정

### 1.1 환경 변수 설정

`.env` 파일에 다음 항목을 추가하세요:

```bash
# 카카오톡 설정
KAKAO_REST_API_KEY=your_rest_api_key_here
KAKAO_ADMIN_KEY=your_admin_key_here
KAKAO_CHANNEL_ID=your_channel_id_here
```

### 1.2 카카오 개발자 콘솔 설정

1. [카카오 개발자 콘솔](https://developers.kakao.com/) 접속
2. 애플리케이션 생성 또는 선택
3. **내 애플리케이션 > 앱 키** 에서 REST API 키 복사
4. **도구 > 알림톡 관리** 에서 발신 프로필 등록
5. 템플릿 등록:
   - `MEMORY_GARDEN_ALERT`: 위험 알림
   - `MEMORY_GARDEN_DAILY`: 일상 대화
   - `MEMORY_GARDEN_WEEKLY`: 주간 리포트
   - `MEMORY_GARDEN_IMAGE`: 이미지 분석 결과

---

## 2. Mock 모드 테스트

**실제 메시지를 보내지 않고** 로직만 테스트합니다.

### 2.1 단일 메시지 전송 테스트

```python
from services.kakao_client import KakaoClient

client = KakaoClient(mock_mode=True)

result = await client.send_alimtalk(
    phone="010-1234-5678",
    template_code="MEMORY_GARDEN_DAILY",
    variables={
        "user_name": "홍길동",
        "question": "오늘 아침은 무엇을 드셨나요?",
        "garden_status": "건강함 🌳"
    }
)

print(result)
# {'success': True, 'message_id': 'mock_...', ...}
```

### 2.2 pytest 실행

```bash
# 모든 Mock 테스트 실행
pytest tests/integration/test_kakao_integration.py -v

# 특정 테스트만
pytest tests/integration/test_kakao_integration.py::test_kakao_mock_mode -v
```

---

## 3. 실제 API 테스트

⚠️ **주의**: 실제 카카오톡 메시지가 전송됩니다!

### 3.1 준비사항

1. `.env` 파일에 실제 API 키 설정
2. 테스트용 전화번호 준비 (본인 또는 테스트 계정)
3. 카카오 채널에서 템플릿 승인 완료 확인

### 3.2 실행

```bash
# 실제 API 테스트 (주의!)
pytest tests/integration/test_kakao_integration.py::test_kakao_real_mode -v -m real_kakao
```

### 3.3 테스트 전화번호 변경

`tests/integration/test_kakao_integration.py` 파일에서:

```python
# TODO: 실제 테스트 전화번호로 변경
test_phone = "010-0000-0000"  # ⚠️ 반드시 변경!
```

---

## 4. E2E 시나리오 테스트

전체 사용자 시나리오를 시뮬레이션합니다.

### 4.1 실행

```bash
# E2E 테스트 스크립트 실행
python scripts/test_kakao_e2e.py
```

### 4.2 시나리오 목록

1. **일상 대화 알림**: 사용자에게 질문 전송
2. **위험 알림**: 보호자에게 위험도 알림
3. **주간 리포트**: 주간 분석 요약
4. **이미지 분석 결과**: 식사/장소 분석 완료 알림
5. **다중 사용자**: 여러 사용자에게 동시 전송

### 4.3 출력 예시

```
============================================================
📱 시나리오 1: 일상 대화 알림
============================================================
✅ 메시지 전송 성공
   - Message ID: mock_257a292ba60d
   - 수신자: 010-1234-5678
   - 시간: 2026-02-20T09:48:35
```

---

## 5. 통합 테스트

### 5.1 전체 워크플로우 테스트

```bash
# 대화 → 분석 → 알림 전체 플로우
pytest tests/integration/test_kakao_integration.py::test_full_conversation_workflow_with_kakao -v
```

### 5.2 성능 테스트

```bash
# 100개 메시지 동시 전송
pytest tests/integration/test_kakao_integration.py::test_kakao_concurrent_messages -v
```

---

## 6. 테스트 시나리오별 템플릿

### 6.1 일상 대화 (MEMORY_GARDEN_DAILY)

```python
{
    "user_name": "홍길동",
    "question": "오늘 점심은 무엇을 드셨나요?",
    "garden_status": "건강하게 자라고 있어요 🌳"
}
```

### 6.2 위험 알림 (MEMORY_GARDEN_ALERT)

```python
{
    "urgency": "즉시 확인 필요",
    "user_name": "홍길동",
    "risk_level": "ORANGE",
    "mcdi_score": "58.5",
    "recommendation": "전문의 상담을 권장합니다."
}
```

### 6.3 주간 리포트 (MEMORY_GARDEN_WEEKLY)

```python
{
    "user_name": "홍길동",
    "week_range": "2월 10일 ~ 2월 16일",
    "avg_mcdi": "78.5",
    "conversation_count": "14",
    "garden_growth": "정원이 건강하게 자라고 있어요!",
    "highlight": "이번 주는 특히 일화 기억(ER) 점수가 우수했습니다."
}
```

### 6.4 이미지 분석 (MEMORY_GARDEN_IMAGE)

```python
{
    "user_name": "홍길동",
    "analysis_type": "식사",
    "detected_items": "김치찌개, 밥, 계란후라이",
    "feedback": "영양 균형이 좋습니다!"
}
```

---

## 7. 트러블슈팅

### 7.1 "KAKAO_REST_API_KEY not configured"

**원인**: 환경 변수가 설정되지 않음

**해결**:
```bash
# .env 파일 확인
grep KAKAO .env

# 값이 비어있으면 설정
KAKAO_REST_API_KEY=your_key_here
```

### 7.2 "Template not found"

**원인**: 카카오 채널에 템플릿이 등록되지 않음

**해결**:
1. [카카오 비즈니스](https://business.kakao.com/) 접속
2. 알림톡 관리 > 템플릿 관리
3. 필요한 템플릿 등록 및 승인 요청

### 7.3 "Invalid phone number format"

**원인**: 전화번호 형식이 잘못됨

**해결**:
```python
# 올바른 형식
"010-1234-5678"  # ✅
"01012345678"    # ❌
"010 1234 5678"  # ❌
```

### 7.4 Mock 모드에서 실제 전송되지 않음

**정상 동작**: Mock 모드는 실제 전송 없이 로직만 테스트합니다.

**실제 전송을 원하면**:
```python
client = KakaoClient(
    api_key=settings.KAKAO_REST_API_KEY,
    sender_key=settings.KAKAO_CHANNEL_ID,
    mock_mode=False  # 실제 모드
)
```

---

## 8. 빠른 명령어 참조

```bash
# Mock 테스트 (안전)
pytest tests/integration/test_kakao_integration.py -v

# E2E 시나리오 실행
python scripts/test_kakao_e2e.py

# 실제 API 테스트 (주의!)
pytest tests/integration/test_kakao_integration.py -v -m real_kakao

# 성능 테스트
pytest tests/integration/test_kakao_integration.py::test_kakao_concurrent_messages -v

# 전체 워크플로우
pytest tests/integration/test_kakao_integration.py::test_full_conversation_workflow_with_kakao -v
```

---

## 9. 체크리스트

테스트 전 확인사항:

- [ ] `.env` 파일에 카카오 API 키 설정
- [ ] 카카오 채널 생성 및 승인 완료
- [ ] 필요한 템플릿 등록 및 승인
- [ ] 테스트용 전화번호 준비
- [ ] Docker Compose 서비스 실행 중 (`postgres`, `redis`, `qdrant`)
- [ ] Python 가상환경 활성화

---

## 📞 문의

문제가 발생하면 다음을 확인하세요:

1. 로그 파일: `logs/app.log`
2. 카카오 개발자 콘솔 로그
3. 템플릿 승인 상태

Happy Testing! 🎉
