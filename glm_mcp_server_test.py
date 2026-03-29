import sys
import json
import urllib.request

# 발급받은 실제 Zhipu API 키를 여기에 입력하세요
API_KEY = "367dc07225e847bab59fd32e91df5e82.qAvCGt5g1bOdvKnU"
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def process_request(req):
    method = req.get("method")
    
    # 1. 초기화 (나는 '도구'를 제공하는 서버라고 선언)
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "glm-cloud-server", "version": "1.0.0"}
        }
        
    if method == "notifications/initialized":
        return None
        
    # 2. 도구 목록 제공 (안티그래비티가 "너 무슨 도구 있어?" 하고 물어볼 때)
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "ask_glm_model",
                    "description": "Send a text prompt to Zhipu AI's GLM-4 model and get the generated response. Useful for complex reasoning or alternative perspectives.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "The message or question to send to the GLM model"}
                        },
                        "required": ["prompt"]
                    }
                }
            ]
        }
        
    # 3. 도구 실행 (채팅창에서 GLM 호출을 지시했을 때 실제 실행되는 부분)
    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name == "ask_glm_model":
            user_prompt = tool_args.get("prompt", "")
            
            payload = {
                "model": "glm-4-plus",
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": 0.7
            }
            data = json.dumps(payload).encode('utf-8')
            request = urllib.request.Request(GLM_API_URL, data=data, headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}'
            })
            
            try:
                with urllib.request.urlopen(request) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    glm_reply = result["choices"][0]["message"]["content"]
                    return {"content": [{"type": "text", "text": glm_reply}]}
            except urllib.error.HTTPError as e:
                try:
                    error_body = e.read().decode('utf-8')
                    return {"content": [{"type": "text", "text": f"API Error {e.code}: {error_body}"}]}
                except:
                    return {"content": [{"type": "text", "text": f"HTTP Error {e.code}: {e.reason}"}]}
            except Exception as e:
                return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    return {} # 알 수 없는 요청

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            result = process_request(req)
            
            if result is None: continue
                
            response = {"jsonrpc": "2.0", "id": req_id}
            if "error" in result:
                response["error"] = {"code": -32603, "message": result["error"]}
            else:
                response["result"] = result
                
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

if __name__ == "__main__":
    main()
