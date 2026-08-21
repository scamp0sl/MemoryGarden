# Memory Garden — 신규 서버 이관 및 작업 재개 가이드

> 작성일: 2026-08-21
> 대상: 기존 서버(`/home/admin/docker/MemoryGardenAI`)의 작업을 **새 서버에서 이어서** 진행하려는 개발자
> 저장소: https://github.com/scamp0sl/MemoryGarden.git (branch: `main`)

---

## 0. 30초 요약

```bash
# 1) 코드
git clone https://github.com/scamp0sl/MemoryGarden.git
cd MemoryGarden

# 2) 비공개 파일 복원 (별도 백업 zip)
unzip -o ~/MemoryGarden_private_backup_20260821.zip -d /tmp/mgrestore
cp -a /tmp/mgrestore/secrets/.env                       ./.env
cp -a /tmp/mgrestore/secrets/firebase-adminsdk.json     ./config/
cp -a /tmp/mgrestore/secrets/certs                      ./
mkdir -p logs

# 3) 인프라
docker compose up -d          # postgres(timescale) / redis / qdrant

# 4) 파이썬
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 5) 데이터 복원 (§5)
# 6) 기동
./start_server.sh && curl -s localhost:8002/health
```

---

## 1. 현재 상태 스냅샷 (이관 시점)

| 항목 | 값 |
|------|-----|
| 최신 커밋 | `a66e508` docs: 사만다 기억 시스템 개선 방안 (Action 01) |
| 브랜치 | `main` (origin/main과 동기화 완료) |
| Python | 3.13.4 (`.python-version` = 3.13) |
| 앱 포트 | **8002** (uvicorn, `start_server.sh`) |
| 리버스 프록시 | nginx → `localhost:8002`, 도메인 `n8n.softline.co.kr` |
| PostgreSQL | TimescaleDB pg15, `localhost:5432`, DB `memory_garden`, user `memgarden` |
| Redis | `localhost:6379` (앱은 db0 사용) |
| Qdrant | `localhost:6333` (v1.7.4) |
| LLM Provider | `anthropic` (`LLM_PROVIDER=anthropic`) |

### 실데이터 규모 (이관 시점)

| 저장소 | 내용 | 규모 |
|--------|------|------|
| PostgreSQL | `users` | 30 |
| PostgreSQL | `conversations` | 2,872 |
| PostgreSQL | `analysis_results` | 2,437 |
| PostgreSQL | DB 전체 | 약 25 MB |
| Qdrant | `episodic_memory` | 3,206 points (1536-dim, Cosine) |
| Qdrant | `biographical_memory` | 278 points (1536-dim, Cosine) |
| Redis | db0 | 192 keys |

> ⚠️ Qdrant에 있는 `seculine_*` 컬렉션은 **다른 프로젝트 소유**입니다. Memory Garden과 무관하므로 이관 대상이 아닙니다.

---

## 2. 새 서버 사전 요구사항

- Linux (기존: RHEL 8 계열 / Linux 4.18)
- **Python 3.13** (`requires-python = ">=3.13"`)
- Docker + Docker Compose v2
- nginx (외부 노출 시)
- `git`, `unzip`, `lsof`
- 아웃바운드 HTTPS 허용: `api.anthropic.com`, `api.openai.com`, `kapi.kakao.com` / `kauth.kakao.com`, Firebase(FCM)

---

## 3. 코드 가져오기

```bash
git clone https://github.com/scamp0sl/MemoryGarden.git
cd MemoryGarden
git log --oneline -3      # a66e508 이 최상단이면 정상
```

### 파일 권한(filemode) 참고

기존 서버에서 전체 파일이 `755`로 변경된 이력이 있어, 저장소에는 `core.filemode=false`를 적용해
**모드 변경 노이즈가 커밋되지 않도록** 했습니다. 새 서버에서도 동일하게 두는 것을 권장합니다.

```bash
git config core.filemode false
```

`*.sh` 스크립트는 인덱스상 이미 `100755`이므로 clone 직후 실행 가능합니다.

---

## 4. 비공개 파일 복원 (백업 zip)

