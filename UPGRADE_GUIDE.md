# 🚀 Memory Garden 최신 버전 업그레이드 가이드

**작성일:** 2026-02-11
**목적:** 구버전(2022-2023) → 최신 안정 버전(2025-2026) 업그레이드

---

## 📊 업그레이드 개요

### 주요 패키지 버전 변화

| 패키지 | 구버전 | 최신 버전 | Breaking Changes |
|--------|--------|-----------|------------------|
| **FastAPI** | 0.83.0 | 0.115+ | 중간 업데이트 多 |
| **Pydantic** | 1.9.2 | 2.10+ | 🔴 **Major** |
| **SQLAlchemy** | 1.4.54 | 2.0+ | 🔴 **Major** |
| **NumPy** | 1.19.5 | 2.2+ | 🔴 **Major** |
| **Pandas** | 1.1.5 | 2.2+ | 🔴 **Major** |
| **Uvicorn** | 0.16.0 | 0.34+ | 중간 업데이트 |

---

## ⚡ 빠른 시작 (자동 스크립트)

```bash
cd /home/admin/docker/MemoryGardenAI

# 실행 권한 부여
chmod +x upgrade_venv.sh

# 업그레이드 실행 (약 5분 소요)
./upgrade_venv.sh
```

**스크립트가 자동으로 수행:**
1. ✅ 기존 .venv 백업
2. ✅ venv 디렉토리 제거 (미사용)
3. ✅ 새 가상환경 생성
4. ✅ 최신 패키지 설치
5. ✅ Import 테스트
6. ✅ 업그레이드 리포트 생성

---

## 🔧 수동 업그레이드 (단계별)

자동 스크립트를 신뢰하지 않는 경우:

### Step 1: 백업
```bash
cd /home/admin/docker/MemoryGardenAI

# 현재 패키지 목록 저장
source .venv/bin/activate
pip freeze > requirements_backup_$(date +%Y%m%d).txt

# .venv 백업
mv .venv .venv_backup_$(date +%Y%m%d)
```

### Step 2: 새 가상환경 생성
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 3: pip 업그레이드
```bash
pip install --upgrade pip setuptools wheel
```

### Step 4: 의존성 설치
```bash
pip install -r requirements.txt
```

### Step 5: 설치 확인
```bash
pip list | head -20
```

---

## 🐛 코드 수정 가이드

### 1. Pydantic v2 마이그레이션

#### config/settings.py (이미 OK ✅)
```python
# ✅ 현재 코드는 이미 Pydantic v2 호환
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ...
    class Config:  # v2에서는 model_config 권장하지만 호환됨
        env_file = ".env"
```

#### api/schemas/*.py (확인 필요)
```python
# ❌ Pydantic v1 스타일 (수정 필요 시)
from pydantic import BaseModel, validator

class User(BaseModel):
    email: str

    @validator('email')
    def validate_email(cls, v):
        # ...
        return v

# ✅ Pydantic v2 스타일
from pydantic import BaseModel, field_validator

class User(BaseModel):
    email: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # ...
        return v
```

**마이그레이션 도구 사용:**
```bash
# Pydantic v2 자동 마이그레이션
pip install bump-pydantic
bump-pydantic api/schemas/
```

---

### 2. SQLAlchemy 2.0 마이그레이션

#### database/models.py (확인 필요)
```python
# ❌ SQLAlchemy 1.4 스타일
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    # ...

# ✅ SQLAlchemy 2.0 스타일 (권장)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    # ...
```

#### database/postgres.py (확인 필요)
```python
# ❌ SQLAlchemy 1.4 스타일
from sqlalchemy.orm import sessionmaker

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# ✅ SQLAlchemy 2.0 스타일
from sqlalchemy.ext.asyncio import async_sessionmaker

async_session = async_sessionmaker(
    engine, expire_on_commit=False
)
```

---

### 3. NumPy 2.0 호환성

대부분 자동 호환되지만, deprecated 경고 확인:

```bash
# 경고 메시지 확인
python -W default -c "import numpy; import core.analysis.lexical_richness"
```

