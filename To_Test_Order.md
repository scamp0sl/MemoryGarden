# 📋 Memory Garden - 내일 테스트 작업 순서

> **작성일**: 2025-02-10
> **목적**: API 키 설정 후 모듈별 테스트 및 최종 통합 테스트 수행

---

## 1. 🔑 API 키 설정

### 1.1 환경 변수 파일 (.env) 수정

```bash
# 프로젝트 루트에 .env 파일 열기
nano .env

# 또는
vi .env
```

### 1.2 필수 API 키 추가

`.env` 파일에 다음 내용을 추가/수정:

```env
# ============================================
# OpenAI API (GPT-4o-mini 사용)
# ============================================
OPENAI_API_KEY=sk-proj-...your-key-here...

# ============================================
# Anthropic API (Claude Sonnet 사용)
# ============================================
ANTHROPIC_API_KEY=sk-ant-...your-key-here...

# ============================================
# 기타 설정 (이미 있을 경우 확인만)
# ============================================
APP_ENV=development
DEBUG=True
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://memgarden:memgarden_password@localhost:5432/memory_garden
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Kakao (나중에 필요)
KAKAO_API_KEY=your-kakao-key
KAKAO_REDIRECT_URI=http://localhost:8000/api/v1/auth/kakao/callback
```

### 1.3 API 키 확인 방법

```bash
# .env 파일 로드 확인 (Python 콘솔에서)
python3 << 'EOF'
from config.settings import settings
print(f"OpenAI Key: {settings.OPENAI_API_KEY[:20]}...")
print(f"Anthropic Key: {settings.ANTHROPIC_API_KEY[:20]}...")
EOF
```

**✅ 체크포인트**: API 키가 올바르게 로드되는지 확인

---

## 2. 🔄 Mock LLM을 실제 API로 변경하기

현재 Mock으로 구현된 부분과 수정 방법을 정리합니다.

### 2.1 현재 Mock 사용 위치

| 파일 | Mock 대상 | 실제 사용 위치 |
|------|-----------|----------------|
| `tests/test_core/test_nlp.py` | OpenAI ChatCompletion | `core/nlp/emotion_detector.py`<br>`core/nlp/keyword_extractor.py` |
| `tests/test_core/test_dialogue.py` | OpenAI AsyncClient | `core/dialogue/response_generator.py` |
| `conftest.py` | OpenAI, Claude, Embeddings | 전역 fixture (모든 테스트) |

### 2.2 Mock 제거 방법 (실제 API 호출)

#### 옵션 A: pytest 마커로 실제 API 테스트 분리 (권장)

**1단계: 새로운 마커 추가**

`pyproject.toml` 또는 `pytest.ini`에 추가:

```toml
[tool.pytest.ini_options]
markers = [
    "asyncio: async test",
    "integration: integration test with real APIs (slow)"
]
```

**2단계: 실제 API 테스트 작성**

```bash
# Claude Code에 요청:
"tests/test_core/test_nlp.py에 @pytest.mark.integration 마커를 사용한
실제 OpenAI API 호출 테스트를 추가해줘.
기존 mock 테스트는 유지하고, 새로운 테스트만 추가."
```

**3단계: 실제 API 테스트 실행**

```bash
# Mock 테스트만 실행 (빠름)
pytest tests/ -v -m "not integration"

# 실제 API 테스트 실행 (느림, API 키 필요)
pytest tests/ -v -m "integration"

# 모든 테스트 실행
pytest tests/ -v
```

#### 옵션 B: 환경 변수로 Mock/Real 전환

**conftest.py 수정 요청:**

```bash
# Claude Code에 요청:
"conftest.py의 mock_openai, mock_claude fixture를 수정해줘.
환경 변수 USE_REAL_API=true일 때는 실제 API를 사용하고,
false일 때는 mock을 사용하도록."
```

**사용법:**

```bash
# Mock 사용 (기본)
pytest tests/test_core/test_nlp.py -v

# 실제 API 사용
USE_REAL_API=true pytest tests/test_core/test_nlp.py -v
```