Git에 **절대 올라가지 않는** 파일들입니다. 반드시 별도 백업 zip에서 복원하세요.

| 복원 위치 | 파일 | 용도 |
|-----------|------|------|
| `./.env` | 환경변수 전체 | API 키·DB·JWT 등 |
| `./config/firebase-adminsdk.json` | Firebase 서비스 계정 | FCM 푸시 발송 |
| `./certs/` | `cert.pem`, `key.pem`, `openssl.cnf` | 로컬 HTTPS 테스트용 자체 서명 인증서 |
| `./logs/` | (빈 디렉터리 생성) | `start_server.sh`가 `logs/fastapi.log`에 기록 |
| `./.claude/`, `./.agents/` | 에이전트/스킬 설정 | 선택 사항 |

```bash
mkdir -p logs
chmod 600 .env config/firebase-adminsdk.json certs/key.pem
```

### 새 서버에서 **반드시 수정해야 하는** `.env` 항목

| 키 | 기존 값 | 조치 |
|----|---------|------|
| `KAKAO_REDIRECT_URI` | `https://n8n.softline.co.kr/api/v1/auth/kakao/callback` | 새 도메인으로 변경 + **카카오 개발자 콘솔에 동일하게 등록** |
| `KAKAO_CHANNEL_DEEP_LINK` | 기존 채널 링크 | 채널 유지 시 그대로, 변경 시 갱신 |
| `DATABASE_URL` | `postgresql+asyncpg://memgarden:***@localhost:5432/memory_garden` | 호스트가 달라지면 갱신 |
| `REDIS_URL` / `QDRANT_URL` | `localhost` | 호스트가 달라지면 갱신 |
| `SECRET_KEY` | 기존 JWT 시크릿 | **그대로 유지**해야 기존 발급 토큰이 유효 |
| `APP_ENV` | `development` | 운영 전환 시 `production` |
| `KAKAO_MOCK_MODE` | `false` | 실발송 없이 테스트하려면 `true` |

> `.env.example`에 전체 키 목록이 있습니다. `.env`와 `.env.example`의 키가 어긋나면 `config/settings.py`를 기준으로 맞추세요.

---

## 5. 인프라 및 데이터 복원

### 5-1. 컨테이너 기동

```bash
docker compose up -d
docker compose ps          # 3개 모두 healthy 확인
```

`docker-compose.yml`은 다음을 띄웁니다.

- `memgarden-postgres` — `timescale/timescaledb:latest-pg15`, 5432
- `memgarden-redis` — `redis:7-alpine`, 6379
- `memgarden-qdrant` — `qdrant/qdrant:v1.7.4`, 6333/6334

> compose의 `POSTGRES_PASSWORD`는 `password`(기본값)입니다. `.env`의 `DATABASE_URL` 비밀번호와 반드시 일치시키세요.

### 5-2. PostgreSQL 복원

```bash
gunzip -c data/postgres_memory_garden.sql.gz \
  | docker exec -i memgarden-postgres psql -U memgarden -d memory_garden

# 확인
docker exec memgarden-postgres psql -U memgarden -d memory_garden \
  -c "SELECT count(*) FROM users;  SELECT count(*) FROM conversations;"
```

> 덤프는 `--no-owner --no-acl`로 생성되었습니다. TimescaleDB 확장이 먼저 설치되어 있어야 하므로
> **compose로 timescaledb 이미지를 띄운 뒤** 복원하세요.

### 5-3. Redis 복원

```bash
docker compose stop redis
docker cp data/redis_dump.rdb memgarden-redis:/data/dump.rdb
docker compose start redis
docker exec memgarden-redis redis-cli DBSIZE     # 192 근처면 정상
```

### 5-4. Qdrant 복원

```bash
# 컬렉션별 snapshot 업로드
for c in episodic_memory biographical_memory; do
  curl -X POST "http://localhost:6333/collections/${c}/snapshots/upload?priority=snapshot" \
       -H 'Content-Type: multipart/form-data' \
       -F "snapshot=@data/qdrant_${c}.snapshot"
done

# 확인
curl -s http://localhost:6333/collections/episodic_memory | python3 -m json.tool | grep points_count
```

