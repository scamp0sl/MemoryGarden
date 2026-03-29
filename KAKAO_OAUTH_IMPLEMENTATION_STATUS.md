# 카카오 OAuth 구현 상태 보고서

**작성일**: 2026-02-24 14:05
**세션 ID**: 6ffc9891-7319-4bba-b49f-c7f83e0a4a

---

## ✅ 완료된 작업

### 1. 카카오 OAuth 인증 시스템
- **파일**: `api/routes/auth.py`
- **엔드포인트**:
  - `GET /api/v1/auth/kakao/login` - 카카오 로그인 시작
  - `GET /api/v1/auth/kakao/callback` - OAuth 콜백 (토큰 교환)
  - `POST /api/v1/auth/kakao/refresh/{user_id}` - 토큰 갱신
- **상태**: ✅ 완료 및 테스트 완료

**설정값**:
```
KAKAO_REDIRECT_URI=https://n8n.softline.co.kr/api/v1/auth/kakao/callback
KAKAO_REST_API_KEY=dbd781ee1536f158091e578abe27e1e3
KAKAO_CLIENT_SECRET=Vo4MhZUrrG3ycWdSQgBY1hSCBXGUVyBL
KAKAO_MOCK_MODE=false
```

### 2. 데이터베이스 스키마
- **파일**: `database/models.py`
- **추가된 컬럼** (users 테이블):
  ```sql
  kakao_access_token TEXT
  kakao_refresh_token TEXT
  kakao_token_expires_at TIMESTAMP
  kakao_refresh_token_expires_at TIMESTAMP
  ```
- **마이그레이션**: `alembic/versions/20260224_1101-6da46d0d1818_add_kakao_oauth_tokens_to_users_table.py`
- **상태**: ✅ 프로덕션 DB 적용 완료

### 3. 메시지 전송 기능
- **파일**: `services/kakao_client.py`
- **메서드**:
  - `send_to_me(access_token, message)` - 나에게 보내기 ✅
  - `get_friends(access_token)` - 친구 목록 조회 ✅
  - `send_to_friends(access_token, receiver_uuids, message)` - 친구에게 보내기 (UUID 형식 이슈)
- **상태**: ✅ "나에게 보내기" 완벽 작동

### 4. 자동 스케줄러
- **파일**: `core/dialogue/scheduler.py`
- **기본 시간**: 09:00, 14:00, 19:00
- **저장소**: Redis (영구 저장)
- **통합**: FastAPI lifespan 이벤트에 통합됨 (`api/main.py`)
- **상태**: ✅ 작동 중

### 5. 자동 스케줄 등록 (최종 추가)
- **파일**: `api/routes/auth.py` (라인 145-160)
- **기능**: OAuth 로그인 완료 시 자동으로 3회 메시지 스케줄 등록
- **상태**: ✅ 구현 완료 (FastAPI reload로 자동 적용됨)

### 6. 토큰 자동 갱신
- **파일**: `tasks/dialogue.py` (라인 930-945)
- **로직**: 토큰 만료 1시간 전 자동 갱신
- **상태**: ✅ 구현 및 테스트 완료

---

## 📊 현재 등록된 사용자

### User 1 (본인)
```
kakao_id: 4763495478
name: 사용자
created_at: 2026-02-24 13:45:34
token_expires_at: 2026-02-24 19:49:57
스케줄: ✅ 등록됨 (09:00, 14:00, 19:00)
```

### User 2 (새 사용자)
```
kakao_id: 4765476999
name: 사용자
created_at: 2026-02-24 13:57:10
token_expires_at: 2026-02-24 19:57:09
스케줄: ✅ 자동 등록 테스트 완료
```

**테스트 결과**:
- ✅ 두 사용자 모두 카카오톡 메시지 수신 확인
- ✅ OAuth 로그인 플로우 정상 작동
- ✅ 토큰 저장 및 갱신 정상 작동

---

## 🔴 **중요 발견: 미구현 사항**

### 현재 시스템의 한계

**현재 상태**:
```
스케줄러 → 카카오톡 메시지 전송 (일방향)
           ↓
         사용자가 메시지 받음
           ↓
         메시지 클릭 → index.html 이동
           ↓
         "알림받기 시작" 버튼만 있음
```

**문제점**:
1. ❌ **사용자 응답을 받을 수 없음** (일방향 메시지)
2. ❌ **대화 UI 없음** (웹에서 응답 입력 불가)
3. ❌ **분석 파이프라인 미연동** (응답 분석 불가)
4. ❌ **MCDI 점수 계산 안 됨** (데이터 없음)
5. ❌ **치매 진단 데이터 쌓이지 않음**

### 현재 메시지 플로우
```python
# tasks/dialogue.py → send_scheduled_dialogue()
메시지 내용: "안녕하세요! 🌤️\n\n오늘 하루는 어떠셨나요? 😊"
링크: https://n8n.softline.co.kr/static/index.html
버튼: "대화하기"

# 하지만...
사용자 클릭 → index.html 이동
→ Firebase 웹 푸시 알림 등록 UI만 있음
→ 대화 입력창 없음!
```

---

## 🎯 다음 단계 (필수 구현)

### Option A: 웹 대화 UI 추가 (추천)

**1. index.html 수정**
- 대화 입력창 추가
- 질문 표시 UI
- 응답 전송 버튼

