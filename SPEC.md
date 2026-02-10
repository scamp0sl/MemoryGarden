# ?? 기억의 정원 (Memory Garden) - 기술 명세서			
			
> Version: 1.0.0  			
> Last Updated: 2025-01-15  			
> Status: Development			
			
## ?? 목차			
			
- [1. 프로젝트 개요](#1-프로젝트-개요)			
- [2. 기능 요구사항](#2-기능-요구사항)			
- [3. 시스템 아키텍처](#3-시스템-아키텍처)			
- [4. 데이터 모델](#4-데이터-모델)			
- [5. API 명세](#5-api-명세)			
- [6. 파일 구조](#6-파일-구조)			
- [7. 개발 가이드](#7-개발-가이드)			
- [8. 배포 전략](#8-배포-전략)			
- [9. 테스트 전략](#9-테스트-전략)			
- [10. 보안 및 규제](#10-보안-및-규제)			
			
---			
			
## 1. 프로젝트 개요			
			
### 1.1 서비스 개요			
			
**기억의 정원 (Memory Garden)**은 카카오톡 채널을 통해 매일 2~3개의 가벼운 대화를 나누며, 
사용자의 치매 위험 신호(인지 기능 저하)를 조기에 감지하는 AI 기반 디지털 바이오마커 서비스입니다.			
			
**핵심 가치:**			
 - ?? 병원 방문 없이 일상 대화로 조기 감지			
- ?? "평가"가 아닌 "정원 가꾸기" 놀이로 습관화			
- ?? 30일 이상 종단 추적으로 미세 변화 포착			
 - ???????? 가족 참여형 (보호자 대시보드)			
			
### 1.2 비즈니스 목표			
			
| 단계 | 기간 | 목표 |			
|------|------|------|			
| MVP | 2개월 | 20명 내부 테스터, 핵심 기능 검증 |			
| Beta | 3개월 | 200명 사용자, 치매안심센터 협력 |			
| Launch | 6개월 | 1,000명 사용자, 임상 데이터 수집 |			
| Scale | 1년 | 10,000명 사용자, B2B/B2G 확장 |			
			
### 1.3 기술 목표			
			
- ? 순수 Python 기반 (LangGraph 불필요)			
- ? 평균 응답 시간 < 3초			
- ? 일일 처리량 > 10,000 메시지			
- ? 분석 정확도 (민감도 85%, 특이도 80%)			
- ? 데이터 보안 (AES-256 암호화, GDPR 준수)			
			
---			
			
## 2. 기능 요구사항			
			
### 2.1 핵심 기능			
			
#### 2.1.1 대화 시스템			
			
**6개 카테고리:**			
			
| 카테고리 | 영문명 | 측정 대상 | 빈도 |			
|----------|--------|-----------|------|			
| 회상의 꽃밭 | Reminiscence | 일화적 기억, 어휘 풍부도 | 주 2회 |			
| 오늘의 한 접시 | Daily Episodic | 단기 기억, 시각-언어 연계 | 주 3회 |			
| 이름 꽃밭 | Naming | 이름대기, 범주 유창성 | 주 1회 |			
| 시간의 나침반 | Temporal | 시간적 지남력, 계절감 | 주 2회 |			
| 그림 읽기 놀이 | Visual-Linguistic | 시공간 인지, 주의력 | 주 1회 |			
| 선택의 정원 | Non-verbal | 시각적 주의력, 패턴 인식 | 주 1회 |			
			
**대화 흐름 예시:**			
[오전 11:30] ??? "점심시간이 다가오네요! 오늘 뭐 드실 예정이세요? 혹시 사진 찍으시면 정원에 올려주세요! ??"			
			
[사용자] (사진 전송 + "된장찌개 먹었어")			
			
[오후 6:00] ?? "저녁 시간이에요! 오늘 정원에 예쁜 꽃이 피었더라고요. 그런데 기억력 퀴즈 하나! ?? 오늘 점심에 드신 메뉴에 들어간 재료 3가지만 말씀해주실 수 있으세요? (힌트: 국물 요리였어요~)"			
			
#### 2.1.2 MCDI 분석 프레임워크			
			
**6개 분석 지표:**			
MCDI = w₁·LR + w₂·SD + w₃·NC + w₄·TO + w?·ER + w?·RT			
			
가중치 (초기값, 임상 데이터로 최적화 예정):
 w₁ = 0.20 (LR: Lexical Richness)
 w₂ = 0.20 (SD: Semantic Drift)
 w₃ = 0.15 (NC: Narrative Coherence)
 w₄ = 0.15 (TO: Temporal Orientation)
 w? = 0.20 (ER: Episodic Recall)
 w? = 0.10 (RT: Response Time)			
			
**지표별 상세:**			
			
1. **LR (어휘 풍부도)**			
   - 대명사 비율: `pronouns / (pronouns + nouns)`			
   - MATTR (Moving Average TTR): window=20			
   - 구체성 점수: 구체 명사 vs 추상어 비율			
   - 빈 발화 비율: "그거", "뭐더라" 등			
			
2. **SD (의미적 표류)**			
   - 질문-응답 관련도: cosine similarity > 0.65			
   - 문장 간 응집도: 인접 문장 유사도 > 0.55			
   - 주제 이탈 횟수			
   - LLM Judge 논리성 평가 (1-5점)			
			
3. **NC (서사 일관성)**			
   - 서사 구조 요소: 5W1H 포함도			
   - 인과관계 접속사 사용: "그래서", "왜냐하면"			
   - 반복 진술 비율			
   - 시간 순서 역전 탐지			
			
4. **TO (시간적 지남력)**			
   - 요일/날짜 정확도			
   - 계절 적합성			
   - 시제 혼동 탐지			
   - 상대적 시간 표현 정확성			
			
5. **ER (일화 기억)**			
   - 당일 자유 회상 정확도			
   - 단서 재인 정확도			
   - 자유회상-재인 격차 (인코딩 vs 인출)			
   - 모순 진술 탐지 (high/medium/low severity)			
			
6. **RT (반응 시간)**			
   - 메시지 발송 → 응답 지연 시간			
   - 응답 길이 대비 효율성			
   - 타이핑 패턴 (가능 범위 내)			
   - 주차별 변화 추세			
			
#### 2.1.3 위험도 분류 체계			
			
| 레벨 | 조건 | 사용자 메시지 | 보호자 알림 |			
|------|------|---------------|-------------|			
| ?? GREEN | MCDI ≥ 70, slope > -0.5/주 | "정원이 건강하게 자라고 있어요!" | 없음 |			
| ??? YELLOW | MCDI 50-70, slope -0.5~-1.5/주 | "정원에 구름이 조금 낀 것 같아요" | 없음 |			
| ??? ORANGE | MCDI 30-50, slope < -1.5/주, 2개 지표 2σ↓ | "정원에 비가 내리고 있어요. 건강 점검 어떠세요?" | 알림 |			
| ?? RED | MCDI < 30, 지남력 반복 실패, 자기정보 오류 | (보호자 중심 알림) | 긴급 알림 |			
			
#### 2.1.4 메모리 시스템 (4계층)			
Layer 1: Session Memory (Redis, TTL 24h)			
 ├─ 현재 대화 세션 컨텍스트 (최근 10턴)			
 └─ 오늘의 맥락 참조용			
			
Layer 2: Episodic Memory (Qdrant, 영구)			
 ├─ 일화 기억: "2024.12.15 점심에 된장찌개"			
 ├─ 감정 기억: "12.14 딸이 전화해서 기분 좋았다"			
 └─ 메타데이터: timestamp, category, confidence			
			
Layer 3: Biographical Memory (Qdrant + PostgreSQL)			
 ├─ 불변 사실: 이름, 생년월일, 고향, 자녀 이름			
 ├─ 반불변 사실: 거주지, 직업, 건강 상태			
 ├─ 선호도: 좋아하는 음식, 취미			
 └─ 모순 발생 시 버전 관리 (overwrite X, append O)			
			
Layer 4: Analytical Memory (TimescaleDB)			
 ├─ 일별 MCDI 점수 및 하위 지표			
 ├─ 주간/월간 트렌드			
 └─ 이상 감지 이벤트 로그			
			
### 2.2 부가 기능			
			
#### 2.2.1 게이미피케이션			
정원 상태:			
			
?? 꽃 심기: 1회 대화 완료			
?? 나비 방문: 3일 연속 참여			
?? 정원 확장: 7일 연속 참여			
??? 계절 뱃지: 한 달 참여			
			
#### 2.2.2 보호자 대시보드			
			
- 주간 트렌드 시각화 (??????????)			
 - 관찰 사항 요약			
 - 권장 조치 체크리스트			
 - 의사용 리포트 다운로드			
			
#### 2.2.3 의료기관 연계			
			
 - 임상 리포트 생성 (PDF)			
 - MMSE/MoCA 대비 상관관계 분석			
 - 치매안심센터 연동 api			
			
---			
			
## 3. 시스템 아키텍처			
			
### 3.1 전체 아키텍처 다이어그램			
┌─────────────────────────────────────────────────────────┐			
 │ Client Layer │			
 ├─────────────────────────────────────────────────────────┤			
 │ ?? KakaoTalk Channel │ ?? Guardian Web Dashboard │			
 └─────────────┬───────────────────────┬───────────────────┘			
│ │			
 ▼ ▼			
┌─────────────────────────────────────────────────────────┐			
 │ API Gateway (FastAPI) │			
 ├─────────────────────────────────────────────────────────┤			
 │ /api/v1/kakao/webhook │ /api/v1/users/{id}/analysis │			
 └─────────────┬───────────────────────┬───────────────────┘			
│ │			
 ▼ ▼			
┌─────────────────────────────────────────────────────────┐			
 │ Core Workflow Engine (순수 Python) │			
 ├─────────────────────────────────────────────────────────┤			
 │	 │		
 │ MessageProcessor (메인 오케스트레이터) │			
 │ ├─ retrieve_memory() │			
 │ ├─ analyze_response() ← Analyzer (6개 지표) │			
 │ ├─ evaluate_risk() ← RiskEvaluator │			
 │ ├─ [조건부] send_alert() ← NotificationService │			
 │ ├─ plan_next() ← DialogueManager │			
 │ ├─ generate_response() ← LLM Service │			
 │ └─ store_memory() ← MemoryManager │			
 │ │			
 └─────────────┬───────────────────────┬───────────────────┘			
│ │			
 ▼ ▼			
┌─────────────────────────────────────────────────────────┐			
 │ Data Layer │			
 ├─────────────────────────────────────────────────────────┤			
 │ Redis │ Qdrant │ PostgreSQL │ TimescaleDB │			
 │ (Session) │ (Vector) │ (RDBMS) │ (Timeseries)│			
 └─────────────────────────────────────────────────────────┘			
 │			
▼			
┌─────────────────────────────────────────────────────────┐			
 │ External Services │			
 ├─────────────────────────────────────────────────────────┤			
 │ Claude 3.5 │ GPT-4o │ Kakao API │ Email/SMS │			
 └─────────────────────────────────────────────────────────┘			
			
### 3.2 기술 스택			
			
#### Backend			
```yaml			
언어: Python 3.11+			
프레임워크: FastAPI 0.104+			
비동기: asyncio, aiohttp			
타입 체킹: mypy, pydantic 2.0+			
			
Database			
PostgreSQL: 15+ (RDBMS)			
Redis: 7.0+ (Cache, Session)			
Qdrant: 1.7+ (Vector DB)			
TimescaleDB: 2.11+ (Time-series extension for PostgreSQL)			
			
AI/ML			
LLM:			
  - Claude 4.5 Sonnet (Anthropic)			
  - GPT-4o (OpenAI)			
Embedding: text-embedding-3-large (OpenAI, 1536 dim)			
Vision: GPT-4o (이미지 분석)			
NLP: Kiwi 0.15+ (한국어 형태소 분석)			
			
Task Queue			
Celery: 5.3+			
Broker: Redis			
Backend: Redis			
			
Testing			
pytest: 7.4+			
pytest-asyncio: 0.21+			
pytest-cov: 4.1+ (커버리지)			
httpx: 0.25+ (async HTTP client for testing)			
faker: 20.0+ (테스트 데이터 생성)			
			
Monitoring			
Logging: structlog 23.2+			
Metrics: Prometheus + Grafana			
Tracing: Sentry 1.39+			
LLM Monitoring: LangSmith (선택)			
			
DevOps			
Container: Docker 24+, Docker Compose 2.23+			
Orchestration: Kubernetes (프로덕션)			
CI/CD: GitHub Actions			
Reverse Proxy: Nginx 1.24+			
			
3.3 워크플로우 상세			
			
메시지 처리 플로우			
# Pseudo-code			
			
async def process_message(user_id: str, message: str) -> str:			
    """			
    메인 워크플로우			
    """			
    # 1. 컨텍스트 생성			
    ctx = ProcessingContext(user_id, message)			
    			
    # 2. 메모리 검색 (4계층 병렬)			
    ctx.memory = await memory_manager.retrieve_all(user_id, message)			
    # → Redis (세션), Qdrant (일화/전기), TimescaleDB (분석)			
    			
    # 3. 응답 분석 (6개 지표 병렬)			
    ctx.analysis = await analyzer.analyze(message, ctx.memory)			
    # → LR, SD, NC, TO, ER, RT 계산			
    # → MCDI 종합 점수 계산			
    			
    # 4. 위험도 평가			
    ctx.risk_level = await risk_evaluator.evaluate(			
        user_id, ctx.analysis			
    )			
    # → Baseline 대비 z-score 계산			
    # → 4주 기울기 계산			
    # → GREEN/YELLOW/ORANGE/RED 판정			
    			
    # 5. 조건부 알림 (if문)			
    if ctx.risk_level in ["ORANGE", "RED"]:			
        await notification_service.send_guardian_alert(			
            user_id, ctx.risk_level, ctx.analysis			
        )			
        # → 보호자 카카오톡/이메일 발송			
        # → 임상 리포트 PDF 첨부			
    			
    # 6. 교란 변수 체크 (if문)			
    if ctx.should_check_confounds:			
        # 점수 하락 시 수면/우울/약물 등 확인 질문 스케줄			
        await schedule_confound_question(user_id)			
    			
    # 7. 다음 상호작용 계획			
    next_plan = await dialogue_manager.plan_next(			
        user_id, ctx.analysis, ctx.risk_level			
    )			
    # → 카테고리 선택 (weakest metric 우선)			
    # → 난이도 조정 (risk_level 기반)			
    			
    # 8. 응답 생성			
    ctx.response = await dialogue_manager.generate_response(			
        user_id, ctx, next_plan			
    )			
    # → LLM 호출 (Claude/GPT)			
    # → 정원 메타포 적용			
    			
    # 9. 메모리 저장 (4계층 병렬)			
    await memory_manager.store_all(			
        user_id, message, ctx.response, ctx.analysis			
    )			
    # → 사실 추출 후 각 레이어 저장			
    			
    return ctx.response			
			
			
			
4. 데이터 모델			
			
4.1 PostgreSQL 스키마			
			
4.1.1 ERD			
┌─────────────┐         ┌──────────────────┐			
│    users                            │?───────┤  conversations   │			
├─────────────┤   1:N  ├──────────────────┤			
│ id (PK)                             │         │ id (PK)          │			
│ kakao_id                           │         │ user_id (FK)     │			
│ name                                │         │ message          │			
│ birth_date                          │         │ response         │			
│ created_at                          │         │ message_type     │			
└─────────────┘           │ image_url        │			
                                                        │ category         │			
       │                                              │ created_at       │			
       │                                              └──────────────────┘			
       │                                                 │			
       │                                                 │			
       │                                                 ▼			
       │                ┌──────────────────┐			
       │                │ analysis_results │			
       │                ├──────────────────┤			
       │                │ id (PK)          │			
       │                │ conversation_id  │			
       │                │ mcdi_score       │			
       │                │ lr_score         │			
       │                │ sd_score         │			
       │                │ nc_score         │			
       │                │ to_score         │			
       │                │ er_score         │			
       │                │ rt_score         │			
       │                │ risk_level       │			
       │                │ created_at       │			
       │                └──────────────────┘			
       │			
       │ 1:N			
       ▼			
┌─────────────┐         ┌──────────────────┐			
│  guardians                          │    N:M  │ user_guardians   │			
├─────────────┤?────┤──────────────────┤			
│ id (PK)                             │           │ user_id (FK)     │			
│ name                                │         │ guardian_id (FK) │			
│ phone                               │         │ relation         │			
│ email                               │          │ created_at       │			
│ created_at                          │         └──────────────────┘			
└─────────────┘			
       │			
       │ 1:N			
       ▼			
┌─────────────────┐			
│  notifications  │			
├─────────────────┤			
│ id (PK)         │			
│ guardian_id(FK) │			
│ user_id (FK)    │			
│ type            │			
│ content         │			
│ sent_at         │			
│ read_at         │			
└─────────────────┘			
			
4.1.2 테이블 정의			
 -- users 테이블			
CREATE TABLE users (			
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),			
    kakao_id VARCHAR(100) UNIQUE NOT NULL,			
    name VARCHAR(100) NOT NULL,			
    birth_date DATE,			
    gender VARCHAR(10),			
    phone VARCHAR(20),			
    email VARCHAR(100),			
    baseline_mcdi FLOAT,  -- 개인 baseline (14일 후 설정)			
    baseline_established_at TIMESTAMP,			
    created_at TIMESTAMP DEFAULT NOW(),			
    updated_at TIMESTAMP DEFAULT NOW(),			
    deleted_at TIMESTAMP,			
    			
    INDEX idx_kakao_id (kakao_id),			
    INDEX idx_created_at (created_at)			
);			
			
 -- conversations 테이블			
CREATE TABLE conversations (			
    id BIGSERIAL PRIMARY KEY,			
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,			
    message TEXT NOT NULL,			
    response TEXT,			
    message_type VARCHAR(20) DEFAULT 'text',  -- text/image/selection			
    image_url TEXT,			
    category VARCHAR(50),  -- reminiscence/daily_episodic/naming/...			
    response_latency_ms INTEGER,  -- 응답 지연 시간 (밀리초)			
    created_at TIMESTAMP DEFAULT NOW(),			
    			
    INDEX idx_user_created (user_id, created_at),			
    INDEX idx_category (category)			
);			
			
 -- analysis_results 테이블			
CREATE TABLE analysis_results (			
    id BIGSERIAL PRIMARY KEY,			
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,			
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,			
    			
    -- 종합 점수			
    mcdi_score FLOAT NOT NULL,			
    risk_level VARCHAR(20) NOT NULL,  -- GREEN/YELLOW/ORANGE/RED			
    			
    -- 6개 지표			
    lr_score FLOAT,			
    lr_detail JSONB,  -- 상세 분석 결과 (대명사비율, MATTR 등)			
    			
    sd_score FLOAT,			
    sd_detail JSONB,			
    			
    nc_score FLOAT,			
    nc_detail JSONB,			
    			
    to_score FLOAT,			
    to_detail JSONB,			
    			
    er_score FLOAT,			
    er_detail JSONB,			
    			
    rt_score FLOAT,			
    rt_detail JSONB,			
    			
    -- 메타데이터			
    contradictions JSONB,  -- 모순 탐지 결과			
    confounds_detected JSONB,  -- 교란 변수 탐지			
    created_at TIMESTAMP DEFAULT NOW(),			
    			
    INDEX idx_user_created (user_id, created_at),			
    INDEX idx_risk_level (risk_level),			
    INDEX idx_mcdi_score (mcdi_score)			
);			
			
 -- guardians 테이블			
CREATE TABLE guardians (			
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),			
    name VARCHAR(100) NOT NULL,			
    phone VARCHAR(20),			
    email VARCHAR(100),			
    kakao_id VARCHAR(100),  -- 카카오톡 알림용			
    created_at TIMESTAMP DEFAULT NOW(),			
    			
    INDEX idx_phone (phone),			
    INDEX idx_email (email)			
);			
			
 -- user_guardians 테이블 (M:N 관계)			
CREATE TABLE user_guardians (			
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,			
    guardian_id UUID NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,			
    relation VARCHAR(50),  -- daughter/son/spouse/caregiver			
    notification_enabled BOOLEAN DEFAULT TRUE,			
    created_at TIMESTAMP DEFAULT NOW(),			
    			
    PRIMARY KEY (user_id, guardian_id),			
    INDEX idx_user (user_id),			
    INDEX idx_guardian (guardian_id)			
);			
			
 -- notifications 테이블			
CREATE TABLE notifications (			
    id BIGSERIAL PRIMARY KEY,			
    guardian_id UUID NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,			
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,			
    type VARCHAR(50) NOT NULL,  -- concern/urgent/info			
    title VARCHAR(200) NOT NULL,			
    content TEXT NOT NULL,			
    risk_level VARCHAR(20),			
    analysis_snapshot JSONB,  -- 당시 분석 결과 스냅샷			
    sent_at TIMESTAMP DEFAULT NOW(),			
    read_at TIMESTAMP,			
    			
    INDEX idx_guardian_sent (guardian_id, sent_at),			
    INDEX idx_user_sent (user_id, sent_at)			
);			
			
 -- memory_events 테이블 (모순 탐지 이력)			
CREATE TABLE memory_events (			
    id BIGSERIAL PRIMARY KEY,			
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,			
    event_type VARCHAR(50) NOT NULL,  -- fact_stored/contradiction_detected			
    entity VARCHAR(100),  -- family_name/hometown/food_preference			
    old_value TEXT,			
    new_value TEXT,			
    severity VARCHAR(20),  -- high/medium/low			
    confidence FLOAT,			
    conversation_id BIGINT REFERENCES conversations(id),			
    created_at TIMESTAMP DEFAULT NOW(),			
    			
    INDEX idx_user_type (user_id, event_type),			
    INDEX idx_severity (severity)			
);			
			
 -- garden_status 테이블 (게이미피케이션)			
CREATE TABLE garden_status (			
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,			
    flower_count INTEGER DEFAULT 0,			
    butterfly_count INTEGER DEFAULT 0,			
    consecutive_days INTEGER DEFAULT 0,			
    total_conversations INTEGER DEFAULT 0,			
    last_interaction_at TIMESTAMP,			
    season_badge VARCHAR(50),  -- spring_2025/summer_2025			
    updated_at TIMESTAMP DEFAULT NOW()			
);			
			
4.1.3 TimescaleDB Hypertable (시계열 데이터)			
 -- 분석 점수 시계열 (TimescaleDB extension 사용)			
CREATE TABLE analysis_timeseries (			
    user_id UUID NOT NULL,			
    timestamp TIMESTAMP NOT NULL,			
    mcdi_score FLOAT NOT NULL,			
    lr_score FLOAT,			
    sd_score FLOAT,			
    nc_score FLOAT,			
    to_score FLOAT,			
    er_score FLOAT,			
    rt_score FLOAT,			
    risk_level VARCHAR(20),			
    			
    PRIMARY KEY (user_id, timestamp)			
);			
			
 -- Hypertable 변환			
SELECT create_hypertable('analysis_timeseries', 'timestamp');			
			
-- 연속 집계 뷰 (1시간 간격)			
CREATE MATERIALIZED VIEW analysis_hourly			
WITH (timescaledb.continuous) AS			
SELECT			
    user_id,			
    time_bucket('1 hour', timestamp) AS hour,			
    AVG(mcdi_score) AS avg_mcdi,			
    MIN(mcdi_score) AS min_mcdi,			
    MAX(mcdi_score) AS max_mcdi,			
    COUNT(*) AS conversation_count			
FROM analysis_timeseries			
GROUP BY user_id, hour;			
			
 -- 일별 집계 뷰			
CREATE MATERIALIZED VIEW analysis_daily			
WITH (timescaledb.continuous) AS			
SELECT			
    user_id,			
    time_bucket('1 day', timestamp) AS day,			
    AVG(mcdi_score) AS avg_mcdi,			
    STDDEV(mcdi_score) AS stddev_mcdi,			
    COUNT(*) AS conversation_count			
FROM analysis_timeseries			
GROUP BY user_id, day;			
			
4.2 Vector DB 스키마 (Qdrant)			
			
4.2.1 Collection 구조			
# Collection 1: episodic_memory			
{			
    "collection_name": "episodic_memory",			
    "vector_size": 1536,  # text-embedding-3-large			
    "distance": "Cosine",			
    "payload_schema": {			
        "user_id": "keyword",			
        "content": "text",			
        "category": "keyword",  # meal/emotion/event/conversation			
        "timestamp": "datetime",			
        "confidence": "float",			
        "metadata": {			
            "location": "text",			
            "people_mentioned": ["text"],			
            "emotions": ["text"]			
        }			
    },			
    "indexes": [			
        {"field": "user_id", "type": "keyword"},			
        {"field": "category", "type": "keyword"},			
        {"field": "timestamp", "type": "datetime"}			
    ]			
}			
			
# Collection 2: biographical_memory			
{			
    "collection_name": "biographical_memory",			
    "vector_size": 1536,			
    "distance": "Cosine",			
    "payload_schema": {			
        "user_id": "keyword",			
        "entity": "keyword",  # hometown/family_name/food_preference			
        "value": "text",			
        "fact_type": "keyword",  # immutable/semi_mutable/preference			
        "first_mentioned_at": "datetime",			
        "last_confirmed_at": "datetime",			
        "confidence": "float",			
        "version": "integer"  # 모순 발생 시 버전 증가			
    }			
}			
			
# Collection 3: question_history			
{			
    "collection_name": "question_history",			
    "vector_size": 1536,			
    "distance": "Cosine",			
    "payload_schema": {			
        "user_id": "keyword",			
        "question": "text",			
        "category": "keyword",			
        "difficulty": "keyword",  # easy/medium/hard			
        "asked_at": "datetime",			
        "user_response": "text",			
        "response_quality": "float"  # 0-1			
    }			
}			
			
4.2.2 벡터 검색 예시			
# 일화 기억 검색			
search_result = qdrant_client.search(			
    collection_name="episodic_memory",			
    query_vector=embed("오늘 점심 메뉴"),			
    query_filter={			
        "must": [			
            {"key": "user_id", "match": {"value": "user_123"}},			
            {"key": "category", "match": {"value": "meal"}},			
            {			
                "key": "timestamp",			
                "range": {			
                    "gte": "2025-01-15T00:00:00Z",			
                    "lte": "2025-01-15T23:59:59Z"			
                }			
            }			
        ]			
    },			
    limit=5			
)			
			
4.3 Redis 스키마			
# Session Memory 구조			
			
# Key: session:{user_id}			
# Type: Hash			
# TTL: 24 hours			
			
{			
    "user_id": "user_123",			
    "last_message": "오늘 점심에 된장찌개 먹었어요",			
    "last_response": "된장찌개 맛있으셨겠어요! ...",			
    "last_question": "오늘 점심에 들어간 재료 3가지만 말씀해주세요",			
    "last_category": "daily_episodic",			
    "conversation_count_today": 3,			
    "last_interaction_at": "2025-01-15T14:30:00Z"			
}			
			
# Key: garden:{user_id}			
# Type: Hash			
# TTL: None (영구)			
			
{			
    "flower_count": 15,			
    "butterfly_count": 2,			
    "consecutive_days": 5,			
    "season": "winter_2025"			
}			
			
# Key: confound_check:{user_id}			
# Type: String (JSON)			
# TTL: 7 days			
			
{			
    "check_needed": true,			
    "factors": ["sleep_deprivation", "depression"],			
    "scheduled_at": "2025-01-16T10:00:00Z"			
}			
			
			
			
5. API 명세			
			
5.1 Base URL			
Development: http://localhost:8000/api/v1			
Production: https://api.memory-garden.ai/api/v1			
			
5.2 인증			
Type: Bearer Token (JWT)			
Header: Authorization: Bearer {token}			
			
Token 발급:			
POST /api/v1/auth/token			
Request:			
  {			
    "kakao_id": "1234567890",			
    "name": "홍길동"			
  }			
Response:			
  {			
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",			
    "token_type": "bearer",			
    "expires_in": 3600			
  }			
			
5.3 엔드포인트 목록			
			
5.3.1 카카오톡 웹훅			
POST /api/v1/kakao/webhook			
			
Description: 카카오톡 메시지 수신 및 응답 생성			
			
Request Body:			
  {			
    "user_key": "kakao_user_1234567890",			
    "type": "text",  # text/image/button			
    "content": "안녕하세요",			
    "image_url": "https://...",  # type=image일 때			
    "timestamp": "2025-01-15T10:30:00Z"			
  }			
			
Response (200 OK):			
  {			
    "version": "2.0",			
    "template": {			
      "outputs": [			
        {			
          "simpleText": {			
            "text": "안녕하세요! ?? 수진이네 정원에 오신 걸 환영해요!"			
          }			
        }			
      ]			
    }			
  }			
			
Response (500 Error):			
  {			
    "version": "2.0",			
    "template": {			
      "outputs": [			
        {			
          "simpleText": {			
            "text": "앗, 잠시 정원을 가꾸는데 문제가 생겼어요. 조금 후에 다시 이야기 나눠요!"			
          }			
        }			
      ]			
    }			
  }			
			
Rate Limit: 100 requests/minute per user			
			
5.3.2 사용자 관리			
POST /api/v1/users			
			
Description: 사용자 생성 (온보딩)			
			
Request Body:			
  {			
    "kakao_id": "1234567890",			
    "name": "홍길동",			
    "birth_date": "1953-05-15",			
    "gender": "male",			
    "garden_name": "수진이네 정원"			
  }			
			
Response (201 Created):			
  {			
    "id": "550e8400-e29b-41d4-a716-446655440000",			
    "kakao_id": "1234567890",			
    "name": "홍길동",			
    "garden_name": "수진이네 정원",			
    "created_at": "2025-01-15T10:00:00Z"			
  }			
			
---			
			
GET /api/v1/users/{user_id}			
			
Description: 사용자 정보 조회			
			
Response (200 OK):			
  {			
    "id": "550e8400-e29b-41d4-a716-446655440000",			
    "name": "홍길동",			
    "garden_name": "수진이네 정원",			
    "baseline_mcdi": 78.2,			
    "current_mcdi": 72.5,			
    "risk_level": "YELLOW",			
    "consecutive_days": 15,			
    "total_conversations": 42,			
    "garden_status": {			
      "flower_count": 42,			
      "butterfly_count": 5,			
      "season_badge": "winter_2025"			
    }			
  }			
			
5.3.3 대화 이력			
GET /api/v1/users/{user_id}/conversations			
			
Description: 대화 이력 조회 (페이지네이션)			
			
Query Parameters:			
  - page: integer (default: 1)			
  - page_size: integer (default: 20, max: 100)			
  - category: string (optional, filter by category)			
  - start_date: date (optional, YYYY-MM-DD)			
  - end_date: date (optional, YYYY-MM-DD)			
			
Response (200 OK):			
  {			
    "total": 42,			
    "page": 1,			
    "page_size": 20,			
    "conversations": [			
      {			
        "id": 12345,			
        "message": "오늘 점심에 된장찌개 먹었어요",			
        "response": "된장찌개 맛있으셨겠어요! 반찬은 뭐였나요?",			
        "category": "daily_episodic",			
        "mcdi_score": 75.2,			
        "risk_level": "YELLOW",			
        "created_at": "2025-01-15T12:30:00Z"			
      },			
      ...			
    ]			
  }			
			
5.3.4 분석 결과			
GET /api/v1/users/{user_id}/analysis			
			
Description: 분석 결과 및 트렌드 조회			
			
Query Parameters:			
  - period: string (day/week/month, default: week)			
  - start_date: date (optional)			
  - end_date: date (optional)			
			
Response (200 OK):			
  {			
    "user_id": "550e8400-e29b-41d4-a716-446655440000",			
    "period": "week",			
    "start_date": "2025-01-08",			
    "end_date": "2025-01-15",			
    "baseline": {			
      "mcdi": 78.2,			
      "established_at": "2025-01-07",			
      "scores": {			
        "LR": 80.1,			
        "SD": 82.3,			
        "NC": 78.5,			
        "TO": 85.0,			
        "ER": 77.4,			
        "RT": 72.1			
      }			
    },			
    "current": {			
      "mcdi": 72.5,			
      "risk_level": "YELLOW",			
      "scores": {			
        "LR": 75.2,			
        "SD": 78.1,			
        "NC": 72.0,			
        "TO": 80.5,			
        "ER": 68.3,			
        "RT": 70.0			
      }			
    },			
    "trend": {			
      "mcdi_slope": -0.8,  # per week			
      "direction": "declining",			
      "significance": "moderate"			
    },			
    "daily_data": [			
      {			
        "date": "2025-01-15",			
        "mcdi": 72.5,			
        "risk_level": "YELLOW",			
        "conversation_count": 3			
      },			
      ...			
    ],			
    "alerts": [			
      {			
        "type": "metric_decline",			
        "metric": "ER",			
        "severity": "moderate",			
        "message": "일화 기억 점수가 baseline 대비 -1.5σ 하락했습니다"			
      }			
    ]			
  }			
			
---			
			
GET /api/v1/users/{user_id}/analysis/report			
			
Description: 의사용 임상 리포트 생성			
			
Query Parameters:			
  - format: string (pdf/json, default: pdf)			
  - period_days: integer (default: 30)			
			
Response (200 OK):			
  Content-Type: application/pdf			
  Content-Disposition: attachment; filename="memory_garden_report_{user_id}_{date}.pdf"			
  			
  [PDF Binary Data]			
			
5.3.5 보호자 관리			
POST /api/v1/users/{user_id}/guardians			
			
Description: 보호자 추가			
			
Request Body:			
  {			
    "name": "김수진",			
    "relation": "daughter",			
    "phone": "010-1234-5678",			
    "email": "sujin@example.com",			
    "kakao_id": "sujin_kakao"			
  }			
			
Response (201 Created):			
  {			
    "id": "guardian_uuid",			
    "name": "김수진",			
    "relation": "daughter",			
    "notification_enabled": true			
  }			
			
---			
			
GET /api/v1/guardians/{guardian_id}/dashboard			
			
Description: 보호자 대시보드 데이터			
			
Response (200 OK):			
  {			
    "guardian": {			
      "id": "guardian_uuid",			
      "name": "김수진"			
    },			
    "users": [			
      {			
        "id": "user_uuid",			
        "name": "홍길동",			
        "relation": "father",			
        "current_risk_level": "YELLOW",			
        "mcdi_score": 72.5,			
        "weekly_trend": "????????????",			
        "last_interaction": "2시간 전",			
        "alerts": [			
          {			
            "type": "concern",			
            "message": "최근 2주간 어휘 다양성이 감소했습니다",			
            "created_at": "2025-01-15T10:00:00Z"			
          }			
        ]			
      }			
    ],			
    "recommendations": [			
      {			
        "priority": "high",			
        "action": "치매안심센터 무료 검사 예약",			
        "reason": "MCDI 점수가 4주 연속 하락 중",			
        "link": "https://..."			
      }			
    ]			
  }			
			
5.4 에러 코드			
400 Bad Request:			
  {			
    "error": "validation_error",			
    "message": "Invalid request body",			
    "details": {			
      "field": "birth_date",			
      "error": "Invalid date format. Expected YYYY-MM-DD"			
    }			
  }			
			
401 Unauthorized:			
  {			
    "error": "unauthorized",			
    "message": "Missing or invalid authentication token"			
  }			
			
404 Not Found:			
  {			
    "error": "not_found",			
    "message": "User not found",			
    "resource_id": "550e8400-e29b-41d4-a716-446655440000"			
  }			
			
429 Too Many Requests:			
  {			
    "error": "rate_limit_exceeded",			
    "message": "Too many requests. Please try again later.",			
    "retry_after": 60			
  }			
			
500 Internal Server Error:			
  {			
    "error": "internal_server_error",			
    "message": "An unexpected error occurred",			
    "request_id": "req_abc123"			
  }			
			
			
			
6. 파일 구조			
			
6.1 전체 디렉토리 트리			
memory-garden/			
├── README.md			
├── requirements.txt              # Python 의존성			
├── .env.example                  # 환경 변수 템플릿			
├── .gitignore			
├── docker-compose.yml            # 로컬 개발 환경			
├── Dockerfile			
├── pyproject.toml                # Poetry 설정 (선택)			
├── setup.py			
│			
├── config/			
│   ├── __init__.py			
│   ├── settings.py               # Pydantic BaseSettings			
│   ├── prompts.py                # LLM 프롬프트 템플릿			
│   └── constants.py              # 상수 정의			
│			
├── api/			
│   ├── __init__.py			
│   ├── main.py                   # FastAPI 앱 엔트리포인트			
│   ├── dependencies.py           # 의존성 주입			
│   ├── middleware.py             # 인증, 로깅, CORS			
│   │			
│   ├── routes/			
│   │   ├── __init__.py			
│   │   ├── kakao.py              # 카카오톡 웹훅			
│   │   ├── user.py               # 사용자 관리			
│   │   ├── conversation.py       # 대화 이력			
│   │   ├── analysis.py           # 분석 결과			
│   │   └── guardian.py           # 보호자 대시보드			
│   │			
│   └── schemas/			
│       ├── __init__.py			
│       ├── user.py               # Pydantic 스키마			
│       ├── conversation.py			
│       ├── analysis.py			
│       └── notification.py			
│			
├── core/			
│   ├── __init__.py			
│   │			
│   ├── workflow/			
│   │   ├── __init__.py			
│   │   ├── message_processor.py  # ?? 메인 워크플로우			
│   │   ├── context.py            # ProcessingContext			
│   │   └── pipeline.py           # 파이프라인 헬퍼			
│   │			
│   ├── analysis/			
│   │   ├── __init__.py			
│   │   ├── analyzer.py           # ?? 분석 통합			
│   │   ├── mcdi_calculator.py			
│   │   ├── lexical_richness.py			
│   │   ├── semantic_drift.py			
│   │   ├── narrative_coherence.py			
│   │   ├── temporal_orientation.py			
│   │   ├── episodic_recall.py			
│   │   ├── response_time.py			
│   │   ├── contradiction_detector.py			
│   │   └── risk_evaluator.py     # ?? 위험도 평가			
│   │			
│   ├── dialogue/			
│   │   ├── __init__.py			
│   │   ├── dialogue_manager.py   # ?? 대화 통합			
│   │   ├── question_generator.py			
│   │   ├── category_selector.py			
│   │   ├── difficulty_adapter.py			
│   │   └── response_formatter.py			
│   │			
│   ├── memory/			
│   │   ├── __init__.py			
│   │   ├── memory_manager.py     # ?? 메모리 통합			
│   │   ├── session_memory.py			
│   │   ├── episodic_memory.py			
│   │   ├── biographical_memory.py			
│   │   ├── analytical_memory.py			
│   │   └── fact_extractor.py			
│   │			
│   └── nlp/			
│       ├── __init__.py			
│       ├── morphological_analyzer.py			
│       ├── embedder.py			
│       ├── sentence_splitter.py			
│       └── korean_utils.py			
│			
├── services/			
│   ├── __init__.py			
│   ├── llm_service.py            # Claude/GPT API			
│   ├── vision_service.py         # 이미지 분석			
│   ├── kakao_service.py          # 카카오톡 메시지 전송			
│   ├── notification_service.py   # 보호자 알림			
│   ├── scheduler_service.py      # 스케줄링			
│   └── report_generator.py       # PDF 리포트			
│			
├── database/			
│   ├── __init__.py			
│   ├── postgres.py               # SQLAlchemy 연결			
│   ├── redis_client.py			
│   ├── vector_db.py              # Qdrant 연결			
│   └── timescale.py              # TimescaleDB			
│			
├── models/			
│   ├── __init__.py			
│   ├── user.py                   # SQLAlchemy 모델			
│   ├── conversation.py			
│   ├── analysis_result.py			
│   ├── memory_event.py			
│   ├── notification.py			
│   └── guardian.py			
│			
├── utils/			
│   ├── __init__.py			
│   ├── logger.py                 # structlog 설정			
│   ├── validators.py			
│   ├── encryption.py			
│   ├── metrics.py			
│   └── exceptions.py             # 커스텀 예외			
│			
├── tasks/			
│   ├── __init__.py			
│   ├── celery_app.py             # Celery 설정			
│   ├── delayed_questions.py      # 지연 질문 전송			
│   ├── daily_summary.py          # 일일 요약			
│   └── risk_monitoring.py        # 위험도 모니터링			
│			
├── tests/			
│   ├── __init__.py			
│   ├── conftest.py               # pytest fixtures			
│   ├── test_workflow/			
│   │   ├── __init__.py			
│   │   ├── test_message_processor.py			
│   │   └── test_context.py			
│   ├── test_core/			
│   │   ├── __init__.py			
│   │   ├── test_analysis.py			
│   │   ├── test_dialogue.py			
│   │   └── test_memory.py			
│   ├── test_services/			
│   │   ├── __init__.py			
│   │   ├── test_llm_service.py			
│   │   └── test_kakao_service.py			
│   └── test_api/			
│       ├── __init__.py			
│       └── test_routes.py			
│			
├── scripts/			
│   ├── init_db.py                # DB 초기화			
│   ├── seed_data.py              # 테스트 데이터			
│   └── migrate.py                # 마이그레이션			
│			
├── alembic/			
│   ├── env.py			
│   ├── script.py.mako			
│   └── versions/			
│       └── 001_initial_schema.py			
│			
└── docs/			
    ├── CODING_CONVENTION.md			
    ├── ADR.md                    # Architecture Decision Records			
    ├── PROMPT_GUIDE.md			
    └── CODE_REVIEW_CHECKLIST.md			
			
6.2 핵심 파일 역할 요약			
			
파일	역할	담당 개발자	
core/workflow/message_processor.py	전체 워크플로우 조율	Dev A	
core/analysis/analyzer.py	6개 지표 통합 분석	Dev A	
core/dialogue/dialogue_manager.py	대화 생성 및 질문 전략	Dev A	
core/memory/memory_manager.py	4계층 메모리 관리	Dev B	
services/llm_service.py	LLM API 호출	Dev B	
api/routes/kakao.py	카카오톡 웹훅 처리	Dev C	
api/main.py	FastAPI 앱 설정	Dev C	
			
			
7. 개발 가이드			
			
7.1 로컬 개발 환경 설정			
# 1. 저장소 클론			
git clone https://github.com/your-org/memory-garden.git			
cd memory-garden			
			
# 2. Python 가상환경 생성			
python3.11 -m venv venv			
source venv/bin/activate  # Windows: venv\Scripts\activate			
			
# 3. 의존성 설치			
pip install -r requirements.txt			
			
# 4. 환경 변수 설정			
cp .env.example .env			
# .env 파일 편집하여 API 키 입력			
			
# 5. Docker Compose로 DB 실행			
docker-compose up -d postgres redis qdrant			
			
# 6. DB 초기화			
python scripts/init_db.py			
			
# 7. 개발 서버 실행			
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000			
			
# 8. 테스트 실행			
pytest -v			
			
# 9. 코드 포맷팅			
black .			
isort .			
			
7.2 환경 변수			
# .env.example			
			
# Application			
APP_ENV=development			
DEBUG=True			
LOG_LEVEL=INFO			
			
# Database			
DATABASE_URL=postgresql://memgarden:password@localhost:5432/memory_garden			
REDIS_URL=redis://localhost:6379/0			
QDRANT_URL=http://localhost:6333			
QDRANT_API_KEY=your_qdrant_api_key			
			
# AI Services			
CLAUDE_API_KEY=sk-ant-api03-...			
OPENAI_API_KEY=sk-...			
CLAUDE_MODEL=claude-3-5-sonnet-20241022			
GPT_MODEL=gpt-4o-2024-08-06			
			
# Kakao			
KAKAO_REST_API_KEY=your_kakao_rest_api_key			
KAKAO_ADMIN_KEY=your_kakao_admin_key			
KAKAO_CHANNEL_ID=your_channel_id			
			
# Celery			
CELERY_BROKER_URL=redis://localhost:6379/1			
CELERY_RESULT_BACKEND=redis://localhost:6379/2			
			
# Security			
SECRET_KEY=your-secret-key-here-change-in-production			
JWT_ALGORITHM=HS256			
JWT_EXPIRATION_HOURS=24			
			
# Monitoring			
SENTRY_DSN=https://...@sentry.io/...			
			
7.3 개발 워크플로우			
			
브랜치 전략			
main (프로덕션)			
  ↓			
develop (개발 통합)			
  ↓			
├─ feature/dev-a/{feature-name}			
├─ feature/dev-b/{feature-name}			
└─ feature/dev-c/{feature-name}			
			
커밋 메시지 규칙			
<type>(<scope>): <subject>			
<body>			
<footer>			
Types:			
 - feat: 새 기능			
 - fix: 버그 수정			
 - docs: 문서 수정			
 - style: 코드 포맷 (로직 변경 없음)			
 - refactor: 리팩토링			
 - test: 테스트 추가/수정			
 - chore: 빌드, 설정 파일 수정			
			
Example:			
 feat(analysis): Add lexical richness analyzer			
 - Implement pronoun ratio calculation			
 - Add MATTR algorithm			
 - Include empty speech detection			
 Closes #42			
			
7.4 코드 리뷰 체크리스트			
## 코드 품질			
- [ ] 타입 힌팅 모든 함수에 추가			
- [ ] Docstring 작성 (Google Style)			
- [ ] 에러 처리 (try-except)			
- [ ] 로깅 추가 (적절한 레벨)			
			
## 테스트			
- [ ] 단위 테스트 작성			
- [ ] 커버리지 80% 이상			
- [ ] 엣지 케이스 포함			
			
## 성능			
- [ ] N+1 쿼리 없음			
- [ ] 비동기 IO 작업은 async/await			
- [ ] 캐싱 적절히 사용			
			
## 보안			
- [ ] SQL Injection 방어			
- [ ] API 키 환경변수로 관리			
- [ ] 민감정보 암호화			
			
8. 배포 전략			
			
8.1 Docker Compose (개발)			
# docker-compose.yml			
			
version: '3.8'			
			
services:			
  api:			
    build: .			
    ports:			
      - "8000:8000"			
    environment:			
      - DATABASE_URL=postgresql://memgarden:password@postgres:5432/memory_garden			
      - REDIS_URL=redis://redis:6379/0			
      - QDRANT_URL=http://qdrant:6333			
    depends_on:			
      - postgres			
      - redis			
      - qdrant			
    volumes:			
      - .:/app			
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload			
			
  postgres:			
    image: timescale/timescaledb:latest-pg15			
    environment:			
      POSTGRES_DB: memory_garden			
      POSTGRES_USER: memgarden			
      POSTGRES_PASSWORD: password			
    ports:			
      - "5432:5432"			
    volumes:			
      - postgres_data:/var/lib/postgresql/data			
			
  redis:			
    image: redis:7-alpine			
    ports:			
      - "6379:6379"			
    volumes:			
      - redis_data:/data			
			
  qdrant:			
    image: qdrant/qdrant:v1.7.4			
    ports:			
      - "6333:6333"			
      - "6334:6334"			
    volumes:			
      - qdrant_data:/qdrant/storage			
			
  celery_worker:			
    build: .			
    command: celery -A tasks.celery_app worker --loglevel=info			
    environment:			
      - CELERY_BROKER_URL=redis://redis:6379/1			
    depends_on:			
      - redis			
    volumes:			
      - .:/app			
			
  celery_beat:			
    build: .			
    command: celery -A tasks.celery_app beat --loglevel=info			
    environment:			
      - CELERY_BROKER_URL=redis://redis:6379/1			
    depends_on:			
      - redis			
    volumes:			
      - .:/app			
			
volumes:			
  postgres_data:			
  redis_data:			
  qdrant_data:			
			
8.2 Dockerfile			
# Dockerfile			
			
FROM python:3.11-slim			
			
WORKDIR /app			
			
# 시스템 의존성 설치			
RUN apt-get update && apt-get install -y \			
    build-essential \			
    libpq-dev \			
    && rm -rf /var/lib/apt/lists/*			
			
# Python 의존성 설치			
COPY requirements.txt .			
RUN pip install --no-cache-dir -r requirements.txt			
			
# 애플리케이션 코드 복사			
COPY . .			
			
# 비root 사용자 생성			
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app			
USER appuser			
			
# 헬스체크			
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \			
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"			
			
EXPOSE 8000			
			
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]			
			
8.3 Kubernetes (프로덕션)			
# k8s/deployment.yaml			
			
apiVersion: apps/v1			
kind: Deployment			
metadata:			
  name: memory-garden-api			
spec:			
  replicas: 3			
  selector:			
    matchLabels:			
      app: memory-garden-api			
  template:			
    metadata:			
      labels:			
        app: memory-garden-api			
    spec:			
      containers:			
      - name: api			
        image: memory-garden:latest			
        ports:			
        - containerPort: 8000			
        env:			
        - name: DATABASE_URL			
          valueFrom:			
            secretKeyRef:			
              name: memory-garden-secrets			
              key: database-url			
        - name: CLAUDE_API_KEY			
          valueFrom:			
            secretKeyRef:			
              name: memory-garden-secrets			
              key: claude-api-key			
        resources:			
          requests:			
            memory: "512Mi"			
            cpu: "500m"			
          limits:			
            memory: "1Gi"			
            cpu: "1000m"			
        livenessProbe:			
          httpGet:			
            path: /health			
            port: 8000			
          initialDelaySeconds: 30			
          periodSeconds: 10			
        readinessProbe:			
          httpGet:			
            path: /ready			
            port: 8000			
          initialDelaySeconds: 5			
          periodSeconds: 5			
			
---			
apiVersion: v1			
kind: Service			
metadata:			
  name: memory-garden-api			
spec:			
  type: LoadBalancer			
  ports:			
  - port: 80			
    targetPort: 8000			
  selector:			
    app: memory-garden-api			
			
8.4 CI/CD (GitHub Actions)			
# .github/workflows/ci.yml			
			
name: CI/CD			
			
on:			
  push:			
    branches: [main, develop]			
  pull_request:			
    branches: [main, develop]			
			
jobs:			
  test:			
    runs-on: ubuntu-latest			
    			
    services:			
      postgres:			
        image: postgres:15			
        env:			
          POSTGRES_DB: test_db			
          POSTGRES_USER: test_user			
          POSTGRES_PASSWORD: test_pass			
        ports:			
          - 5432:5432			
      			
      redis:			
        image: redis:7-alpine			
        ports:			
          - 6379:6379			
    			
    steps:			
    - uses: actions/checkout@v3			
    			
    - name: Set up Python			
      uses: actions/setup-python@v4			
      with:			
        python-version: '3.11'			
    			
    - name: Install dependencies			
      run: |			
        pip install -r requirements.txt			
        pip install pytest pytest-cov black isort mypy			
    			
    - name: Run linters			
      run: |			
        black --check .			
        isort --check-only .			
        mypy .			
    			
    - name: Run tests			
      env:			
        DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_db			
        REDIS_URL: redis://localhost:6379/0			
      run: |			
        pytest --cov=. --cov-report=xml --cov-report=html			
    			
    - name: Upload coverage			
      uses: codecov/codecov-action@v3			
      with:			
        files: ./coverage.xml			
			
  build:			
    runs-on: ubuntu-latest			
    needs: test			
    if: github.ref == 'refs/heads/main'			
    			
    steps:			
    - uses: actions/checkout@v3			
    			
    - name: Build Docker image			
      run: |			
        docker build -t memory-garden:${{ github.sha }} .			
    			
    - name: Push to registry			
      run: |			
        echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin			
        docker push memory-garden:${{ github.sha }}			
			
9. 테스트 전략			
			
9.1 테스트 피라미드			
        ┌─────────────────┐			
        │ E2E Tests (5%)  │  ← 전체 플로우			
        ├─────────────────┤			
        │ Integration     │			
        │ Tests (25%)     │  ← API, DB 연동			
        ├─────────────────┤			
        │                 │			
        │ Unit Tests      │			
        │ (70%)           │  ← 개별 함수/클래스			
        │                 │			
        └─────────────────┘			
			
9.2 단위 테스트 예시			
# tests/test_core/test_analysis.py			
			
import pytest			
from core.analysis.lexical_richness import LexicalRichnessAnalyzer			
			
@pytest.fixture			
def lr_analyzer():			
    return LexicalRichnessAnalyzer()			
			
@pytest.mark.asyncio			
async def test_lexical_richness_normal_response(lr_analyzer):			
    """정상 응답: 구체적인 명사 사용"""			
    # Arrange			
    message = "봄이면 우리 엄마가 꼭 쑥을 뜯으러 뒷산에 가셨어. 쑥떡을 만드셨지."			
    			
    # Act			
    result = await lr_analyzer.analyze(message)			
    			
    # Assert			
    assert result["score"] > 70			
    assert result["pronoun_ratio"] < 0.15			
    assert result["concreteness"] > 0.7			
			
@pytest.mark.asyncio			
async def test_lexical_richness_empty_speech(lr_analyzer):			
    """비정상 응답: 빈 발화 많음"""			
    # Arrange			
    message = "그거... 뭐... 있잖아... 그런 거 했지... 뭐였더라..."			
    			
    # Act			
    result = await lr_analyzer.analyze(message)			
    			
    # Assert			
    assert result["score"] < 50			
    assert result["pronoun_ratio"] > 0.3			
    assert result["empty_speech_ratio"] > 0.4			
			
@pytest.mark.asyncio			
async def test_lexical_richness_with_empty_input(lr_analyzer):			
    """엣지 케이스: 빈 입력"""			
    # Arrange			
    message = ""			
    			
    # Act & Assert			
    with pytest.raises(ValueError, match="Message cannot be empty"):			
        await lr_analyzer.analyze(message)			
			
9.3 통합 테스트 예시			
# tests/test_api/test_routes.py			
			
import pytest			
from fastapi.testclient import TestClient			
from api.main import app			
			
client = TestClient(app)			
			
@pytest.fixture			
def test_user(test_db):			
    """테스트용 사용자 생성"""			
    user = {			
        "kakao_id": "test_kakao_123",			
        "name": "테스트 사용자",			
        "birth_date": "1950-01-01"			
    }			
    response = client.post("/api/v1/users", json=user)			
    assert response.status_code == 201			
    return response.json()			
			
def test_kakao_webhook_text_message(test_user):			
    """카카오톡 텍스트 메시지 처리"""			
    # Arrange			
    payload = {			
        "user_key": "test_kakao_123",			
        "type": "text",			
        "content": "안녕하세요",			
        "timestamp": "2025-01-15T10:00:00Z"			
    }			
    			
    # Act			
    response = client.post("/api/v1/kakao/webhook", json=payload)			
    			
    # Assert			
    assert response.status_code == 200			
    data = response.json()			
    assert "template" in data			
    assert "outputs" in data["template"]			
    assert len(data["template"]["outputs"]) > 0			
			
def test_analysis_endpoint(test_user):			
    """분석 결과 조회"""			
    # Arrange			
    user_id = test_user["id"]			
    			
    # Act			
    response = client.get(f"/api/v1/users/{user_id}/analysis?period=week")			
    			
    # Assert			
    assert response.status_code == 200			
    data = response.json()			
    assert "baseline" in data			
    assert "current" in data			
    assert "trend" in data			
			
9.4 E2E 테스트 시나리오			
# tests/test_e2e/test_user_journey.py			
			
@pytest.mark.e2e			
@pytest.mark.asyncio			
async def test_30day_user_journey():			
    """30일 사용자 여정 시뮬레이션"""			
    			
    # Day 0: 온보딩			
    user = await create_test_user("홍길동", "1950-05-15")			
    			
    # Day 1-14: Baseline 설정			
    for day in range(1, 15):			
        # 일일 2-3회 대화			
        for _ in range(2):			
            message = generate_realistic_message(day)			
            response = await send_message(user["id"], message)			
            assert response is not None			
    			
    # Baseline 확인			
    analysis = await get_user_analysis(user["id"])			
    assert analysis["baseline"]["mcdi"] is not None			
    assert 70 <= analysis["baseline"]["mcdi"] <= 90  # 정상 범위			
    			
    # Day 15-30: 모니터링			
    for day in range(15, 31):			
        # 점진적 점수 하락 시뮬레이션			
        degraded_message = generate_degraded_message(day - 14)			
        response = await send_message(user["id"], degraded_message)			
    			
    # Day 30: 위험도 확인			
    final_analysis = await get_user_analysis(user["id"])			
    			
    # ORANGE 레벨 도달 확인			
    assert final_analysis["current"]["risk_level"] in ["YELLOW", "ORANGE"]			
    			
    # 보호자 알림 발송 확인			
    notifications = await get_guardian_notifications(user["id"])			
    assert len(notifications) > 0			
    assert notifications[0]["type"] in ["concern", "urgent"]			
			
10. 보안 및 규제			
			
10.1 데이터 보안			
			
암호화			
# utils/encryption.py			
			
from cryptography.fernet import Fernet			
from config.settings import settings			
			
class DataEncryption:			
    """AES-256 암호화"""			
    			
    def __init__(self):			
        self.cipher = Fernet(settings.ENCRYPTION_KEY)			
    			
    def encrypt(self, plaintext: str) -> str:			
        """텍스트 암호화"""			
        return self.cipher.encrypt(plaintext.encode()).decode()			
    			
    def decrypt(self, ciphertext: str) -> str:			
        """텍스트 복호화"""			
        return self.cipher.decrypt(ciphertext.encode()).decode()			
			
# 사용 예시			
encryption = DataEncryption()			
			
# 대화 내용 저장 시			
encrypted_message = encryption.encrypt(user_message)			
db.store(encrypted_message)			
			
# 의사에게 전달 시에만 복호화			
original_message = encryption.decrypt(encrypted_message)			
			
개인정보 비식별화			
# utils/anonymization.py			
			
import hashlib			
			
def anonymize_user_id(user_id: str) -> str:			
    """사용자 ID 해싱"""			
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]			
			
def mask_phone(phone: str) -> str:			
    """전화번호 마스킹: 010-1234-5678 → 010-****-5678"""			
    return f"{phone[:3]}-****-{phone[-4:]}"			
			
def mask_name(name: str) -> str:			
    """이름 마스킹: 홍길동 → 홍*동"""			
    if len(name) <= 2:			
        return name[0] + "*"			
    return name[0] + "*" * (len(name) - 2) + name[-1]			
			
10.2 GDPR 준수			
# api/routes/user.py			
			
@router.delete("/api/v1/users/{user_id}")			
async def delete_user_data(user_id: str, db: Session = Depends(get_db)):			
    """			
    사용자 데이터 완전 삭제 (Right to be Forgotten)			
    			
    삭제 대상:			
    - PostgreSQL: users, conversations, analysis_results			
    - Qdrant: episodic_memory, biographical_memory			
    - Redis: session 데이터			
    - TimescaleDB: analysis_timeseries			
    """			
    # 1. RDBMS 삭제 (CASCADE)			
    db.query(User).filter(User.id == user_id).delete()			
    			
    # 2. Vector DB 삭제			
    qdrant_client.delete(			
        collection_name="episodic_memory",			
        points_selector={"filter": {"user_id": user_id}}			
    )			
    			
    # 3. Redis 삭제			
    redis_client.delete(f"session:{user_id}")			
    redis_client.delete(f"garden:{user_id}")			
    			
    # 4. 로그 기록 (감사용)			
    logger.info(f"User data deleted: {user_id}", extra={"gdpr": True})			
    			
    return {"message": "All user data has been permanently deleted"}			
			
10.3 의료기기 규제 대응			
			
면책 조항			
# api/routes/analysis.py			
			
MEDICAL_DISCLAIMER = """			
?? 중요 고지사항			
			
본 서비스는 의학적 진단을 제공하지 않습니다.			
'기억의 정원'은 일상 대화 분석을 통한 참고 정보를 제공하는 			
건강관리 서비스이며, 의료 전문가의 진단, 치료, 처방을 대체할 수 없습니다.			
			
분석 결과에 이상이 감지될 경우, 반드시 의료 전문가와 상담하시기 바랍니다.			
			
본 서비스는 식품의약품안전처의 의료기기로 허가받지 않았으며,			
질병의 예방, 진단, 치료를 목적으로 하지 않습니다.			
"""

@router.get(/api/v1/users/{user_id}/analysis/report"")"			
async def get_clinical_report(user_id: str):			
    """임상 리포트 생성 (의사 전달용)"""			
    report = generate_report(user_id)			
    			
    # 면책 조항 포함			
    report["disclaimer"] = MEDICAL_DISCLAIMER			
    			
    return report			
			
인허가 로드맵			
Phase 1 (MVP~Beta): 건강관리 서비스			
- 포지셔닝: "일상 대화 분석 서비스"			
 - 면책 조항 명시			
 - 진단 용어 사용 금지			
			
Phase 2 (임상 검증): 의료기기 준비			
- 1,000명 임상 데이터 수집			
 - MMSE/MoCA 대비 상관관계 분석			
 - 민감도/특이도 논문 발표 (SCI급)			
 - 식약처 사전 상담			
			
Phase 3 (인허가): 디지털 치료기기 신청			
 - SaMD (Software as Medical Device) 등급 판정			
 - 임상시험 계획서 제출			
 - 품목 허가 신청			
- 예상 소요 기간: 12~18개월			
			
Phase 4 (보험 연계): 건강보험 적용			
 - 요양급여 대상 검토			
 - 수가 산정			
 - 치매안심센터 공식 연동			
			
10.4 감사 로그			
# utils/audit_logger.py			
			
from datetime import datetime			
from typing import Dict, Any			
import json			
			
class AuditLogger:			
    """감사 로그 (의료기기 인허가 대비)"""			
    			
    @staticmethod			
    def log_analysis(			
        user_id: str,			
        analysis_result: Dict[str, Any],			
        llm_provider: str,			
        model_version: str			
    ):			
        """분석 수행 로그"""			
        audit_log = {			
            "timestamp": datetime.now().isoformat(),			
            "event_type": "analysis_performed",			
            "user_id": user_id,			
            "mcdi_score": analysis_result["mcdi_score"],			
            "risk_level": analysis_result["risk_level"],			
            "llm_provider": llm_provider,			
            "model_version": model_version,			
            "analysis_version": "v1.0.0"			
        }			
        			
        # 별도 감사 로그 DB에 저장			
        save_audit_log(audit_log)			
    			
    @staticmethod			
    def log_notification(			
        user_id: str,			
        guardian_id: str,			
        notification_type: str,			
        content: str			
    ):			
        """알림 발송 로그"""			
        audit_log = {			
            "timestamp": datetime.now().isoformat(),			
            "event_type": "notification_sent",			
            "user_id": user_id,			
            "guardian_id": guardian_id,			
            "type": notification_type,			
            "content_hash": hashlib.sha256(content.encode()).hexdigest()			
        }			
        			
        save_audit_log(audit_log)			
    			
    @staticmethod			
    def log_data_access(			
        accessor_id: str,			
        user_id: str,			
        access_type: str,			
        data_category: str			
    ):			
        """데이터 접근 로그 (GDPR)"""			
        audit_log = {			
            "timestamp": datetime.now().isoformat(),			
            "event_type": "data_access",			
            "accessor_id": accessor_id,			
            "user_id": user_id,			
            "access_type": access_type,  # read/write/delete			
            "data_category": data_category  # conversation/analysis/personal_info			
        }			
        			
        save_audit_log(audit_log)			
			
			
			
11. 성능 최적화			
			
11.1 목표 성능 지표			
			
항목	목표	측정 방법	
API 응답 시간	P50 < 500ms, P95 < 2s	Prometheus	
전체 워크플로우	< 3초 (사용자 체감)	end-to-end 타이밍	
LLM 호출 시간	< 2초	개별 타이밍	
DB 쿼리 시간	< 100ms	SQLAlchemy logging	
Vector 검색	< 200ms	Qdrant metrics	
동시 사용자	100+ (MVP), 1,000+ (Production)	부하 테스트	
			
11.2 최적화 전략			
# core/memory/session_memory.py			
			
from functools import lru_cache			
from cachetools import TTLCache			
import asyncio			
			
class SessionMemory:			
    """Redis 기반 세션 메모리 + 로컬 캐시"""			
    			
    def __init__(self, redis_client):			
        self.redis = redis_client			
        # 로컬 LRU 캐시 (메모리 절약)			
        self.local_cache = TTLCache(maxsize=1000, ttl=300)  # 5분			
    			
    async def get(self, user_id: str) -> dict:			
        """세션 데이터 조회 (2단계 캐싱)"""			
        			
        # 1. 로컬 캐시 확인			
        if user_id in self.local_cache:			
            return self.local_cache[user_id]			
        			
        # 2. Redis 확인			
        data = await self.redis.hgetall(f"session:{user_id}")			
        			
        if data:			
            # 로컬 캐시에 저장			
            self.local_cache[user_id] = data			
            return data			
        			
        return {}			
			
병렬 처리			
# core/analysis/analyzer.py			
			
import asyncio			
			
class Analyzer:			
    async def analyze(self, message: str, memory: dict) -> dict:			
        """6개 지표 병렬 계산"""			
        			
        # 병렬 실행 (asyncio.gather)			
        results = await asyncio.gather(			
            self.lr.analyze(message),			
            self.sd.analyze(message, memory),			
            self.nc.analyze(message),			
            self.to.analyze(message, memory),			
            self.er.analyze(message, memory),			
            self.rt.analyze(message, memory),			
            return_exceptions=True			
        )			
        			
        # 에러 핸들링			
        scores = {}			
        for name, result in zip(["LR", "SD", "NC", "TO", "ER", "RT"], results):			
            if isinstance(result, Exception):			
                logger.error(f"{name} analysis failed: {result}")			
                scores[name] = None  # 실패 시 None, MCDI 계산에서 제외			
            else:			
                scores[name] = result["score"]			
        			
        return scores			
			
DB 쿼리 최적화			
# models/conversation.py			
			
from sqlalchemy import Index			
			
class Conversation(Base):			
    __tablename__ = "conversations"			
    			
    id = Column(BigInteger, primary_key=True)			
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)			
    message = Column(Text, nullable=False)			
    created_at = Column(DateTime, default=datetime.now, nullable=False)			
    			
    # 복합 인덱스 (자주 조회하는 패턴)			
    __table_args__ = (			
        Index('idx_user_created', 'user_id', 'created_at'),			
        Index('idx_created_desc', 'created_at', postgresql_using='btree', 			
              postgresql_ops={'created_at': 'DESC'}),			
    )			
			
# 쿼리 예시 (N+1 문제 방지)			
from sqlalchemy.orm import joinedload			
			
conversations = (			
    db.query(Conversation)			
    .options(joinedload(Conversation.analysis_result))  # JOIN 사용			
    .filter(Conversation.user_id == user_id)			
    .order_by(Conversation.created_at.desc())			
    .limit(20)			
    .all()			
)			
			
Vector DB 최적화			
# database/vector_db.py			
			
class QdrantClient:			
    async def search_optimized(			
        self,			
        collection_name: str,			
        query_vector: list,			
        user_id: str,			
        top_k: int = 5			
    ):			
        """최적화된 벡터 검색"""			
        			
        # Payload 인덱스 활용			
        search_result = await self.client.search(			
            collection_name=collection_name,			
            query_vector=query_vector,			
            query_filter={			
                "must": [			
                    {"key": "user_id", "match": {"value": user_id}}			
                ]			
            },			
            limit=top_k,			
            # 점수 임계값 설정 (관련 없는 결과 제외)			
            score_threshold=0.7,			
            # 필요한 필드만 반환			
            with_payload=["content", "timestamp", "category"],			
            with_vectors=False  # 벡터는 반환 안 함 (성능 향상)			
        )			
        			
        return search_result			
			
11.3 모니터링			
# utils/metrics.py			
			
from prometheus_client import Counter, Histogram, Gauge			
import time			
			
# 메트릭 정의			
api_requests_total = Counter(			
    'api_requests_total',			
    'Total API requests',			
    ['method', 'endpoint', 'status']			
)			
			
api_request_duration = Histogram(			
    'api_request_duration_seconds',			
    'API request duration',			
    ['endpoint']			
)			
			
llm_call_duration = Histogram(			
    'llm_call_duration_seconds',			
    'LLM API call duration',			
    ['provider', 'model']			
)			
			
active_users = Gauge(			
    'active_users_total',			
    'Number of active users'			
)			
			
# 사용 예시			
class MetricsMiddleware:			
    async def __call__(self, request, call_next):			
        start_time = time.time()			
        			
        response = await call_next(request)			
        			
        duration = time.time() - start_time			
        			
        # 메트릭 기록			
        api_requests_total.labels(			
            method=request.method,			
            endpoint=request.url.path,			
            status=response.status_code			
        ).inc()			
        			
        api_request_duration.labels(			
            endpoint=request.url.path			
        ).observe(duration)			
        			
        return response			
			
			
			
12. 부록			
			
12.1 의존성 목록 (requirements.txt)			
# requirements.txt			
			
# Web Framework			
fastapi==0.104.1			
uvicorn[standard]==0.24.0			
pydantic==2.5.0			
pydantic-settings==2.1.0			
			
# Database			
sqlalchemy==2.0.23			
psycopg2-binary==2.9.9			
alembic==1.13.0			
redis==5.0.1			
qdrant-client==1.7.3			
			
# AI/ML			
anthropic==0.7.8			
openai==1.3.9			
kiwipiepy==0.16.2			
numpy==1.26.2			
scikit-learn==1.3.2			
			
# Task Queue			
celery==5.3.4			
flower==2.0.1			
			
# Utilities			
python-dotenv==1.0.0			
httpx==0.25.2			
aiohttp==3.9.1			
tenacity==8.2.3			
python-jose[cryptography]==3.3.0			
passlib[bcrypt]==1.7.4			
python-multipart==0.0.6			
			
# Logging & Monitoring			
structlog==23.2.0			
sentry-sdk==1.38.0			
prometheus-client==0.19.0			
			
# Testing			
pytest==7.4.3			
pytest-asyncio==0.21.1			
pytest-cov==4.1.0			
pytest-mock==3.12.0			
faker==20.1.0			
httpx==0.25.2			
			
# Code Quality			
black==23.12.0			
isort==5.13.2			
flake8==6.1.0			
mypy==1.7.1			
pylint==3.0.3			
			
# Documentation			
mkdocs==1.5.3			
mkdocs-material==9.5.2			
			
# Utilities			
python-dateutil==2.8.2			
pytz==2023.3			
			
12.2 프로젝트 타임라인			
title Memory Garden Development Timeline			
			
section Phase 1: MVP			
Infrastructure Setup       :2025-01-15, 7d			
Core Workflow             :2025-01-22, 14d			
Basic Analysis            :2025-01-29, 14d			
API Development           :2025-02-05, 14d			
Testing & Bug Fix         :2025-02-19, 7d			
			
section Phase 2: Beta			
Advanced Features         :2025-02-26, 14d			
Memory System             :2025-03-05, 14d			
Integration               :2025-03-19, 14d			
Beta Testing              :2025-04-02, 14d			
			
section Phase 3: Clinical			
Data Collection           :2025-04-16, 60d			
Clinical Validation       :2025-06-15, 90d			
Paper Submission          :2025-09-13, 30d			
			
section Phase 4: Launch			
Production Prep           :2025-10-13, 21d			
Launch                    :2025-11-03, 7d			
			
12.3 용어집			
			
용어	설명		
MCDI	Memory Garden Cognitive Decline Index. 6개 지표를 종합한 인지 기능 점수 (0-100)		
LR	Lexical Richness. 어휘 풍부도 지표		
SD	Semantic Drift. 의미적 표류 지표		
NC	Narrative Coherence. 서사 일관성 지표		
TO	Temporal Orientation. 시간적 지남력 지표		
ER	Episodic Recall. 일화 기억 지표		
RT	Response Time. 반응 시간 지표		
Baseline	개인별 기준선. 첫 14일간 데이터로 설정		
Slope	점수 변화율. 주당 변화 추세		
z-score	표준편차 점수. baseline 대비 표준편차 단위 변화		
Confound	교란 변수. 일시적 인지 저하 요인 (수면 부족, 우울 등)		
Vector DB	벡터 데이터베이스. 임베딩 검색용 (Qdrant)		
RAG	Retrieval-Augmented Generation. 검색 증강 생성		
			


