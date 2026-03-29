# Redis 사용 가이드

Memory Garden 프로젝트의 Redis 클라이언트 사용 가이드입니다.

---

## 📋 목차

1. [Redis 역할](#1-redis-역할)
2. [환경 설정](#2-환경-설정)
3. [기본 사용법](#3-기본-사용법)
4. [고급 기능](#4-고급-기능)
5. [실전 예제](#5-실전-예제)
6. [성능 최적화](#6-성능-최적화)
7. [문제 해결](#7-문제-해결)

---

## 1. Redis 역할

Memory Garden에서 Redis는 **Layer 1 (Session Memory)** 역할을 합니다.

### 사용 용도

| 용도 | TTL | 설명 |
|------|-----|------|
| **세션 저장** | 24시간 | 사용자 세션 데이터 (마지막 메시지, 턴 수 등) |
| **대화 컨텍스트** | 1시간 | 현재 대화 컨텍스트 (최근 10턴, 현재 카테고리) |
| **일반 캐싱** | 30분 | API 응답, 분석 결과 등 캐싱 |

### 메모리 계층 구조

```
Layer 1: Redis (Session Memory)
  └─ TTL: 24시간
  └─ 용도: 현재 대화 세션

Layer 2: Qdrant (Episodic Memory)
  └─ 영구 저장
  └─ 용도: 일화 기억

Layer 3: Qdrant + PostgreSQL (Biographical Memory)
  └─ 영구 저장
  └─ 용도: 불변/반불변 사실

Layer 4: TimescaleDB (Analytical Memory)
  └─ 영구 저장
  └─ 용도: MCDI 점수 시계열
```

---

## 2. 환경 설정

### 2.1 Redis 서버 실행

```bash
# Docker Compose 사용 (권장)
docker-compose up -d redis

# 로그 확인
docker-compose logs -f redis

# 상태 확인
docker-compose ps
```

### 2.2 환경 변수 설정

```bash
# .env 파일
REDIS_URL=redis://localhost:6379/0
```

**형식:**
```
redis://[비밀번호@]호스트:포트/DB번호
```

**예시:**
```bash
# 비밀번호 없음
REDIS_URL=redis://localhost:6379/0

# 비밀번호 있음
REDIS_URL=redis://:mypassword@localhost:6379/0

# 원격 서버
REDIS_URL=redis://:password@redis.example.com:6379/1
```

### 2.3 연결 테스트

```bash
python scripts/test_redis_connection.py

# 예상 출력:
# ✅ Redis connection successful!
# ✅ All tests passed!
```

---

## 3. 기본 사용법

### 3.1 클라이언트 가져오기

```python
from database.redis_client import redis_client

# Singleton 인스턴스 (전역)
client = redis_client
```

### 3.2 기본 연산

#### GET / SET / DELETE

```python
# SET (TTL 포함)
await redis_client.set("user:123", "John Doe", ttl=3600)

# GET
value = await redis_client.get("user:123")
print(value)  # "John Doe"

# DELETE
deleted = await redis_client.delete("user:123")
print(deleted)  # 1

# 여러 키 삭제
deleted = await redis_client.delete("key1", "key2", "key3")
```

#### EXISTS / EXPIRE / TTL

```python
# EXISTS (키 존재 확인)
exists = await redis_client.exists("user:123", "user:456")
print(exists)  # 2 (두 개 모두 존재)

# EXPIRE (TTL 설정)
await redis_client.expire("user:123", 7200)  # 2시간

# TTL (남은 시간 확인)
remaining = await redis_client.ttl("user:123")
print(f"Remaining: {remaining}s")  # 7200
```

### 3.3 JSON 직렬화

```python
# JSON 저장
user_data = {
    "name": "John Doe",
    "age": 30,
    "tags": ["python", "redis"]
}
await redis_client.set_json("user:123:profile", user_data, ttl=3600)

# JSON 조회
profile = await redis_client.get_json("user:123:profile")
print(profile["name"])  # "John Doe"
```

---

## 4. 고급 기능

### 4.1 세션 관리

```python
from database.redis_client import redis_client

# 세션 저장
session_data = {
    "last_message": "안녕하세요",
    "turn": 5,
    "category": "reminiscence",
    "timestamp": "2025-01-15T10:00:00Z"
}
await redis_client.set_session("user_123", session_data)

# 세션 조회
session = await redis_client.get_session("user_123")
print(session["turn"])  # 5

# 세션 삭제
await redis_client.delete_session("user_123")
```

**저장 위치:** `session:user_123`
**기본 TTL:** 24시간

### 4.2 대화 컨텍스트 관리

```python
# 컨텍스트 저장
context_data = {
    "recent_turns": [
        {"role": "user", "message": "안녕하세요"},
        {"role": "bot", "message": "반가워요!"}
    ],
    "current_category": "daily_episodic",
    "next_question": "오늘 점심 뭐 드셨어요?"
}
await redis_client.set_context("user_123", context_data)

# 컨텍스트 조회
context = await redis_client.get_context("user_123")
print(len(context["recent_turns"]))  # 2

# 컨텍스트 삭제
await redis_client.delete_context("user_123")
```

**저장 위치:** `context:user_123`
**기본 TTL:** 1시간

### 4.3 일반 캐싱

```python
# 문자열 캐싱
await redis_client.set_cache("baseline:user_123", "78.5", ttl=1800)
baseline = await redis_client.get_cache("baseline:user_123")

# 딕셔너리 캐싱
await redis_client.set_cache(
    "analysis:user_123",
    {"mcdi_score": 78.5, "risk_level": "GREEN"},
    ttl=1800
)
analysis = await redis_client.get_cache("analysis:user_123")
print(analysis["mcdi_score"])  # 78.5
```

**저장 위치:** `cache:{cache_key}`
**기본 TTL:** 30분

---

## 5. 실전 예제

### 5.1 FastAPI 엔드포인트에서 사용

```python
from fastapi import APIRouter, Depends
from database.redis_client import redis_client, get_redis
from redis.asyncio import Redis

router = APIRouter()

# 방법 1: 전역 클라이언트 사용
@router.get("/session/{user_id}")
async def get_user_session(user_id: str):
    session = await redis_client.get_session(user_id)
    if not session:
        return {"error": "Session not found"}
    return session

# 방법 2: Dependency Injection
@router.post("/cache/{key}")
async def set_cache_value(
    key: str,
    value: str,
    redis: Redis = Depends(get_redis)
):
    await redis.set(f"cache:{key}", value, ex=1800)
    return {"status": "cached"}
```

### 5.2 MessageProcessor에서 세션 활용

```python
# core/workflow/message_processor.py

from database.redis_client import redis_client
from datetime import datetime

class MessageProcessor:
    async def process(self, user_id: str, message: str) -> str:
        # 1. 세션 조회
        session = await redis_client.get_session(user_id)

        if not session:
            # 새 세션 생성
            session = {
                "turn": 0,
                "started_at": datetime.now().isoformat(),
                "last_category": None
            }

        # 2. 턴 수 증가
        session["turn"] += 1
        session["last_message"] = message
        session["last_updated"] = datetime.now().isoformat()

        # 3. 대화 처리 로직
        # ...

        # 4. 세션 저장
        await redis_client.set_session(user_id, session)

        return response
```

### 5.3 대화 컨텍스트 유지 (최근 10턴)

```python
from typing import List, Dict

async def update_context(user_id: str, new_turn: Dict):
    """최근 10턴 대화 유지"""

    # 기존 컨텍스트 조회
    context = await redis_client.get_context(user_id)

    if not context:
        context = {
            "recent_turns": [],
            "current_category": None
        }

    # 새 턴 추가
    context["recent_turns"].append(new_turn)

    # 최근 10턴만 유지
    if len(context["recent_turns"]) > 10:
        context["recent_turns"] = context["recent_turns"][-10:]

    # 저장
    await redis_client.set_context(user_id, context)
```

### 5.4 분석 결과 캐싱

```python
from core.analysis.analyzer import Analyzer

class CachedAnalyzer:
    def __init__(self, analyzer: Analyzer):
        self.analyzer = analyzer

    async def analyze_with_cache(self, user_id: str, message: str):
        """분석 결과 캐싱 (30분)"""

        # 캐시 키 생성 (메시지 해시)
        import hashlib
        message_hash = hashlib.md5(message.encode()).hexdigest()
        cache_key = f"analysis:{user_id}:{message_hash}"

        # 캐시 확인
        cached = await redis_client.get_cache(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return cached

        # 캐시 미스 - 실제 분석
        result = await self.analyzer.analyze(message, {})

        # 결과 캐싱
        await redis_client.set_cache(cache_key, result, ttl=1800)

        return result
```

---

## 6. 성능 최적화

### 6.1 연결 풀 설정

```python
# database/redis_client.py에서 설정됨

ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,  # 최대 연결 수
    socket_timeout=5.0,
    socket_connect_timeout=5.0,
    retry_on_timeout=True
)
```

### 6.2 파이프라인 (Pipeline)

여러 명령을 한 번에 실행:

```python
redis_conn = await redis_client.get_client()

# 파이프라인 사용
async with redis_conn.pipeline() as pipe:
    pipe.set("key1", "value1", ex=60)
    pipe.set("key2", "value2", ex=60)
    pipe.set("key3", "value3", ex=60)
    results = await pipe.execute()

print(results)  # [True, True, True]
```

### 6.3 배치 삭제

```python
# 여러 키를 한 번에 삭제
keys_to_delete = [f"temp:{i}" for i in range(100)]
deleted = await redis_client.delete(*keys_to_delete)
print(f"Deleted {deleted} keys")
```

### 6.4 TTL 전략

| 데이터 유형 | TTL | 이유 |
|------------|-----|------|
| 세션 | 24시간 | 하루 동안 활성 유지 |
| 대화 컨텍스트 | 1시간 | 실시간 대화용 |
| 분석 결과 | 30분 | 동일 메시지 반복 방지 |
| Baseline | 7일 | 자주 변하지 않음 |

---

## 7. 문제 해결

### Q1. "Connection refused" 에러

**원인:** Redis 서버가 실행 중이 아님

**해결:**
```bash
# Docker 사용 시
docker-compose up -d redis
docker-compose logs redis

# 로컬 Redis 사용 시
redis-server
# 또는
sudo systemctl start redis
```

### Q2. "WRONGTYPE" 에러

**원인:** 키에 다른 타입의 데이터가 저장되어 있음

**해결:**
```python
# 키 삭제 후 재저장
await redis_client.delete("problematic_key")
await redis_client.set("problematic_key", "new_value")
```

### Q3. 메모리 부족

**원인:** TTL이 설정되지 않아 메모리 누적

**해결:**
```bash
# Redis CLI에서 확인
redis-cli
> INFO memory
> DBSIZE

# TTL 없는 키 찾기
> KEYS *
> TTL key_name  # -1이면 영구 저장

# Python에서 TTL 설정
await redis_client.expire("key_name", 3600)
```

### Q4. 성능 저하

**원인:** 큰 데이터를 자주 조회

**해결:**
```python
# 데이터 크기 확인
redis_conn = await redis_client.get_client()
size = await redis_conn.memory_usage("large_key")
print(f"Key size: {size} bytes")

# 큰 데이터는 압축하거나 PostgreSQL로 이동
# 또는 Hash 자료구조 사용
await redis_conn.hset("user:123", mapping={
    "name": "John",
    "age": "30"
})
```

---

## 🔧 디버깅 팁

### Redis CLI로 직접 확인

```bash
# Redis CLI 접속
redis-cli

# 모든 키 조회 (주의: 운영 환경에서는 사용 금지)
KEYS *

# 특정 패턴 키 조회
KEYS session:*
KEYS context:*

# 키 값 확인
GET session:user_123

# 키 TTL 확인
TTL session:user_123

# 키 삭제
DEL session:user_123

# 전체 DB 삭제 (주의!)
FLUSHDB
```

### Python에서 디버깅

```python
# 모든 세션 키 조회
redis_conn = await redis_client.get_client()
session_keys = await redis_conn.keys("session:*")
print(f"Active sessions: {len(session_keys)}")

# 각 세션 TTL 확인
for key in session_keys:
    ttl = await redis_conn.ttl(key)
    print(f"{key}: {ttl}s remaining")
```

---

## ✅ 체크리스트

Redis 설정 완료 후 확인:

- [ ] Redis 서버 실행 중
- [ ] `.env`에 REDIS_URL 설정
- [ ] `python scripts/test_redis_connection.py` 성공
- [ ] 세션 저장/조회 테스트 완료
- [ ] 대화 컨텍스트 저장/조회 테스트 완료
- [ ] 캐싱 동작 확인
- [ ] FastAPI 엔드포인트에서 사용 가능

---

## 📚 추가 자료

- [Redis 공식 문서](https://redis.io/docs/)
- [redis-py 문서](https://redis-py.readthedocs.io/)
- [Redis 모범 사례](https://redis.io/docs/manual/patterns/)

---

**작성일:** 2025-01-15
**작성자:** Memory Garden Team