### 2.3 실제 API 호출 테스트 시 주의사항

```bash
⚠️  주의사항:
1. API 비용 발생 (특히 GPT-4 사용 시)
2. 속도 느림 (Mock: 0.5초 vs Real: 2-5초)
3. Rate Limit 가능성
4. 네트워크 의존성

💡 권장: 개발 중에는 Mock 테스트 사용,
         배포 전에만 실제 API 통합 테스트 수행
```

---

## 3. 📝 모듈 테스트 진행 순서

### Phase 1: 기초 모듈 테스트 (Mock 사용)

#### 3.1 NLP 모듈 (감정 분석, 키워드 추출)

```bash
# 1. 테스트 실행
pytest tests/test_core/test_nlp.py -v

# 2. 커버리지 확인
pytest tests/test_core/test_nlp.py --cov=core/nlp --cov-report=term-missing

# ✅ 기대 결과: 23/23 tests passed
```

**문제 발생 시 Claude Code 요청:**
```
"tests/test_core/test_nlp.py에서 [에러 메시지] 발생했어.
core/nlp/emotion_detector.py를 확인하고 수정해줘."
```

#### 3.2 Memory 모듈 (4계층 메모리)

```bash
# 1. Redis/Qdrant 실행 확인
docker-compose ps

# Redis, Qdrant가 실행 중이어야 함
# 실행 안 되어 있으면:
docker-compose up -d redis qdrant

# 2. 테스트 실행
pytest tests/test_core/test_memory.py -v --cov=core/memory

# ✅ 기대 결과: 13/13 tests passed
```

**문제 발생 시:**
```
"tests/test_core/test_memory.py에서 Qdrant 연결 실패 에러가 나.
database/qdrant_client.py를 확인하고 연결 설정을 수정해줘."
```

#### 3.3 Dialogue 모듈 (대화 관리)

```bash
# 1. 테스트 실행
pytest tests/test_core/test_dialogue.py -v --cov=core/dialogue

# ✅ 기대 결과: 17/17 tests passed
```

**문제 발생 시:**
```
"tests/test_core/test_dialogue.py의 test_response_generator_generate에서
OpenAI 호출 실패 에러가 나. mock_redis_for_dialogue fixture를 확인해줘."
```

### Phase 2: API 엔드포인트 테스트

#### 3.4 Conversations API

```bash
# 1. FastAPI 앱 시작 (별도 터미널)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 2. 테스트 실행 (새 터미널)
pytest tests/test_api/test_conversations.py -v --cov=api/routes/conversations

# ✅ 기대 결과: 20/20 tests passed
```

**문제 발생 시:**
```
"tests/test_api/test_conversations.py에서 500 Internal Server Error가 나.
api/routes/conversations.py의 send_message 함수를 디버깅해줘."
```

### Phase 3: 실제 API 통합 테스트 (선택)

```bash
# 실제 OpenAI API 호출 테스트
USE_REAL_API=true pytest tests/test_core/test_nlp.py::test_detect_emotion_joy -v -s

# 실제 Claude API 호출 테스트
USE_REAL_API=true pytest tests/test_core/test_dialogue.py::test_response_generator_generate -v -s

# ⚠️  API 비용 발생 주의!
```

---

## 4. 🔗 통합 테스트 수행 방법

### 4.1 전체 시스템 시작

```bash
# 1. Docker 서비스 시작
docker-compose up -d

# 2. 서비스 상태 확인
docker-compose ps

# 예상 출력:
# NAME                COMMAND             STATUS              PORTS
# memgarden-postgres  postgres            Up                  5432
# memgarden-redis     redis-server        Up                  6379
# memgarden-qdrant    qdrant              Up                  6333

# 3. DB 초기화 (최초 1회)
python scripts/init_db.py

# 4. FastAPI 서버 시작
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 통합 테스트 시나리오

#### 시나리오 A: 수동 E2E 테스트 (브라우저)

```bash
# 1. Swagger UI 열기
open http://localhost:8000/docs