기대값: `episodic_memory` ≈ 3,206 / `biographical_memory` ≈ 278

### 5-5. 스키마 확인 (Alembic)

```bash
.venv/bin/alembic current      # 최신 리비전과 일치하는지 확인
.venv/bin/alembic upgrade head # 덤프 없이 새로 구성할 경우
```

최신 마이그레이션: `20260330_1013_add_is_active_to_users.py`

TimescaleDB 하이퍼테이블 초기화가 필요하면:

```bash
.venv/bin/python scripts/init_timescale.py
```

---

## 6. 파이썬 환경

기존 서버는 **uv**로 `.venv`를 만들었습니다(venv 안에 pip 없음). 둘 중 편한 쪽을 쓰세요.

### 방법 A — 표준 venv + pip (권장, 단순)

```bash
python3.13 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### 방법 B — uv (기존과 동일)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.13
uv pip install -r requirements.txt
```

### 버전 재현이 필요하면

`requirements.txt`는 버전 핀이 없어 최신 버전이 설치됩니다. 기존 서버와 **정확히 동일한 버전**이 필요하면
백업 zip의 `requirements-lock.txt`(이관 시점 설치본 125개 패키지)를 사용하세요.

```bash
.venv/bin/pip install -r requirements-lock.txt
```

> ⚠️ `.venv/` 디렉터리 자체는 절대 복사하지 마세요. 경로가 하드코딩되어 있어 다른 서버에서 동작하지 않습니다.

---

## 7. 애플리케이션 기동

```bash
mkdir -p logs
./start_server.sh
tail -f logs/fastapi.log
curl -s http://localhost:8002/health
curl -s http://localhost:8002/docs   # Swagger
```

`start_server.sh` 동작:
- `ANTHROPIC_BASE_URL`을 공식 엔드포인트로 강제(Claude Code 환경변수 상속 방지)
- 8002 포트 점유 프로세스 종료
- `nohup .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8002` 백그라운드 실행

### ⚠️ 포트 불일치 주의

리포지토리 안에 **서로 다른 포트를 쓰는 파일**이 섞여 있습니다. 새 서버에서는 하나로 통일하세요.

| 파일 | 포트 | 상태 |
|------|------|------|
| `start_server.sh` | **8002** | ✅ 실제 사용 중 (nginx가 여기로 프록시) |
| `/etc/nginx/conf.d/memgarden.conf` (운영) | **8002** | ✅ 실제 사용 중 |
| `memgarden.service` (리포지토리) | 8000 | ⚠️ 미사용 / 오래됨 — systemd 등록 안 되어 있음 |
| `memgarden-nginx.conf` (리포지토리) | 8000 | ⚠️ 운영 conf와 다름 — 참고용으로만 |
| `.env.example`의 `KAKAO_REDIRECT_URI` | 8001 | ⚠️ 예시값일 뿐, 실제는 도메인 기반 |

→ **운영 nginx conf 원본은 백업 zip의 `nginx/memgarden.conf`에 포함**되어 있습니다. 리포지토리의 `memgarden-nginx.conf`보다 이 쪽이 최신입니다.

---

## 8. nginx / 도메인 / 카카오 연동

1. 백업 zip의 `nginx/memgarden.conf`를 새 서버 `/etc/nginx/conf.d/`에 배치
2. `server_name`을 새 도메인으로 변경
3. Memory Garden 관련 `location` 블록만 남기고 나머지(n8n, boardg, stockline 등 타 서비스)는 제거
4. TLS 인증서 경로 갱신 (`certbot` 등)
5. `nginx -t && systemctl reload nginx`
6. **카카오 개발자 콘솔**에서 아래를 새 도메인으로 갱신
   - Redirect URI (`/api/v1/auth/kakao/callback`)
   - 웹훅(스킬 서버) URL (`/kakao/...`)
   - 플랫폼 등록 도메인

> 카카오 웹훅은 응답 지연에 민감합니다. nginx의 `proxy_read_timeout`을 30s 이상 유지하세요.

