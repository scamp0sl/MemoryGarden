# 데이터베이스 설정 가이드

Memory Garden 프로젝트의 PostgreSQL 데이터베이스 설정 및 마이그레이션 가이드입니다.

---

## 📋 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [환경 변수 설정](#2-환경-변수-설정)
3. [데이터베이스 생성](#3-데이터베이스-생성)
4. [마이그레이션 실행](#4-마이그레이션-실행)
5. [테스트](#5-테스트)
6. [자주 묻는 질문](#6-자주-묻는-질문)

---

## 1. 사전 요구사항

### 필수 소프트웨어

- **PostgreSQL** 14+ (권장: 15+)
- **Python** 3.11+
- **Docker** (선택, PostgreSQL 컨테이너 사용 시)

### Python 패키지

```bash
# 가상환경 활성화
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

주요 패키지:
- `sqlalchemy[asyncio]` - ORM (비동기 지원)
- `asyncpg` - PostgreSQL 비동기 드라이버
- `psycopg2-binary` - PostgreSQL 동기 드라이버 (Alembic용)
- `alembic` - 마이그레이션 도구

---

## 2. 환경 변수 설정

### .env 파일 생성

```bash
# .env.example 복사
cp .env.example .env

# .env 파일 편집
nano .env  # 또는 vim, code 등
```

### DATABASE_URL 설정

```bash
# .env 파일 내용
DATABASE_URL=postgresql://memgarden:password@localhost:5432/memory_garden
```

**형식:**
```
postgresql://[사용자명]:[비밀번호]@[호스트]:[포트]/[데이터베이스명]
```

**주의:**
- FastAPI 앱에서는 자동으로 `postgresql+asyncpg://`로 변환됩니다.
- Alembic 마이그레이션은 `postgresql://` (psycopg2) 사용합니다.

---

## 3. 데이터베이스 생성

### Docker Compose 사용 (권장)

```bash
# PostgreSQL 컨테이너 시작
docker-compose up -d postgres

# 로그 확인
docker-compose logs -f postgres

# 컨테이너 상태 확인
docker-compose ps
```

### 수동 생성 (Docker 미사용 시)

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE memory_garden;
CREATE USER memgarden WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE memory_garden TO memgarden;

# 확인 후 종료
\l
\q
```

### TimescaleDB 확장 설치 (선택)

분석 점수 시계열 데이터 최적화를 위해 TimescaleDB 사용:

```sql
-- PostgreSQL에 접속
psql -U memgarden -d memory_garden

-- TimescaleDB 확장 설치
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Hypertable 변환 (마이그레이션 후 수동 실행)
SELECT create_hypertable('analysis_timeseries', 'timestamp');
```

---

## 4. 마이그레이션 실행

### 4.1 현재 상태 확인

```bash
# 현재 마이그레이션 상태
alembic current

# 마이그레이션 히스토리
alembic history --verbose
```

### 4.2 마이그레이션 적용

```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 예상 출력:
# INFO [alembic.runtime.migration] Running upgrade -> 8b1eea533361, Initial migration - create all tables
```

### 4.3 롤백 (필요 시)

```bash
# 1단계 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade 8b1eea533361

# 전체 롤백 (주의!)
alembic downgrade base
```

### 4.4 새 마이그레이션 생성

모델 변경 후 자동 마이그레이션 생성:

```bash
# models/__init__.py 수정 후
alembic revision --autogenerate -m "Add new column to users"

# 생성된 파일 확인
ls -lh alembic/versions/

# 마이그레이션 적용
alembic upgrade head
```

---

## 5. 테스트

### 5.1 연결 테스트 스크립트

```bash
# 데이터베이스 연결 테스트
python scripts/test_db_connection.py

# 예상 출력:
# ============================================================
# 🔍 Database Connection Test
# ============================================================
#
# 1️⃣ Testing database connection...
# ✅ Database connection successful!
#
# 2️⃣ Testing table access...
# ✅ Found 9 tables:
#    - analysis_results
#    - analysis_timeseries
#    - conversations
#    - garden_status
#    - guardians
#    - memory_events
#    - notifications
#    - user_guardians
#    - users
#
# 3️⃣ Testing SQLAlchemy models...
# ✅ User model: users
# ✅ Conversation model: conversations
# ✅ AnalysisResult model: analysis_results
# ============================================================
# ✅ All tests passed!
# ============================================================
```

### 5.2 수동 테스트 (psql)

```bash
# PostgreSQL 접속
psql -U memgarden -d memory_garden

# 테이블 확인
\dt

# 테이블 구조 확인
\d users
\d conversations
\d analysis_results

# 샘플 데이터 삽입 테스트
INSERT INTO users (id, kakao_id, name)
VALUES (gen_random_uuid(), 'test_kakao_123', 'Test User');

# 조회
SELECT * FROM users;

# 삭제
TRUNCATE users CASCADE;
```

### 5.3 FastAPI 서버 테스트

```bash
# 개발 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 브라우저에서 확인
# http://localhost:8000/docs  (Swagger UI)
# http://localhost:8000/health  (Health Check)
```

---

## 6. 자주 묻는 질문

### Q1. "FATAL: password authentication failed" 에러

**원인:** DATABASE_URL의 사용자명/비밀번호가 틀림

**해결:**
```bash
# .env 파일 확인
cat .env | grep DATABASE_URL

# PostgreSQL 비밀번호 재설정
psql -U postgres
ALTER USER memgarden WITH PASSWORD 'new_password';
```

### Q2. "relation does not exist" 에러

**원인:** 마이그레이션이 적용되지 않음

**해결:**
```bash
# 마이그레이션 상태 확인
alembic current

# 마이그레이션 적용
alembic upgrade head
```

### Q3. "could not connect to server" 에러

**원인:** PostgreSQL 서버가 실행 중이 아님

**해결:**
```bash
# Docker 사용 시
docker-compose up -d postgres
docker-compose logs postgres

# 시스템 PostgreSQL 사용 시
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### Q4. 마이그레이션 충돌 ("Multiple head revisions")

**원인:** 브랜치에서 동시에 마이그레이션 생성

**해결:**
```bash
# 현재 헤드 확인
alembic heads

# 병합
alembic merge -m "Merge migrations" <rev1> <rev2>

# 병합된 마이그레이션 적용
alembic upgrade head
```

### Q5. asyncpg vs psycopg2 차이

| 항목 | asyncpg | psycopg2 |
|------|---------|----------|
| 용도 | FastAPI 앱 (비동기) | Alembic 마이그레이션 (동기) |
| 형식 | `postgresql+asyncpg://` | `postgresql://` |
| 성능 | 빠름 (비동기 I/O) | 보통 (동기 I/O) |
| 사용 | `database/postgres.py` | `alembic/env.py` |

**중요:** 두 드라이버 모두 설치되어야 합니다!

```bash
pip install asyncpg psycopg2-binary
```

---

## 🔧 Troubleshooting

### 전체 재설정 (주의!)

데이터베이스를 완전히 초기화하고 싶을 때:

```bash
# 1. 모든 마이그레이션 롤백
alembic downgrade base

# 2. 데이터베이스 삭제 및 재생성
psql -U postgres -c "DROP DATABASE IF EXISTS memory_garden;"
psql -U postgres -c "CREATE DATABASE memory_garden OWNER memgarden;"

# 3. 마이그레이션 재적용
alembic upgrade head

# 4. 테스트
python scripts/test_db_connection.py
```

### 마이그레이션 파일 수동 수정

자동 생성된 마이그레이션이 잘못되었을 때:

```bash
# 마이그레이션 파일 편집
nano alembic/versions/20260210_1644-8b1eea533361_initial_migration_create_all_tables.py

# 수정 후 재적용
alembic downgrade -1
alembic upgrade head
```

---

## 📚 추가 자료

- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 공식 문서](https://docs.sqlalchemy.org/)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [TimescaleDB 공식 문서](https://docs.timescale.com/)

---

## ✅ 체크리스트

설정 완료 후 확인:

- [ ] PostgreSQL 서버 실행 중
- [ ] `.env` 파일에 DATABASE_URL 설정
- [ ] `alembic upgrade head` 성공
- [ ] `python scripts/test_db_connection.py` 성공
- [ ] 9개 테이블 생성 확인 (users, conversations, analysis_results 등)
- [ ] FastAPI 서버 정상 실행
- [ ] `/health` 엔드포인트 응답 확인

---

**작성일:** 2025-01-15
**작성자:** Memory Garden Team