# 2. 다음 순서로 API 호출:

# 2.1 사용자 생성
POST /api/v1/users
{
  "name": "테스트 사용자",
  "birth_date": "1950-01-01",
  "kakao_id": "test_kakao_123"
}
# → user_id 복사

# 2.2 세션 시작
POST /api/v1/sessions
{
  "user_id": "[복사한 user_id]"
}
# → session_id 복사

# 2.3 메시지 전송
POST /api/v1/conversations/sessions/[session_id]/messages
{
  "user_id": "[user_id]",
  "message": "오늘 점심에 된장찌개 먹었어요",
  "message_type": "text"
}
# → 응답 확인: AI 답변, MCDI 점수, 정원 상태

# 2.4 정원 상태 조회
GET /api/v1/garden/[user_id]/status

# 2.5 분석 결과 조회
GET /api/v1/analysis/[user_id]/latest
```

#### 시나리오 B: 자동화된 통합 테스트 (curl)

```bash
# integration_test.sh 파일 생성
cat > integration_test.sh << 'EOF'
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

echo "=== 1. 사용자 생성 ==="
USER_RESPONSE=$(curl -s -X POST "$BASE_URL/users" \
  -H "Content-Type: application/json" \
  -d '{"name":"테스트사용자","birth_date":"1950-01-01","kakao_id":"test_123"}')
echo $USER_RESPONSE | jq .

USER_ID=$(echo $USER_RESPONSE | jq -r '.user_id')
echo "User ID: $USER_ID"

echo -e "\n=== 2. 세션 시작 ==="
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\"}")
echo $SESSION_RESPONSE | jq .

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

echo -e "\n=== 3. 메시지 전송 ==="
MESSAGE_RESPONSE=$(curl -s -X POST "$BASE_URL/conversations/sessions/$SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"message\":\"오늘 점심에 김치찌개 먹었어요\",\"message_type\":\"text\"}")
echo $MESSAGE_RESPONSE | jq .

echo -e "\n=== 4. 정원 상태 조회 ==="
GARDEN_RESPONSE=$(curl -s -X GET "$BASE_URL/garden/$USER_ID/status")
echo $GARDEN_RESPONSE | jq .

echo -e "\n=== 5. 분석 결과 조회 ==="
ANALYSIS_RESPONSE=$(curl -s -X GET "$BASE_URL/analysis/$USER_ID/latest")
echo $ANALYSIS_RESPONSE | jq .

echo -e "\n✅ 통합 테스트 완료!"
EOF

chmod +x integration_test.sh
./integration_test.sh
```

#### 시나리오 C: pytest 통합 테스트 작성

```bash
# Claude Code에 요청:
"tests/test_integration/test_full_workflow.py 파일을 생성해줘.
사용자 생성 → 세션 시작 → 메시지 전송 → 분석 → 정원 업데이트까지
전체 워크플로우를 테스트하는 통합 테스트를 작성해줘."
```

### 4.3 전체 테스트 스위트 실행

```bash
# 1. 모든 단위 테스트 실행 (Mock 사용)
pytest tests/ -v --cov=. --cov-report=html

# 2. 커버리지 확인
open htmlcov/index.html

# 3. 목표 커버리지
# - Core 모듈: 80% 이상
# - API 라우트: 70% 이상
# - 전체: 75% 이상

# 4. 특정 모듈만 테스트
pytest tests/test_core/ -v                    # Core 모듈만
pytest tests/test_api/ -v                     # API만
pytest tests/test_core/test_nlp.py -v         # NLP만

# 5. 실패한 테스트만 재실행
pytest --lf -v                                # Last Failed
pytest --ff -v                                # Failed First

