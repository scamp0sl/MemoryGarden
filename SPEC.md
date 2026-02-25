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

### 1.4 비용 추정 (MVP 기준)

#### 1.4.1 LLM API 비용

**사용량 가정:**
- MVP: 20명 사용자
- 일일 대화: 3회/인
- 월간 대화: 20명 × 3회 × 30일 = 1,800회

**Claude 4.5 Sonnet 비용:**
입력: 평균 2,000 tokens/요청 (시스템 프롬프트 + 컨텍스트)
출력: 평균 200 tokens/응답
월간 토큰:

Input: 1,800회 × 2,000 tokens = 3,600,000 tokens
Output: 1,800회 × 200 tokens = 360,000 tokens

비용:

Input: $3 / 1M tokens = $10.8
Output: $15 / 1M tokens = $5.4
합계: $16.2/월

**Embedding API 비용 (OpenAI):**
월간 임베딩 요청: 1,800회
평균 입력: 500 tokens
비용: 1,800 × 500 / 1M × $0.13 = $0.12/월

**Vision API 비용 (GPT-4o):**
이미지 분석: 1회/일 × 20명 × 30일 = 600회
비용: 600회 × $0.01 = $6/월

**LLM 총 비용: $22.32/월**

#### 1.4.2 인프라 비용 (AWS 기준)
EC2 (t3.medium × 1):  $30/월
RDS PostgreSQL (db.t3.small): $25/월
ElastiCache Redis (cache.t3.micro): $15/월
S3 (이미지 저장 50GB): $1.15/월
Qdrant Cloud (Starter): $25/월
인프라 총 비용: $96.15/월

#### 1.4.3 총 비용 정리

| 단계 | 사용자 수 | LLM 비용 | 인프라 비용 | 총 비용 |
|------|----------|----------|-------------|---------|
| MVP | 20명 | $22 | $96 | **$118/월** |
| Beta | 200명 | $220 | $250 | **$470/월** |
| Launch | 1,000명 | $1,100 | $800 | **$1,900/월** |
| Scale | 10,000명 | $11,000 | $3,500 | **$14,500/월** |

**1인당 비용:** $1.45/월 (Scale 기준)

#### 1.4.4 비용 최적화 전략

1. **LLM 비용 절감**
   - 프롬프트 압축 (불필요한 컨텍스트 제거)
   - 캐싱 활용 (동일 질문 재사용)
   - 간단한 응답은 규칙 기반 처리

2. **인프라 비용 절감**
   - Reserved Instances (1년 약정 시 40% 할인)
   - Auto Scaling (야간 트래픽 감소)
   - S3 Intelligent-Tiering

3. **예상 절감액:** 월 20-30%

			
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
MCDI = w₁·LR + w₂·SD + w₃·NC + w₄·TO + w5·ER + w6·RT			
			
가중치 (초기값, 임상 데이터로 최적화 예정):
 w₁ = 0.20 (LR: Lexical Richness)
 w₂ = 0.20 (SD: Semantic Drift)
 w₃ = 0.15 (NC: Narrative Coherence)
 w₄ = 0.15 (TO: Temporal Orientation)
 w5 = 0.20 (ER: Episodic Recall)
 w6 = 0.10 (RT: Response Time)			
			
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
### 2.3 프롬프트 엔지니어링

#### 2.3.1 시스템 프롬프트 (정원사 페르소나)