**일반적인 변경사항:**
```python
# ❌ NumPy 1.x deprecated
np.float  # → np.float64
np.int    # → np.int64

# ✅ NumPy 2.0
np.float64
np.int64
```

---

## ✅ 테스트 및 검증

### 1. Import 테스트
```bash
python -c "
import fastapi
import pydantic
import sqlalchemy
import redis
import anthropic
import openai
import numpy
import pandas
print('✅ All imports successful!')
"
```

### 2. 단위 테스트 실행
```bash
# 전체 테스트
pytest tests/ -v

# 특정 모듈만
pytest tests/test_core/ -v
pytest tests/test_api/ -v
```

### 3. API 서버 시작 테스트
```bash
uvicorn api.main:app --reload --port 8000
```

브라우저에서 확인:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/health (헬스 체크)

---

## 🔄 롤백 절차 (문제 발생 시)

### Option 1: 백업에서 복원
```bash
cd /home/admin/docker/MemoryGardenAI

# 현재 .venv 제거
rm -rf .venv

# 백업 복원
mv .venv_backup_YYYYMMDD .venv

# 활성화
source .venv/bin/activate

# 확인
pip list
```

### Option 2: 백업 requirements.txt로 재설치
```bash
# 새 가상환경
python3.11 -m venv .venv
source .venv/bin/activate

# 구버전 재설치
pip install -r requirements_backup_YYYYMMDD.txt
```

---

## 📋 체크리스트

### 업그레이드 전
- [ ] 현재 .venv 백업 완료
- [ ] Docker 컨테이너 중지
- [ ] Git commit (현재 작업 저장)

### 업그레이드 중
- [ ] upgrade_venv.sh 실행
- [ ] Import 테스트 통과
- [ ] 주요 패키지 버전 확인

### 업그레이드 후
- [ ] Pydantic v2 호환성 확인
- [ ] SQLAlchemy 2.0 호환성 확인
- [ ] pytest 테스트 통과 (275개)
- [ ] API 서버 정상 실행
- [ ] Docker 컨테이너 재시작
- [ ] 통합 테스트 실행

---

## ⚠️ 알려진 이슈

### Issue 1: Pydantic 경고 메시지
```
UserWarning: Field "..." has conflict with protected namespace "model_"
```

**해결:** 필드명 변경 또는 경고 무시
```python
model_config = ConfigDict(protected_namespaces=())
```

### Issue 2: SQLAlchemy 2.0 Select 구문
```python
# ❌ 1.4 스타일
session.query(User).filter(User.id == 1)

# ✅ 2.0 스타일
session.execute(select(User).where(User.id == 1))
```

### Issue 3: NumPy 2.0 타입 경고
```
DeprecationWarning: `np.float` is deprecated
```

**해결:** `np.float` → `np.float64` 변경

---

## 📞 문제 해결

1. **의존성 충돌**
   ```bash
   pip install --upgrade --force-reinstall -r requirements.txt
   ```

2. **빌드 실패 (kiwipiepy 등)**
   ```bash
   # 빌드 도구 설치
   pip install --upgrade build wheel
   ```

3. **테스트 실패**
   - 각 테스트 파일 개별 실행
   - 에러 메시지 확인
   - Pydantic/SQLAlchemy 마이그레이션 가이드 참조

---

## 🎯 최종 검증 명령어

```bash
# 모든 검증을 한 번에
cd /home/admin/docker/MemoryGardenAI
source .venv/bin/activate

# 1. Import 테스트
python -c "import fastapi, pydantic, sqlalchemy, redis, anthropic, openai, numpy, pandas; print('✅ Imports OK')"

# 2. 단위 테스트
pytest tests/ -v --tb=short

# 3. API 서버
uvicorn api.main:app --reload &
sleep 5
curl http://localhost:8000/health
kill %1

# 4. Docker 재시작
docker-compose up -d
docker-compose ps
```

---

## 📚 참고 자료

- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [SQLAlchemy 2.0 Migration](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [NumPy 2.0 Release Notes](https://numpy.org/devdocs/release/2.0.0-notes.html)
- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/)

---

**작성:** Memory Garden Team
**최종 업데이트:** 2026-02-11
