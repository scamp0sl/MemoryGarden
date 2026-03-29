# Memory Garden AI - 시스템 아키텍처

> 기억의 정원 서비스의 전체 아키텍처, API 명세, 파일 구조 팀 공유 문서
> 작성일: 2026-02-25

---

## 목차

1. [전체 아키텍처 다이어그램](#1-전체-아키텍처-다이어그램)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [메시지 처리 파이프라인](#3-메시지-처리-파이프라인)
4. [스케줄 알림 플로우](#4-스케줄-알림-플로우)
5. [MCDI 분석 파이프라인](#5-mcdi-분석-파이프라인)
6. [데이터베이스 스키마](#6-데이터베이스-스키마)
7. [API 명세](#7-api-명세)
8. [파일 구조](#8-파일-구조)
9. [기술 스택](#9-기술-스택)
10. [환경 변수](#10-환경-변수)

---

## 1. 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           사용자 (테스터)                                │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │  카카오톡 앱
                ┌───────────┴────────────┐
                │                        │
        ┌───────▼────────┐     ┌─────────▼──────────┐
        │  카카오 채널   │     │  카카오 나에게보내기 │
        │   @기억의정원  │     │    (send_to_me)     │
        └───────┬────────┘     └─────────┬──────────┘
                │ 채널 메시지              │ 스케줄 알림
                │                         │
        ┌───────▼─────────────────────────▼──────────┐
        │           카카오 서버                       │
        │     (Kakao i Open Builder)                  │
        └───────────────────┬────────────────────────┘
                            │ POST /kakao/webhook
                            │ (HTTPS)
        ┌───────────────────▼────────────────────────┐
        │         Nginx (Reverse Proxy)               │
        │         n8n.softline.co.kr                  │
        │         SSL Termination                      │
        └───────────────────┬────────────────────────┘
                            │ HTTP (127.0.0.1:8001)
        ┌───────────────────▼────────────────────────┐
        │         FastAPI 서버 (Uvicorn)              │
        │         Memory Garden AI API               │
        │                                             │
        │  ┌─────────────┐  ┌────────────────────┐  │
        │  │  Webhook    │  │   Scheduler        │  │
        │  │  Handler    │  │   (APScheduler)    │  │
        │  └──────┬──────┘  └────────┬───────────┘  │
        │         │                   │               │
        │  ┌──────▼───────────────────▼───────────┐  │
        │  │         Core Business Logic           │  │
        │  │                                       │  │
        │  │  ┌──────────┐  ┌──────────────────┐  │  │
        │  │  │ Dialogue │  │    Analyzer      │  │  │
        │  │  │ Manager  │  │  (6 indicators)  │  │  │
        │  │  └──────────┘  └──────────────────┘  │  │
        │  │                                       │  │
        │  │  ┌──────────────────────────────────┐ │  │
        │  │  │       Memory Manager             │ │  │
        │  │  │  Session│Episodic│Bio│Analytical │ │  │
        │  │  └──────────────────────────────────┘ │  │
        │  └───────────────────────────────────────┘  │
        └──────────┬────────────────────┬─────────────┘
                   │                    │
     ┌─────────────▼──────┐  ┌──────────▼──────────────┐
     │   데이터베이스      │  │    외부 AI 서비스        │
     │                    │  │                          │
     │ ┌──────────────┐   │  │  ┌──────────────────┐   │
     │ │ PostgreSQL   │   │  │  │  Claude Sonnet   │   │
     │ │ (users,      │   │  │  │  (대화 생성)     │   │
     │ │  conv, mcdi) │   │  │  └──────────────────┘   │
     │ └──────────────┘   │  │                          │
     │ ┌──────────────┐   │  │  ┌──────────────────┐   │
     │ │    Redis     │   │  │  │    GPT-4o        │   │
     │ │ (session,    │   │  │  │  (MCDI 분석)     │   │
     │ │  scheduler)  │   │  │  └──────────────────┘   │
     │ └──────────────┘   │  │                          │
     │ ┌──────────────┐   │  │  ┌──────────────────┐   │
     │ │   Qdrant     │   │  │  │  GPT-4o Vision   │   │
     │ │ (episodic,   │   │  │  │  (이미지 분석)   │   │
     │ │  bio memory) │   │  │  └──────────────────┘   │
     │ └──────────────┘   │  └──────────────────────────┘
     └────────────────────┘
```

---

## 2. 시스템 아키텍처

### 계층 구조

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│                                                          │
│   카카오 채널   │   REST API   │   Admin Dashboard      │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                     API Layer                            │
│                                                          │
│   kakao_webhook.py  │  auth.py  │  conversations.py     │
│   users.py  │  analysis.py  │  garden.py  │  push.py    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    Core Business Logic                   │
│                                                          │
│  ┌───────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │   Dialogue    │  │  Analysis   │  │    Memory     │  │
│  │   Manager     │  │  (MCDI 6개) │  │  Manager      │  │
│  │               │  │             │  │  (4 계층)     │  │
│  │ - Response    │  │ - LR,SD,NC  │  │ - Session     │  │
│  │   Generator   │  │ - TO,ER,RT  │  │ - Episodic    │  │
│  │ - Prompt      │  │ - MCDI Calc │  │ - Bio         │  │
│  │   Builder     │  │ - Risk Eval │  │ - Analytical  │  │
│  └───────────────┘  └─────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                         │
│                                                          │
│  LLMService  │  KakaoClient  │  ImageAnalysisService    │
│  NotificationService  │  VisionService                  │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                    │
│                                                          │
│   PostgreSQL  │  Redis  │  Qdrant  │  Firebase FCM       │
└─────────────────────────────────────────────────────────┘
```

### 서버 구성

```
외부 인터넷
    │ HTTPS (443)
    ▼
Nginx (Reverse Proxy)
  - SSL/TLS 인증서 처리
  - /api/v1/* → 8001 (FastAPI)
  - /kakao/*  → 8001 (FastAPI)
    │ HTTP (127.0.0.1:8001)
    ▼
FastAPI (Uvicorn)
  - 비동기 처리 (asyncio)
  - APScheduler (인-프로세스)
  - BackgroundTasks (응답 후 실행)
    │
    ├─ PostgreSQL (5432) - 영구 데이터
    ├─ Redis (6379)       - 세션/스케줄
    └─ Qdrant (6333)      - 벡터 검색
```

---

## 3. 메시지 처리 파이프라인

### 일반 텍스트 메시지

```
사용자가 채널방에 메시지 입력
            │
            ▼ POST /kakao/webhook (카카오 서버 → 우리 서버)
┌───────────────────────────────────┐
│  1. 페이로드 파싱                  │
│     plusfriendUserKey 추출         │
└─────────────┬─────────────────────┘
              │
              ▼
┌───────────────────────────────────┐
│  2. 사용자 조회/생성               │
│     channel_user_key → DB 조회     │
│     없으면 신규 생성 + 스케줄 등록 │
└─────────────┬─────────────────────┘
              │
              ▼
┌───────────────────────────────────┐
│  3. AI 응답 생성                   │
│     DialogueManager.generate()    │
│     Claude Sonnet API 호출         │
└─────────────┬─────────────────────┘
              │
              ▼
┌───────────────────────────────────┐
│  4. 대화 저장                      │
│     PostgreSQL conversations 테이블│
└─────────────┬─────────────────────┘
              │
              ▼ HTTP 200 응답 (카카오 규격 JSON)
    채널방에 AI 응답 표시 ✅

              │ (응답 후 BackgroundTask)
              ▼
┌───────────────────────────────────┐
│  5. MCDI 분석 (백그라운드)         │
│     6개 지표 병렬 분석             │
│     analysis_results 테이블 저장   │
│     위험도 평가 → DB 기록          │
│     ※ 보호자 알림: 미구현 (예정)  │
└───────────────────────────────────┘

⚠️ 카카오 타임아웃: 5초
   → 응답(3~4단계)은 5초 내 완료
   → MCDI 분석은 백그라운드로 분리
```

### 이미지 메시지

```
사용자가 채널방에 사진 전송
            │
            ▼ POST /kakao/webhook
            │ utterance = "https://talk.kakaocdn.net/..."
            │
┌───────────────────────────────────┐
│  이미지 URL 감지                   │
│  talk.kakaocdn.net 포함 여부 확인  │
└─────────────┬─────────────────────┘
              │
              ▼ 즉시 응답 (5초 이내)
    채널방: "사진을 받았어요! 잠깐만요..." ✅

              │ (응답 후 BackgroundTask)
              ▼
┌───────────────────────────────────┐
│  이미지 분석 (백그라운드, ~10초)   │
│                                   │
│  1. Kakao CDN에서 이미지 다운로드  │
│     (Base64 변환)                  │
│                                   │
│  2. GPT-4o Vision 분석            │
│     - 주요 객체                    │
│     - 분위기                       │
│     - 시간대                       │
│                                   │
│  3. AI 대화 응답 생성              │
│     (분석 결과 기반)               │
│                                   │
│  4. send_to_me로 전송             │
│     → "나에게 보내기" 수신 ✅     │
└───────────────────────────────────┘

📌 이미지 응답은 채널방이 아닌
   "나에게 보내기"로 수신됨
   (친구톡 설정 시 채널방으로 통합 가능)
```

---

## 4. 스케줄 알림 플로우

### OAuth 연동 사용자 (완전 연동)

```
APScheduler 트리거 (09:00 / 14:00 / 19:00)
            │
            ▼
  send_scheduled_dialogue(user_id)
            │
            ▼
  AI 메시지 생성
  "오늘 점심은 어떻게 드셨나요? 🌱"
            │
            ▼
  send_to_me API 호출
  (카카오 OAuth access_token 사용)
            │
            ▼
┌─────────────────────────────┐
│  "나에게 보내기" 수신       │
│                             │
│  오늘 점심은 어떻게...      │
│                             │
│  [채널에서 답하기 🌱]       │
└─────────────┬───────────────┘
              │ 버튼 클릭
              ▼
  https://n8n.softline.co.kr/kakao/channel
              │ 302 Redirect
              ▼
  채널 채팅방 열림
              │
              ▼
  채널방에서 대화 답장 → AI 응답
```

### 채널 전용 사용자 (OAuth 미연동)

```
APScheduler 트리거
            │
            ▼
  OAuth 토큰 없음 감지
            │
            ▼
  channel_pending 상태 반환
  (비즈메시지 설정 후 친구톡으로 전환 가능)
```

---

## 5. MCDI 분석 파이프라인

```
대화 텍스트 수신
        │
        ▼
┌───────────────────────────────────────────────────────┐
│              6개 지표 병렬 분석 (asyncio.gather)       │
│                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │    LR    │ │    SD    │ │          NC          │  │
│  │어휘풍부도│ │의미적표류│ │      서사일관성       │  │
│  │  가중치  │ │  가중치  │ │       가중치         │  │
│  │  0.20    │ │  0.20    │ │        0.15          │  │
│  └──────────┘ └──────────┘ └──────────────────────┘  │
│                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │    TO    │ │    ER    │ │          RT          │  │
│  │시간지남력│ │ 일화기억 │ │       반응시간        │  │
│  │  가중치  │ │  가중치  │ │       가중치         │  │
│  │  0.15    │ │  0.20    │ │        0.10          │  │
│  └──────────┘ └──────────┘ └──────────────────────┘  │
└───────────────────────────┬───────────────────────────┘
                            │
                            ▼
              MCDICalculator.calculate()
              가중 평균 = Σ(점수 × 가중치)
                            │
                            ▼
              RiskEvaluator.evaluate()
              ┌─────────────────────────────────┐
              │  Z-score 계산 (baseline 대비)   │
              │  4주 기울기 분석                 │
              │                                 │
              │  GREEN  : MCDI ≥ 80             │
              │  YELLOW : MCDI 60~79            │
              │  ORANGE : MCDI 40~59            │
              │  RED    : MCDI < 40             │
              └─────────────┬───────────────────┘
                            │
                ┌───────────┴────────────┐
                │                        │
          GREEN/YELLOW              ORANGE/RED
                │                        │
         DB 저장만                  DB 저장만
                                    (보호자 알림: 미구현)
                                    ※ 코드 설계는 완료,
                                      보호자 등록 API 및
                                      알림톡 연동 미완성
```

---

## 6. 데이터베이스 스키마

```
┌──────────────────────────────────────────────────────┐
│                      users                           │
├──────────────────┬───────────────────────────────────┤
│ id               │ UUID (PK)                         │
│ kakao_id         │ VARCHAR (UNIQUE)                  │
│ name             │ VARCHAR                           │
│ birth_date       │ TIMESTAMP (nullable)              │
│ kakao_access_token│ VARCHAR (nullable)               │
│ kakao_refresh_token│ VARCHAR (nullable)              │
│ kakao_channel_user_key│ VARCHAR (UNIQUE, nullable)   │
│ baseline_mcdi    │ FLOAT (nullable)                  │
│ created_at       │ TIMESTAMP                         │
│ deleted_at       │ TIMESTAMP (soft delete)           │
└──────────────────┴───────────────────────────────────┘
            │ 1
            │
            │ N
┌──────────────────────────────────────────────────────┐
│                   conversations                      │
├──────────────────┬───────────────────────────────────┤
│ id               │ BIGINT (PK, autoincrement)        │
│ user_id          │ UUID (FK → users.id)              │
│ message          │ VARCHAR (사용자 입력)             │
│ response         │ VARCHAR (AI 응답)                 │
│ message_type     │ VARCHAR (text/image/selection)    │
│ image_url        │ VARCHAR (nullable)                │
│ category         │ VARCHAR (nullable)                │
│ response_latency_ms│ INTEGER                        │
│ created_at       │ TIMESTAMP                         │
└──────────────────┴───────────────────────────────────┘
            │ 1
            │
            │ 1
┌──────────────────────────────────────────────────────┐
│                  analysis_results                    │
├──────────────────┬───────────────────────────────────┤
│ id               │ BIGINT (PK, autoincrement)        │
│ conversation_id  │ BIGINT (FK → conversations.id)    │
│ user_id          │ UUID (FK → users.id)              │
│ mcdi_score       │ FLOAT (0~100)                     │
│ risk_level       │ VARCHAR (GREEN/YELLOW/ORANGE/RED) │
│ lr_score         │ FLOAT (nullable)                  │
│ lr_detail        │ JSONB (nullable)                  │
│ sd_score         │ FLOAT (nullable)                  │
│ sd_detail        │ JSONB (nullable)                  │
│ nc_score / detail│ FLOAT / JSONB                     │
│ to_score / detail│ FLOAT / JSONB                     │
│ er_score / detail│ FLOAT / JSONB                     │
│ rt_score / detail│ FLOAT / JSONB                     │
│ processing_time_ms│ INTEGER                          │
│ created_at       │ TIMESTAMP                         │
└──────────────────┴───────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                    fcm_tokens                        │
├──────────────────┬───────────────────────────────────┤
│ id               │ BIGINT (PK)                       │
│ user_id          │ UUID (FK → users.id)              │
│ token            │ VARCHAR (UNIQUE)                  │
│ device_type      │ VARCHAR (android/ios/web)         │
│ is_active        │ BOOLEAN                           │
│ created_at       │ TIMESTAMP                         │
└──────────────────┴───────────────────────────────────┘
```

---

## 7. API 명세

### 카카오 연동 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/kakao/webhook` | 채널 메시지 수신·응답 (카카오 서버 → 우리 서버) |
| `GET`  | `/kakao/channel` | 채널 리다이렉트 (send_to_me 버튼 클릭 시) |
| `GET`  | `/kakao/channel-auth/{token}` | OAuth↔채널 자동 연동 |
| `GET`  | `/api/v1/auth/kakao/login` | 카카오 OAuth 로그인 시작 |
| `GET`  | `/api/v1/auth/kakao/callback` | 카카오 OAuth 콜백 처리 |

### 사용자 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET`  | `/api/v1/users/{user_id}` | 사용자 조회 |
| `PUT`  | `/api/v1/users/{user_id}` | 사용자 정보 수정 |
| `POST` | `/api/v1/users/{user_id}/guardians` | 보호자 추가 *(미구현)* |

### 대화

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/v1/conversations/sessions/{session_id}/messages` | 메시지 전송 |
| `GET`  | `/api/v1/conversations/sessions/{session_id}/history` | 대화 기록 |
| `POST` | `/api/v1/conversations/messages/image` | 이미지 메시지 |

### 분석

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET`  | `/api/v1/users/{user_id}/mcdi` | 최신 MCDI 점수 |
| `GET`  | `/api/v1/users/{user_id}/risk` | 위험도 평가 |
| `GET`  | `/api/v1/users/{user_id}/analysis/weekly` | 주간 보고서 |
| `GET`  | `/api/v1/users/{user_id}/analysis/monthly` | 월간 보고서 |

### 스케줄

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/v1/sessions/users/{user_id}/schedule` | 대화 스케줄 설정 |
| `GET`  | `/api/v1/sessions/users/{user_id}/schedule` | 스케줄 조회 |
| `DELETE` | `/api/v1/sessions/users/{user_id}/schedule` | 스케줄 삭제 |

---

## 8. 파일 구조

```
MemoryGardenAI/
│
├── api/                          # API 계층
│   ├── main.py                   # FastAPI 앱, 미들웨어, 라우터 등록
│   ├── dependencies.py           # 인증, DB 의존성 주입
│   ├── routes/
│   │   ├── kakao_webhook.py      # ★ 채널 웹훅 (핵심)
│   │   ├── auth.py               # ★ 카카오 OAuth (핵심)
│   │   ├── users.py
│   │   ├── conversations.py
│   │   ├── analysis.py
│   │   ├── garden.py
│   │   ├── sessions.py
│   │   ├── memories.py
│   │   ├── kakao_oauth.py
│   │   └── push.py
│   └── schemas/                  # Pydantic 요청/응답 모델
│       ├── user.py
│       ├── conversation.py
│       ├── analysis.py
│       └── ...
│
├── core/                         # 핵심 비즈니스 로직
│   ├── analysis/                 # MCDI 분석
│   │   ├── analyzer.py           # ★ 6개 지표 통합 (핵심)
│   │   ├── mcdi_calculator.py    # ★ 가중 평균 계산
│   │   ├── risk_evaluator.py     # ★ 위험도 판정
│   │   ├── lexical_richness.py   # LR 지표
│   │   ├── semantic_drift.py     # SD 지표
│   │   ├── narrative_coherence.py# NC 지표
│   │   ├── temporal_orientation.py# TO 지표
│   │   ├── episodic_recall.py    # ER 지표
│   │   └── response_time.py      # RT 지표
│   │
│   ├── dialogue/                 # 대화 생성
│   │   ├── dialogue_manager.py   # ★ 대화 총괄 (핵심)
│   │   ├── response_generator.py # AI 응답 생성
│   │   ├── prompt_builder.py     # 프롬프트 구성
│   │   └── scheduler.py          # ★ APScheduler 래퍼
│   │
│   └── memory/                   # 4계층 메모리
│       ├── memory_manager.py     # 메모리 총괄
│       ├── session_memory.py     # Redis (세션)
│       ├── episodic_memory.py    # Qdrant (에피소드)
│       ├── biographical_memory.py# DB (생애 정보)
│       └── analytical_memory.py  # 시계열 (분석)
│
├── services/                     # 외부 서비스 연동
│   ├── kakao_client.py           # ★ 카카오 API 클라이언트
│   ├── llm_service.py            # Claude/GPT API
│   ├── image_analysis_service.py # GPT-4o Vision
│   ├── notification_service.py   # 보호자 알림
│   └── vision_service.py         # 정원 시각화
│
├── database/                     # DB 연결
│   ├── models.py                 # ★ ORM 모델 4개 테이블
│   ├── postgres.py               # AsyncSession 팩토리
│   └── redis_client.py           # Redis 클라이언트
│
├── tasks/
│   └── dialogue.py               # ★ 스케줄 발송, MCDI 백그라운드
│
├── config/
│   ├── settings.py               # 환경 변수 관리
│   └── prompts.py                # AI 프롬프트 템플릿
│
├── alembic/                      # DB 마이그레이션
│   └── versions/                 # 4개 마이그레이션 파일
│
├── .env                          # 환경 변수 (Git 제외)
├── start_server.sh               # 서버 시작 스크립트
└── logs/fastapi.log              # 서비스 로그
```

★ 표시 = 핵심 파일

---

## 9. 기술 스택

| 분류 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **Web Framework** | FastAPI | 0.115+ | REST API, 웹훅 처리 |
| **ASGI Server** | Uvicorn | - | 비동기 서버 |
| **Reverse Proxy** | Nginx | - | SSL, 로드밸런싱 |
| **Database** | PostgreSQL | 16 | 사용자, 대화, 분석 결과 |
| **Cache/Session** | Redis | 7 | 세션, 스케줄러 잡 스토어 |
| **Vector DB** | Qdrant | - | 에피소드/생애 기억 검색 |
| **ORM** | SQLAlchemy | 2.0 | 비동기 DB 접근 |
| **Migration** | Alembic | - | DB 스키마 버전 관리 |
| **AI (대화)** | Claude Sonnet 4.5 | - | 자연스러운 대화 생성 |
| **AI (분석)** | GPT-4o-mini | - | MCDI 지표 분석 |
| **AI (이미지)** | GPT-4o Vision | - | 사진 내용 분석 |
| **Scheduler** | APScheduler | - | 일일 대화 알림 스케줄 |
| **HTTP Client** | httpx | - | 비동기 외부 API 호출 |
| **NLP** | kiwipiepy | - | 한국어 형태소 분석 |
| **Push** | Firebase FCM | - | 모바일 푸시 알림 |
| **OAuth** | 카카오 OAuth 2.0 | - | 사용자 인증 |

---

## 10. 환경 변수

```bash
# === AI 서비스 ===
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# === 데이터베이스 ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/memory_garden
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# === 카카오 ===
KAKAO_REST_API_KEY=...          # 앱 REST API 키
KAKAO_ADMIN_KEY=...             # 앱 Admin 키
KAKAO_CHANNEL_ID=_tDPzX        # 채널 ID (@기억의정원)
KAKAO_REDIRECT_URI=https://n8n.softline.co.kr/api/v1/auth/kakao/callback
KAKAO_CHANNEL_DEEP_LINK=...    # 채널 딥링크

# 친구톡 (서비스 오픈 후 설정)
KAKAO_BIZ_CLIENT_ID=           # 비즈메시지 Client ID
KAKAO_BIZ_CLIENT_SECRET=       # 비즈메시지 Client Secret
KAKAO_SENDER_KEY=               # 발신프로파일키 (40자)

# === Firebase ===
FIREBASE_PROJECT_ID=...
FIREBASE_CREDENTIALS_PATH=config/firebase-adminsdk.json

# === 서버 ===
APP_ENV=production
DEBUG=False
SECRET_KEY=...                  # 32자 이상 랜덤 문자열
```
