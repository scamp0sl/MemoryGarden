# 기억의 정원 (Memory Garden) - SPEC vs 현재 구현 갭 분석

> **분석 일자**: 2026-02-27
> **SPEC 버전**: 1.0.0 (2025-01-15 기준)
> **현재 구현 상태**: Beta 진행 중
> **분석 범위**: SPEC.md 전 섹션 (1~10) 대비 소스코드 직접 비교

---

## 목차

1. [현재 구현 완료 항목](#1-현재-구현-완료-항목-)
2. [갭 분석: 부족하거나 미구현 항목](#2-갭-분석-부족하거나-미구현-항목)
   - [🔴 CRITICAL (즉시 필요)](#-critical-즉시-필요)
   - [🟠 HIGH (단기 필요)](#-high-단기-필요)
   - [🟡 MEDIUM (중기 필요)](#-medium-중기-필요)
   - [🟢 LOW (장기 로드맵)](#-low-장기-로드맵)
3. [우선순위별 구현 로드맵](#3-우선순위별-구현-로드맵)
4. [기술 부채 목록](#4-기술-부채-목록)
5. [검증 기준 (Definition of Done)](#5-검증-기준-definition-of-done)

---

## 1. 현재 구현 완료 항목 ✅

### 1.1 핵심 인프라

| 항목 | 파일 | 상태 |
|------|------|------|
| FastAPI 서버 + Nginx 리버스 프록시 | `api/main.py`, `memgarden-nginx.conf` | ✅ 운영 중 |
| PostgreSQL 연동 (SQLAlchemy ORM) | `database/postgres.py`, `database/models.py` | ✅ 완료 |
| Redis 연동 (세션 메모리) | `database/redis_client.py` | ✅ 완료 |
| Alembic 마이그레이션 | `alembic/versions/` | ✅ 완료 |
| TimescaleDB 클라이언트 코드 | `database/timescale.py` | ✅ 구현 완료 |

### 1.2 카카오 채널 통합

| 항목 | 파일 | 상태 |
|------|------|------|
| 카카오 채널 웹훅 수신 | `api/routes/kakao_webhook.py` | ✅ 운영 중 |
| plusfriendUserKey 기반 사용자 자동 생성 | `api/routes/kakao_webhook.py` | ✅ 완료 |
| 카카오 OAuth 로그인 + 토큰 관리 | `api/routes/kakao_oauth.py` | ✅ 완료 |
| OAuth send_to_me (스케줄 메시지) | `tasks/dialogue.py`, `services/kakao_client.py` | ✅ 검증 완료 |
| 카카오 채널 리다이렉트 엔드포인트 | `api/routes/kakao_webhook.py::channel` | ✅ 완료 |
| 비즈메시지 친구톡 클라이언트 코드 | `services/kakao_client.py` | ✅ 구현 (자격증명 필요) |

### 1.3 MCDI 분석 파이프라인

| 항목 | 파일 | 상태 |
|------|------|------|
| LR (어휘 풍부도) 분석기 | `core/analysis/lexical_richness.py` | ✅ 완료 |
| SD (의미적 표류) 분석기 | `core/analysis/semantic_drift.py` | ✅ 완료 |
| NC (서사 일관성) 분석기 | `core/analysis/narrative_coherence.py` | ✅ 완료 |
| TO (시간적 지남력) 분석기 | `core/analysis/temporal_orientation.py` | ✅ 완료 |
| ER (일화 기억) 분석기 | `core/analysis/episodic_recall.py` | ✅ 완료 |
| RT (반응 시간) 분석기 | `core/analysis/response_time.py` | ✅ 완료 |
| MCDI 가중 평균 계산기 | `core/analysis/mcdi_calculator.py` | ✅ 완료 (가중치 SPEC 일치) |
| 모순 탐지기 | `core/analysis/contradiction_detector.py` | ✅ 완료 |
| 통합 Analyzer (6개 병렬 실행) | `core/analysis/analyzer.py` | ✅ 완료 |
| 위험도 평가기 (z-score + 기울기) | `core/analysis/risk_evaluator.py` | ✅ 로직 완료 |
| 분석 결과 DB 저장 | `database/models.py::AnalysisResult` | ✅ 완료 |
| 백그라운드 MCDI 분석 | `api/routes/kakao_webhook.py::BackgroundTasks` | ✅ 완료 |

### 1.4 대화 시스템

| 항목 | 파일 | 상태 |
|------|------|------|
| 대화 흐름 관리자 | `core/dialogue/dialogue_manager.py` | ✅ 완료 |
| 프롬프트 빌더 (정원사 페르소나) | `core/dialogue/prompt_builder.py` | ✅ 완료 |
| LLM 응답 생성기 (Claude) | `core/dialogue/response_generator.py` | ✅ 완료 |
| 세션 메모리 (Redis TTL 24h) | `core/memory/session_memory.py` | ✅ 완료 |
| APScheduler 기반 대화 스케줄링 | `core/dialogue/scheduler.py`, `services/push_scheduler.py` | ✅ 완료 |
| 스케줄 등록 (신규 사용자 자동) | `api/routes/kakao_webhook.py::_register_user_schedule` | ✅ 완료 |

### 1.5 메모리 시스템 (부분 완료)

| 항목 | 파일 | 상태 |
|------|------|------|
| 4계층 MemoryManager 구조 | `core/memory/memory_manager.py` | ✅ 구조 완료 |
| Session Memory (Layer 1, Redis) | `core/memory/session_memory.py` | ✅ 완료 |
| Analytical Memory Layer 4 코드 | `core/memory/analytical_memory.py` | ✅ 코드 완료 |
| 전기적 메모리 Layer 3 코드 | `core/memory/biographical_memory.py` | ✅ 코드 완료 |
| 에피소딕 메모리 Layer 2 코드 | `core/memory/episodic_memory.py` | ✅ 코드 완료 |

### 1.6 API 라우트

| 항목 | 파일 | 상태 |
|------|------|------|
| 사용자 CRUD | `api/routes/users.py` | ✅ 완료 |
| 대화 이력 조회 | `api/routes/conversations.py` | ✅ 완료 |
| 분석 결과 조회 | `api/routes/analysis.py` | ✅ 완료 |
| 정원 상태 조회 | `api/routes/garden.py` | ✅ 완료 |
| 푸시 알림 등록 | `api/routes/push.py` | ✅ 완료 |
| FCM 토큰 모델 | `database/models.py::FCMToken` | ✅ 완료 |

---

## 2. 갭 분석: 부족하거나 미구현 항목

---

### 🔴 CRITICAL (즉시 필요)

> 서비스 핵심 기능이 막히거나 데이터 일관성이 깨질 수 있는 항목

---

#### [CRIT-1] DB 모델 누락: guardians / user_guardians / notifications / memory_events / garden_status

**문제**: SPEC.md §4.1.2에 명시된 5개 테이블이 `database/models.py`에 전혀 없음.

```
현재 models.py: User, Conversation, AnalysisResult, FCMToken
SPEC 요구 추가: guardians, user_guardians, notifications, memory_events, garden_status
```

**영향**:
- 보호자 연결 기능 전혀 작동 불가
- 알림 이력 저장 불가
- 모순 탐지 이력 저장 불가
- 게이미피케이션 꽃/나비/연속 일수 영구 저장 불가

**구현 위치**: `database/models.py`, 새 Alembic 마이그레이션 필요

```python
# 필요한 모델들
class Guardian(Base): ...          # 보호자
class UserGuardian(Base): ...      # 사용자-보호자 M:N
class Notification(Base): ...      # 알림 이력
class MemoryEvent(Base): ...       # 모순 탐지 이력
class GardenStatus(Base): ...      # 게이미피케이션 상태
```

---

#### [CRIT-2] User 모델 누락 컬럼: garden_name, onboarding_state

**문제**: SPEC.md §2.4.1에서 첫 대화 시 `garden_name` 수집이 필수지만 `users` 테이블에 해당 컬럼 없음. 온보딩 진행 상태 추적 필드도 없음.

```
SPEC 요구 컬럼:
- garden_name: VARCHAR(100)
- onboarding_day: INTEGER DEFAULT 0  (Day 0-14 추적)
- last_interaction_at: TIMESTAMP     (중도 이탈 방지)

현재: 없음
```

**구현 위치**: `database/models.py::User`, Alembic 마이그레이션

---

#### [CRIT-3] 온보딩 플로우 미구현 (Day 0-14)

**문제**: SPEC.md §2.4에서 14일 베이스라인 수집 플로우를 명시했지만, 현재는 첫 대화부터 바로 MCDI 분석을 실행함. 베이스라인이 없으면 RiskEvaluator의 z-score가 항상 `None`으로 반환되어 위험도 판정 신뢰도가 0.5에 머뭄.

**SPEC 요구 플로우**:
```
Day 0:    정원 이름 짓기 + 기본 정보 수집
Day 1-7:  관계 형성 + 전기적 정보 수집 (고향, 자녀, 직업)
Day 8-14: 6개 카테고리 순환 노출 + 선호도 파악
Day 15+:  baseline 확립 → z-score 기반 이상 감지 시작
```

**현재**: 구조 없음. 첫 메시지부터 동일한 파이프라인 실행

**구현 위치**:
- `core/workflow/onboarding_flow.py` (신규)
- `api/routes/kakao_webhook.py` (분기 추가)
- `database/models.py::User.onboarding_day`

---

#### [CRIT-4] TimescaleDB 실제 연결 미검증

**문제**: `database/timescale.py` 코드는 완성도 높게 작성되어 있으나, 실제 Docker Compose에 TimescaleDB extension 설치 여부 및 `analysis_timeseries` hypertable 생성 여부가 불명확. RiskEvaluator가 historical scores를 가져오지 못하면 위험도 판정이 항상 MCDI 절댓값 기반으로만 동작함.

**확인 필요**:
```sql
-- 실행 여부 확인 필요
SELECT create_hypertable('analysis_timeseries', 'timestamp');

-- Continuous Aggregates 생성 여부 확인
CREATE MATERIALIZED VIEW analysis_daily
WITH (timescaledb.continuous) AS ...
```

**구현 위치**:
- `scripts/init_timescale.py` (hypertable 초기화 스크립트)
- `docker-compose.yml` (timescaledb 이미지 확인)

---

#### [CRIT-5] 보호자 알림 실제 전송 미구현

**문제**: `services/notification_service.py`가 `mock_mode=True`로 초기화되어 있어 ORANGE/RED 위험도 시에도 보호자에게 실제 알림이 발송되지 않음.

```python
# services/notification_service.py:75
def __init__(self, kakao_client=None, mock_mode: bool = True):
```

또한 보호자 정보를 DB에서 조회하는 로직이 작동하려면 [CRIT-1]의 `guardians`, `user_guardians` 테이블이 먼저 생성되어야 함.

**구현 위치**:
- `services/notification_service.py` (mock_mode=False 전환 + guardian DB 조회 완성)
- `database/models.py` ([CRIT-1] 선행 필요)

---

### 🟠 HIGH (단기 필요)

> 핵심 사용자 경험 또는 데이터 신뢰성에 영향을 주는 항목

---

#### [HIGH-1] Qdrant 벡터 DB 연결 미완성

**문제**: Episodic Memory(Layer 2)와 Biographical Memory(Layer 3)의 Qdrant 연동 코드가 있으나 실제 프로덕션에서 "skipped" 상태. Collection 생성 및 벡터 저장/검색이 작동하지 않으면 ER(일화 기억) 분석의 실효성이 낮아짐.

**SPEC 요구 Collections**:
```
episodic_memory    - 일화 기억 (점심 메뉴, 감정 등)
biographical_memory - 전기적 정보 (이름, 고향, 자녀)
question_history   - 질문 이력 (중복 방지)
```

**구현 위치**:
- `core/memory/episodic_memory.py` (실제 Qdrant 저장/검색 활성화)
- `core/memory/biographical_memory.py` (동일)
- `scripts/init_qdrant.py` (Collection 초기화 스크립트)

---

#### [HIGH-2] 6개 대화 카테고리 라우팅 미구현

**문제**: SPEC §2.1.1에서 6개 카테고리(회상/일화/이름/시간/시각-언어/선택)를 각각 다른 빈도로 운영하도록 명시했지만, 현재 대화 시스템은 카테고리 구분 없이 단일 파이프라인으로 실행됨.

```
SPEC 요구 빈도:
- 회상의 꽃밭 (Reminiscence): 주 2회
- 오늘의 한 접시 (Daily Episodic): 주 3회
- 이름 꽃밭 (Naming): 주 1회
- 시간의 나침반 (Temporal): 주 2회
- 그림 읽기 놀이 (Visual-Linguistic): 주 1회 (이미지)
- 선택의 정원 (Non-verbal): 주 1회 (버튼 선택)

현재: 카테고리 컬럼 DB에 있으나 대화 생성 시 카테고리 선택 로직 없음
```

**구현 위치**:
- `core/dialogue/category_selector.py` (신규: 약한 지표 우선 카테고리 선택)
- `core/dialogue/dialogue_manager.py` (카테고리별 질문 템플릿 라우팅)
- `api/routes/kakao_webhook.py` (Non-verbal 카테고리 버튼 카드 응답)

---

#### [HIGH-3] 이미지 분석 카테고리 플로우 미완성

**문제**: `services/vision_service.py`와 `services/image_analysis_service.py`가 존재하나, '그림 읽기 놀이(Visual-Linguistic)' 카테고리의 실제 대화 플로우가 없음. 사진을 업로드한 후 대화로 이어지는 2턴 구조가 미구현.

```
SPEC 예시:
[오전] 점심 사진 찍어서 올려주세요
[사용자] (사진 전송)
[오후] 오늘 점심에 드신 재료 3가지를 말씀해주세요 (ER 측정)
```

**구현 위치**:
- `core/dialogue/category_selector.py` (이미지 업로드 트리거 포함)
- `core/memory/episodic_memory.py` (이미지 컨텍스트 저장)
- `api/routes/kakao_webhook.py` (이미지 메시지 타입 처리)

---

#### [HIGH-4] 중도 이탈 방지 태스크 미구현

**문제**: SPEC §2.4.4에서 비활성 사용자를 24시간 단위로 체크하고 1일차/3일차/7일차 재참여 메시지를 보내도록 명시했지만, `tasks/` 폴더에 해당 태스크 없음. 현재 스케줄러는 일일 대화 발송만 처리.

**SPEC 요구 태스크**:
```python
# tasks/engagement_monitor.py (존재하지 않음)
async def check_inactive_users():
    """24시간 무응답 사용자 체크 → 단계별 재참여 메시지"""
    ...
```

**구현 위치**:
- `tasks/engagement_monitor.py` (신규)
- `services/push_scheduler.py` (비활성 체크 스케줄 추가)

---

#### [HIGH-5] 보호자 연결 대화 플로우 미구현

**문제**: SPEC §2.4.3에서 온보딩 완료 후 보호자 연락처를 수집하고, 보호자에게 초대 메시지를 보내는 플로우가 명시되어 있으나 전혀 구현되지 않음.

**SPEC 요구 플로우**:
```
① 사용자에게 보호자 연락처 요청
② 보호자에게 서비스 소개 카카오톡 발송
③ 보호자가 대시보드 링크를 통해 확인
```

**구현 위치**:
- `core/dialogue/prompt_builder.py` (보호자 연결 안내 프롬프트)
- `api/routes/users.py` (보호자 등록 API)
- `database/models.py` ([CRIT-1] 선행 필요)

---

#### [HIGH-6] 주간/일일 리포트 생성 미구현

**문제**: `tasks/dialogue.py`에 `TASK_TYPE_WEEKLY_REPORT`, `TASK_TYPE_MONTHLY_REPORT` 상수는 정의되어 있으나 실제 리포트 생성 함수가 없음. SPEC §2.5.1에서 Celery Beat로 매일 23:00 및 매주 일요일 22:00에 실행하도록 명시.

**구현 위치**:
- `tasks/report_generator.py` (신규: 일간/주간 리포트 생성)
- `core/analysis/report_generator.py` (기존 파일 완성)

---

### 🟡 MEDIUM (중기 필요)

> 서비스 품질과 운영 안정성에 영향을 주는 항목

---

#### [MED-1] Celery 미도입 (APScheduler 사용 중)

**문제**: SPEC §3.2에서 Celery 5.3+ Redis Broker를 명시했으나, 현재 APScheduler + FastAPI BackgroundTasks 조합을 사용 중. APScheduler는 단일 서버에서만 동작하며 프로세스 재시작 시 스케줄이 초기화됨.

```
SPEC: Celery 5.3 + Redis Broker + Redis Backend
현재: APScheduler (메모리 기반) + FastAPI BackgroundTasks
```

**영향**:
- 서버 재시작 시 스케줄 누락 가능
- 다중 서버 확장 시 중복 실행 위험
- 태스크 실패 시 자동 재시도 없음

**구현 위치**:
- `tasks/celery_app.py` (신규: Celery 앱 설정)
- `tasks/celery_beat_schedule.py` (신규: SPEC §2.5.1 스케줄 설정)
- `docker-compose.yml` (celery worker, beat 서비스 추가)

---

#### [MED-2] 보호자 대시보드 프론트엔드 없음

**문제**: SPEC §2.2.2에서 보호자용 웹 대시보드를 명시했지만, 현재 백엔드 API만 있고 프론트엔드 없음.

```
SPEC 요구 기능:
- 주간 MCDI 트렌드 그래프
- 관찰 사항 요약
- 권장 조치 체크리스트
- 의사용 리포트 PDF 다운로드
```

**구현 위치**: 별도 프론트엔드 프로젝트 필요 (React/Vue)

---

#### [MED-3] 게이미피케이션 로직 미완성

**문제**: SPEC §2.2.1에서 꽃/나비/정원 확장/계절 배지 시스템을 명시했으나, `GardenStatus` 모델이 없음([CRIT-1])이고 배지 발급 로직도 없음.

```
SPEC 요구:
🌸 꽃 심기: 1회 대화 완료 → flower_count +1
🦋 나비 방문: 3일 연속 → butterfly_count +1
🏡 정원 확장: 7일 연속
🏅 계절 배지: 한 달 참여 → season_badge 업데이트

현재: api/routes/garden.py 라우트 있으나 실제 로직 없음
```

**구현 위치**:
- `database/models.py::GardenStatus` ([CRIT-1] 선행 필요)
- `core/analysis/garden_mapper.py` (배지 발급 로직)
- `api/routes/kakao_webhook.py` (대화 완료 시 꽃 심기 트리거)

---

#### [MED-4] 비즈메시지 친구톡 자격증명 미설정

**문제**: 카카오 비즈메시지 친구톡 전송 코드(`services/kakao_client.py::send_bizmessage_friend_talk`)는 완성되어 있으나, 환경 변수 미설정으로 채널 사용자 대상 push 전송 불가. 현재 상태: `channel_pending`.

**필요 환경 변수** (`.env`에 추가 필요):
```
KAKAO_BIZ_CLIENT_ID=       # 비즈메시지 클라이언트 ID
KAKAO_BIZ_CLIENT_SECRET=   # 비즈메시지 클라이언트 시크릿
KAKAO_SENDER_KEY=          # 발신프로파일키 (40자)
```

**발급 경로**: https://business.kakao.com → 카카오톡 비즈메시지 → 발신프로파일 등록

---

#### [MED-5] MCDI 위험도 임계값 SPEC 불일치

**문제**: `core/analysis/risk_evaluator.py`의 임계값이 SPEC §2.1.3과 다름.

```
SPEC §2.1.3:
GREEN  : MCDI ≥ 70, slope > -0.5/주
YELLOW : MCDI 50-70, slope -0.5~-1.5/주
ORANGE : MCDI 30-50, slope < -1.5/주
RED    : MCDI < 30

현재 코드 (risk_evaluator.py):
GREEN  : MCDI ≥ 80
YELLOW : MCDI 60-80
ORANGE : MCDI 40-60
RED    : MCDI < 40
```

**구현 위치**: `core/analysis/risk_evaluator.py::MCDI_THRESHOLDS` 값 수정

---

#### [MED-6] Rate Limiting 미구현

**문제**: SPEC §5.3.1에서 "Rate Limit: 100 requests/minute per user"를 명시했으나 현재 구현 없음.

**구현 위치**:
- `api/middleware/rate_limiter.py` (신규: Redis 기반 sliding window)
- `api/main.py` (미들웨어 등록)

---

#### [MED-7] JWT 인증 체계 부분 미완성

**문제**: SPEC §5.2에서 Bearer Token (JWT) 인증을 명시했으나, 현재 일부 엔드포인트에 인증이 적용되지 않음.

**구현 위치**:
- `api/routes/auth.py` (JWT 토큰 발급 확인)
- `api/dependencies.py` (get_current_user dependency 전 엔드포인트 적용)

---

### 🟢 LOW (장기 로드맵)

> 론칭 이후 또는 Scale 단계에서 필요한 항목

---

#### [LOW-1] AES-256 암호화 미적용

SPEC §10에서 개인정보(이름, 생년월일, 전화번호)의 AES-256 암호화를 요구했으나 현재 평문 저장.

**구현 위치**: `utils/encryption.py` (신규), DB 마이그레이션

---

#### [LOW-2] Kubernetes 배포 설정 없음

SPEC §8 (배포 전략)에서 Kubernetes 운영을 명시했으나 현재 단일 서버(n8n.softline.co.kr) 운영 중.

**구현 위치**: `k8s/` 디렉토리 (신규), Helm Charts

---

#### [LOW-3] Prometheus + Grafana 모니터링 없음

SPEC §3.2에서 Prometheus + Grafana 메트릭 수집을 명시했으나 현재 없음.

**구현 위치**:
- `api/middleware/metrics.py` (신규: prometheus_client)
- `docker-compose.yml` (prometheus, grafana 서비스 추가)

---

#### [LOW-4] Sentry 에러 트래킹 미연동

SPEC §3.2에서 Sentry 1.39+ 연동을 명시했으나 현재 없음.

**구현 위치**: `api/main.py` (`sentry_sdk.init()` 추가), `.env` SENTRY_DSN 추가

---

#### [LOW-5] 분석 정확도 임상 검증 미실시

SPEC §1.3에서 민감도 85%, 특이도 80%를 목표로 명시했으나 실제 임상 데이터 기반 검증 없음.

**필요 작업**:
- 치매안심센터 협력 → MMSE/MoCA 데이터와 MCDI 상관관계 분석
- Confusion Matrix 계산 스크립트 작성

---

#### [LOW-6] 부하 테스트 미실시

SPEC §1.3에서 일 10,000 메시지 처리를 목표로 명시했으나 성능 테스트 없음.

**구현 위치**: `tests/performance/locust_test.py` (신규), Locust 기반 부하 테스트

---

#### [LOW-7] 의료기관 연계 API 없음

SPEC §2.2.3에서 임상 리포트 PDF, MMSE/MoCA 대비 분석, 치매안심센터 연동을 명시했으나 미구현.

---

#### [LOW-8] GDPR/개인정보 컴플라이언스 없음

SPEC §10에서 GDPR 준수(삭제권, 이식성)를 요구했으나 현재 계정 탈퇴/데이터 삭제 API 없음.

**구현 위치**: `api/routes/users.py` (soft delete → hard delete 지원)

---

## 3. 우선순위별 구현 로드맵

### Phase 1: Beta 완성 (1~2주)

> 현재 베타테스터가 사용할 수 있는 최소 완성 상태

| 순서 | ID | 작업 | 예상 공수 | 파일 |
|------|-----|------|-----------|------|
| 1 | CRIT-1 | DB 모델 추가 (Guardian, GardenStatus 등) | 1일 | `database/models.py` + Alembic |
| 2 | CRIT-2 | User 모델에 garden_name, onboarding_day 추가 | 0.5일 | `database/models.py` + Alembic |
| 3 | CRIT-4 | TimescaleDB hypertable 초기화 스크립트 | 0.5일 | `scripts/init_timescale.py` |
| 4 | MED-5 | MCDI 위험도 임계값 SPEC 맞춤 수정 | 0.5일 | `core/analysis/risk_evaluator.py` |
| 5 | MED-4 | 비즈메시지 자격증명 설정 + 테스트 | 0.5일 | `.env`, 카카오 비즈 콘솔 |
| 6 | CRIT-3 | 온보딩 플로우 기본 구조 (Day 0: 정원 이름 수집) | 2일 | `core/workflow/onboarding_flow.py` |
| 7 | MED-3 | 게이미피케이션 꽃 심기 기본 로직 | 1일 | `core/analysis/garden_mapper.py` |

---

### Phase 2: 론칭 준비 (1개월)

> 200명 사용자 베타 → 1,000명 론칭 전 필요 기능

| 순서 | ID | 작업 | 예상 공수 | 파일 |
|------|-----|------|-----------|------|
| 1 | CRIT-5 | 보호자 알림 실제 발송 구현 | 2일 | `services/notification_service.py` |
| 2 | HIGH-1 | Qdrant 벡터 DB 완전 활성화 | 3일 | `core/memory/episodic_memory.py` |
| 3 | HIGH-2 | 6개 카테고리 라우팅 구현 | 3일 | `core/dialogue/category_selector.py` |
| 4 | HIGH-3 | 이미지 분석 2턴 플로우 | 2일 | `core/dialogue/`, `api/routes/kakao_webhook.py` |
| 5 | HIGH-4 | 중도 이탈 방지 태스크 | 1일 | `tasks/engagement_monitor.py` |
| 6 | HIGH-5 | 보호자 연결 대화 플로우 | 2일 | `core/dialogue/`, `api/routes/users.py` |
| 7 | HIGH-6 | 주간/일간 리포트 생성 | 2일 | `tasks/report_generator.py` |
| 8 | MED-6 | Rate Limiting | 1일 | `api/middleware/rate_limiter.py` |
| 9 | MED-1 | Celery 전환 (APScheduler → Celery) | 3일 | `tasks/celery_app.py` |

---

### Phase 3: 스케일업 (3~6개월)

> 10,000명 사용자, B2B/B2G 확장 준비

| ID | 작업 |
|----|------|
| MED-2 | 보호자 대시보드 프론트엔드 (React) |
| LOW-1 | AES-256 개인정보 암호화 |
| LOW-2 | Kubernetes 배포 설정 |
| LOW-3 | Prometheus + Grafana 모니터링 |
| LOW-4 | Sentry 에러 트래킹 |
| LOW-5 | 임상 데이터 기반 정확도 검증 |
| LOW-6 | Locust 부하 테스트 |
| LOW-7 | 의료기관 연계 API + PDF 리포트 |
| LOW-8 | GDPR 컴플라이언스 (데이터 삭제권) |

---

## 4. 기술 부채 목록

| ID | 부채 내용 | 위치 | 영향도 |
|----|-----------|------|--------|
| DEBT-1 | `NotificationService`의 `mock_mode=True` 기본값 | `services/notification_service.py:75` | 높음 |
| DEBT-2 | `risk_evaluator.py` 임계값이 SPEC과 불일치 | `core/analysis/risk_evaluator.py::MCDI_THRESHOLDS` | 높음 |
| DEBT-3 | APScheduler 사용 (Celery 마이그레이션 필요) | `core/dialogue/scheduler.py`, `services/push_scheduler.py` | 중간 |
| DEBT-4 | Qdrant "skipped" 상태 (벡터 검색 비활성) | `core/memory/episodic_memory.py`, `biographical_memory.py` | 중간 |
| DEBT-5 | Guardian/GardenStatus DB 모델 없이 API 라우트만 존재 | `api/routes/garden.py`, `api/routes/users.py` | 높음 |
| DEBT-6 | TimescaleDB hypertable 초기화 스크립트 없음 | `scripts/` | 높음 |
| DEBT-7 | 테스트 커버리지 80% 미달 추정 (실제 측정 필요) | `tests/` | 중간 |
| DEBT-8 | `structlog` 미도입 (현재 standard logging 사용) | 전체 | 낮음 |
| DEBT-9 | 일부 엔드포인트 JWT 인증 미적용 | `api/routes/` | 중간 |
| DEBT-10 | `confound_check:{user_id}` Redis 키 스키마 미구현 | `core/memory/session_memory.py` | 낮음 |

---

## 5. 검증 기준 (Definition of Done)

### Phase 1 완료 기준

```
□ DB 마이그레이션 성공 (guardians, garden_status 등 5개 테이블 생성)
□ User.garden_name 컬럼 추가 + 기존 사용자 데이터 NULL 허용 마이그레이션 완료
□ TimescaleDB `analysis_timeseries` hypertable 생성 확인
  → SELECT * FROM timescaledb_information.hypertables;
□ MCDI 임계값 SPEC 일치 확인 (GREEN ≥ 70)
□ 첫 대화 시 garden_name 수집 + DB 저장 확인
□ 꽃 심기 로직: 1회 대화 완료 시 flower_count +1 확인
□ MCDI 분석 후 analysis_timeseries 테이블에 데이터 적재 확인
```

### Phase 2 완료 기준

```
□ ORANGE/RED 위험도 시 보호자 카카오톡 실제 발송 확인 (Mock 모드 OFF)
□ Qdrant episodic_memory collection 데이터 적재 + 벡터 검색 응답 < 500ms
□ 6개 카테고리 대화 로그 category 컬럼에 올바르게 기록 확인
□ 3일 비활성 사용자에게 재참여 메시지 자동 발송 확인
□ 비즈메시지 친구톡 채널 사용자 발송 성공 확인 (result_code: 0)
□ 주간 리포트 생성 + 보호자 발송 확인 (매주 일요일 22:00)
□ Rate Limit 초과 시 429 응답 확인 (100 req/min)
□ Celery worker 정상 기동 + beat 스케줄 등록 확인
```

### Phase 3 완료 기준

```
□ 보호자 대시보드 MCDI 트렌드 그래프 렌더링 확인
□ AES-256 암호화 적용 후 DB 컬럼 암호문 저장 확인
□ Kubernetes Pod 3개 이상 운영 시 중복 스케줄 실행 없음 확인
□ Prometheus 메트릭 수집 + Grafana 대시보드 표시 확인
□ Locust 부하 테스트: 일 10,000 메시지 처리 시 평균 응답 < 3초
□ MMSE/MoCA 대비 MCDI 상관관계 분석 리포트 작성 완료
  → 목표: 민감도 ≥ 85%, 특이도 ≥ 80%
```

---

## 요약

| 우선순위 | 건수 | 핵심 내용 |
|----------|------|-----------|
| 🔴 CRITICAL | 5건 | DB 모델 누락, 온보딩 플로우 없음, TimescaleDB 미검증, 알림 Mock 모드 |
| 🟠 HIGH | 6건 | Qdrant 미활성, 카테고리 라우팅 없음, 비활성 사용자 관리 없음 |
| 🟡 MEDIUM | 7건 | Celery 미도입, 보호자 대시보드 없음, 게이미피케이션 미완성 |
| 🟢 LOW | 8건 | 암호화, K8s, 모니터링, 임상 검증, GDPR |
| **합계** | **26건** | |

> SPEC.md 핵심 요구사항 대비 현재 구현률: **약 45%**
> MCDI 분석 코어 로직 완성도: **약 85%** (코드 완성, DB/인프라 연결 부분 미완)
> 인프라/운영 완성도: **약 20%**

---

*이 문서는 2026-02-27 기준으로 소스코드 직접 비교를 통해 작성되었습니다.*
*SPEC.md 버전: 1.0.0 | 분석자: Claude Sonnet 4.6*
