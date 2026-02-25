# ?? Claude Code 개발 가이드		
		
> 이 문서는 Claude Code (Cursor AI, GitHub Copilot 포함)를 사용하여  		
> Memory Garden 프로젝트를 개발할 때 참고하는 **개발자 바이블**입니다.		
		
---		
		
## ?? 목차		
		
1. [프로젝트 이해](#1-프로젝트-이해)		
2. [코딩 컨벤션](#2-코딩-컨벤션)		
3. [파일별 개발 가이드](#3-파일별-개발-가이드)		
4. [프롬프트 템플릿](#4-프롬프트-템플릿)		
5. [디버깅 가이드](#5-디버깅-가이드)		
6. [AI 도구 활용 팁](#6-ai-도구-활용-팁)		
		
---		
---

## 0. ?? 시작하기 전에

### 0.1 개발 환경 요구사항

```yaml
필수 요구사항:
  - Python: 3.11+
  - Docker: 24.0+
  - Docker Compose: 2.23+
  - Git: 2.40+

권장 도구:
  - IDE: Cursor AI / VS Code
  - Terminal: iTerm2 (macOS) / Windows Terminal
  - API 테스트: Postman / HTTPie

0.2 로컬 개발 환경 설정 (최초 1회)
# ============================================
# 1. 저장소 클론
# ============================================
git clone https://github.com/your-org/memory-garden.git
cd memory-garden

# ============================================
# 2. Python 가상환경 생성
# ============================================
python3.11 -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate

# ============================================
# 3. 의존성 설치
# ============================================
pip install --upgrade pip
pip install -r requirements.txt

# 개발 도구 추가 설치
pip install -r requirements-dev.txt

# ============================================
# 4. 환경 변수 설정
# ============================================
cp .env.example .env

# .env 파일 편집 (필수!)
# - CLAUDE_API_KEY: Anthropic API 키
# - OPENAI_API_KEY: OpenAI API 키
# - DATABASE_URL: PostgreSQL 연결 정보
# - REDIS_URL: Redis 연결 정보

# macOS/Linux
nano .env

# Windows
notepad .env

# ============================================
# 5. Docker Compose로 DB 실행
# ============================================
docker-compose up -d postgres redis qdrant

# 컨테이너 상태 확인
docker-compose ps

# 로그 확인 (문제 발생 시)
docker-compose logs -f postgres

# ============================================
# 6. 데이터베이스 초기화
# ============================================
# 테이블 생성
python scripts/init_db.py

# 마이그레이션 실행 (Alembic)
alembic upgrade head

# 테스트 데이터 추가 (선택)
python scripts/seed_data.py

# ============================================
# 7. 개발 서버 실행
# ============================================
# FastAPI 서버 (Hot Reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ============================================
# 8. API 문서 확인
# ============================================
# 브라우저에서 열기:
# - Swagger UI: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc

# ============================================
# 9. 헬스 체크
# ============================================
curl http://localhost:8000/health

# 예상 응답:
# {"status": "ok", "timestamp": "2025-01-15T10:00:00Z"}

0.3 Cursor AI 설정
# ============================================
# 1. .cursorrules 파일 생성
# ============================================
# 프로젝트 루트에 생성
touch .cursorrules

# 아래 내용 복사 (이 문서의 2장 코딩 컨벤션 전체)

# ============================================
# 1. .cursorrules 파일 생성
# ============================================
# 프로젝트 루트에 생성
touch .cursorrules

# 아래 내용 복사 (이 문서의 2장 코딩 컨벤션 전체)

.cursorrules 내용:
# Memory Garden - Cursor AI Rules

## Project Context
- 치매 조기 감지 서비스 (카카오톡 기반)
- 순수 Python (LangGraph 불사용)
- 비동기 처리 (asyncio)

## Coding Standards
1. 타입 힌팅 필수
2. Google Style Docstring
3. 에러 처리 (try-except)
4. 로깅 추가 (logger.info/error)
5. async/await for I/O operations

## File Structure
- snake_case for files
- PascalCase for classes
- snake_case for functions

## Testing
- pytest + pytest-asyncio
- 최소 80% 커버리지
- AAA 패턴 (Arrange-Act-Assert)

자세한 내용은 docs/CLAUDE.md 참조

# ============================================
# 2. Cursor 설정 확인
# ============================================
# Cursor에서 Cmd+, (설정 열기)
# Rules for AI > .cursorrules 자동 인식 확인

0.4 첫 번째 코드 작성 테스트
# ============================================
# 1. 간단한 테스트 실행
# ============================================
pytest tests/test_api/test_health.py -v

# 예상 출력:
# tests/test_api/test_health.py::test_health_check PASSED

# ============================================
# 2. 코드 포맷팅 테스트
# ============================================
black --check core/
isort --check-only core/

# ============================================
# 3. 타입 체킹 테스트
# ============================================
mypy core/

# ============================================
# 4. Hello World API 작성
# ============================================
# api/routes/hello.py 생성 (Cursor에서)

Cursor에서 Cmd+K 후:
"api/routes/hello.py를 생성해줘.
GET /api/v1/hello 엔드포인트 하나만.
{'message': 'Hello, Memory Garden!'} 반환.
.cursorrules 준수."

# ============================================
# 5. 작성한 API 테스트
# ============================================
# 서버 재시작 (자동 reload)
curl http://localhost:8000/api/v1/hello

# 예상 응답:
# {"message": "Hello, Memory Garden!"}

0.5 문제 해결 (Troubleshooting)
# 문제 1: Docker 컨테이너가 시작 안 됨
docker-compose down
docker-compose up -d --force-recreate

# 문제 2: 포트 충돌 (8000 포트 사용 중)
# 다른 프로세스 확인
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 프로세스 종료 후 재시도

# 문제 3: Python 가상환경 활성화 안 됨
which python  # 가상환경 python인지 확인
# 출력: /path/to/memory-garden/venv/bin/python (정상)

# 문제 4: 의존성 설치 실패
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --no-cache-dir

# 문제 5: DB 연결 실패
# PostgreSQL 컨테이너 로그 확인
docker-compose logs postgres

# DB 접속 테스트
docker-compose exec postgres psql -U memgarden -d memory_garden

0.6 다음 단계
설정이 완료되면 1. 프로젝트 이해부터 읽고 개발을 시작하세요!

권장 순서:

1장: 프로젝트 이해 (워크플로우 외우기)
2장: 코딩 컨벤션 (스타일 익히기)
3장: 핵심 파일 작성 (context.py → message_processor.py 순)
4장: AI 프롬프트 활용

---

## ?? 우선순위 중간

### 4. 개별 지표 파일 스켈레톤 추가

**위치: 3장 파일별 개발 가이드 → analyzer.py 다음에 추가**

```markdown
---

**5. 개별 분석 지표 (6개 파일)**

다음 6개 파일은 각각 독립적인 분석 지표를 구현합니다.
모두 동일한 인터페이스를 따라 Analyzer에서 병렬 실행됩니다.

**공통 인터페이스:**
```python
from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseMetricAnalyzer(ABC):
    """모든 지표 분석기의 베이스 클래스"""
    
    @abstractmethod
    async def analyze(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            message: 사용자 응답 텍스트
            context: 분석에 필요한 추가 정보
        
        Returns:
            {
                "score": float (0-100),
                "components": dict,
                "details": dict
            }
        """
        pass
5.1 core/analysis/lexical_richness.py
"""
어휘 풍부도 (LR) 분석기

Fraser et al. (2016) 기반:
- 대명사 대체율 증가 = 인지 저하 신호
- Type-Token Ratio (TTR) 감소 = 어휘 빈약
- 빈 발화 증가 = 단어 인출 장애
"""

from typing import Dict, Any, List
from kiwipiepy import Kiwi
import numpy as np

from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)

class LexicalRichnessAnalyzer:
    """어휘 풍부도 분석"""
    
    def __init__(self):
        self.kiwi = Kiwi()
        
        # 빈 발화 패턴
        self.empty_speech_patterns = [
            "그거", "저거", "뭐더라", "있잖아", "그게", 
            "어", "음", "그", "저"
        ]
    
    async def analyze(
        self, 
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        어휘 풍부도 분석
        
        Returns:
            {
                "score": 78.5,
                "components": {
                    "pronoun_ratio": 0.15,
                    "mattr": 0.72,
                    "concreteness": 0.85,
                    "empty_speech_ratio": 0.05
                },
                "details": {
                    "total_tokens": 42,
                    "unique_tokens": 30,
                    "pronouns": ["그거", "저거"],
                    "concrete_nouns": ["쑥", "뒷산", "엄마"]
                }
            }
        """
        try:
            # 형태소 분석
            tokens = self._tokenize(message)
            
            # 4개 하위 지표 계산
            pronoun_ratio = self._calculate_pronoun_ratio(tokens)
            mattr = self._calculate_mattr(tokens)
            concreteness = self._calculate_concreteness(tokens)
            empty_speech_ratio = self._calculate_empty_speech(message)
            
            # 종합 점수 (4개 평균, 역방향 지표는 반전)
            score = (
                (1 - pronoun_ratio) * 25 +  # 낮을수록 좋음
                mattr * 100 * 0.25 +
                concreteness * 100 * 0.25 +
                (1 - empty_speech_ratio) * 25
            )
            
            return {
                "score": round(score, 2),
                "components": {
                    "pronoun_ratio": round(pronoun_ratio, 3),
                    "mattr": round(mattr, 3),
                    "concreteness": round(concreteness, 3),
                    "empty_speech_ratio": round(empty_speech_ratio, 3)
                },
                "details": {
                    "total_tokens": len(tokens),
                    "unique_tokens": len(set(t['form'] for t in tokens)),
                    "pronouns": self._extract_pronouns(tokens),
                    "concrete_nouns": self._extract_concrete_nouns(tokens)
                }
            }
            
        except Exception as e:
            logger.error(f"Lexical Richness analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"LR analysis failed: {e}") from e
    
    def _tokenize(self, text: str) -> List[Dict]:
        """Kiwi 형태소 분석"""
        result = self.kiwi.analyze(text)
        tokens = []
        for token, pos, _, _ in result[0][0]:
            tokens.append({"form": token, "pos": pos})
        return tokens
    
    def _calculate_pronoun_ratio(self, tokens: List[Dict]) -> float:
        """대명사 비율 = 대명사 / (대명사 + 명사)"""
        pronouns = [t for t in tokens if t['pos'] == 'NP']  # 대명사
        nouns = [t for t in tokens if t['pos'].startswith('N')]  # 명사류
        
        if not nouns:
            return 0.0
        
        return len(pronouns) / len(nouns)
    
    def _calculate_mattr(self, tokens: List[Dict], window: int = 20) -> float:
        """Moving Average TTR"""
        if len(tokens) < window:
            # 짧은 문장은 일반 TTR
            forms = [t['form'] for t in tokens]
            return len(set(forms)) / len(forms) if forms else 0.0
        
        ttrs = []
        for i in range(len(tokens) - window + 1):
            window_tokens = [tokens[j]['form'] for j in range(i, i + window)]
            ttr = len(set(window_tokens)) / window
            ttrs.append(ttr)
        
        return np.mean(ttrs)
    
    def _calculate_concreteness(self, tokens: List[Dict]) -> float:
        """구체 명사 비율"""
        # 간단 구현: 일반명사(NNG) vs 고유명사(NNP)
        nouns = [t for t in tokens if t['pos'].startswith('NN')]
        concrete = [t for t in nouns if t['pos'] == 'NNG']
        
        if not nouns:
            return 0.5  # 중립
        
        return len(concrete) / len(nouns)
    
    def _calculate_empty_speech(self, text: str) -> float:
        """빈 발화 비율"""
        words = text.split()
        if not words:
            return 0.0
        
        empty_count = sum(
            1 for word in words 
            if any(pattern in word for pattern in self.empty_speech_patterns)
        )
        
        return empty_count / len(words)
    
    def _extract_pronouns(self, tokens: List[Dict]) -> List[str]:
        """대명사 추출"""
        return [t['form'] for t in tokens if t['pos'] == 'NP']
    
    def _extract_concrete_nouns(self, tokens: List[Dict]) -> List[str]:
        """구체 명사 추출"""
        return [t['form'] for t in tokens if t['pos'] == 'NNG'][:5]  # 최대 5개

AI에게 요청 시:
"core/analysis/lexical_richness.py를 위 구조대로 완성해줘.
주석으로 각 지표의 수식도 명시해줘."

5.2 core/analysis/semantic_drift.py
"""
의미적 표류 (SD) 분석기

질문-응답 관련도 저하 = 주의력/집행기능 저하
"""

from typing import Dict, Any
import numpy as np

from services.llm_service import LLMService
from core.nlp.embedder import Embedder
from utils.logger import get_logger

logger = get_logger(__name__)

class SemanticDriftAnalyzer:
    """의미적 표류 분석"""
    
    def __init__(self, llm_service: LLMService, embedder: Embedder):
        self.llm = llm_service
        self.embedder = embedder
    
    async def analyze(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        의미적 표류 분석
        
        context:
            - question: 원래 질문
            - previous_messages: 이전 대화들
        
        Returns:
            {
                "score": 82.3,
                "components": {
                    "relevance": 0.75,
                    "coherence": 0.82,
                    "topic_drift": 0,
                    "logical_flow": 4
                }
            }
        """
        question = context.get("question", "") if context else ""
        
        # 1. 질문-응답 관련도 (Embedding Cosine Similarity)
        relevance = await self._calculate_relevance(question, message)
        
        # 2. 문장 간 응집도
        coherence = await self._calculate_coherence(message)
        
        # 3. 주제 이탈 탐지 (LLM Judge)
        topic_drift = await self._detect_topic_drift(question, message)
        
        # 4. 논리성 평가 (LLM Judge 1-5점)
        logical_flow = await self._evaluate_logic(message)
        
        # 종합 점수
        score = (
            relevance * 100 * 0.35 +
            coherence * 100 * 0.30 +
            (1 - topic_drift) * 100 * 0.15 +
            logical_flow * 20 * 0.20
        )
        
        return {
            "score": round(score, 2),
            "components": {
                "relevance": round(relevance, 3),
                "coherence": round(coherence, 3),
                "topic_drift": int(topic_drift),
                "logical_flow": logical_flow
            }
        }
    
    async def _calculate_relevance(self, question: str, answer: str) -> float:
        """질문-응답 cosine similarity"""
        if not question:
            return 1.0  # 질문이 없으면 중립
        
        q_vec = await self.embedder.embed(question)
        a_vec = await self.embedder.embed(answer)
        
        similarity = np.dot(q_vec, a_vec) / (
            np.linalg.norm(q_vec) * np.linalg.norm(a_vec)
        )
        
        # 0.5~1.0 범위로 정규화
        normalized = max(0, (similarity + 1) / 2)
        return normalized
    
    async def _calculate_coherence(self, text: str) -> float:
        """문장 간 응집도"""
        sentences = text.split('.')
        if len(sentences) < 2:
            return 1.0
        
        # 각 문장 임베딩 후 인접 문장 유사도
        embeddings = [await self.embedder.embed(s.strip()) for s in sentences if s.strip()]
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i+1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1])
            )
            similarities.append(sim)
        
        return np.mean(similarities) if similarities else 1.0
    
    async def _detect_topic_drift(self, question: str, answer: str) -> int:
        """주제 이탈 탐지 (0: 정상, 1: 이탈)"""
        if not question:
            return 0
        
        prompt = f"""
다음 질문과 답변의 관련성을 평가하세요.

질문: {question}
답변: {answer}

답변이 질문과 관련이 있으면 0, 주제를 완전히 벗어났으면 1을 출력하세요.
숫자만 출력하세요.
"""
        
        result = await self.llm.call(prompt, max_tokens=5)
        try:
            return int(result.strip())
        except:
            return 0
    
    async def _evaluate_logic(self, text: str) -> int:
        """논리성 평가 (1-5점)"""
        prompt = f"""
다음 텍스트의 논리성을 1-5점으로 평가하세요.

텍스트: {text}

평가 기준:
5점: 논리적 흐름이 명확, 인과관계 뚜렷
4점: 대체로 논리적
3점: 보통
2점: 다소 비논리적, 비약이 있음
1점: 논리 없음, 횡설수설

숫자만 출력하세요.
"""
        
        result = await self.llm.call(prompt, max_tokens=5)
        try:
            score = int(result.strip())
            return max(1, min(5, score))  # 1-5 범위 강제
        except:
            return 3  # 실패 시 중립

5.3 나머지 4개 지표 파일 (간략 버전)
# core/analysis/narrative_coherence.py
"""서사 일관성 (NC) - 5W1H 포함도, 시간 순서, 반복성"""
class NarrativeCoherenceAnalyzer:
    async def analyze(self, message: str, context: Dict = None) -> Dict:
        # TODO: 구현
        pass

# core/analysis/temporal_orientation.py
"""시간적 지남력 (TO) - 요일/날짜 정확도, 계절 적합성"""
class TemporalOrientationAnalyzer:
    async def analyze(self, message: str, context: Dict = None) -> Dict:
        # TODO: 구현
        pass

# core/analysis/episodic_recall.py
"""일화 기억 (ER) - 자유 회상 정확도, 단서 재인, 모순 탐지"""
class EpisodicRecallAnalyzer:
    async def analyze(self, message: str, context: Dict = None) -> Dict:
        # TODO: 구현
        pass

# core/analysis/response_time.py
"""반응 시간 (RT) - 메시지 지연 시간, 효율성"""
class ResponseTimeAnalyzer:
    async def analyze(self, message: str, context: Dict = None) -> Dict:
        # TODO: 구현
        pass

AI에게 순차 요청:
"core/analysis/narrative_coherence.py를 완성해줘.
lexical_richness.py와 같은 구조로."

"core/analysis/temporal_orientation.py를 완성해줘.
현재 날짜/요일 확인, 계절 적합성 판단 포함."

"core/analysis/episodic_recall.py를 완성해줘.
context['episodic']에서 과거 기록 비교."

"core/analysis/response_time.py를 완성해줘.
context['response_latency']에서 지연 시간 추출."




		
## 1. 프로젝트 이해		
		
### ?? 핵심 컨셉		
Memory Garden = 치매 조기 감지 서비스		
		
?? 정원 가꾸기 메타포 사용자: "매일 정원에 물 주기" AI: 배후에서 인지 기능 분석		
		
?? MCDI 분석 (6개 지표) LR + SD + NC + TO + ER + RT → 종합 점수		
		
?? 위험도 4단계 GREEN → YELLOW → ORANGE → RED		
		
?? 카카오톡 기반 일일 2~3회 자연스러운 대화		
		
### ??? 아키텍처 철학		
		
```python		
# ? LangGraph 사용 안 함!		
# ? 순수 Python 기반		
		
# 이유:		
# 1. 복잡한 분기가 2개뿐 (if문으로 충분)		
# 2. 러닝 커브 제거 (팀 생산성 우선)		
# 3. 디버깅 용이성		
# 4. 성능 오버헤드 없음		
		
# 대신 사용:		
# - MessageProcessor: 메인 워크플로우 클래스		
# - ProcessingContext: State 역할 (dataclass)		
# - async/await: 비동기 처리		
		
?? 워크플로우 (외워두기!)		
"""
핵심 플로우 (이 순서를 항상 기억!)

MCDI 종합 점수 계산:
MCDI = w₁·LR + w₂·SD + w₃·NC + w₄·TO + w5·ER + w6·RT

가중치:
- w₁ = 0.20 (LR: Lexical Richness - 어휘 풍부도)
- w₂ = 0.20 (SD: Semantic Drift - 의미적 표류)
- w₃ = 0.15 (NC: Narrative Coherence - 서사 일관성)
- w₄ = 0.15 (TO: Temporal Orientation - 시간적 지남력)
- w5 = 0.20 (ER: Episodic Recall - 일화 기억)
- w6 = 0.10 (RT: Response Time - 반응 시간)
"""		
		
async def process_message(user_id, message):		
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
        await send_alert(user_id, ctx.analysis)		
    		
    # 6. 대화 생성		
    ctx.response = await dialogue_manager.generate(user_id, ctx)		
    		
    # 7. 메모리 저장 (4계층 병렬)		
    await memory_manager.store_all(user_id, message, ctx)		
    		
    return ctx.response		
		
2. 코딩 컨벤션		
		
?? 파일 구조 템플릿		
		
모든 Python 파일은 이 구조를 따릅니다:		
"""
모듈 한 줄 설명

상세 설명 (선택사항, 복잡한 로직일 때만)

Author: Dev A/B/C
Created: YYYY-MM-DD
"""		
		
# ============================================		
# 1. Standard Library Imports (알파벳 순)		
# ============================================		
import asyncio		
import logging		
from datetime import datetime		
from typing import Dict, List, Optional, Any		
		
# ============================================		
# 2. Third-Party Imports (알파벳 순)		
# ============================================		
from fastapi import HTTPException		
from pydantic import BaseModel, Field		
from sqlalchemy.orm import Session		
		
# ============================================		
# 3. Local Imports (상대 경로 우선)		
# ============================================		
from config.settings import settings		
from core.memory.session_memory import SessionMemory		
from utils.logger import get_logger		
		
# ============================================		
# 4. Logger 설정		
# ============================================		
logger = get_logger(__name__)		
		
# ============================================		
# 5. 상수 정의 (대문자 + 언더스코어)		
# ============================================		
MAX_RETRIES = 3		
DEFAULT_TIMEOUT = 30		
VALID_RISK_LEVELS = ["GREEN", "YELLOW", "ORANGE", "RED"]		
		
# ============================================		
# 6. 타입 Alias (복잡한 타입은 별도 정의)		
# ============================================		
UserID = str		
MCDIScore = float		
AnalysisResult = Dict[str, Any]		
		
		
# ============================================		
# 7. 클래스 정의		
# ============================================		
class ExampleClass:		
    """클래스 설명		
    		
    Attributes:		
        attr1: 속성 설명		
        attr2: 속성 설명		
    """		
    		
    def __init__(self, param1: str, param2: int):		
        self.attr1 = param1		
        self.attr2 = param2		
    		
    async def method(self, arg: str) -> str:		
        """메서드 설명		
        		
        Args:		
            arg: 인자 설명		
        		
        Returns:		
            반환값 설명		
        		
        Raises:		
            ValueError: 발생 조건		
        		
        Example:		
            >>> obj = ExampleClass("test", 42)		
            >>> result = await obj.method("input")		
            >>> print(result)		
            "output"		
        """		
        try:		
            # 로직 구현		
            logger.info(f"Processing: {arg}")		
            result = f"processed_{arg}"		
            return result		
        		
        except Exception as e:		
            logger.error(f"Method failed: {e}", exc_info=True)		
            raise		
		
		
# ============================================		
# 8. 독립 함수 (클래스 밖)		
# ============================================		
async def standalone_function(param: str) -> str:		
    """독립 함수 설명"""		
    ...		
		
?? 네이밍 규칙		
# ? 변수명: snake_case		
user_id = "user_123"		
mcdi_score = 78.5		
analysis_result = {...}		
		
# ? Boolean 변수: is_, has_, should_ 접두사		
is_valid = True		
has_error = False		
should_retry = True		
		
# ? 함수명: 동사 + 명사		
def calculate_score() -> float:		
    ...		
		
async def fetch_data() -> dict:  # async 접두사 X		
    ...		
		
# ? 클래스명: PascalCase		
class AnalysisResult:		
    ...		
		
class MCDICalculator:		
    ...		
		
# ? 상수: 대문자 + 언더스코어		
MAX_RETRIES = 3		
DEFAULT_TIMEOUT = 30		
		
# ? Private: 언더스코어 접두사		
def _internal_helper():  # 모듈 내부용		
    ...		
		
class Example:		
    def __init__(self):		
        self._private_attr = 42  # 외부 접근 지양		
		
?? 타입 힌팅 (필수!)		
from typing import Dict, List, Optional, Any, Union		
		
# ? 모든 함수 시그니처에 타입 힌팅		
async def process_data(		
    input_data: List[str],		
    options: Optional[Dict[str, Any]] = None		
) -> Dict[str, float]:		
    """타입 힌팅 예시"""		
    ...		
		
# ? 클래스 속성		
class User:		
    id: str		
    age: int		
    created_at: datetime		
		
# ? 복잡한 타입은 Alias 사용		
from typing import TypeAlias		
		
UserId: TypeAlias = str		
MCDIScores: TypeAlias = Dict[str, float]		
AnalysisResult: TypeAlias = Dict[str, Any]		
		
def analyze(user_id: UserId) -> AnalysisResult:		
    ...		
		
# ? Optional 명시적 사용		
def get_user(user_id: str) -> Optional[User]:		
    ...		
		
# Python 3.10+ 문법도 OK		
def get_user(user_id: str) -> User | None:		
    ...		
		
??? 에러 처리 패턴		
# ? 구체적인 예외 처리		
try:		
    result = await llm.call(prompt)		
except RateLimitError as e:		
    logger.warning(f"Rate limited, retrying: {e}")		
    await asyncio.sleep(60)		
    result = await llm.call(prompt)		
except APIError as e:		
    logger.error(f"API error: {e}", exc_info=True)		
    raise AnalysisError(f"Failed to call LLM: {e}") from e		
except Exception as e:		
    logger.critical(f"Unexpected error: {e}", exc_info=True)		
    raise		
		
# ? 너무 광범위한 예외 처리 금지		
try:		
    ...		
except Exception:  # 피할 것!		
    pass		
		
# ? Custom Exception 정의 및 사용		
# utils/exceptions.py		
class MemoryGardenError(Exception):		
    """베이스 예외"""		
    pass		
		
class AnalysisError(MemoryGardenError):		
    """분석 실패"""		
    pass		
		
class MCDICalculationError(AnalysisError):		
    """MCDI 계산 실패"""		
    pass		
		
# 사용		
if not scores:		
    raise MCDICalculationError("No valid scores to calculate MCDI")		
		
?? 로깅 규칙		
from utils.logger import get_logger		
		
logger = get_logger(__name__)		
		
# ? 로그 레벨 가이드		
logger.debug(f"State updated: {state}")        # 개발 중 상세 정보		
logger.info(f"Processing user: {user_id}")     # 주요 작업 시작/완료		
logger.warning(f"Cache miss for {user_id}")    # 예상 가능한 문제		
logger.error(f"Parse failed: {e}", exc_info=True)  # 복구 가능한 오류		
logger.critical(f"DB connection lost!")        # 시스템 중단 수준		
		
# ? 구조화된 로그 (권장)		
logger.info(		
    "MCDI calculated",		
    extra={		
        "user_id": user_id,		
        "mcdi_score": score,		
        "processing_time_ms": elapsed_time,		
        "risk_level": risk_level		
    }		
)		
		
# ? 읽기 어려운 로그		
logger.info(f"Score: {score} for {user_id} in {elapsed_time}ms level {risk_level}")		
		
? Async/Await 규칙		
# ? IO-bound 작업은 async		
async def fetch_from_db(user_id: str) -> User:		
    """DB 조회는 async"""		
    async with db.session() as session:		
        return await session.get(User, user_id)		
		
# ? CPU-bound 작업은 executor 사용		
import asyncio		
from concurrent.futures import ProcessPoolExecutor		
		
async def calculate_heavy_metric(data: List[str]) -> float:		
    """CPU 집약적 작업"""		
    loop = asyncio.get_event_loop()		
    with ProcessPoolExecutor() as executor:		
        result = await loop.run_in_executor(		
            executor,		
            _sync_heavy_calculation,  # 동기 함수		
            data		
        )		
    return result		
		
def _sync_heavy_calculation(data: List[str]) -> float:		
    """CPU 집약적 동기 함수"""		
    # numpy, sklearn 등 CPU 작업		
    ...		
		
# ? 병렬 실행		
results = await asyncio.gather(		
    task1(),		
    task2(),		
    task3(),		
    return_exceptions=True  # 하나 실패해도 계속 진행		
)		
		
# ? 타임아웃		
try:		
    result = await asyncio.wait_for(		
        slow_operation(),		
        timeout=10.0		
    )		
except asyncio.TimeoutError:		
    logger.error("Operation timed out")		
		
?? 테스트 코드 작성		
# tests/test_core/test_analysis.py		
		
import pytest		
from unittest.mock import AsyncMock, patch, MagicMock		
		
@pytest.fixture		
def sample_context():		
    """테스트용 컨텍스트"""		
    return ProcessingContext(		
        user_id="test_user",		
        message="안녕하세요",		
        timestamp=datetime.now()		
    )		
		
@pytest.mark.asyncio		
async def test_analyze_normal_response(sample_context):		
    """정상 케이스: 구체적인 응답"""		
    # Arrange (준비)		
    analyzer = Analyzer()		
    message = "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요"		
    		
    # Act (실행)		
    result = await analyzer.analyze(message, {})		
    		
    # Assert (검증)		
    assert result["lr_score"] > 70		
    assert result["mcdi_score"] > 70		
		
@pytest.mark.asyncio		
async def test_analyze_empty_input():		
    """엣지 케이스: 빈 입력"""		
    # Arrange		
    analyzer = Analyzer()		
    		
    # Act & Assert		
    with pytest.raises(ValueError, match="Message cannot be empty"):		
        await analyzer.analyze("", {})		
		
@pytest.mark.asyncio		
@patch('services.llm_service.LLMService.call')		
async def test_analyze_with_llm_failure(mock_llm_call):		
    """에러 케이스: LLM 호출 실패"""		
    # Arrange		
    mock_llm_call.side_effect = Exception("API Error")		
    analyzer = Analyzer()		
    		
    # Act & Assert		
    with pytest.raises(AnalysisError):		
        await analyzer.analyze("test message", {})		
		
@pytest.mark.asyncio		
async def test_analyze_with_mock_dependencies():		
    """Mock 사용 예시"""		
    # Arrange		
    mock_llm = AsyncMock()		
    mock_llm.call.return_value = "LLM response"		
    		
    analyzer = Analyzer(llm_service=mock_llm)		
    		
    # Act		
    result = await analyzer.analyze("test", {})		
    		
    # Assert		
    mock_llm.call.assert_called_once()		
    assert result is not None		
		
		
		
3. 파일별 개발 가이드		
		
?? 핵심 파일 (우선 순위 순)		
		
1. core/workflow/context.py		
"""
처리 컨텍스트

LangGraph State 대신 사용하는 dataclass.
메시지 처리 과정의 모든 정보를 담는 컨테이너.
"""		
		
from dataclasses import dataclass, field		
from datetime import datetime		
from typing import Optional, Dict, Any		
		
@dataclass		
class ProcessingContext:		
    """메시지 처리 컨텍스트		
    		
    워크플로우의 모든 단계에서 공유하는 상태 객체.		
    		
    Attributes:		
        user_id: 사용자 고유 ID		
        message: 사용자 입력 메시지		
        message_type: text/image/selection		
        memory: 검색된 메모리 데이터		
        analysis: 분석 결과		
        risk_level: 위험도 (GREEN/YELLOW/ORANGE/RED)		
        response: 최종 응답 메시지		
    """		
    		
    # ============================================		
    # 입력 (Required)		
    # ============================================		
    user_id: str		
    message: str		
    		
    # ============================================		
    # 입력 (Optional)		
    # ============================================		
    message_type: str = "text"		
    image_url: Optional[str] = None		
    timestamp: datetime = field(default_factory=datetime.now)		
    		
    # ============================================		
    # 중간 처리 결과		
    # ============================================		
    memory: Optional[Dict[str, Any]] = None		
    analysis: Optional[Dict[str, Any]] = None		
    mcdi_score: Optional[float] = None		
    		
    # ============================================		
    # 위험도 평가		
    # ============================================		
    risk_level: Optional[str] = None		
    alert_needed: bool = False		
    should_check_confounds: bool = False		
    		
    # ============================================		
    # 다음 상호작용 계획		
    # ============================================		
    next_category: Optional[str] = None		
    next_difficulty: Optional[str] = None		
    confound_question_scheduled: Optional[str] = None		
    		
    # ============================================		
    # 최종 출력		
    # ============================================		
    response: Optional[str] = None		
    		
    # ============================================		
    # 메타데이터		
    # ============================================		
    processing_time_ms: Optional[float] = None		
    error: Optional[str] = None		
    		
    def to_dict(self) -> Dict[str, Any]:		
        """로깅/저장용 딕셔너리 변환"""		
        return {		
            "user_id": self.user_id,		
            "message": self.message,		
            "message_type": self.message_type,		
            "timestamp": self.timestamp.isoformat(),		
            "mcdi_score": self.mcdi_score,		
            "risk_level": self.risk_level,		
            "next_category": self.next_category,		
            "processing_time_ms": self.processing_time_ms,		
            "error": self.error		
        }		
		
AI에게 요청 시:		
"core/workflow/context.py를 위 템플릿대로 작성해줘.
추가로 validate() 메서드를 만들어서 필수 필드가 모두 채워졌는지 검증해줘."		
		
2. core/workflow/message_processor.py		
"""
메시지 처리 메인 워크플로우

전체 처리 플로우를 조율하는 핵심 클래스.
LangGraph 없이 순수 Python으로 구현.
"""		
		
from typing import Optional		
import time		
		
from core.workflow.context import ProcessingContext		
from core.memory.memory_manager import MemoryManager		
from core.analysis.analyzer import Analyzer		
from core.analysis.risk_evaluator import RiskEvaluator		
from core.dialogue.dialogue_manager import DialogueManager		
from services.notification_service import NotificationService		
from utils.logger import get_logger		
from utils.exceptions import WorkflowError		
		
logger = get_logger(__name__)		
		
		
class MessageProcessor:		
    """메시지 처리 메인 워크플로우		
    		
    8단계 처리 플로우:		
    1. 컨텍스트 생성		
    2. 메모리 검색		
    3. 응답 분석		
    4. 위험도 평가		
    5. 조건부 알림		
    6. 교란 변수 처리		
    7. 다음 상호작용 계획		
    8. 응답 생성 및 메모리 저장		
    """		
    		
    def __init__(		
        self,		
        memory_manager: MemoryManager,		
        analyzer: Analyzer,		
        risk_evaluator: RiskEvaluator,		
        dialogue_manager: DialogueManager,		
        notification_service: NotificationService		
    ):		
        self.memory = memory_manager		
        self.analyzer = analyzer		
        self.risk_evaluator = risk_evaluator		
        self.dialogue = dialogue_manager		
        self.notification = notification_service		
    		
    async def process(		
        self,		
        user_id: str,		
        message: str,		
        message_type: str = "text",		
        image_url: Optional[str] = None		
    ) -> str:		
        """		
        메시지 처리 메인 엔트리포인트		
        		
        Args:		
            user_id: 사용자 ID		
            message: 사용자 메시지		
            message_type: text/image/selection		
            image_url: 이미지 URL (선택)		
        		
        Returns:		
            응답 메시지		
        		
        Raises:		
            WorkflowError: 처리 중 오류 발생 시		
        """		
        start_time = time.time()		
        		
        logger.info(		
            f"Starting message processing",		
            extra={		
                "user_id": user_id,		
                "message_type": message_type		
            }		
        )		
        		
        # 1. 컨텍스트 생성		
        ctx = ProcessingContext(		
            user_id=user_id,		
            message=message,		
            message_type=message_type,		
            image_url=image_url		
        )		
        		
        try:		
            # 2. 메모리 검색		
            ctx = await self._retrieve_memory(ctx)		
            		
            # 3. 응답 분석		
            ctx = await self._analyze_response(ctx)		
            		
            # 4. 위험도 평가		
            ctx = await self._evaluate_risk(ctx)		
            		
            # 5. 조건부 알림 (분기)		
            if ctx.risk_level in ["ORANGE", "RED"]:		
                await self._send_alert(ctx)		
            		
            # 6. 교란 변수 처리 (분기)		
            if ctx.should_check_confounds:		
                ctx = await self._handle_confounds(ctx)		
            		
            # 7. 다음 상호작용 계획		
            ctx = await self._plan_next_interaction(ctx)		
            		
            # 8. 응답 생성		
            ctx = await self._generate_response(ctx)		
            		
            # 9. 메모리 저장		
            await self._store_memory(ctx)		
            		
            # 처리 시간 기록		
            ctx.processing_time_ms = (time.time() - start_time) * 1000		
            		
            logger.info(		
                "Message processed successfully",		
                extra=ctx.to_dict()		
            )		
            		
            return ctx.response		
            		
        except Exception as e:		
            ctx.error = str(e)		
            ctx.processing_time_ms = (time.time() - start_time) * 1000		
            		
            logger.error(		
                f"Workflow failed: {e}",		
                extra=ctx.to_dict(),		
                exc_info=True		
            )		
            		
            # Fallback 응답		
            return await self._generate_fallback_response(ctx)		
    		
    async def _retrieve_memory(self, ctx: ProcessingContext) -> ProcessingContext:		
        """		
        Step 2: 메모리 검색		
        		
        4계층에서 병렬로 데이터 검색:		
        - Session (Redis)		
        - Episodic (Qdrant)		
        - Biographical (Qdrant + PostgreSQL)		
        - Analytical (TimescaleDB)		
        """		
        logger.debug(f"Retrieving memory for user: {ctx.user_id}")		
        		
        memory_data = await self.memory.retrieve_all(		
            user_id=ctx.user_id,		
            query=ctx.message		
        )		
        		
        ctx.memory = memory_data		
        return ctx		
    		
    async def _analyze_response(self, ctx: ProcessingContext) -> ProcessingContext:		
        """		
        Step 3: 응답 분석		
        		
        6개 지표 병렬 계산:		
        - LR (어휘 풍부도)		
        - SD (의미적 표류)		
        - NC (서사 일관성)		
        - TO (시간적 지남력)		
        - ER (일화 기억)		
        - RT (반응 시간)		
        """		
        logger.debug("Analyzing response")		
        		
        analysis_result = await self.analyzer.analyze(		
            message=ctx.message,		
            memory=ctx.memory,		
            message_type=ctx.message_type,		
            image_url=ctx.image_url		
        )		
        		
        ctx.analysis = analysis_result		
        ctx.mcdi_score = analysis_result["mcdi_score"]		
        		
        return ctx		
    		
    async def _evaluate_risk(self, ctx: ProcessingContext) -> ProcessingContext:		
        """		
        Step 4: 위험도 평가		
        		
        - Baseline 대비 z-score 계산		
        - 4주 기울기 계산		
        - GREEN/YELLOW/ORANGE/RED 판정		
        """		
        logger.debug("Evaluating risk level")		
        		
        risk_evaluation = await self.risk_evaluator.evaluate(		
            user_id=ctx.user_id,		
            current_score=ctx.mcdi_score,		
            analysis=ctx.analysis		
        )		
        		
        ctx.risk_level = risk_evaluation["risk_level"]		
        ctx.should_check_confounds = risk_evaluation["check_confounds"]		
        ctx.alert_needed = risk_evaluation["alert_needed"]		
        		
        return ctx		
    		
    async def _send_alert(self, ctx: ProcessingContext) -> None:		
        """		
        Step 5: 알림 전송 (조건부)		
        		
        ORANGE/RED 레벨일 때만 실행.		
        """		
        logger.info(f"Sending alert for risk level: {ctx.risk_level}")		
        		
        await self.notification.send_guardian_alert(		
            user_id=ctx.user_id,		
            risk_level=ctx.risk_level,		
            analysis=ctx.analysis		
        )		
    		
    async def _handle_confounds(self, ctx: ProcessingContext) -> ProcessingContext:		
        """		
        Step 6: 교란 변수 처리 (조건부)		
        		
        점수 하락 시 수면/우울/약물 등 확인 질문 스케줄.		
        """		
        logger.info("Scheduling confound check question")		
        		
        confound_question = await self.dialogue.generate_confound_question(		
            user_id=ctx.user_id		
        )		
        		
        ctx.confound_question_scheduled = confound_question		
        return ctx		
    		
    async def _plan_next_interaction(self, ctx: ProcessingContext) -> ProcessingContext:		
        """		
        Step 7: 다음 상호작용 계획		
        		
        - 카테고리 선택 (weakest metric 우선)		
        - 난이도 조정 (risk_level 기반)		
        """		
        logger.debug("Planning next interaction")		
        		
        next_plan = await self.dialogue.plan_next(		
            user_id=ctx.user_id,		
            current_analysis=ctx.analysis,		
            risk_level=ctx.risk_level		
        )		
        		
        ctx.next_category = next_plan["category"]		
        ctx.next_difficulty = next_plan["difficulty"]		
        		
        return ctx		
    		
    async def _generate_response(self, ctx: ProcessingContext) -> ProcessingContext:		
        """		
        Step 8: 응답 생성		
        		
        - 공감 반응		
        - 다음 질문		
        - 정원 메타포 적용		
        """		
        logger.debug("Generating response")		
        		
        response = await self.dialogue.generate_response(		
            user_id=ctx.user_id,		
            context=ctx		
        )		
        		
        ctx.response = response		
        return ctx		
    		
    async def _store_memory(self, ctx: ProcessingContext) -> None:		
        """		
        Step 9: 메모리 저장		
        		
        - 사실 추출		
        - 4계층 병렬 저장		
        """		
        logger.debug("Storing memory")		
        		
        await self.memory.store_all(		
            user_id=ctx.user_id,		
            message=ctx.message,		
            response=ctx.response,		
            analysis=ctx.analysis		
        )		
    		
    async def _generate_fallback_response(self, ctx: ProcessingContext) -> str:		
        """에러 시 Fallback 응답"""		
        return (		
            "앗, 잠시 정원을 가꾸는데 문제가 생겼어요 ??\n"		
            "조금 후에 다시 이야기 나눠요!"		
        )		
		
AI에게 요청 시:		
"core/workflow/message_processor.py를 위 구조대로 작성해줘.
각 Step별로 상세한 로깅을 추가하고, 에러 발생 시에도 부분적으로 저장된 데이터는 유지되도록 해줘."		
		
3. core/analysis/analyzer.py		
"""
분석 총괄 클래스

6개 분석 지표를 통합 관리하고 MCDI 점수를 계산.
"""		
		
import asyncio		
from typing import Dict, Any, Optional		
from datetime import datetime		
		
from core.analysis.lexical_richness import LexicalRichnessAnalyzer		
from core.analysis.semantic_drift import SemanticDriftAnalyzer		
from core.analysis.narrative_coherence import NarrativeCoherenceAnalyzer		
from core.analysis.temporal_orientation import TemporalOrientationAnalyzer		
from core.analysis.episodic_recall import EpisodicRecallAnalyzer		
from core.analysis.response_time import ResponseTimeAnalyzer		
from core.analysis.mcdi_calculator import MCDICalculator		
from core.analysis.contradiction_detector import ContradictionDetector		
from utils.logger import get_logger		
from utils.exceptions import AnalysisError		
		
logger = get_logger(__name__)		
		
		
class Analyzer:		
    """분석 총괄 클래스		
    		
    6개 지표를 병렬로 실행하고 MCDI 종합 점수 계산.		
    개별 지표 실패 시에도 나머지는 계속 진행.		
    """		
    		
    def __init__(		
        self,		
        lr_analyzer: LexicalRichnessAnalyzer,		
        sd_analyzer: SemanticDriftAnalyzer,		
        nc_analyzer: NarrativeCoherenceAnalyzer,		
        to_analyzer: TemporalOrientationAnalyzer,		
        er_analyzer: EpisodicRecallAnalyzer,		
        rt_analyzer: ResponseTimeAnalyzer,		
        mcdi_calculator: MCDICalculator,		
        contradiction_detector: ContradictionDetector		
    ):		
        self.lr = lr_analyzer		
        self.sd = sd_analyzer		
        self.nc = nc_analyzer		
        self.to = to_analyzer		
        self.er = er_analyzer		
        self.rt = rt_analyzer		
        self.mcdi = mcdi_calculator		
        self.contradiction = contradiction_detector		
    		
    async def analyze(		
        self,		
        message: str,		
        memory: Dict[str, Any],		
        message_type: str = "text",		
        image_url: Optional[str] = None		
    ) -> Dict[str, Any]:		
        """		
        전체 분석 실행		
        		
        Args:		
            message: 사용자 메시지		
            memory: 검색된 메모리 데이터		
            message_type: text/image/selection		
            image_url: 이미지 URL (선택)		
        		
        Returns:		
            {		
                "scores": {"LR": 78.5, "SD": 82.3, ...},		
                "mcdi_score": 80.2,		
                "lr_detail": {...},		
                ...		
                "contradictions": [...]		
            }		
        		
        Raises:		
            AnalysisError: 모든 지표 실패 시		
        """		
        logger.info("Starting comprehensive analysis")		
        		
        if not message:		
            raise AnalysisError("Message cannot be empty")		
        		
        # 6개 지표 병렬 실행 (asyncio.gather)		
        results = await asyncio.gather(		
            self.lr.analyze(message),		
            self.sd.analyze(message, memory.get("question_context")),		
            self.nc.analyze(message),		
            self.to.analyze(message, memory.get("current_datetime")),		
            self.er.analyze(message, memory.get("episodic")),		
            self.rt.analyze(message, memory.get("response_latency")),		
            return_exceptions=True  # 일부 실패해도 계속 진행		
        )		
        		
        # 결과 언팩		
        lr_result, sd_result, nc_result, to_result, er_result, rt_result = results		
        		
        # 에러 핸들링 & 점수 집계		
        scores = {}		
        details = {}		
        failed_metrics = []		
        		
        for name, result in zip(		
            ["LR", "SD", "NC", "TO", "ER", "RT"],		
            results		
        ):		
            if isinstance(result, Exception):		
                logger.error(f"{name} analysis failed: {result}")		
                scores[name] = None		
                details[f"{name.lower()}_detail"] = {"error": str(result)}		
                failed_metrics.append(name)		
            else:		
                scores[name] = result["score"]		
                details[f"{name.lower()}_detail"] = result		
        		
        # 모든 지표 실패 시 에러		
        if len(failed_metrics) == 6:		
            raise AnalysisError("All analysis metrics failed")		
        		
        # MCDI 계산 (None 값 제외)		
        valid_scores = {k: v for k, v in scores.items() if v is not None}		
        mcdi_score = self.mcdi.calculate(valid_scores)		
        		
        # 모순 탐지 (비동기)		
        contradictions = await self.contradiction.detect(		
            user_id=memory.get("user_id"),		
            new_statement=message,		
            biographical_memory=memory.get("biographical")		
        )		
        		
        return {		
            "scores": scores,		
            "mcdi_score": mcdi_score,		
            **details,		
            "contradictions": contradictions,		
            "failed_metrics": failed_metrics,		
            "timestamp": datetime.now().isoformat()		
        }		
		
AI에게 요청 시:		
"core/analysis/analyzer.py를 위 구조대로 작성해줘.
만약 3개 이상 지표가 실패하면 MCDI 신뢰도를 낮게 표시하는 로직도 추가해줘."		
		
---

**4. core/analysis/mcdi_calculator.py**

"""
MCDI 종합 점수 계산기

6개 지표를 가중 평균하여 0-100 사이의 종합 점수 산출.
일부 지표 실패 시 자동으로 가중치 재정규화.
"""

from typing import Dict
from utils.logger import get_logger
from utils.exceptions import MCDICalculationError

logger = get_logger(__name__)

class MCDICalculator:
    """MCDI 종합 점수 계산
    
    Fraser et al. (2016) 기반 디지털 바이오마커 점수.
    6개 지표를 가중 평균하여 최종 인지 기능 점수 산출.
    """
    
    # ============================================
    # 가중치 (SPEC.md 2.1.2 참조)
    # ============================================
    WEIGHTS = {
        "LR": 0.20,  # Lexical Richness
        "SD": 0.20,  # Semantic Drift
        "NC": 0.15,  # Narrative Coherence
        "TO": 0.15,  # Temporal Orientation
        "ER": 0.20,  # Episodic Recall
        "RT": 0.10   # Response Time
    }
    
    # 최소 유효 지표 개수
    MIN_VALID_METRICS = 3
    
    def calculate(self, scores: Dict[str, float]) -> float:
        """
        6개 지표를 가중 평균하여 MCDI 계산
        
        Args:
            scores: {"LR": 78.5, "SD": 82.3, ...}
                    (None 값은 이미 제거된 상태)
        
        Returns:
            0-100 사이의 MCDI 점수
            
        Raises:
            MCDICalculationError: 유효 지표가 3개 미만일 때
            
        Example:
            >>> calculator = MCDICalculator()
            >>> scores = {"LR": 78.5, "SD": 82.3, "NC": 75.0, 
            ...           "TO": 80.0, "ER": 72.5, "RT": 70.0}
            >>> mcdi = calculator.calculate(scores)
            >>> print(mcdi)
            76.88
        """
        if not scores:
            raise MCDICalculationError("No valid scores provided")
        
        # 유효 지표 개수 확인
        if len(scores) < self.MIN_VALID_METRICS:
            raise MCDICalculationError(
                f"At least {self.MIN_VALID_METRICS} metrics required, "
                f"got {len(scores)}: {list(scores.keys())}"
            )
        
        # 유효한 지표만 가중치 추출
        valid_weights = {k: self.WEIGHTS[k] for k in scores.keys()}
        weight_sum = sum(valid_weights.values())
        
        # 가중치 재정규화 (합이 1.0이 되도록)
        normalized_weights = {
            k: v / weight_sum 
            for k, v in valid_weights.items()
        }
        
        # 가중 평균 계산
        mcdi = sum(
            scores[k] * normalized_weights[k] 
            for k in scores.keys()
        )
        
        # 신뢰도 계산 (6개 중 몇 개 사용했는가)
        reliability = len(scores) / len(self.WEIGHTS)
        
        logger.info(
            f"MCDI calculated: {mcdi:.2f}",
            extra={
                "used_metrics": list(scores.keys()),
                "reliability": f"{reliability:.2%}",
                "normalized_weights": normalized_weights
            }
        )
        
        return round(mcdi, 2)
    
    def calculate_with_confidence(
        self, 
        scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        MCDI 점수 + 신뢰도 함께 반환
        
        Returns:
            {
                "mcdi_score": 76.88,
                "reliability": 1.0,  # 6/6 지표 사용
                "used_metrics": ["LR", "SD", ...],
                "missing_metrics": []
            }
        """
        mcdi_score = self.calculate(scores)
        
        all_metrics = set(self.WEIGHTS.keys())
        used_metrics = set(scores.keys())
        missing_metrics = all_metrics - used_metrics
        
        return {
            "mcdi_score": mcdi_score,
            "reliability": len(used_metrics) / len(all_metrics),
            "used_metrics": sorted(used_metrics),
            "missing_metrics": sorted(missing_metrics)
        }


# ============================================
# 테스트 코드 예시
# ============================================
"""
# tests/test_core/test_mcdi_calculator.py

import pytest
from core.analysis.mcdi_calculator import MCDICalculator
from utils.exceptions import MCDICalculationError

@pytest.fixture
def calculator():
    return MCDICalculator()

def test_calculate_all_metrics(calculator):
    \"\"\"정상 케이스: 6개 지표 모두 있음\"\"\"
    scores = {
        "LR": 80.0,
        "SD": 85.0,
        "NC": 75.0,
        "TO": 82.0,
        "ER": 78.0,
        "RT": 70.0
    }
    
    mcdi = calculator.calculate(scores)
    
    # 가중 평균 검증
    expected = (
        80.0 * 0.20 +  # LR
        85.0 * 0.20 +  # SD
        75.0 * 0.15 +  # NC
        82.0 * 0.15 +  # TO
        78.0 * 0.20 +  # ER
        70.0 * 0.10    # RT
    )
    
    assert mcdi == pytest.approx(expected, rel=0.01)
    assert 0 <= mcdi <= 100

def test_calculate_partial_metrics(calculator):
    \"\"\"일부 지표만 있을 때 (3개)\"\"\"
    scores = {
        "LR": 80.0,
        "SD": 85.0,
        "NC": 75.0
    }
    
    # 가중치 재정규화 후 계산
    # 원래 합: 0.20 + 0.20 + 0.15 = 0.55
    # 정규화: LR=0.364, SD=0.364, NC=0.273
    
    mcdi = calculator.calculate(scores)
    expected = 80.0 * (0.20/0.55) + 85.0 * (0.20/0.55) + 75.0 * (0.15/0.55)
    
    assert mcdi == pytest.approx(expected, rel=0.01)

def test_calculate_insufficient_metrics(calculator):
    \"\"\"에러 케이스: 2개만 있음 (최소 3개 필요)\"\"\"
    scores = {"LR": 80.0, "SD": 85.0}
    
    with pytest.raises(MCDICalculationError, match="At least 3 metrics"):
        calculator.calculate(scores)

def test_calculate_empty_scores(calculator):
    \"\"\"엣지 케이스: 빈 딕셔너리\"\"\"
    with pytest.raises(MCDICalculationError, match="No valid scores"):
        calculator.calculate({})

def test_calculate_with_confidence(calculator):
    \"\"\"신뢰도 포함 반환\"\"\"
    scores = {"LR": 80.0, "SD": 85.0, "NC": 75.0, "TO": 82.0}
    
    result = calculator.calculate_with_confidence(scores)
    
    assert "mcdi_score" in result
    assert result["reliability"] == 4 / 6  # 4개 / 6개
    assert len(result["used_metrics"]) == 4
    assert len(result["missing_metrics"]) == 2
"""

**AI에게 요청 시:**
"core/analysis/mcdi_calculator.py를 위 구조대로 작성해줘.
테스트 코드도 함께 생성해줘."

		
4. 프롬프트 템플릿		
		
?? 기본 파일 생성 프롬프트		
다음 구조로 {파일 경로} 파일을 생성해주세요:		
		
【Context】		
 - 프로젝트: memory Garden (치매 조기 감지 서비스)		
- 역할: {파일의 역할 설명}		
- 목적: {구체적인 목적}		
		
【Requirements】		
1. {기능 요구사항 1}		
2. {기능 요구사항 2}		
3. {기능 요구사항 3}		
		
【Dependencies】		
- {사용할 라이브러리 1}		
- {사용할 라이브러리 2}		
		
【Coding Convention】		
 - docs/CODING_CONVENTION.md 준수		
 - 모든 함수에 타입 힌팅 및 docstring (Google Style)		
- 에러 처리 (try-except)		
- 로깅 추가 (logger.info/error)		
		
【Reference Files】		
- {참고할 기존 파일 1}		
- {참고할 기존 파일 2}		
		
【Expected Structure】		
```python		
# 원하는 골격 코드		
		
### ?? 개별 지표 구현 프롬프트 (예: LR)		
		
다음 구조로 core/analysis/lexical_richness.py 파일을 생성해주세요:		
		
【Context】		
		
프로젝트: Memory Garden		
역할: 어휘 풍부도(LR) 지표 계산		
목적: 사용자 응답의 어휘 다양성 분석으로 인지 저하 감지		
		
【Scientific Basis】 Fraser et al. (2016) 논문 기반:		
		
대명사 대체율 증가 = 인지 저하 신호		
Type-Token Ratio (TTR) 감소 = 어휘 빈약		
빈 발화("그거", "뭐더라") 증가 = 단어 인출 장애		
		
【Requirements】		
		
1. 입력:		
message: str (사용자 응답)		
baseline_stats: Optional[Dict] (개인 baseline)		
2. 출력:		
LexicalRichnessResult (Pydantic 모델)		
score: float (0-100)		
components: Dict (세부 지표들)		
z_score: float (baseline 대비)		
3. 측정 지표:		
pronoun_ratio: 대명사 / (대명사 + 명사)		
mattr: Moving Average TTR (window=20)		
concreteness: 구체 명사 / 전체 명사		
empty_speech_ratio: 빈 발화 / 전체 어절		
		
【Dependencies】		
		
Kiwi: 한국어 형태소 분석		
numpy: 통계 계산		
		
【Coding Convention】		
		
docs/CODING_CONVENTION.md 준수		
async 함수로 구현		
상세한 Docstring		
주석으로 수식 명시 예: # Formula: TTR = unique_tokens / total_tokens		
		
【Expected Output Example】		
{		
    "score": 78.5,		
    "components": {		
        "pronoun_ratio": 0.15,		
        "mattr": 0.72,		
        "concreteness": 0.85,		
        "empty_speech_ratio": 0.05		
    },		
    "z_score": -0.5,		
    "details": {		
        "total_tokens": 42,		
        "unique_tokens": 30,		
        "pronouns": ["그거", "저거"],		
        "concrete_nouns": ["쑥", "뒷산", "엄마", "쑥떡"]		
    }		
}		
		
【Test Requirements】 다음 테스트 케이스도 함께 작성:		
		
1. 정상 응답 (구체 명사 많음)		
2. 비정상 응답 (대명사 과다)		
3. 빈 입력 (ValueError)		
### ?? API 라우트 생성 프롬프트		
다음 구조로 api/routes/{리소스명}.py 파일을 생성해주세요:		
		
【Context】		
		
프로젝트: Memory Garden		
역할: {리소스} REST API 엔드포인트		
목적: {리소스} CRUD 및 조회		
		
【Endpoints】		
		
1. POST /{리소스}: 생성		
2. GET /{리소스}/{id}: 단건 조회		
3. GET /{리소스}: 리스트 조회 (페이지네이션)		
4. PUT /{리소스}/{id}: 수정		
5. DELETE /{리소스}/{id}: 삭제		
		
【Requirements】		
		
1. Pydantic 스키마:		
api/schemas/{리소스}.py 참조		
{리소스}Create, {리소스}Update, {리소스}Response		
2. 의존성:		
database/postgres.py의 get_db		
api/dependencies.py의 get_current_user (인증 필요 시)		
3. 에러 처리:		
404: HTTPException (리소스 없음)		
400: HTTPException (잘못된 요청)		
500: 로깅 후 일반 에러 메시지		
		
【Coding Convention】		
		
docs/CODING_CONVENTION.md 준수		
모든 엔드포인트에 Docstring		
OpenAPI tags 및 summary 추가		
페이지네이션: skip, limit 파라미터		
		
【Example Structure】		
from fastapi import APIRouter, Depends, HTTPException, Query		
from sqlalchemy.orm import Session		
from typing import List		
		
router = APIRouter(prefix="/{리소스}", tags=["{리소스}"])		
		
@router.post("/", response_model={리소스}Response, status_code=201)		
async def create_{리소스}(		
    {리소스}_data: {리소스}Create,		
    db: Session = Depends(get_db)		
):		
    """		
    {리소스} 생성		
    		
    - **field1**: 설명		
    - **field2**: 설명		
    """		
    ...		
		
@router.get("/{id}", response_model={리소스}Response)		
async def get_{리소스}(		
    id: int,		
    db: Session = Depends(get_db)		
):		
    """단건 조회"""		
    obj = db.query({리소스}).filter({리소스}.id == id).first()		
    if not obj:		
        raise HTTPException(status_code=404, detail="{리소스} not found")		
    return obj		
		
@router.get("/", response_model=List[{리소스}Response])		
async def list_{리소스}s(		
    skip: int = Query(0, ge=0),		
    limit: int = Query(20, ge=1, le=100),		
    db: Session = Depends(get_db)		
):		
    """리스트 조회 (페이지네이션)"""		
    objects = db.query({리소스}).offset(skip).limit(limit).all()		
    return objects		
		
### ?? 테스트 코드 생성 프롬프트		
다음 구조로 tests/test_{모듈}/test_{파일명}.py 테스트 파일을 생성해주세요:		
		
【Context】		
		
프로젝트: Memory Garden		
대상: {파일 경로}		
목적: {대상 파일} 단위 테스트		
		
【Test Coverage】		
		
1. 정상 케이스 (happy path)		
2. 에러 케이스 (exceptions)		
3. 엣지 케이스 (empty input, None, boundary values)		
4. Mock 사용 (외부 의존성)		
		
【Requirements】		
		
1. pytest 사용		
2. pytest-asyncio for async tests		
3. unittest.mock for mocking		
4. Fixtures:		
conftest.py에 공통 fixture		
테스트별 로컬 fixture		
		
【Coding Convention】		
		
AAA 패턴: Arrange, Act, Assert		
테스트 함수명: test_{함수명}_{시나리오}		
Docstring: 테스트 목적 명시		
		
【Example Structure】		
import pytest		
from unittest.mock import AsyncMock, patch		
		
@pytest.fixture		
def sample_data():		
    """테스트용 샘플 데이터"""		
    return {"user_id": "test_user", "message": "안녕하세요"}		
		
@pytest.mark.asyncio		
async def test_{함수명}_success(sample_data):		
    """정상 케이스: {설명}"""		
    # Arrange		
    expected = ...		
    		
    # Act		
    result = await {함수명}(sample_data)		
    		
    # Assert		
    assert result == expected		
		
@pytest.mark.asyncio		
async def test_{함수명}_with_empty_input():		
    """엣지 케이스: 빈 입력"""		
    # Act & Assert		
    with pytest.raises(ValueError, match="cannot be empty"):		
        await {함수명}("")		
		
@pytest.mark.asyncio		
@patch('services.llm_service.LLMService.call')		
async def test_{함수명}_with_llm_failure(mock_llm):		
    """에러 케이스: LLM 실패"""		
    # Arrange		
    mock_llm.side_effect = Exception("API Error")		
    		
    # Act & Assert		
    with pytest.raises(AnalysisError):		
        await {함수명}("test")		
		
【Test Scenarios】 다음 시나리오들을 커버해주세요:		
		
1. {시나리오 1}		
2. {시나리오 2}		
3. {시나리오 3}		
---		
		
## 5. 디버깅 가이드		
		
### ?? 일반적인 문제 해결		
		
```python		
# 문제 1: "AttributeError: 'NoneType' object has no attribute ..."		
# 원인: Optional 값을 체크 안 함		
# 해결:		
		
# ? 나쁜 코드		
result = ctx.memory["episodic"][0]["content"]		
		
# ? 좋은 코드		
if ctx.memory and "episodic" in ctx.memory and ctx.memory["episodic"]:		
    result = ctx.memory["episodic"][0]["content"]		
else:		
    result = None		
		
# 또는		
result = ctx.memory.get("episodic", [{}])[0].get("content")		
		
# 문제 2: "RuntimeError: This event loop is already running"		
# 원인: 중첩된 asyncio.run() 호출		
# 해결:		
		
# ? 나쁜 코드 (Jupyter/async 환경에서)		
import asyncio		
result = asyncio.run(my_async_function())		
		
# ? 좋은 코드		
result = await my_async_function()		
		
# 또는 (동기 환경에서)		
import asyncio		
result = asyncio.get_event_loop().run_until_complete(my_async_function())		
		
# 문제 3: Vector DB 검색 결과 없음		
# 원인: 임베딩 차원 불일치 또는 필터 오류		
# 디버깅:		
		
# 1. 임베딩 차원 확인		
embedding = await embedder.embed("test")		
print(f"Embedding dimension: {len(embedding)}")  # 1536이어야 함		
		
# 2. 필터 조건 확인		
logger.debug(f"Filter: {filter}")		
		
# 3. 필터 없이 검색 테스트		
results = await qdrant_client.search(		
    collection_name="episodic_memory",		
    query_vector=embedding,		
    limit=5		
    # query_filter 제거하고 테스트		
)		
		
?? 로깅 활용		
# 디버깅용 상세 로깅		
		
import logging		
from utils.logger import get_logger		
		
logger = get_logger(__name__)		
		
# 개발 중에는 DEBUG 레벨로 설정		
logger.setLevel(logging.DEBUG)		
		
async def problematic_function(data):		
    logger.debug(f"Input data: {data}")  # 입력 확인		
    		
    result = await some_operation(data)		
    logger.debug(f"Intermediate result: {result}")  # 중간 결과 확인		
    		
    processed = process(result)		
    logger.debug(f"Final output: {processed}")  # 최종 출력 확인		
    		
    return processed		
		
?? 디버깅 테스트		
# pytest로 특정 테스트만 실행		
		
# 1. 파일 전체		
pytest tests/test_core/test_analysis.py -v		
		
# 2. 특정 테스트만		
pytest tests/test_core/test_analysis.py::test_analyze_normal_response -v		
		
# 3. 디버깅 출력 포함		
pytest tests/test_core/test_analysis.py -v -s		
		
# 4. breakpoint() 사용		
def test_example():		
    data = prepare_data()		
    breakpoint()  # 여기서 멈춤, pdb 쉘 진입		
    result = process(data)		
    assert result == expected		
		
6. AI 도구 활용 팁		
		
?? Cursor AI 최적 사용법		
1. .cursorrules 파일 생성		
   → 프로젝트 루트에 코딩 컨벤션 전체 복사		
		
2. Cmd+K (파일 생성)		
   "core/analysis/lexical_richness.py를 생성해줘.		
    .cursorrules의 컨벤션을 따라서."		
		
3. Cmd+L (대화형 수정)		
   "이 함수에 에러 처리를 추가해줘"		
		
4. @파일명 (컨텍스트 참조)		
   "@core/workflow/context.py 참고해서		
    비슷한 구조로 result.py 만들어줘"		
		
5. 멀티 파일 편집		
   여러 파일 선택 후 Cmd+K		
   "이 파일들의 import 순서를 정리해줘"		
		
?? GitHub Copilot 최적 사용법		
# 1. 주석으로 로직 설명 → Tab으로 자동완성		
		
# 형태소 분석 후 명사와 대명사 추출		
# 대명사 비율 = 대명사 수 / (대명사 + 명사) 수		
# → Copilot이 자동으로 코드 생성		
		
# 2. 함수 시그니처 + Docstring → Tab		
		
async def calculate_pronoun_ratio(tokens: List[str]) -> float:		
    """		
    대명사 비율 계산		
    		
    Args:		
        tokens: 형태소 분석 결과		
    		
    Returns:		
        0.0~1.0 사이의 비율		
    """		
    # → Copilot이 구현 제안		
		
# 3. 테스트 케이스 자동 생성		
		
def test_calculate_pronoun_ratio():		
    # → 함수명 쓰면 Copilot이 테스트 코드 제안		
		
?? Claude Code (Artifacts) 최적 사용법		
【고수준 설계 먼저 요청】		
		
"core/analysis/lexical_richness.py의 알고리즘을 
pseudo-code로 먼저 설계해줘.

그 다음 Python 코드로 구현해줘."		
		
→ Claude가 2단계로 작업		
  1) 알고리즘 설계 (검토 가능)		
  2) 코드 구현		
		
【복잡한 로직은 Claude에게】		
		
"다음 논문의 수식을 Python 코드로 변환해줘:
MATTR = (1/N-W+1) * Σ(TTR_i)
..."		
		
→ Claude가 수식 해석 + 구현		
		
【Cursor에 복사】		
		
Claude가 작성한 코드를 Cursor에 복사하여		
프로젝트에 통합		
		
		
		
7. 체크리스트		
		
? 파일 작성 완료 체크리스트		
코드 작성 후 스스로 체크:		
		
□ 타입 힌팅 모든 함수에 추가했는가?		
□ Docstring 작성했는가? (Google Style)		
□ 에러 처리 (try-except) 추가했는가?		
□ 로깅 추가했는가? (logger.info/error)		
□ 변수명이 의미 명확한가? (is_, has_ 접두사)		
□ 주석으로 복잡한 로직 설명했는가?		
□ import 순서가 올바른가? (표준-써드파티-로컬)		
□ 테스트 코드 작성했는가?		
□ docs/CODING_CONVENTION.md 준수했는가?		
		
? PR 제출 전 체크리스트		
# 1. 코드 포맷팅		
black .		
isort .		
		
# 2. 린팅		
flake8 .		
mypy .		
		
# 3. 테스트		
pytest --cov=. --cov-report=term-missing		
		
# 4. 커버리지 확인 (80% 이상)		
# 5. 충돌 해결		
git pull origin develop		
git merge develop		
		
# 6. PR 템플릿 작성		
		
		
		
8. 자주 묻는 질문 (FAQ)		
		
Q1: LangGraph를 왜 안 쓰나요?		
A: 현재 워크플로우는 조건부 분기가 2개뿐입니다.		
   (1) ORANGE/RED 레벨 → 알림		
   (2) 점수 하락 → 교란변수 체크		
   		
   이 정도는 if문으로 충분하며, LangGraph는 오버킬입니다.		
   		
   장점:		
   - 러닝 커브 제거		
   - 디버깅 용이		
   - 성능 향상		
   - 코드 가독성		
   		
   향후 복잡한 멀티 에이전트가 필요하면 그때 도입 검토.		
		
Q2: ProcessingContext vs LangGraph State 차이?		
# LangGraph State (TypedDict)		
class State(TypedDict):		
    user_id: str		
    message: str		
    ...		
		
# ProcessingContext (dataclass)		
@dataclass		
class ProcessingContext:		
    user_id: str		
    message: str		
    ...		
		
차이점:		
1. ProcessingContext는 메서드 추가 가능 (to_dict() 등)		
2. 타입 체킹 더 엄격 (mypy)		
3. IDE 자동완성 우수		
4. LangGraph 의존성 없음		
		
Q3: 비동기 함수는 언제 쓰나요?		
# ? async 사용:		
# - DB 쿼리		
# - API 호출 (LLM, Kakao 등)		
# - Redis 작업		
# - 파일 I/O (aiofiles)		
		
async def fetch_user(user_id: str) -> User:		
    async with db.session() as session:		
        return await session.get(User, user_id)		
		
# ? async 불필요:		
# - 순수 계산 (numpy, sklearn)		
# - 문자열 처리		
# - 형태소 분석 (Kiwi는 동기)		
		
def calculate_ratio(a: int, b: int) -> float:		
    return a / b  # async 불필요		
		
Q4: 테스트는 몇 % 커버리지가 목표인가요?		
A: 최소 80% 권장		
		
커버리지 체크:		
pytest --cov=. --cov-report=html		
open htmlcov/index.html		
		
우선 순위:		
1. 핵심 로직 (analyzer, risk_evaluator): 90%+		
2. 워크플로우 (message_processor): 85%+		
3. 유틸리티 (logger, validators): 80%+		
4. API 라우트: 75%+		
		
		
		
9. 마무리		
		
?? 개발 시 핵심 원칙		
1. KISS (Keep It Simple, Stupid)		
   → 복잡한 것보다 단순하고 명확한 코드		
		
2. YAGNI (You Aren't Gonna Need It)		
   → 필요하지 않을 기능은 만들지 마세요		
		
3. DRY (Don't Repeat Yourself)		
   → 중복 코드는 함수/클래스로 추상화		
		
4. Fail Fast		
   → 에러는 최대한 빨리 감지하고 명확히 표시		
		
5. Test First (가능하면)		
   → 테스트를 먼저 작성하면 설계가 명확해집니다		
		
?? 추가 학습 자료		
1. FastAPI 공식 문서		
   https://fastapi.tiangolo.com/		
		
2. Pydantic v2 문서		
   https://docs.pydantic.dev/latest/		
		
3. SQLAlchemy 2.0 문서		
   https://docs.sqlalchemy.org/en/20/		
		
4. Qdrant 문서		
   https://qdrant.tech/documentation/		
		
5. pytest 문서		
   https://docs.pytest.org/		

