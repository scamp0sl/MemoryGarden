# ?? 기억의 정원 (Memory Garden)		
		
> **"매일 3분, 꽃에 물 주듯 나누는 가벼운 수다 속에서,  		
> AI가 인지 건강의 미세한 변화를 장기 추적하여  		
> 치매 조기 발견의 골든타임을 잡아주는 카카오톡 기반 디지털 바이오마커 서비스"**		
		
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)		
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)		
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)		
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)		
		
---		
		
## ?? 목차		
		
- [프로젝트 개요](#-프로젝트-개요)		
- [핵심 기능](#-핵심-기능)		
- [기술 스택](#-기술-스택)		
- [아키텍처](#-아키텍처)		
- [시작하기](#-시작하기)		
- [개발 가이드](#-개발-가이드)		
- [기여하기](#-기여하기)		
- [라이선스](#-라이선스)		
- [문의](#-문의)		
		
---		
		
## ?? 프로젝트 개요		
		
### 문제 인식		
?? 현재 치매 조기 발견의 한계		
		
? 병원 방문 필수 (접근성 낮음) 		
? MMSE/MoCA 1회성 검사 (변화 추적 불가) 		
? "시험" 느낌 (심리적 거부감) 		
? 증상 발현 후 발견 (늦은 개입)		
		
?? 해결 방안		
		
? 카카오톡 채널 (일상 공간에서) 		
? 30일+ 종단 추적 (미세 변화 포착) 		
? "정원 가꾸기" 놀이 (습관화) 		
? 조기 감지 + 넛지 (골든타임 확보)		
		
### 비전		
		
**2030년까지 한국의 모든 어르신이 일상 대화를 통해 인지 건강을 스스로 관리하는 세상**		
		
### 미션		
		
1. ?? **조기 감지**: 증상 발현 3~5년 전부터 변화 포착		
2. ???????? **가족 참여**: 보호자가 함께 케어하는 생태계		
3. ?? **의료 연계**: 치매안심센터와 원활한 협력		
4. ?? **글로벌 확장**: K-Healthcare의 선도 사례		
		
---		
		
## ? 핵심 기능		
		
### 1. ?? 6가지 대화 카테고리		
		
| 카테고리 | 측정 대상 | 예시 질문 |		
|----------|-----------|-----------|		
| **회상의 꽃밭** | 일화적 기억, 어휘 풍부도 | "어릴 때 봄이 오면 꼭 하시던 일이 있으셨나요?" |		
| **오늘의 한 접시** | 단기 기억, 시각-언어 연계 | "오전: 점심 사진 찍어주세요 ?? / 오후: 재료 3가지는?" |		
| **이름 꽃밭** | 이름대기, 범주 유창성 | "30초 안에 '과일' 이름을 최대한 많이!" |		
| **시간의 나침반** | 시간적 지남력, 계절감 | "오늘 무슨 요일인지, 몇 월인지 말씀해주세요" |		
| **그림 읽기 놀이** | 시공간 인지, 주의력 | "이 그림에서 무엇이 보이나요? (복잡한 장면 이미지)" |		
| **선택의 정원** | 패턴 인식, 실행 기능 | "???????? 중 다른 하나는?" |		
		
### 2. ?? MCDI 분석 프레임워크		
		
┌─────────────────────────────────────────────┐		
 │ MCDI (Memory Garden Cognitive Decline Index) │		
 ├─────────────────────────────────────────────┤		
 │ │		
 │ MCDI = 0.20×LR + 0.20×SD + 0.15×NC │		
 │ + 0.15×TO + 0.20×ER + 0.10×RT │		
 │ │		
 │ 6개 지표: │		
 │		
 ├─ LR: Lexical Richness (어휘 풍부도) │		
 │ ├─ SD: Semantic Drift (의미적 표류) │		
 │ ├─ NC: Narrative Coherence (서사 일관성) │		
 │ ├─ TO: Temporal Orientation (시간 지남력) │		
 │ ├─ ER: Episodic Recall (일화 기억) │		
 │ └─ RT: Response Time (반응 시간) │		
 │ │		
 │ 점수 범위: 0-100 (높을수록 건강) │		
 │ 판정 기준: 개인 baseline 대비 변화율 │		
 │ │		
 └─────────────────────────────────────────────┘		
		
### 3. ?? 4단계 위험도 분류		
?? GREEN (정상) MCDI ≥ 70, slope > -0.5/주 → "정원이 건강하게 자라고 있어요!"		
		
??? YELLOW (관찰) MCDI 50-70, slope -0.5~-1.5/주 → "정원에 구름이 조금 낀 것 같아요"		
		
??? ORANGE (주의) MCDI 30-50, slope < -1.5/주, 2개 지표 2σ↓ → "건강 점검 어떠세요?" + 보호자 알림		
		
?? RED (긴급) MCDI < 30, 지남력 반복 실패 → 보호자 즉시 알림 + 임상 리포트 제공		
		
### 4. ?? 4계층 메모리 시스템		
┌─────────────────────────────────────────────┐		
 │ Layer 1: Session Memory (Redis, 24h TTL) │		
 │ "오늘의 대화 맥락" │		
 └─────────────────────────────────────────────┘		
 ↓		
 ┌─────────────────────────────────────────────┐		
 │ Layer 2: Episodic Memory (Qdrant, 영구) │		
 │ "2024.12.15 점심에 된장찌개 먹음" │		
 └─────────────────────────────────────────────┘		
 ↓		
 ┌─────────────────────────────────────────────┐		
 │ Layer 3: Biographical Memory (Qdrant+PG) │		
 │ "딸 이름: 수진 / 고향: 충주" │		
 └─────────────────────────────────────────────┘		
 ↓		
 ┌─────────────────────────────────────────────┐		
 │ Layer 4: Analytical Memory (TimescaleDB) │		
 │ "일별 MCDI 점수 시계열" │		
 └─────────────────────────────────────────────┘		
		
### 5. ?? 게이미피케이션		
?? 나의 정원 현황		
		
?? 꽃: 15송이 (대화 15회) ?? 나비: 2마리 (연속 3일 보너스) ?? 정원 확장: Lv.3 (누적 50회) ??? 계절 뱃지: Winter 2025		
		
━━━━━━━━━━━━━━━━━━━━━━━ 		
두뇌 건강 날씨: ?? 맑음 		
이번 주도 정원이 건강해요! 		
━━━━━━━━━━━━━━━━━━━━━━━		
		
---		
		
## ??? 기술 스택		
		
### Backend		
		
```yaml		
언어: Python 3.11+		
프레임워크: FastAPI 0.104+		
비동기: asyncio, aiohttp		
타입: mypy, pydantic 2.0+		
		
Database		
RDBMS: PostgreSQL 15+		
Cache: Redis 7.0+		
Vector: Qdrant 1.7+		
Timeseries: TimescaleDB 2.11+ (PostgreSQL extension)		
		
AI/ML		
LLM:		
  - Claude 3.5 Sonnet (Anthropic)		
  - GPT-4o (OpenAI)		
Embedding: text-embedding-3-large (1536 dim)		
Vision: GPT-4o		
NLP: Kiwi 0.15+ (한국어 형태소 분석)		
		
DevOps		
Container: Docker 24+, Docker Compose		
Orchestration: Kubernetes (Production)		
CI/CD: GitHub Actions		
Monitoring: Prometheus + Grafana + Sentry		
		
Task Queue		
Queue: Celery 5.3+		
Broker: Redis		
		
		
		
??? 아키텍처		
		
전체 시스템 다이어그램		
┌─────────────────────────────────────────────────────────┐		
│                    ?? Client Layer                       │		
│  ┌──────────────────┐      ┌──────────────────┐        │		
│  │ KakaoTalk Channel │      │ Guardian Dashboard│        │		
│  │  (사용자 대화)      │      │  (보호자 모니터링) │        │		
│  └──────────────────┘      └──────────────────┘        │		
└───────────────────┬──────────────────┬──────────────────┘		
                    │                  │		
                    ▼                  ▼		
┌─────────────────────────────────────────────────────────┐		
│              ?? API Gateway (FastAPI)                    │		
│  /api/v1/kakao/webhook  │  /api/v1/users/{id}/analysis  │		
└───────────────────┬──────────────────┬──────────────────┘		
                    │                  │		
                    ▼                  ▼		
┌─────────────────────────────────────────────────────────┐		
│           ?? Core Workflow Engine (순수 Python)          │		
│                                                         │		
│  MessageProcessor (메인 오케스트레이터)                   │		
│  ├─ 1. retrieve_memory()                                │		
│  ├─ 2. analyze_response()     ← Analyzer (6개 지표)     │		
│  ├─ 3. evaluate_risk()        ← RiskEvaluator          │		
│  ├─ 4. [if ORANGE/RED] send_alert()                     │		
│  ├─ 5. plan_next()            ← DialogueManager        │		
│  ├─ 6. generate_response()    ← LLM Service            │		
│  └─ 7. store_memory()         ← MemoryManager          │		
│                                                         │		
└───────────────────┬──────────────────┬──────────────────┘		
                    │                  │		
                    ▼                  ▼		
┌─────────────────────────────────────────────────────────┐		
│                 ?? Data Layer                            │		
│  ┌──────┐  ┌──────┐  ┌──────────┐  ┌────────────┐     │		
│  │Redis │  │Qdrant│  │PostgreSQL│  │TimescaleDB │     │		
│  └──────┘  └──────┘  └──────────┘  └────────────┘     │		
└─────────────────────────────────────────────────────────┘		
                    │		
                    ▼		
┌─────────────────────────────────────────────────────────┐		
│              ?? External Services                        │		
│  Claude 3.5 │ GPT-4o │ Kakao API │ Email/SMS           │		
└─────────────────────────────────────────────────────────┘		
		
메시지 처리 플로우		
"""
핵심 워크플로우 (순수 Python, LangGraph 불사용)
"""		
		
async def process_message(user_id: str, message: str) -> str:		
    # 1. 컨텍스트 생성		
    ctx = ProcessingContext(user_id, message)		
    		
    # 2. 메모리 검색 (4계층 병렬)		
    ctx.memory = await memory_manager.retrieve_all(user_id)		
    		
    # 3. 분석 (6개 지표 병렬)		
    ctx.analysis = await analyzer.analyze(message, ctx.memory)		
    		
    # 4. 위험도 평가		
    ctx.risk_level = await risk_evaluator.evaluate(user_id, ctx.analysis)		
    		
    # 5. 조건부 알림 (if문)		
    if ctx.risk_level in ["ORANGE", "RED"]:		
        await notification_service.send_alert(user_id, ctx.analysis)		
    		
    # 6. 대화 생성		
    ctx.response = await dialogue_manager.generate(user_id, ctx)		
    		
    # 7. 메모리 저장 (4계층 병렬)		
    await memory_manager.store_all(user_id, message, ctx)		
    		
    return ctx.response		
		
디렉토리 구조 (간략)		
memory-garden/		
├── api/                      # FastAPI 엔드포인트		
│   ├── routes/		
│   └── schemas/		
├── core/                     # 핵심 비즈니스 로직		
│   ├── workflow/             # ?? 메인 워크플로우		
│   ├── analysis/             # ?? 6개 지표 분석		
│   ├── dialogue/             # ?? 대화 생성		
│   ├── memory/               # ?? 메모리 시스템		
│   └── nlp/                  # NLP 유틸		
├── services/                 # 외부 서비스 연동		
│   ├── llm_service.py		
│   ├── kakao_service.py		
│   └── notification_service.py		
├── database/                 # DB 연결		
├── models/                   # SQLAlchemy 모델		
├── tasks/                    # Celery 작업		
├── tests/                    # 테스트		
└── docs/                     # 문서		
		
?? 시작하기		
		
필수 요구사항		
		
Python 3.11+		
Docker & Docker Compose		
카카오톡 채널 (개발자 계정)		
Claude/OpenAI API 키		
		
로컬 개발 환경 설정		
# 1. 저장소 클론		
git clone https://github.com/your-org/memory-garden.git		
cd memory-garden		
		
# 2. 가상환경 생성		
python3.11 -m venv venv		
source venv/bin/activate  # Windows: venv\Scripts\activate		
		
# 3. 의존성 설치		
pip install -r requirements.txt		
		
# 4. 환경 변수 설정		
cp .env.example .env		
# .env 파일을 편집하여 API 키 입력		
		
# 5. Docker로 DB 실행		
docker-compose up -d postgres redis qdrant		
		
# 6. DB 초기화		
python scripts/init_db.py		
		
# 7. 개발 서버 실행		
uvicorn api.main:app --reload --port 8000		
		
# 8. 브라우저에서 확인		
# http://localhost:8000/docs (Swagger UI)		
		
환경 변수 예시		
# .env		
		
# Database		
DATABASE_URL=postgresql://memgarden:password@localhost:5432/memory_garden		
REDIS_URL=redis://localhost:6379/0		
QDRANT_URL=http://localhost:6333		
		
# AI Services		
CLAUDE_API_KEY=sk-ant-api03-...		
OPENAI_API_KEY=sk-...		
		
# Kakao		
KAKAO_REST_API_KEY=your_kakao_api_key		
KAKAO_CHANNEL_ID=your_channel_id		
		
# Security		
SECRET_KEY=your-secret-key-change-in-production		
		
첫 API 호출 테스트		
# 헬스체크		
curl http://localhost:8000/health		
		
# 사용자 생성		
curl -X POST http://localhost:8000/api/v1/users \		
  -H "Content-Type: application/json" \		
  -d '{		
    "kakao_id": "test_user_123",		
    "name": "홍길동",		
    "birth_date": "1950-05-15"		
  }'		
		
# 테스트 메시지 전송		
curl -X POST http://localhost:8000/api/v1/kakao/webhook \		
  -H "Content-Type: application/json" \		
  -d '{		
    "user_key": "test_user_123",		
    "type": "text",		
    "content": "안녕하세요",		
    "timestamp": "2025-01-15T10:00:00Z"		
  }'		
		
		
		
?? 개발 가이드		
		
개발 철학		
1. KISS (Keep It Simple, Stupid)		
   → 복잡한 것보다 단순하고 명확한 코드		
		
2. YAGNI (You Aren't Gonna Need It)		
   → 미래를 위한 코드 작성 금지, 현재 필요한 것만		
		
3. DRY (Don't Repeat Yourself)		
   → 중복 코드는 함수/클래스로 추상화		
		
4. Fail Fast		
   → 에러는 최대한 빨리 감지하고 명확히 표시		
		
5. 순수 Python 우선		
   → LangGraph 같은 복잡한 프레임워크보다 순수 Python		
		
코딩 컨벤션		
# 파일 구조 템플릿		
"""
모듈 설명 (한 줄)
"""		
		
# Standard Library		
import asyncio		
from datetime import datetime		
from typing import Dict, List, Optional		
		
# Third-Party		
from fastapi import HTTPException		
from pydantic import BaseModel		
		
# Local		
from config.settings import settings		
from utils.logger import get_logger		
		
logger = get_logger(__name__)		
		
# 상수 (대문자)		
MAX_RETRIES = 3		
		
# 타입 Alias		
UserID = str		
		
# 클래스/함수		
class Example:		
    async def method(self, param: str) -> str:		
        """Docstring (Google Style)"""		
        ...		
		
테스트 실행		
# 전체 테스트		
pytest		
		
# 커버리지 포함		
pytest --cov=. --cov-report=html		
		
# 특정 파일만		
pytest tests/test_core/test_analysis.py -v		
		
# 디버깅 모드		
pytest -v -s		
		
브랜치 전략		
main (프로덕션)		
  ↓		
develop (개발 통합)		
  ↓		
├─ feature/dev-a/{feature-name}		
├─ feature/dev-b/{feature-name}		
└─ feature/dev-c/{feature-name}		
		
커밋 메시지		
<type>(<scope>): <subject>		
<body>		
<footer>		
예시:		
feat(analysis): Add lexical richness analyzer		
		
- Implement pronoun ratio calculation		
- Add MATTR algorithm		
- Include empty speech detection		
		
Closes #42		
		
		
		
?? 팀 구성		
		
3인 개발 팀 역할 분담		
		
역할	담당 영역	파일 수
Dev A	Workflow & Analysis	23개
Dev B	Memory & Services	24개
Dev C	API & Integration	25개
		
개발 일정 (8주)		
Week 1-2: 기반 구축 (Context, DB, API 골격)		
Week 3-4: 핵심 기능 (분석, 메모리, 대화)		
Week 5-6: 통합 테스트 (전체 플로우 연결)		
Week 7-8: 최적화 & 배포 (성능, Docker)		
		
		
		
?? 기여하기		
		
기여 방법		
		
1. Fork the Project		
2. Create your Feature Branch (git checkout -b feature/AmazingFeature)		
3. Commit your Changes (git commit -m 'feat: Add some AmazingFeature')		
4. Push to the Branch (git push origin feature/AmazingFeature)		
5. Open a Pull Request		
		
PR 체크리스트		
- [ ] 코드 포맷팅 완료 (black, isort)		
- [ ] 테스트 추가 및 통과		
- [ ] 커버리지 80% 이상		
- [ ] 문서 업데이트		
- [ ] CHANGELOG.md 수정		
		
코드 리뷰 기준		
		
타입 힌팅 및 Docstring 작성		
에러 처리 및 로깅		
테스트 코드 포함		
성능 고려 (N+1 쿼리 등)		
보안 검토 (SQL Injection, XSS 등)		
		
		
		
?? 프로젝트 현황		
		
마일스톤		
		
Phase 1: MVP (2개월) ? 핵심 기능 구현		
Phase 2: Beta (3개월) ? 200명 사용자 테스트		
Phase 3: Clinical (6개월) ? 1,000명 임상 검증		
Phase 4: Launch (3개월) ? 정식 서비스 론칭		
		
현재 지표		
?? 개발 진행률: 0% (설계 완료)		
?? 테스트 커버리지: -		
?? 알려진 버그: 0		
? GitHub Stars: -		
		
		
		
?? 문서		
		
필수 문서		
		
?? SPEC.md ? 기술 명세서 (API, DB 스키마 등)		
?? CLAUDE.md ? Claude Code 개발 가이드		
?? CODING_CONVENTION.md ? 코딩 규칙		
?? ADR.md ? 아키텍처 결정 기록		
		
API 문서		
		
Swagger UI: http://localhost:8000/docs		
ReDoc: http://localhost:8000/redoc		
		
예상 성능		
		
민감도 (Sensitivity): 85%+		
특이도 (Specificity): 80%+		
조기 감지: 증상 발현 3~5년 전		
		
		
		
??? 보안 & 규제		
		
데이터 보안		
		
AES-256 암호화 (대화 내용)		
개인정보 비식별화		
GDPR 준수 (Right to be Forgotten)		
감사 로그 (의료기기 인허가 대비)		
		
의료기기 규제		
Phase 1 (현재): 건강관리 서비스		
- 포지셔닝: "일상 대화 분석 서비스"		
 - 진단 기능 없음, 면책 조항 명시		
		
Phase 2 (임상 검증): 의료기기 준비		
 - 임상 데이터 수집		
 - MMSE/MoCA 상관관계 분석		
 - 식약처 사전 상담		
		
Phase 3 (인허가): 디지털 치료기기 신청		
 - SaMD 등급 판정		
 - 품목 허가 신청		
		
Phase 1 (현재): 건강관리 서비스		
- 포지셔닝: "일상 대화 분석 서비스"		
 - 진단 기능 없음, 면책 조항 명시		
		
Phase 2 (임상 검증): 의료기기 준비		
 - 임상 데이터 수집		
 - MMSE/MoCA 상관관계 분석		
 - 식약처 사전 상담		
		
Phase 3 (인허가): 디지털 치료기기 신청		
 - SaMD 등급 판정		
 - 품목 허가 신청		
		
?? 주요 차별점		
		
항목	기존 솔루션	기억의 정원
접근성	병원 방문 필수	카카오톡 (매일 3분)
측정 방식	1회성 검사	30일+ 종단 추적
사용자 경험	"시험" 느낌	"정원 가꾸기" 놀이
판정 기준	절대 점수	개인 내 변화 (slope)
분석 차원	단일 지표	6차원 복합 (MCDI)
개입 시점	증상 발현 후	조기 감지 + 넛지
가족 참여	환자 단독	보호자 대시보드
		
?? FAQ		
		
Q1: LangGraph를 왜 안 쓰나요?		
		
A: 현재 워크플로우는 조건부 분기가 2개뿐입니다 (알림 발송, 교란변수 체크). 이 정도는 if문으로 충분하며, LangGraph는 오버킬입니다. 순수 Python이 더 단순하고, 디버깅이 쉬우며, 성능도 우수합니다.		
		
Q2: 어떻게 "평가"가 아닌 "놀이"로 느끼게 하나요?		
		
A: 정원 메타포를 사용합니다. 사용자는 매일 "정원에 물 주기"를 하고, 꽃이 피고, 나비가 날아오는 걸 봅니다. 점수나 위험도는 직접 보여주지 않고, "정원 날씨"로 은유적으로 표현합니다.		
		
Q3: 정확도는 얼마나 되나요?		
		
A: 논문 기반 예상 성능은 민감도 85%, 특이도 80%입니다. 단, 이는 1,000명 이상 임상 검증 후 확정됩니다. MVP 단계에서는 "참고용 정보"로만 제공합니다.		
		
Q4: 의사에게 어떤 정보를 제공하나요?		
		
A: 30일간의 대화 분석 리포트를 PDF로 생성합니다. 여기에는 MCDI 점수 추이, 6개 지표 상세, 모순 진술 이력, 어휘 변화 패턴 등이 포함됩니다.		
		