```python
# config/prompts.py

SYSTEM_PROMPT = """
당신은 '기억의 정원'의 정원사입니다.

## 역할
- 사용자의 친근한 동행자로서 매일 2-3회 대화를 나눕니다
- "평가"나 "검사"가 아닌, 정원을 함께 가꾸는 자연스러운 대화를 추구합니다
- 사용자의 일상, 추억, 감정을 존중하며 경청합니다

## 대화 원칙
1. 존댓말 사용 (70대 이상 대상)
2. 이모지 절제적 사용 (1-2개/메시지)
3. 짧은 문장 (2문장 이내)
4. 열린 질문 선호 ("예/아니오" 질문 지양)
5. 긍정적 피드백 ("잘 기억하시네요!", "멋진 추억이에요")

## 금기사항
- "치매", "검사", "평가" 같은 의학적 용어 사용 금지
- 사용자를 시험하는 듯한 태도 금지
- 틀린 답에 대한 지적 금지
- 과도한 걱정/동정 금지

## 예시 대화
좋은 예:
- "오늘 점심 뭐 드셨어요? 사진 찍으셨으면 정원에 올려주세요! ??"
- "어제 말씀하신 딸 이름이 수진이었죠? 수진 씨는 어떤 일을 하시나요?"

나쁜 예:
- "기억력 테스트입니다. 아침 식사 메뉴를 정확히 말씀해주세요."
- "틀렸습니다. 다시 생각해보세요."
"""

### 2.4 온보딩 플로우

#### 2.4.1 첫 대화 시나리오
[Day 0: 첫 만남]
Bot: 안녕하세요! ?? 저는 '기억의 정원' 정원사예요.
앞으로 매일 잠깐씩 이야기 나누며 함께 정원을 가꿔갈 거예요.

먼저 어떻게 부르면 좋을까요?

User: [이름 입력]
Bot: {이름}님, 반갑습니다! ??
{이름}님만의 특별한 정원을 만들어볼까요?
정원 이름은 뭐로 하면 좋을까요?
(예: 수진이네 정원, 행복한 정원)
User: [정원 이름 입력]
Bot: 좋아요! '{정원명}'이 생겼네요! ??

앞으로 매일 2-3번 정도 가볍게 물어볼게요.
 - 오늘 드신 음식 ??
 - 옛날 추억 이야기 ??
 - 간단한 놀이 ??
 
 부담 갖지 마시고, 편하게 이야기 나눠요!
 
 첫 번째 질문 드릴게요.
 오늘 점심은 뭐 드셨어요?

#### 2.4.2 Baseline 수집 기간 (Day 1-14)

**전략:**
Week 1 (Day 1-7): 관계 형성 + 기본 데이터 수집

일일 2회 대화 (점심, 저녁)
가벼운 질문 위주 (음식, 날씨, 기분)
전기적 정보 자연스럽게 수집

"고향이 어디세요?"
"자녀분은 몇 분이세요?"
"젊었을 때 무슨 일 하셨어요?"



Week 2 (Day 8-14): 다양한 카테고리 노출

일일 2-3회 대화
6개 카테고리 골고루 경험
사용자 선호 파악

어떤 주제에 반응이 좋은가?
어떤 시간대에 답변이 빠른가?



Day 15: Baseline 설정

14일간 데이터 집계
개인별 MCDI baseline 계산
표준편차 계산
이후부터 이상 감지 시작

#### 2.4.3 보호자 연결 프로세스
[사용자 온보딩 완료 후]
Bot: {이름}님, 혹시 가족분께도 정원 소식을 알려드릴까요?
따님이나 아드님 전화번호를 알려주시면,
정원이 예쁘게 자라고 있다는 소식을 가끔 전해드려요! ??
User: [보호자 연락처 입력]
Bot: 감사합니다! 곧 인사드릴게요 ??

[보호자에게 카카오톡 발송]
안녕하세요, '기억의 정원' 입니다.
{사용자명}님께서 보호자로 등록해주셨어요.
▶? 기억의 정원이란?
매일 가벼운 대화로 어르신의 인지 건강을
지켜드리는 AI 서비스입니다.
▶? 보호자 대시보드

주간 대화 요약
관찰 포인트
권장 조치사항

[대시보드 바로가기] 버튼

[보호자 앱 초기 화면]
?? {사용자명}님 정원 현황
? 온보딩 완료 (Day 3/14)
?? Baseline 수집 중...
?? 오늘 대화: 2회 완료
※ 2주 후부터 상세 분석이 제공됩니다.
현재는 어르신과 친해지는 기간이에요 ??

#### 2.4.4 중도 이탈 방지 전략

```python
# tasks/engagement_monitor.py

