# 친구톡 API 엔드포인트 수정 가이드

## 🔴 현재 문제

현재 코드에서 사용하는 엔드포인트가 잘못되어 404 에러 발생:
```
https://kapi.kakao.com/v1/api/direct/send  ← 존재하지 않는 엔드포인트
```

## ✅ 올바른 엔드포인트

### **방법 1: 카카오톡 채널 메시지 API (권장)**

```python
# services/kakao_client.py 수정

async def _send_real_friend_talk(self, user_key: str, message: str, retry_count: int):
    """실제 친구톡 전송"""

    endpoint = f"{self.base_url}/v1/api/talk/friends/message/default/send"

    headers = {
        "Authorization": f"KakaoAK {self.admin_key}",  # REST API 키가 아닌 Admin 키 사용!
        "Content-Type": "application/json"
    }

    payload = {
        "receiver_uuids": [user_key],
        "template_object": {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://n8n.softline.co.kr",
                "mobile_web_url": "https://n8n.softline.co.kr"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        return response.json()
```

### **방법 2: 나에게 보내기 API (테스트용)**

```python
# 테스트용 - 자기 자신에게만 전송 가능

async def send_to_me(self, message: str):
    """나에게 보내기 (테스트용)"""

    endpoint = f"{self.base_url}/v2/api/talk/memo/default/send"

    headers = {
        "Authorization": f"Bearer {self.access_token}",  # 사용자 액세스 토큰 필요!
        "Content-Type": "application/json"
    }

    payload = {
        "template_object": {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://n8n.softline.co.kr"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        return response.json()
```

## 🔑 필요한 권한

### **카카오 디벨로퍼 콘솔 설정**

1. [https://developers.kakao.com/console/app](https://developers.kakao.com/console/app) 접속
2. 앱 선택
3. **제품 설정 > 카카오톡 채널**
   - 채널 연결
   - 채널 ID: `_tDPzX`
4. **제품 설정 > 카카오톡 메시지**
   - 활성화 ON
   - 메시지 전송 권한 요청
5. **앱 키 확인**
   - REST API 키: `dbd781ee1536f158091e578abe27e1e3`
   - Admin 키: `b20e346dc40fc7e121c5dda62b9b4194`

## 📋 API 스펙 비교

| 기능 | 엔드포인트 | 인증 | 대상 |
|------|-----------|------|------|
| 친구에게 메시지 | /v1/api/talk/friends/message/default/send | Admin Key | 채널 친구 |
| 나에게 보내기 | /v2/api/talk/memo/default/send | Access Token | 자기 자신 |
| ~~직접 전송~~ | ~~/v1/api/direct/send~~ | ❌ 존재 안 함 | - |

## ⚠️ 중요 사항

### **1. Admin 키 사용**
```python
headers = {
    "Authorization": f"KakaoAK {settings.KAKAO_ADMIN_KEY}",  # Admin 키!
    # ❌ f"KakaoAK {settings.KAKAO_REST_API_KEY}"  # REST API 키 아님!
}
```

### **2. receiver_uuids vs user_id**
- `receiver_uuids`: 배열 형식 `["AkBz5V9CUoEn"]`
- 단일 사용자도 배열로 전송

### **3. template_object 구조**
```json
{
  "object_type": "text",  # 필수
  "text": "메시지 내용",  # 필수
  "link": {  # 선택
    "web_url": "https://...",
    "mobile_web_url": "https://..."
  },
  "button_title": "자세히 보기"  # 선택
}
```

## 🧪 테스트 방법

### **1. 나에게 보내기로 먼저 테스트**

```bash
# 카카오 디벨로퍼 콘솔에서 "나에게 보내기" 테스트
https://developers.kakao.com/tool/rest-api/open/post/v2-api-talk-memo-default-send
```

### **2. 친구에게 메시지 테스트**

```bash
# plusfriendUserKey 사용
curl -X POST "https://kapi.kakao.com/v1/api/talk/friends/message/default/send" \
  -H "Authorization: KakaoAK b20e346dc40fc7e121c5dda62b9b4194" \
  -H "Content-Type: application/json" \
  -d '{
    "receiver_uuids": ["AkBz5V9CUoEn"],
    "template_object": {
      "object_type": "text",
      "text": "Memory Garden 테스트 메시지입니다! 🌱",
      "link": {
        "web_url": "https://n8n.softline.co.kr"
      }
    }
  }'
```

## 🎯 다음 단계

1. `services/kakao_client.py` 파일 수정
2. 엔드포인트 변경
3. Admin 키 사용 확인
4. template_object 형식 적용
5. 테스트 실행

---

생성일: 2026-02-20
작성자: Memory Garden DevOps Team
