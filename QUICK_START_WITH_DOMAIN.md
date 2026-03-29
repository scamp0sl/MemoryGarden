# 🚀 실제 도메인으로 카카오 연동하기 (n8n.softline.co.kr)

## 🎉 **ngrok 필요 없음!** 실제 도메인 사용

```yaml
도메인: n8n.softline.co.kr
상태: ✅ 활성화
장점:
  - ngrok 불필요 ✅
  - 안정적인 Webhook URL ✅
  - 즉시 실제 user_key 수집 가능 ✅
  - 전문적인 서비스 운영 가능 ✅
```

---

## ⚡ 빠른 시작 (3단계, 10분)

### **1단계: Nginx 설정 추가 (5분)**

```bash
# 자동 설정 스크립트 실행
cd /home/admin/docker/MemoryGardenAI
sudo bash scripts/setup_nginx.sh

# 스크립트가 자동으로:
# ✅ 기존 설정 백업
# ✅ /kakao/ 경로 추가
# ✅ Nginx 재시작
# ✅ 자동 테스트
```

**또는 수동 설정:** `docs/DOMAIN_SETUP_GUIDE.md` 참조

---

### **2단계: 카카오 Webhook URL 설정 (3분)**

```
1. https://business.kakao.com 접속
2. Memory Garden 채널 선택
3. 관리 > 상세 설정 > Webhook URL 설정
4. URL 입력:
   https://n8n.softline.co.kr/kakao/webhook
                          ^^^^^^^^^^^^^^
                          ← 실제 도메인!
5. 저장
```

---

### **3단계: 실제 user_key 수집! (2분)**

```
1. 카카오톡에서 Memory Garden 채널 찾기
2. 메시지 전송: "안녕하세요"
3. FastAPI 로그 확인:

   ============================================================
   📨 카카오 메시지 수신!
   ============================================================
   👤 user_key: user_abc123def456  # ← 실제 user_key!
   💬 메시지: 안녕하세요
   ⏰ 시간: 2026-02-20 15:30:00
   ============================================================

4. 성공! 이제 이 user_key로 친구톡 전송 가능!
```

---

## 🧪 테스트 방법

### **로컬 테스트 (FastAPI 직접)**

```bash
# 1. Webhook 엔드포인트 확인
curl http://localhost:8000/kakao/webhook/test

# 예상 응답:
{"status":"ok","message":"Webhook endpoint is working!"}
```

### **도메인 테스트 (Nginx 경유)**

```bash
# 1. Webhook 엔드포인트 (외부 접근)
curl https://n8n.softline.co.kr/kakao/webhook/test

# 예상 응답:
{"status":"ok","message":"Webhook endpoint is working!"}

# 2. Webhook 시뮬레이션
curl -X POST "https://n8n.softline.co.kr/kakao/webhook/simulate?user_key=test_001&message=Hello"

# 예상 응답:
{"status":"ok","user_key":"test_001","message":"Simulation completed"}
```

### **API 문서 확인**

```bash
# 브라우저에서 접속:
https://n8n.softline.co.kr/docs

# Swagger UI가 열리면 성공!
```

---

## 💻 친구톡 전송 예시

실제 수집한 user_key로 메시지 전송:

```python
from services.kakao_client import KakaoClient

# 1. 클라이언트 초기화
client = KakaoClient(mock_mode=False)  # 실제 전송!

# 2. 실제 user_key로 메시지 전송
result = await client.send_friend_talk(
    user_key="user_abc123def456",  # 카카오에서 수집한 실제 user_key
    message="""안녕하세요! Memory Garden 🌱

오늘의 정원 가꾸기 시간입니다.

어제 저녁은 무엇을 드셨나요?
가족이나 친구와 함께 드셨다면 어떤 이야기를 나누셨는지도 말씀해 주세요."""
)

print(result)
# {
#     "success": True,
#     "message_id": "ft_xyz789",
#     "user_key": "user_abc123def456",
#     "timestamp": "2026-02-20T15:35:00"
# }
```

---

## 🔧 Nginx 설정 상세

### **자동 설정 (권장)**

```bash
sudo bash scripts/setup_nginx.sh
```

스크립트가 다음을 자동으로 수행:
1. ✅ 기존 설정 파일 찾기
2. ✅ 백업 생성
3. ✅ Memory Garden 경로 추가 (/kakao/, /api/, /docs)
4. ✅ Nginx 설정 테스트
5. ✅ Nginx 재시작
6. ✅ Webhook 엔드포인트 테스트

### **수동 설정 (고급)**

상세 가이드: `docs/DOMAIN_SETUP_GUIDE.md`