# 6. 병렬 실행 (속도 향상)
pytest tests/ -v -n auto                      # CPU 코어 수만큼 병렬
```

---

## 5. ✅ 체크리스트: 빠진 작업 확인

### 5.1 구현 완료된 항목

- ✅ 테스트 파일 작성 (conftest, test_nlp, test_memory, test_dialogue, test_conversations)
- ✅ Mock 기반 단위 테스트 (73개 테스트)
- ✅ API 스키마 정의 (Pydantic)
- ✅ 기본 API 라우트 구현

### 5.2 내일 해야 할 작업

#### 우선순위 1: 필수 작업

- [ ] **API 키 설정** (.env 파일)
- [ ] **Docker 서비스 시작** (Redis, Qdrant, PostgreSQL)
- [ ] **DB 초기화** (테이블 생성)
- [ ] **모듈별 테스트 실행** (Phase 1, 2)
- [ ] **통합 테스트 수행** (시나리오 A 또는 B)
- [ ] **커버리지 확인** (목표: 75% 이상)

#### 우선순위 2: 코드 완성 (구현 안 된 부분)

**아직 구현 안 된 핵심 모듈:**

1. **분석 모듈 (6개 지표)**
   ```bash
   # Claude Code 요청:
   "core/analysis/lexical_richness.py를 CLAUDE.md의 4장 스펙대로 구현해줘."
   "core/analysis/semantic_drift.py를 구현해줘."
   "core/analysis/narrative_coherence.py를 구현해줘."
   "core/analysis/temporal_orientation.py를 구현해줘."
   "core/analysis/episodic_recall.py를 구현해줘."
   "core/analysis/response_time.py를 구현해줘."
   ```

2. **MCDI 계산기**
   ```bash
   "core/analysis/mcdi_calculator.py를 완성해줘.
   CLAUDE.md의 MCDI 공식대로 6개 지표 가중 평균 계산."
   ```

3. **위험도 평가기**
   ```bash
   "core/analysis/risk_evaluator.py를 구현해줘.
   Baseline 대비 z-score와 4주 기울기로 GREEN/YELLOW/ORANGE/RED 판정."
   ```

4. **메모리 관리자 (4계층)**
   ```bash
   "core/memory/memory_manager.py를 완성해줘.
   Session, Episodic, Biographical, Analytical 4계층 통합."
   ```

5. **대화 관리자**
   ```bash
   "core/dialogue/dialogue_manager.py가 실제로 동작하도록
   ResponseGenerator와 통합해줘."
   ```

6. **세션 워크플로우 (최종 통합)**
   ```bash
   "core/workflow/session_workflow.py를 구현해줘.
   전체 8단계 워크플로우를 통합하는 메인 클래스."
   ```

#### 우선순위 3: 추가 개선 사항

- [ ] **로깅 개선** (구조화된 로그, 에러 추적)
- [ ] **에러 핸들링 강화** (Retry 로직, Circuit Breaker)
- [ ] **성능 테스트** (부하 테스트, 응답 시간)
- [ ] **보안 검토** (API 인증, Rate Limiting)
- [ ] **문서화** (API 문서, 아키텍처 다이어그램)

### 5.3 구현 순서 제안

```
Day 1 (내일):
1. API 키 설정 및 환경 확인
2. 기존 테스트 실행 (Mock)
3. 분석 모듈 6개 구현 시작 (LR, SD 우선)

Day 2:
4. 나머지 분석 모듈 구현 (NC, TO, ER, RT)
5. MCDI 계산기 + 위험도 평가기
6. 실제 API 통합 테스트

Day 3:
7. 메모리 관리자 통합
8. 세션 워크플로우 구현
9. E2E 통합 테스트

Day 4:
10. 성능 최적화
11. 문서화
12. 배포 준비
```

---

## 6. 🐛 트러블슈팅 가이드

### 문제 1: API 키 인식 안 됨

```bash
# 증상
AssertionError: API key not found

# 해결
1. .env 파일이 프로젝트 루트에 있는지 확인
2. 환경 변수 재로드: source .env
3. Python에서 확인:
   python -c "from config.settings import settings; print(settings.OPENAI_API_KEY)"