### systemd로 상시 기동하려면

`memgarden.service`를 아래 기준으로 수정 후 등록하세요.
- `WorkingDirectory` / `ExecStart` 경로를 새 서버 경로로
- 포트를 **8002**로
- `User`/`Group`을 실제 실행 계정으로

```bash
sudo cp memgarden.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now memgarden
```

---

## 9. 검증 체크리스트

```bash
# 인프라
docker compose ps                                    # 3개 healthy
docker exec memgarden-postgres pg_isready -U memgarden -d memory_garden
docker exec memgarden-redis redis-cli ping
curl -s http://localhost:6333/collections

# 데이터
docker exec memgarden-postgres psql -U memgarden -d memory_garden -c "SELECT count(*) FROM conversations;"
curl -s http://localhost:6333/collections/episodic_memory | grep -o '"points_count":[0-9]*'

# 앱
curl -s http://localhost:8002/health
curl -s http://localhost:8002/docs -o /dev/null -w '%{http_code}\n'

# 연결성 개별 점검 스크립트
.venv/bin/python scripts/test_db_connection.py
.venv/bin/python scripts/test_redis_connection.py

# 테스트
.venv/bin/pytest tests/ -v
```

- [ ] `docker compose ps` 3개 healthy
- [ ] PostgreSQL 행수가 §1 표와 일치
- [ ] Qdrant `points_count` 일치
- [ ] Redis `DBSIZE` 일치
- [ ] `/health` 200
- [ ] `.env`의 `KAKAO_REDIRECT_URI`가 새 도메인 & 카카오 콘솔과 일치
- [ ] Firebase 서비스 계정 경로(`config/firebase-adminsdk.json`) 존재 및 권한 600
- [ ] `SECRET_KEY` 기존 값 유지
- [ ] 카카오 웹훅 실호출 1건 성공

---

## 10. 리포지토리 구조 요약

```
api/          FastAPI 라우트 · 스키마 · 미들웨어
core/
  analysis/   MCDI 6지표 (LR, SD, NC, TO, ER, RT) + 위험도 평가
  dialogue/   대화 관리 · 프롬프트 빌더 · 응답 생성
  memory/     4계층 메모리 (추출/관리/의도 스코어링)
  nlp/        형태소·언어 처리
  workflow/   처리 파이프라인
services/     LLM · 카카오 · 이미지 분석 등 외부 연동
database/     postgres / redis / qdrant / timescale 클라이언트
tasks/        스케줄 작업 (대화 발송, 참여 모니터링, 토큰 관리)
scripts/      운영·점검·데이터 보정 스크립트 (일회성 다수)
alembic/      DB 마이그레이션
tests/        pytest
docs/         설계·가이드 문서
static/       대시보드 · FCM 서비스워커
```

핵심 문서:
- `SPEC.md` — 전체 명세 (MCDI 가중치, 위험도 기준, 데이터 모델, API)
- `CLAUDE.md` — 코딩 컨벤션 / AI 어시스턴트 가이드
- `docs/SYSTEM_ARCHITECTURE.md` — 시스템 아키텍처
- `docs/samantha_upgrade_action01_2026-03-31.md` — **가장 최근 진행 중이던 작업** (사만다 기억 시스템 개선)

---

## 11. 이어서 할 작업 (마지막 컨텍스트)

최근 커밋 흐름:

```
a66e508  docs: 사만다 기억 시스템 개선 방안 (Action 01) 문서 작성   ← 최신
41cc315  chore: 프로젝트 전체 파일 스냅샷 커밋
195527c  docs: 사만다 페르소나 업그레이드 로드맵 추가
c217489  fix: 퀴즈 완료 후 회상 문맥 제거
```

진행 맥락:
1. **사만다 페르소나 업그레이드** — `docs/samantha_*.md` 계열 문서에 로드맵/설계/결함분석이 정리되어 있음
2. **Action 01: 기억 시스템 개선** — `docs/samantha_upgrade_action01_2026-03-31.md`가 최신 실행 문서
   - 관련 구현: `core/memory/intent_scorer.py` (의도 스코어링, 신규)
   - 관련 수정: `core/memory/memory_manager.py`, `core/memory/memory_extractor.py`
   - 관련 테스트: `tests/test_action01_validation.py`