핵심 설정:
```nginx
# /etc/nginx/sites-available/n8n.softline.co.kr

server {
    listen 443 ssl http2;
    server_name n8n.softline.co.kr;

    # 기존 n8n 설정 (유지)
    location / {
        proxy_pass http://localhost:5678;
        # ...
    }

    # Memory Garden 추가
    location /kakao/ {
        proxy_pass http://localhost:8000/kakao/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🚀 SystemD 서비스 등록 (선택, 권장)

FastAPI 서버를 자동으로 시작:

```bash
# 1. 서비스 파일 생성
sudo nano /etc/systemd/system/memgarden.service
```

```ini
[Unit]
Description=Memory Garden API Server
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/docker/MemoryGardenAI
Environment="PATH=/home/admin/docker/MemoryGardenAI/.venv/bin"
ExecStart=/home/admin/docker/MemoryGardenAI/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable memgarden.service
sudo systemctl start memgarden.service

# 3. 상태 확인
sudo systemctl status memgarden.service
```

---

## 📊 전체 아키텍처

```
사용자 (카카오톡)
      ↓
카카오 서버
      ↓
인터넷
      ↓
[n8n.softline.co.kr]
      ↓
Nginx (443 → 8000)
      ↓
      ├─ / → n8n (5678)
      ├─ /kakao/ → Memory Garden (8000)
      ├─ /api/ → Memory Garden (8000)
      └─ /docs → Memory Garden (8000)
      ↓
FastAPI (Memory Garden)
      ↓
      ├─ PostgreSQL (5432)
      ├─ Redis (6379)
      └─ Qdrant (6333)
```

---

## ✅ 체크리스트

### 설정 전

- [x] 도메인 확인: n8n.softline.co.kr
- [x] FastAPI 서버 실행 중: Port 8000
- [x] Nginx 실행 중
- [x] 카카오 채널 등록 완료

### 설정 중

- [ ] Nginx 설정 추가 (`sudo bash scripts/setup_nginx.sh`)
- [ ] Nginx 재시작
- [ ] 도메인 테스트 (`curl https://n8n.softline.co.kr/kakao/webhook/test`)

### 설정 후

- [ ] 카카오 Webhook URL 설정 (`https://n8n.softline.co.kr/kakao/webhook`)
- [ ] 카카오톡에서 메시지 전송
- [ ] user_key 수집 확인
- [ ] 친구톡 전송 테스트

### 운영 준비

- [ ] SystemD 서비스 등록
- [ ] 로그 모니터링 설정
- [ ] DB에 user_key 저장 로직 구현
- [ ] 일일 대화 플로우 통합

---

## 🔍 문제 해결

### 502 Bad Gateway

```bash
# FastAPI 서버 확인
ps aux | grep uvicorn

# 실행 중이 아니면:
cd /home/admin/docker/MemoryGardenAI
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
```

### 404 Not Found

```bash
# Nginx 설정 확인
sudo nginx -T | grep "location /kakao"

# 설정이 없으면:
sudo bash scripts/setup_nginx.sh
```

### Webhook 응답 없음

```bash
# FastAPI 로그 확인
sudo journalctl -u memgarden.service -f

# 또는 프로세스 로그
ps aux | grep uvicorn
```

---

## 📚 참고 문서

1. **QUICK_START_WITH_DOMAIN.md** (현재 문서) - 도메인 사용 빠른 시작
2. **docs/DOMAIN_SETUP_GUIDE.md** - 상세 설정 가이드
3. **docs/FRIEND_TALK_GUIDE.md** - 친구톡 완벽 가이드
4. **docs/USER_KEY_GUIDE.md** - user_key 수집 방법
5. **scripts/setup_nginx.sh** - 자동 설정 스크립트

---

## 🎯 다음 단계

### 오늘 (즉시 가능)

```bash
# 1. Nginx 설정
sudo bash scripts/setup_nginx.sh

# 2. 테스트
curl https://n8n.softline.co.kr/kakao/webhook/test

# 3. 카카오 Webhook URL 설정
# https://business.kakao.com

# 4. 메시지 전송 → user_key 수집!
```

### 이번 주

- [ ] User 모델에 kakao_user_key 필드 추가
- [ ] Alembic 마이그레이션
- [ ] Webhook에서 자동 DB 저장
- [ ] 친구톡 전송 테스트

### 다음 주

- [ ] Celery Beat 스케줄링 (매일 9시)
- [ ] 일일 대화 플로우 통합
- [ ] 베타 사용자 초대

---

## 🎉 요약

```yaml
기존 방식 (ngrok):
  - 불안정한 URL
  - 세션마다 URL 변경
  - 무료 버전 제약
  - 전문적이지 않음

새로운 방식 (실제 도메인):
  - ✅ 안정적인 URL
  - ✅ 고정 URL (변경 없음)
  - ✅ 제약 없음
  - ✅ 전문적인 서비스

설정 방법:
  1. sudo bash scripts/setup_nginx.sh (5분)
  2. 카카오 Webhook URL 설정 (3분)
  3. 메시지 전송 → user_key 수집! (2분)

총 소요 시간: 10분
```

**실제 도메인으로 전문적인 서비스 운영하세요!** 🚀
