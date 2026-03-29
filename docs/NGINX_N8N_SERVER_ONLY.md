# N8N 서버 Nginx 설정 가이드

## 🏗️ 아키텍처 이해

```
사용자
  ↓
Domain 서버 (softline.co.kr - Nginx)
  └─ n8n.softline.co.kr/* → N8N 서버로 모든 경로 포워딩
       ↓
N8N 서버 (Nginx) ← 여기만 설정하면 됩니다!
  ├─ / → localhost:5678 (n8n)
  ├─ /kakao/ → localhost:8000 (Memory Garden) ← 추가
  ├─ /api/ → localhost:8000 (Memory Garden) ← 추가
  └─ /docs → localhost:8000 (Memory Garden) ← 추가
```

**Domain 서버는 변경 불필요!** ✅

---

## ⚡ 빠른 설정 (5분)

### 방법 1: 자동 스크립트 (권장)

```bash
cd /home/admin/docker/MemoryGardenAI
sudo bash scripts/setup_nginx.sh
```

### 방법 2: 수동 설정

```bash
# 1. N8N 서버의 Nginx 설정 파일 찾기
sudo find /etc/nginx -name "*n8n*" -o -name "*default*" | grep -v ".default"

# 2. 설정 파일 편집 (예시)
sudo nano /etc/nginx/sites-available/default
```

### 추가할 설정:

```nginx
server {
    listen 80;
    server_name _;  # 또는 특정 서버명

    # 기존 n8n 설정 (그대로 유지)
    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # ============================================
    # Memory Garden API 추가
    # ============================================

    # Kakao Webhook (중요!)
    location /kakao/ {
        proxy_pass http://localhost:8000/kakao/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Webhook 타임아웃
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }

    # Memory Garden API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Docs (Swagger)
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # ReDoc
    location /redoc {
        proxy_pass http://localhost:8000/redoc;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

### 설정 적용:

```bash
# 1. 문법 확인
sudo nginx -t

# 2. Nginx 재시작
sudo systemctl reload nginx

# 3. 테스트
curl https://n8n.softline.co.kr/kakao/webhook/test
```

---

## 🧪 테스트

### 1. 로컬 테스트 (N8N 서버에서)

```bash
# FastAPI 직접 접근
curl http://localhost:8000/kakao/webhook/test

# 예상 응답:
{"status":"ok","message":"Webhook endpoint is working!"}
```

### 2. N8N 서버 Nginx 테스트

```bash
# N8N 서버에서 로컬 Nginx 확인
curl http://localhost/kakao/webhook/test

# 예상 응답:
{"status":"ok","message":"Webhook endpoint is working!"}
```

### 3. 외부 도메인 테스트

```bash
# 다른 서버나 로컬 컴퓨터에서
curl https://n8n.softline.co.kr/kakao/webhook/test

# 예상 응답:
{"status":"ok","message":"Webhook endpoint is working!"}
```

---

## 🔍 문제 해결

### 404 Not Found (설정 후에도)

```bash
# N8N 서버에서 확인:

# 1. Nginx 설정 확인
sudo nginx -T | grep "location /kakao"

# 2. FastAPI 실행 확인
ps aux | grep uvicorn

# 3. FastAPI 포트 확인
netstat -tuln | grep 8000

# 4. Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log
```

### 502 Bad Gateway

```bash
# FastAPI 서버 확인
ps aux | grep uvicorn

# 실행 중이 아니면:
cd /home/admin/docker/MemoryGardenAI
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
```

### Domain 서버 확인 (필요 시)

Domain 서버 관리자에게 요청:

```nginx
# Domain 서버 설정 확인
server {
    server_name n8n.softline.co.kr;

    location / {
        proxy_pass http://N8N서버IP;  # 모든 경로 포워딩
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

→ 이미 이렇게 설정되어 있을 것 (변경 불필요)

---

## ✅ 설정 완료 확인

```bash
# 1. N8N 서버에서
curl http://localhost:8000/kakao/webhook/test
→ ✅ 성공

# 2. N8N 서버 Nginx 경유
curl http://localhost/kakao/webhook/test
→ ✅ 성공

# 3. 외부 도메인
curl https://n8n.softline.co.kr/kakao/webhook/test
→ ✅ 성공

# 4. Swagger UI
https://n8n.softline.co.kr/docs
→ ✅ FastAPI 문서 표시

# 5. Webhook 시뮬레이션
curl -X POST "https://n8n.softline.co.kr/kakao/webhook/simulate?user_key=test&message=OK"
→ ✅ {"status":"ok","user_key":"test",...}
```

---

## 🎯 요약

```yaml
Domain 서버 (softline.co.kr):
  - 현재 상태: 모든 경로를 N8N 서버로 포워딩 중
  - 필요 작업: 없음 ✅
  - 담당자: Domain 서버 관리자

N8N 서버:
  - 현재 상태: n8n만 설정됨 (localhost:5678)
  - 필요 작업: /kakao/ 경로 추가 (localhost:8000)
  - 담당자: 당신! (지금 바로 설정 가능)

설정 방법:
  1. sudo bash scripts/setup_nginx.sh (자동)
  2. 또는 수동으로 위의 설정 추가
  3. sudo nginx -t && sudo systemctl reload nginx
  4. curl https://n8n.softline.co.kr/kakao/webhook/test

소요 시간: 5분
```

**N8N 서버만 설정하면 끝!** 🚀