**2. API 엔드포인트 추가**
```python
# api/routes/conversations.py
@router.post("/respond")
async def submit_response(
    user_id: str,
    message: str,
    question_id: str = None
):
    # 1. 응답 저장
    # 2. 분석 파이프라인 실행
    # 3. MCDI 점수 계산
    # 4. DB 저장
    # 5. 피드백 반환
```

**3. 분석 파이프라인 연동**
- `core/workflow/message_processor.py` 사용
- 6개 지표 분석 (LR, SD, NC, TO, ER, RT)
- MCDI 종합 점수 계산
- DB 저장 (`analysis_results` 테이블)

### Option B: 카카오톡 채널 챗봇 (복잡)
- 카카오 채널 생성
- 챗봇 개발
- Webhook 설정
- 복잡하고 시간 소요

---

## 📁 주요 파일 경로

### OAuth 관련
```
api/routes/auth.py                    - OAuth 엔드포인트
database/models.py                    - User 모델 (토큰 필드)
.env                                  - OAuth 설정
```

### 메시지 전송
```
services/kakao_client.py              - 카카오 API 클라이언트
tasks/dialogue.py                     - 스케줄된 메시지 전송
```

### 스케줄러
```
core/dialogue/scheduler.py            - DialogueScheduler
api/main.py                           - FastAPI lifespan 통합
```

### 프론트엔드
```
static/index.html                     - 웹 UI (현재: Firebase 푸시만)
static/firebase-messaging-sw.js      - Service Worker
```

### 분석 파이프라인 (미연동)
```
core/workflow/message_processor.py   - 메인 워크플로우
core/analysis/analyzer.py             - 6개 지표 통합
core/analysis/mcdi_calculator.py     - MCDI 점수 계산
```

---

## 🗄️ 데이터베이스 상태

### PostgreSQL (localhost:5432)
```sql
-- 현재 사용자 수
SELECT COUNT(*) FROM users WHERE kakao_access_token IS NOT NULL;
-- 결과: 2명

-- 토큰 만료 시간 확인
SELECT kakao_id, name, kakao_token_expires_at
FROM users
WHERE kakao_access_token IS NOT NULL
ORDER BY created_at DESC;
```

### Redis (localhost:6379)
```bash
# DB 0: 애플리케이션 데이터
redis-cli GET "schedule:4763495478"
redis-cli GET "schedule:4765476999"

# DB 1: APScheduler JobStore
redis-cli -n 1 HLEN "apscheduler.jobs"
# 결과: 19개 작업
```

---

## 🚀 FastAPI 서버 상태

**실행 중**: ✅
**포트**: 8001
**모드**: --reload (코드 변경 시 자동 재시작)
**로그**: `/tmp/fastapi.log`

**확인 명령어**:
```bash
# 서버 상태
pgrep -f "uvicorn api.main:app"

# 로그 확인
tail -f /tmp/fastapi.log

# 스케줄러 작업 수
docker exec memgarden-redis redis-cli -n 1 HLEN "apscheduler.jobs"
```

---

## 🔧 다음 세션 시작 시

### 1. 상태 확인
```bash
# 서버 실행 중인지 확인
pgrep -f "uvicorn api.main:app"

# 사용자 수 확인
docker exec memgarden-postgres psql -U memgarden -d memory_garden \
  -c "SELECT COUNT(*) FROM users WHERE kakao_access_token IS NOT NULL;"

# 스케줄 확인
docker exec memgarden-redis redis-cli KEYS "schedule:*"
```

### 2. 필요한 구현

**우선순위 1: 대화 UI (index.html)**
- 질문 표시
- 답변 입력창
- 제출 버튼
- 사용자 ID 전달 (URL 파라미터 또는 로컬 스토리지)

**우선순위 2: 응답 API**
- `POST /api/v1/conversations/respond`
- 요청: `{user_id, message, question_id?}`
- 응답 저장 → 분석 → MCDI 계산 → DB 저장

**우선순위 3: 분석 파이프라인 연동**
- `MessageProcessor` 통합
- 6개 지표 분석 활성화
- `analysis_results` 테이블 저장

### 3. 테스트 플로우
```
1. 카카오톡 메시지 받음
2. 메시지 클릭 → 웹 이동
3. 웹에서 질문 확인
4. 답변 입력 → 제출
5. 서버에서 분석
6. MCDI 점수 계산
7. DB 저장
8. 피드백 표시
```

---

## 📝 핵심 요약

### ✅ 완료
- OAuth 인증 시스템
- 자동 메시지 전송
- 자동 스케줄 등록
- 토큰 자동 갱신

### ❌ 미완료 (치명적!)
- **사용자 응답 받기**
- **대화 분석**
- **MCDI 점수 계산**
- **치매 진단 데이터 축적**

### 🎯 다음 작업
1. index.html에 대화 UI 추가
2. `/api/v1/conversations/respond` API 생성
3. 분석 파이프라인 연동

---

## 🔗 참고 URL

- **OAuth 로그인**: https://n8n.softline.co.kr/api/v1/auth/kakao/login
- **웹 UI**: https://n8n.softline.co.kr/static/index.html
- **API 문서**: http://localhost:8001/docs

---

**다음 세션에서 이 파일을 읽고 시작하세요!**