```

### 문제 2: Docker 서비스 시작 실패

```bash
# 증상
ERROR: Cannot start service postgres: port is already allocated

# 해결
1. 포트 충돌 확인: lsof -i :5432
2. 기존 서비스 종료: docker-compose down
3. 강제 재생성: docker-compose up -d --force-recreate
```

### 문제 3: Qdrant 연결 실패

```bash
# 증상
QdrantConnectionError: Cannot connect to Qdrant

# 해결
1. Qdrant 컨테이너 상태 확인: docker-compose logs qdrant
2. 포트 확인: curl http://localhost:6333/collections
3. 재시작: docker-compose restart qdrant
```

### 문제 4: 테스트 실패 시 Claude Code 요청 템플릿

```bash
# 템플릿
"tests/[테스트_파일]의 [테스트_함수]에서 다음 에러가 발생했어:

[에러 메시지 전체 복사]

관련 파일:
- [구현 파일 경로]
- [테스트 파일 경로]

이 문제를 디버깅하고 수정해줘."
```

### 문제 5: 커버리지 목표 미달

```bash
# 현재 커버리지 확인
pytest --cov=. --cov-report=term-missing

# 커버리지 낮은 파일 찾기
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Claude Code 요청
"[파일명]의 커버리지가 50%밖에 안 돼.
누락된 라인들에 대한 테스트를 추가해줘."
```

---

## 7. 📚 참고 문서

- **CLAUDE.md**: 개발 가이드 (코딩 컨벤션, 프롬프트 템플릿)
- **SPEC.md**: 프로젝트 명세 (아키텍처, API 스펙, MCDI 공식)
- **README.md**: 프로젝트 개요 및 설치 가이드
- **tests/conftest.py**: 공통 fixture 및 mock 설정
- **pyproject.toml**: 프로젝트 설정 및 의존성

---

## 8. 🎯 성공 기준

### 내일 작업 완료 조건

1. ✅ API 키가 올바르게 설정되고 로드됨
2. ✅ 모든 Docker 서비스가 정상 실행 중
3. ✅ 기존 73개 테스트가 모두 통과
4. ✅ 분석 모듈 최소 2개 이상 구현 (LR, SD)
5. ✅ 수동 E2E 테스트 1회 성공 (Swagger UI)
6. ✅ 전체 커버리지 60% 이상

### 최종 목표 (3-4일 후)

1. ✅ 모든 핵심 모듈 구현 완료
2. ✅ 100개 이상 테스트 통과
3. ✅ 전체 커버리지 75% 이상
4. ✅ 실제 API 통합 테스트 성공
5. ✅ E2E 통합 테스트 성공
6. ✅ 성능 기준 충족 (응답 <2초)

---

## 9. 💡 팁

### 효율적인 개발 순서

```bash
# 1. 작은 단위로 테스트하며 개발
# 2. 테스트 먼저 작성 (TDD)
# 3. Mock으로 빠르게 검증
# 4. 실제 API는 최종 단계에서만
# 5. 커밋을 자주 (기능 단위로)

# 예시 워크플로우:
1. "lexical_richness.py 구현해줘"
2. pytest tests/test_analysis/test_lexical_richness.py -v
3. 통과 → git commit -m "feat: Add lexical richness analyzer"
4. 다음 모듈로 이동
```

### Claude Code 활용 팁

```bash
# 좋은 요청 예시
"core/analysis/semantic_drift.py를 구현해줘.
config/prompts.py의 ANALYSIS_PROMPTS['semantic_drift']를 사용하고,
LLMService로 Claude API를 호출해.
test_semantic_drift.py의 테스트가 통과하도록."

# 나쁜 요청 예시
"의미적 표류 만들어줘"  # 너무 모호함
```

---

**작성자**: Claude Code
**마지막 업데이트**: 2025-02-10
**다음 리뷰**: 내일 작업 후 체크리스트 업데이트
