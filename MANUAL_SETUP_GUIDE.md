# 🔧 수동 Nginx 설정 가이드

## 📋 준비된 설정 파일

`memgarden-nginx.conf` 파일이 생성되었습니다!

---

## ⚡ 빠른 설정 (터미널에서 복사-붙여넣기)

터미널을 열고 **아래 명령어를 순서대로 실행**하세요:

### 1단계: 기존 설정 백업

```bash
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
```

### 2단계: 설정 파일 복사

```bash
sudo cp /home/admin/docker/MemoryGardenAI/memgarden-nginx.conf /etc/nginx/conf.d/memgarden.conf
```

### 3단계: 설정 문법 확인

```bash
sudo nginx -t
```

**예상 출력:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 4단계: Nginx 재시작

```bash
sudo systemctl reload nginx
```

### 5단계: 테스트

```bash
# 로컬 테스트
curl http://localhost/kakao/webhook/test

# 외부 도메인 테스트
curl https://n8n.softline.co.kr/kakao/webhook/test
```

**예상 응답:**
```json
{"status":"ok","message":"Webhook endpoint is working!"}
```

---

## 🔍 문제 해결

### nginx -t 실패 시

```bash
# 에러 로그 확인
sudo nginx -t

# 문제가 있으면 백업 복원
sudo cp /etc/nginx/nginx.conf.backup.* /etc/nginx/nginx.conf
```

### 포트 충돌 시

```bash
# 포트 8000 확인
netstat -tuln | grep 8000

# FastAPI 재시작
cd /home/admin/docker/MemoryGardenAI
source .venv/bin/activate
pkill -f "uvicorn api.main:app"
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
```

### Nginx 시작 실패 시

```bash
# Nginx 상태 확인
sudo systemctl status nginx

# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log

# Nginx 강제 재시작
sudo systemctl restart nginx
```

---

## 📝 단계별 상세 설명

### 1. 설정 파일 확인

```bash
# 생성된 설정 파일 내용 확인
cat /home/admin/docker/MemoryGardenAI/memgarden-nginx.conf
```

### 2. conf.d 디렉토리 확인

```bash
# conf.d 디렉토리 존재 확인
ls -la /etc/nginx/conf.d/

# nginx.conf에서 include 확인
grep "include.*conf.d" /etc/nginx/nginx.conf
```

**출력 예상:**
```
include /etc/nginx/conf.d/*.conf;
```

### 3. 복사 및 권한 설정

```bash
# 설정 파일 복사
sudo cp /home/admin/docker/MemoryGardenAI/memgarden-nginx.conf /etc/nginx/conf.d/memgarden.conf

# 권한 확인
ls -l /etc/nginx/conf.d/memgarden.conf

# 예상 출력:
# -rw-r--r-- 1 root root ... /etc/nginx/conf.d/memgarden.conf
```

### 4. 설정 테스트

```bash
# 문법 검사
sudo nginx -t

# 설정 파일 로드 확인
sudo nginx -T | grep -A 5 "location /kakao"
```

### 5. 재시작 및 확인

```bash
# Nginx 재시작 (reload는 다운타임 없음)
sudo systemctl reload nginx

# 재시작 확인
sudo systemctl status nginx

# 프로세스 확인
ps aux | grep nginx
```

---

## 🧪 전체 테스트 스크립트

테스트를 자동화하려면:

```bash
#!/bin/bash
echo "=== Memory Garden Nginx 테스트 ==="
echo ""

echo "1. 로컬 FastAPI 직접 접근:"
curl -s http://localhost:8000/kakao/webhook/test | python3 -m json.tool
echo ""

echo "2. Nginx를 통한 로컬 접근:"
curl -s http://localhost/kakao/webhook/test | python3 -m json.tool
echo ""

echo "3. 외부 도메인 접근:"
curl -s https://n8n.softline.co.kr/kakao/webhook/test | python3 -m json.tool
echo ""

echo "4. Swagger UI:"
echo "https://n8n.softline.co.kr/docs"
echo ""

echo "5. Webhook 시뮬레이션:"
curl -s -X POST "https://n8n.softline.co.kr/kakao/webhook/simulate?user_key=test_001&message=Hello" | python3 -m json.tool
```

---

## ✅ 성공 확인

모든 단계가 완료되면:

1. ✅ `sudo nginx -t` → syntax is ok
2. ✅ `curl http://localhost/kakao/webhook/test` → {"status":"ok"}
3. ✅ `curl https://n8n.softline.co.kr/kakao/webhook/test` → {"status":"ok"}
4. ✅ Swagger UI 접근: https://n8n.softline.co.kr/docs

---

## 🎯 다음 단계

설정이 완료되면:

1. 카카오 비즈니스 센터 Webhook URL 설정
   - https://business.kakao.com
   - URL: `https://n8n.softline.co.kr/kakao/webhook`

2. 카카오톡에서 메시지 전송
   - Memory Garden 채널 찾기
   - "안녕하세요" 전송

3. FastAPI 로그 확인
   - `sudo journalctl -u memgarden.service -f`
   - 또는 `ps aux | grep uvicorn`

4. user_key 수집 확인
   - 로그에 `user_key: user_abc...` 출력 확인

---

## 📞 추가 도움말

문제가 계속되면:

```bash
# 전체 Nginx 설정 확인
sudo nginx -T

# Memory Garden 관련 설정만 확인
sudo nginx -T | grep -A 30 "location /kakao"

# Nginx 에러 로그 실시간 확인
sudo tail -f /var/log/nginx/error.log

# FastAPI 로그 확인
ps aux | grep uvicorn
netstat -tuln | grep 8000
```

---

## 🎉 요약

```bash
# 한 번에 실행 (복사-붙여넣기):
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d) && \
sudo cp /home/admin/docker/MemoryGardenAI/memgarden-nginx.conf /etc/nginx/conf.d/memgarden.conf && \
sudo nginx -t && \
sudo systemctl reload nginx && \
echo "✅ 설정 완료!" && \
curl http://localhost/kakao/webhook/test
```

**소요 시간: 2분**