@celery.task
async def check_inactive_users():
    """24시간 무응답 사용자 체크"""
    
    inactive_users = db.query(User).filter(
        User.last_interaction_at < datetime.now() - timedelta(hours=24)
    ).all()
    
    for user in inactive_users:
        days_inactive = (datetime.now() - user.last_interaction_at).days
        
        if days_inactive == 1:
            # 1일차: 가벼운 리마인더
            send_message(user.kakao_id, 
                "?? 정원이 {이름}님을 기다리고 있어요! 오늘 어떻게 지내셨나요?")
        
        elif days_inactive == 3:
            # 3일차: 보호자 알림 + 사용자 독려
            send_guardian_alert(user.id, "concern", 
                "3일간 대화가 없어요. 어르신께 확인 부탁드려요.")
            send_message(user.kakao_id,
                "정원에 비가 내리고 있어요 ?? 괜찮으신가요?")
        
        elif days_inactive >= 7:
            # 7일차: 온보딩 재시작 제안
            send_message(user.kakao_id,
                "오랜만이에요! 다시 시작해볼까요? ??")

### 2.5 스케줄링 전략

#### 2.5.1 Celery Beat 스케줄

```python
# tasks/celery_app.py

from celery.schedules import crontab

app.conf.beat_schedule = {
    # 오전 인사 (10:00-11:00)
    'morning-greeting': {
        'task': 'tasks.dialogue.send_morning_message',
        'schedule': crontab(hour=10, minute=0),
    },
    
    # 점심 체크 (11:30-12:30)
    'lunch-check': {
        'task': 'tasks.dialogue.send_lunch_question',
        'schedule': crontab(hour=11, minute=30),
    },
    
    # 오후 회상 질문 (14:00-15:00)
    'afternoon-reminiscence': {
        'task': 'tasks.dialogue.send_reminiscence_question',
        'schedule': crontab(hour=14, minute=0),
        'kwargs': {'category': 'reminiscence'}
    },
    
    # 저녁 일화 기억 체크 (18:00-19:00)
    'evening-recall': {
        'task': 'tasks.dialogue.send_recall_question',
        'schedule': crontab(hour=18, minute=0),
    },
    
    # 일일 리포트 생성 (23:00)
    'daily-report': {
        'task': 'tasks.analysis.generate_daily_report',
        'schedule': crontab(hour=23, minute=0),
    },
    
    # 주간 리포트 (일요일 22:00)
    'weekly-report': {
        'task': 'tasks.analysis.generate_weekly_report',
        'schedule': crontab(day_of_week='sunday', hour=22, minute=0),
    },
    
    # 비활성 사용자 체크 (매 6시간)
    'check-inactive': {
        'task': 'tasks.engagement_monitor.check_inactive_users',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}



			
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
 │ Claude 4.5 │ GPT-4o │ Kakao API │ Email/SMS │			
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
    deleted_at TIMESTAMP
);			

-- 인덱스 생성
CREATE INDEX idx_users_kakao_id ON users(kakao_id);
CREATE INDEX idx_users_created_at ON users(created_at);
			
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
    created_at TIMESTAMP DEFAULT NOW()			
    			
);			
CREATE INDEX idx_conversations_user_created ON conversations(user_id, created_at);
CREATE INDEX idx_conversations_category ON conversations(category);
CREATE INDEX idx_conversations_created_desc ON conversations(created_at DESC);
			
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
    created_at TIMESTAMP DEFAULT NOW()
    			
);			
			
CREATE INDEX idx_user_created ON analysis_results(user_id, created_at);
CREATE INDEX idx_risk_level ON analysis_results(risk_level);
CREATE INDEX idx_mcdi_score ON analysis_results(mcdi_score);

 -- guardians 테이블			
CREATE TABLE guardians (			
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),			
    name VARCHAR(100) NOT NULL,			
    phone VARCHAR(20),			
    email VARCHAR(100),			
    kakao_id VARCHAR(100),  -- 카카오톡 알림용			
    created_at TIMESTAMP DEFAULT NOW()			
    			
);			
CREATE INDEX idx_phone ON guardians(phone);
CREATE INDEX idx_email ON guardians(email);
			
 -- user_guardians 테이블 (M:N 관계)			
CREATE TABLE user_guardians (			
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,			
    guardian_id UUID NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,			
    relation VARCHAR(50),  -- daughter/son/spouse/caregiver			
    notification_enabled BOOLEAN DEFAULT TRUE,			
    created_at TIMESTAMP DEFAULT NOW(),			
    			
    PRIMARY KEY (user_id, guardian_id)			
);			
CREATE INDEX idx_user ON user_guardians(user_id);
CREATE INDEX idx_guardian ON user_guardians(guardian_id);			
			
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
    read_at TIMESTAMP
    			
);			
CREATE INDEX idx_guardian_sent ON notifications(guardian_id, sent_at);
CREATE INDEX idx_user_sent ON notifications(user_id, sent_at);
			
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
    created_at TIMESTAMP DEFAULT NOW()			
    			
);			
CREATE INDEX idx_user_type ON memory_events(user_id, event_type);
CREATE INDEX idx_severity ON memory_events(severity);
			
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

#### 5.3.6 이미지 분석

POST /api/v1/vision/analyze

**Description:** 음식 사진 분석

**Request Body:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_url": "https://storage.memory-garden.ai/images/user123_20250115.jpg",
  "context": "lunch"  // lunch/dinner/snack
}

Response (200 OK):

{
  "detected_items": [
    {
      "name": "된장찌개",
      "confidence": 0.92,
      "category": "soup"
    },
    {
      "name": "김치",
      "confidence": 0.88,
      "category": "side_dish"
    },
    {
      "name": "흰쌀밥",
      "confidence": 0.95,
      "category": "staple"
    }
  ],
  "meal_summary": "된장찌개 정식",
  "nutritional_balance": "good",  // good/fair/poor
  "follow_up_question": "된장찌개에 어떤 재료가 들어갔어요?"
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
CLAUDE_MODEL=claude-4-5-sonnet-20250929			
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
			
```markdown
### 9.1 테스트 환경 설정

