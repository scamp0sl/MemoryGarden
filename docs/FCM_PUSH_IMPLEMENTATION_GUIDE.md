# FCM 푸시 알림 구현 가이드

> Memory Garden - Firebase Cloud Messaging 푸시 알림 시스템

## 📋 목차

1. [개요](#개요)
2. [Firebase 프로젝트 설정](#firebase-프로젝트-설정)
3. [백엔드 설정](#백엔드-설정)
4. [클라이언트 설정](#클라이언트-설정)
5. [테스트](#테스트)
6. [운영](#운영)
7. [문제 해결](#문제-해결)

---

## 개요

### 시스템 구조

```
사용자 기기 (Android/iOS/Web)
    ↓
[FCM 토큰 등록]
    ↓
Memory Garden API
    ↓
[스케줄러 - 일일 3회]
    ↓
Firebase Cloud Messaging
    ↓
[푸시 알림 전송]
    ↓
사용자 기기 알림 수신
    ↓
[딥링크] → 카카오톡 채널
    ↓
Webhook → AI 대화
```

### 주요 기능

- ✅ 일일 3회 자동 푸시 알림 (10시, 15시, 20시)
- ✅ 딥링크로 카카오톡 채널 자동 열기
- ✅ 멀티 디바이스 지원
- ✅ 실패한 토큰 자동 관리
- ✅ 발송 통계 및 로깅

---

## Firebase 프로젝트 설정

### 1. Firebase 프로젝트 생성

1. **Firebase Console 접속**
   ```
   https://console.firebase.google.com/
   ```

2. **프로젝트 추가**
   - 프로젝트 이름: `Memory Garden`
   - Google Analytics: 활성화 (권장)
   - 위치: 대한민국

3. **FCM 활성화**
   ```
   프로젝트 설정 > Cloud Messaging
   → "Cloud Messaging API (V1)" 활성화
   ```

### 2. 서비스 계정 키 다운로드

```
프로젝트 설정 > 서비스 계정
→ "새 비공개 키 생성" 클릭
→ JSON 파일 다운로드
```

**파일 저장 위치**:
```bash
/home/admin/docker/MemoryGardenAI/config/firebase-adminsdk.json
```

**권한 설정**:
```bash
chmod 600 config/firebase-adminsdk.json
```

### 3. 앱 등록 (Android/iOS/Web)

#### Android 앱 등록

```
프로젝트 설정 > 일반
→ "앱 추가" > Android
→ 패키지 이름: com.memorygarden.app
→ google-services.json 다운로드
```

#### iOS 앱 등록

```
프로젝트 설정 > 일반
→ "앱 추가" > iOS
→ 번들 ID: com.memorygarden.app
→ GoogleService-Info.plist 다운로드
```

#### Web 앱 등록

```
프로젝트 설정 > 일반
→ "앱 추가" > 웹
→ 앱 닉네임: Memory Garden Web
→ Firebase SDK 코드 복사
```

---

## 백엔드 설정

### 1. 의존성 설치

```bash
cd /home/admin/docker/MemoryGardenAI

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install firebase-admin apscheduler
```

### 2. 환경 변수 설정

**.env 파일 수정**:
```bash
nano .env
```

**추가할 내용**:
```env
# Firebase Cloud Messaging
FIREBASE_CREDENTIALS_PATH=config/firebase-adminsdk.json
FIREBASE_PROJECT_ID=memory-garden-xxxxx
KAKAO_CHANNEL_DEEP_LINK=kakaotalk://talk/chat/_ZeUTxl
```

**FIREBASE_PROJECT_ID 확인 방법**:
```
Firebase Console > 프로젝트 설정 > 일반
→ "프로젝트 ID" 복사
```

### 3. 데이터베이스 마이그레이션

```bash
# Alembic 마이그레이션 실행
alembic upgrade head

# 또는 수동 실행
python -c "
from database.postgres import engine
from database.models import Base
import asyncio

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
"
```

### 4. 서버 실행

```bash
# 개발 모드
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**실행 확인**:
```bash
# 헬스 체크
curl http://localhost:8000/health

# API 문서
open http://localhost:8000/docs
```

---

## 클라이언트 설정

### 웹 클라이언트 (예시)

**1. Firebase SDK 추가**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Memory Garden</title>
</head>
<body>
    <!-- Firebase SDK -->
    <script src="https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js"></script>

    <script>
        // Firebase 설정
        const firebaseConfig = {
            apiKey: "YOUR_API_KEY",
            authDomain: "memory-garden-xxxxx.firebaseapp.com",
            projectId: "memory-garden-xxxxx",
            messagingSenderId: "123456789",
            appId: "1:123456789:web:abcdef"
        };

        // Firebase 초기화
        firebase.initializeApp(firebaseConfig);
        const messaging = firebase.messaging();

        // 푸시 알림 권한 요청
        messaging.requestPermission()
            .then(() => {
                console.log('Notification permission granted');
                return messaging.getToken();
            })
            .then((token) => {
                console.log('FCM Token:', token);

                // 백엔드에 토큰 등록
                registerToken(token);
            })
            .catch((err) => {
                console.error('Permission denied:', err);
            });

        // 토큰 등록 함수
        function registerToken(token) {
            fetch('http://localhost:8000/api/v1/push/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: 'USER_UUID_HERE',
                    token: token,
                    device_type: 'web',
                    device_name: navigator.userAgent
                })
            })
            .then(res => res.json())
            .then(data => {
                console.log('Token registered:', data);
            })
            .catch(err => {
                console.error('Token registration failed:', err);
            });
        }

        // 포그라운드 메시지 수신
        messaging.onMessage((payload) => {
            console.log('Message received:', payload);

            // 알림 표시
            new Notification(payload.notification.title, {
                body: payload.notification.body,
                icon: '/icon.png'
            });

            // 딥링크 처리
            if (payload.data.deep_link) {
                window.location.href = payload.data.deep_link;
            }
        });
    </script>
</body>
</html>
```

**2. Service Worker 설정** (`firebase-messaging-sw.js`):
```javascript
importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "YOUR_API_KEY",
    authDomain: "memory-garden-xxxxx.firebaseapp.com",
    projectId: "memory-garden-xxxxx",
    messagingSenderId: "123456789",
    appId: "1:123456789:web:abcdef"
});

const messaging = firebase.messaging();

// 백그라운드 메시지 수신
messaging.onBackgroundMessage((payload) => {
    console.log('Background message received:', payload);

    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/icon.png',
        data: payload.data
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// 알림 클릭 이벤트
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    // 딥링크로 이동
    if (event.notification.data.deep_link) {
        event.waitUntil(
            clients.openWindow(event.notification.data.deep_link)
        );
    }
});
```

### Android 클라이언트 (Kotlin 예시)

```kotlin
// build.gradle
dependencies {
    implementation(platform("com.google.firebase:firebase-bom:32.7.0"))
    implementation("com.google.firebase:firebase-messaging-ktx")
}

// FirebaseMessagingService.kt
class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        Log.d(TAG, "FCM Token: $token")

        // 백엔드에 토큰 등록
        registerToken(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        Log.d(TAG, "Message received: ${message.notification?.title}")

        // 알림 표시
        showNotification(message)

        // 딥링크 처리
        message.data["deep_link"]?.let { deepLink ->
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(deepLink))
            startActivity(intent)
        }
    }

    private fun registerToken(token: String) {
        val client = OkHttpClient()
        val json = JSONObject()
            .put("user_id", "USER_UUID_HERE")
            .put("token", token)
            .put("device_type", "android")
            .put("device_name", Build.MODEL)

        val body = json.toString()
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("http://localhost:8000/api/v1/push/register")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                Log.d(TAG, "Token registered: ${response.body?.string()}")
            }

            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Token registration failed", e)
            }
        })
    }

    private fun showNotification(message: RemoteMessage) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(message.notification?.title)
            .setContentText(message.notification?.body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(0, notification)
    }
}
```

---

## 테스트

### 1. FCM 토큰 등록 테스트

```bash
curl -X POST http://localhost:8000/api/v1/push/register \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "YOUR_USER_UUID",
        "token": "YOUR_FCM_TOKEN",
        "device_type": "web",
        "device_name": "Chrome on macOS"
    }'
```

**예상 응답**:
```json
{
    "success": true,
    "token_id": 1,
    "user_id": "...",
    "message": "FCM token registered successfully"
}
```

### 2. 푸시 알림 테스트

```bash
curl -X POST http://localhost:8000/api/v1/push/test \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "YOUR_USER_UUID",
        "title": "Memory Garden 🌱",
        "body": "테스트 알림입니다!",
        "deep_link": "kakaotalk://talk/chat/_ZeUTxl"
    }'
```

**예상 응답**:
```json
{
    "success": true,
    "sent_count": 1,
    "failed_count": 0,
    "message": "Push notifications sent to 1 device(s)"
}
```

### 3. 스케줄러 로그 확인

```bash
# 실시간 로그 모니터링
tail -f logs/fastapi.log | grep "prompt"

# 예상 로그 출력:
# 2026-02-23 10:00:00 - INFO - 🔔 Starting morning prompt for 5 users
# 2026-02-23 10:00:02 - INFO - ✅ Morning prompt completed
```

---

## 운영

### 스케줄 변경

**services/push_scheduler.py** 수정:

```python
# 오전 10시 → 오전 9시로 변경
self.scheduler.add_job(
    self.send_morning_prompt,
    trigger=CronTrigger(hour=9, minute=0),  # 9시로 변경
    id="morning_prompt",
    name="오전 정원 가꾸기 알림"
)
```

### 메시지 변경

**services/push_scheduler.py** 수정:

```python
async def send_morning_prompt(self):
    """오전 알림"""
    await self._send_prompt(
        title="Memory Garden 🌱",
        body="새로운 메시지 내용",  # 메시지 변경
        prompt_type="morning"
    )
```

### 즉시 발송 (수동 트리거)

```python
from services.push_scheduler import get_push_scheduler

scheduler = get_push_scheduler()
await scheduler.send_immediate_prompt(
    user_ids=["user_1", "user_2"],
    title="긴급 알림",
    body="중요한 메시지입니다"
)
```

### 모니터링

**발송 통계 확인**:
```bash
# 오늘 발송 현황
grep "prompt completed" logs/fastapi.log | grep $(date +%Y-%m-%d)

# 실패한 토큰 확인
grep "Token.*marked as inactive" logs/fastapi.log
```

---

## 문제 해결

### Firebase 초기화 실패

**증상**:
```
Failed to initialize Firebase: ...
```

**해결**:
1. `config/firebase-adminsdk.json` 파일 존재 확인
2. JSON 파일 형식 검증
3. 파일 권한 확인: `chmod 600 config/firebase-adminsdk.json`

### 푸시 알림이 전송 안 됨

**체크리스트**:
1. ✅ FCM 토큰이 올바르게 등록되었는가?
2. ✅ 토큰이 `is_active=true`인가?
3. ✅ Firebase 프로젝트 ID가 올바른가?
4. ✅ 클라이언트 앱이 포그라운드인가?

**디버깅**:
```python
# 토큰 상태 확인
curl http://localhost:8000/api/v1/push/tokens/USER_UUID

# 테스트 발송
curl -X POST http://localhost:8000/api/v1/push/test ...
```

### 딥링크가 작동 안 됨

**Android**:
- AndroidManifest.xml에 Intent Filter 추가 필요
- 카카오톡 앱 설치 확인

**iOS**:
- Info.plist에 URL Scheme 추가 필요
- 카카오톡 앱 설치 확인

**Web**:
- 브라우저에서 카카오톡 프로토콜 지원 안 함
- 대안: 카카오톡 웹 URL 사용 (`https://pf.kakao.com/_ZeUTxl`)

---

## 부록

### API 엔드포인트 목록

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/v1/push/register` | FCM 토큰 등록 |
| GET | `/api/v1/push/tokens/{user_id}` | 사용자 토큰 조회 |
| DELETE | `/api/v1/push/tokens/{token_id}` | 토큰 삭제 |
| POST | `/api/v1/push/test` | 테스트 알림 전송 |

### 스케줄 목록

| 시간 | 프롬프트 | 메시지 |
|------|---------|--------|
| 10:00 | morning | "좋은 아침입니다! 어제 저녁은 무엇을 드셨나요?" |
| 15:00 | afternoon | "오후 시간입니다. 점심은 어떤 것을 드셨나요?" |
| 20:00 | evening | "하루를 마무리하며, 오늘 기억에 남는 일이 있나요?" |

---

**구현 완료!** 🎉

이제 Memory Garden 사용자들은 매일 3회 자동 푸시 알림을 받고,
알림을 클릭하면 카카오톡 채널로 자동 이동하여 AI와 자연스럽게 대화를 나눌 수 있습니다!
