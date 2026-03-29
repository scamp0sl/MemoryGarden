# 🔔 카카오 비즈니스 센터 Webhook 설정 가이드

## 📋 준비 사항

✅ 카카오 비즈니스 계정
✅ Memory Garden 채널 등록 완료
✅ Webhook 엔드포인트 준비 완료: `https://n8n.softline.co.kr/kakao/webhook`

---

## 🚀 설정 방법

### **1단계: 카카오 비즈니스 센터 접속**

1. [https://business.kakao.com](https://business.kakao.com) 접속
2. 로그인
3. 좌측 메뉴에서 **"채널"** 선택
4. **"Memory Garden"** 채널 선택

### **2단계: Webhook 설정 메뉴 찾기**

1. 채널 관리 화면에서 **"관리"** 탭 클릭
2. **"상세 설정"** 또는 **"고급 설정"** 찾기
3. **"Webhook"** 또는 **"메시지 수신 설정"** 메뉴 클릭

### **3단계: Webhook URL 입력**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 중요: 정확한 URL 입력
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Webhook URL: https://n8n.softline.co.kr/kakao/webhook

⚠️ 주의사항:
- /test 없이 입력!
- HTTPS 사용 (HTTP 아님)
- 끝에 슬래시(/) 없이 입력

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**설정 항목:**
- **URL**: `https://n8n.softline.co.kr/kakao/webhook`
- **메서드**: POST (기본값)
- **상태**: 활성화 (켜기)

### **4단계: 저장 및 검증**

1. **"저장"** 버튼 클릭
2. 카카오에서 자동으로 Webhook URL 검증 수행
3. ✅ 녹색 체크 표시 확인

---

## 🧪 테스트 방법

### **방법 1: 카카오 비즈니스 센터에서 테스트**

1. Webhook 설정 화면에서 **"테스트 전송"** 버튼 클릭
2. 테스트 메시지 입력
3. **"전송"** 클릭

### **방법 2: 카카오톡 앱에서 직접 테스트**

1. **카카오톡 앱 열기**
2. **검색**: "Memory Garden" 채널 찾기
3. **채널 추가** (아직 안했다면)
4. **메시지 전송**: "안녕하세요" 또는 "테스트"

### **방법 3: 로그 확인**

터미널에서 실시간 로그 모니터링:

```bash
tail -f /home/admin/docker/MemoryGardenAI/logs/fastapi.log
```

**예상 로그:**
```
============================================================
📨 카카오 메시지 수신!
============================================================
👤 user_key: user_abc123def456
💬 메시지: 안녕하세요
⏰ 시간: 2026-02-20 17:20:00
============================================================
```

---

## 🔍 문제 해결

### **문제 1: Webhook URL 검증 실패**

**증상**: "URL을 확인할 수 없습니다" 또는 빨간색 X 표시

**해결:**
1. URL 정확히 입력했는지 확인
   - ✅ `https://n8n.softline.co.kr/kakao/webhook`
   - ❌ `https://n8n.softline.co.kr/kakao/webhook/test`
   - ❌ `http://n8n.softline.co.kr/kakao/webhook` (HTTPS 필수)

2. 엔드포인트 테스트:
   ```bash
   curl https://n8n.softline.co.kr/kakao/webhook/test
   # 예상: {"status":"ok",...}
   ```

3. FastAPI 서버 실행 확인:
   ```bash
   ps aux | grep uvicorn
   ```

### **문제 2: 메시지 수신 안 됨**

**증상**: 메시지를 보내도 로그에 아무것도 안 나타남

**해결:**
1. Webhook 상태 확인 (활성화되어 있는지)
2. 로그 모니터링 터미널 확인
3. FastAPI 로그 에러 확인:
   ```bash
   tail -f /home/admin/docker/MemoryGardenAI/logs/fastapi.log | grep ERROR
   ```

### **문제 3: user_key가 수집 안 됨**

**증상**: 로그에는 나타나지만 user_key가 없음

**해결:**
1. 카카오 채널 "친구 추가" 되어 있는지 확인
2. 채널 관리자 메뉴에서 "메시지 수신 동의" 설정 확인
3. 로그 확인:
   ```bash
   grep "user_key" /home/admin/docker/MemoryGardenAI/logs/fastapi.log
   ```

---

## 📊 Webhook 데이터 구조

카카오에서 전송하는 데이터 형식:

```json
{
  "user_key": "user_abc123def456",
  "type": "text",
  "content": "안녕하세요",
  "timestamp": "2026-02-20T17:20:00+09:00"
}
```

**수집되는 정보:**
- ✅ `user_key`: 사용자 고유 식별자 (친구톡 전송에 필요)
- ✅ `type`: 메시지 타입 (text, image, button 등)
- ✅ `content`: 메시지 내용
- ✅ `timestamp`: 메시지 전송 시간

---

## 🎯 user_key 활용

### **1. user_key 저장**

수집된 user_key를 DB에 저장:

```python
# database/models.py
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    kakao_user_key = Column(String, unique=True, nullable=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.now)
```

### **2. 친구톡 전송**

저장된 user_key로 메시지 전송:

```python
from services.kakao_client import KakaoClient

client = KakaoClient(mock_mode=False)
result = await client.send_friend_talk(
    user_key="user_abc123def456",  # DB에서 조회한 user_key
    message="""안녕하세요! Memory Garden 🌱

오늘의 정원 가꾸기 시간입니다.
어제 저녁에 무엇을 드셨나요?"""
)

print(result)
# {"success": True, "message_id": "ft_xyz789"}
```

### **3. 일일 대화 스케줄링**

Celery Beat으로 매일 정해진 시간에 자동 전송:

```python
# tasks/dialogue.py
@celery.task
def send_daily_prompt():
    users = User.query.filter(User.kakao_user_key.isnot(None)).all()

    for user in users:
        client = KakaoClient(mock_mode=False)
        await client.send_friend_talk(
            user_key=user.kakao_user_key,
            message=generate_daily_prompt(user)
        )
```

---

## ✅ 설정 완료 체크리스트

- [ ] 카카오 비즈니스 센터 접속
- [ ] Memory Garden 채널 선택
- [ ] Webhook URL 설정: `https://n8n.softline.co.kr/kakao/webhook`
- [ ] 상태 "활성화"로 설정
- [ ] 저장 및 검증 완료 (녹색 체크)
- [ ] 테스트 메시지 전송
- [ ] 로그에서 user_key 확인
- [ ] user_key 복사 및 저장

---

## 🎉 성공 확인

모든 단계가 완료되면:

1. ✅ 카카오톡에서 메시지 전송 시 로그 출력
2. ✅ user_key 자동 수집
3. ✅ 친구톡 전송 가능
4. ✅ 일일 대화 자동화 준비 완료

---

## 📞 추가 지원

문제가 계속되면:

1. FastAPI 로그 전체 확인:
   ```bash
   cat /home/admin/docker/MemoryGardenAI/logs/fastapi.log
   ```

2. Nginx 에러 로그:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. 카카오 비즈니스 센터 고객 지원:
   - [https://cs.kakao.com/helps?service=8](https://cs.kakao.com/helps?service=8)

---

생성일: 2026-02-20
작성자: Memory Garden DevOps Team