3. **이브닝 퀴즈 시스템** — `tasks/dialogue.py` 중심으로 구현/버그픽스가 이어짐

새 서버에서 시작할 때는 `docs/samantha_upgrade_action01_2026-03-31.md`를 먼저 읽고
`tests/test_action01_validation.py`를 돌려 현재 상태를 확인하는 것을 권장합니다.

---

## 12. 알려진 정리 대상 (기술 부채)

이관과 함께 정리하면 좋은 항목들입니다. **기능에는 영향 없습니다.**

| 항목 | 내용 |
|------|------|
| 패치 잔여물 | `MemoryGarden_new.html.orig`, `.rej`, `core/dialogue/response_generator.py.orig`, `*.py.bak` 이 추적 중 |
| 임시 스크립트 | `tmp_fetch.py`, `tmp_fetch_all.py`, `tmp_user_evening.py` 가 추적 중 |
| 루트 테스트 파일 | `test_*.py` 20여 개가 루트에 흩어져 있음 → `tests/`로 이동 권장 |
| `scripts/` 일회성 | `check_user_7_*`, `search_rose_*` 등 특정 사용자 디버깅용 스크립트 다수 |
| 미사용 설정 | `memgarden.service`(8000), `memgarden-nginx.conf`(8000), `pyproject.toml.venv` |
| 문서 중복 | 루트에 상태 리포트 `*.md` 15개 이상 → `docs/`로 통합 권장 |
| 대용량 아카이브 | `MG_AI.*.tar` 7개(약 2.7 GB)는 구 서버 스냅샷. `.gitignore` 처리됨, 필요 시에만 별도 이관 |

> `.gitignore`에 `*.orig`, `*.rej`, `tmp_*.py` 패턴을 추가했지만, **이미 추적 중인 파일은 계속 추적**됩니다.
> 정리하려면 `git rm --cached <파일>` 후 커밋하세요.

---

## 13. 보안 주의사항

- `.env`, `config/firebase-adminsdk.json`, `certs/key.pem`은 **Git 이력에 없습니다.** 백업 zip으로만 전달하세요.
- 백업 zip은 실제 API 키(Anthropic / OpenAI / DeepSeek / Kakao)와 Firebase 서비스 계정 개인키를 포함합니다.
  → 안전한 채널로만 전달하고, 복원 후 zip은 파기하세요.
- `static/firebase-messaging-sw.js`의 `AIzaSy...` 키는 Firebase **웹 클라이언트 키**로, 브라우저에 노출되는 것이 정상입니다. 유출이 아닙니다.
- 서버 이전을 계기로 Anthropic / OpenAI / Kakao 키를 **로테이션**하는 것을 권장합니다.
- 30명의 실사용자 대화 데이터가 포함되어 있습니다. 개인정보 처리 관점에서 백업본 취급에 주의하세요 (SPEC.md §10 참조).

---

## 14. 문제 해결

| 증상 | 원인 / 조치 |
|------|------------|
| `logs/fastapi.log: No such file or directory` | `logs/`는 gitignore 대상 → `mkdir -p logs` |
| `alembic` 리비전 불일치 | 덤프 복원 시 `alembic_version` 테이블도 함께 복원됨. `alembic current`로 확인 |
| Qdrant 검색 결과 0건 | 임베딩 차원 확인 (1536이어야 함), 컬렉션명 확인 |
| `dubious ownership` git 오류 | `git config --global --add safe.directory <경로>` |
| `pip: command not found` (venv 내) | uv로 만든 venv에는 pip이 없음 → §6 방법 A로 재생성 |
| LLM 호출이 엉뚱한 엔드포인트로 감 | `ANTHROPIC_BASE_URL` 환경변수 상속 문제. `start_server.sh`가 이를 해결함 |
| 카카오 웹훅 타임아웃 | nginx `proxy_read_timeout 30s` 이상 확인 |