**tests/conftest.py** (모든 테스트에서 공유되는 Fixtures)

```python
"""
공통 테스트 fixtures

pytest가 자동으로 로드하는 설정 파일.
모든 테스트에서 사용 가능한 fixture를 정의.
"""

import pytest
import asyncio
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
import redis
from qdrant_client import QdrantClient

from api.main import app
from database.postgres import Base
from models.user import User
from models.conversation import Conversation
from config.settings import settings

# ============================================
# 1. 이벤트 루프 설정
# ============================================
@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture (session 단위)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ============================================
# 2. 데이터베이스 Fixtures
# ============================================
TEST_DATABASE_URL = "postgresql://test_user:test_pass@localhost:5432/test_memory_garden"

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """테스트 DB 세션 (각 테스트마다 초기화)"""
    # 테스트 DB 엔진 생성
    engine = create_engine(TEST_DATABASE_URL)
    
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    # 세션 생성
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # 테스트 후 테이블 삭제
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_user(test_db: Session) -> User:
    """테스트용 사용자"""
    user = User(
        kakao_id="test_kakao_123",
        name="테스트 사용자",
        birth_date="1950-01-01",
        gender="male",
        baseline_mcdi=78.5,
        baseline_established_at="2025-01-07"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    return user

# ============================================
# 3. Redis Fixtures
# ============================================
@pytest.fixture(scope="function")
def test_redis() -> Generator[redis.Redis, None, None]:
    """테스트용 Redis 클라이언트 (DB 15 사용)"""
    client = redis.Redis(
        host='localhost',
        port=6379,
        db=15,  # 테스트 전용 DB
        decode_responses=True
    )
    
    yield client
    
    # 테스트 후 정리
    client.flushdb()
    client.close()

# ============================================
# 4. Qdrant Fixtures
# ============================================
@pytest.fixture(scope="function")
def test_qdrant() -> Generator[QdrantClient, None, None]:
    """테스트용 Qdrant 클라이언트"""
    client = QdrantClient(url="http://localhost:6333")
    
    # 테스트 컬렉션 생성
    test_collections = [
        "test_episodic_memory",
        "test_biographical_memory",
        "test_question_history"
    ]
    
    for collection in test_collections:
        try:
            client.create_collection(
                collection_name=collection,
                vectors_config={
                    "size": 1536,
                    "distance": "Cosine"
                }
            )
        except Exception:
            pass  # 이미 존재하면 무시
    
    yield client
    
    # 테스트 후 정리
    for collection in test_collections:
        try:
            client.delete_collection(collection_name=collection)
        except Exception:
            pass

# ============================================
# 5. FastAPI 테스트 클라이언트
# ============================================
@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)

# ============================================
# 6. Mock Fixtures
# ============================================
@pytest.fixture
def mock_llm_response():
    """LLM 응답 모킹 (고정값)"""
    return {
        "response": "안녕하세요! 오늘 기분이 어떠세요?",
        "tokens_used": 50
    }

@pytest.fixture
def sample_message():
    """샘플 사용자 메시지"""
    return "봄이면 우리 엄마가 꼭 쑥을 뜯으러 뒷산에 가셨어. 쑥떡을 만드셨지."

@pytest.fixture
def sample_context():
    """샘플 ProcessingContext"""
    from core.workflow.context import ProcessingContext
    from datetime import datetime
    
    return ProcessingContext(
        user_id="test_user_123",
        message="안녕하세요",
        timestamp=datetime.now()
    )

# ============================================
# 7. 환경 변수 Mock
# ============================================
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """테스트 환경 변수 설정"""
    import os
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"
    os.environ["LOG_LEVEL"] = "DEBUG"

# ============================================
# 8. 파일 정리 Fixture
# ============================================
@pytest.fixture
def temp_file(tmp_path):
    """임시 파일 생성 (자동 정리)"""
    file_path = tmp_path / "test_file.txt"
    yield file_path
    # 테스트 후 자동 정리 (tmp_path가 처리)

사용 예시:
# tests/test_core/test_analysis.py

def test_with_db(test_db, test_user):
    """DB fixture 사용"""
    assert test_user.name == "테스트 사용자"
    
    # DB 조회
    user = test_db.query(User).filter(User.id == test_user.id).first()
    assert user is not None

@pytest.mark.asyncio
async def test_with_redis(test_redis):
    """Redis fixture 사용"""
    test_redis.set("test_key", "test_value")
    assert test_redis.get("test_key") == "test_value"

def test_api_with_client(client):
    """FastAPI client fixture 사용"""
    response = client.get("/health")
    assert response.status_code == 200


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
    - Qdrant: episodic_memory, biographical_memory, question_history
    - Redis: session 데이터
    - TimescaleDB: analysis_timeseries
    """			
    # 1. RDBMS 삭제 (CASCADE)			
    db.query(User).filter(User.id == user_id).delete()			
    db.commit
    			
    # 2. Vector DB 삭제 (3개 컬렉션)
    collections = ["episodic_memory", "biographical_memory", "question_history"]
    for collection in collections:
        qdrant_client.delete(
            collection_name=collection,
            points_selector={
                "filter": {
                    "must": [
                        {"key": "user_id", "match": {"value": user_id}}
                    ]
                }
            }
        )
    			
    # 3. Redis 삭제
    redis_client.delete(f"session:{user_id}")
    redis_client.delete(f"garden:{user_id}")
    redis_client.delete(f"confound_check:{user_id}")
    			
    # 5. 로그 기록 (감사용)
    logger.info(
        f"User data deleted: {user_id}",
        extra={"gdpr": True, "timestamp": datetime.now().isoformat()}
    )
    			
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

@router.get("/api/v1/users/{user_id}/analysis/report")			
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
			


