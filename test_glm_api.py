import urllib.request
import json

API_KEY = "367dc07225e847bab59fd32e91df5e82.qAvCGt5g1bOdvKnU"
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

models = [
    "glm-4-plus", "glm-4-0520", "glm-4-flash", "glm-4-9b", 
    "glm-4-air", "glm-4-air-0111", "glm-4-flash-0111", "glm-4v",
    "glm-4-alltools", "glm-4-assistant"
]
auth = f"Bearer {API_KEY}"

for model in models:
    print(f"Testing model: {model}")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
    }
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(GLM_API_URL, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': auth
    })

    try:
        with urllib.request.urlopen(request) as response:
            print(f"SUCCESS for {model}: {response.read().decode('utf-8')}")
            exit(0)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"FAILED for {model}: HTTP {e.code} - {body}")
    except Exception as e:
        print(f"Error for {model}: {e}")
