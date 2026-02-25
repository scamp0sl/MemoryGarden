# config/prompts.py

QUESTION_GENERATION_PROMPTS = {
    "reminiscence": """
사용자의 과거 기억을 자연스럽게 이끌어내는 질문을 생성하세요.

## 컨텍스트
- 사용자 정보: {user_profile}
- 이전 대화: {previous_conversations}
- 계절: {current_season}

## 요구사항
1. 50-60대 시절 기억 유도 (청년기, 육아기)
2. 구체적인 감각 정보 포함 (냄새, 소리, 색깔)
3. 감정과 연결된 질문

## 출력 형식
질문: [생성된 질문]
후속 질문: [사용자가 대답하면 이어갈 질문]
""",
    
    "daily_episodic": """
오늘 또는 최근의 일화 기억을 확인하는 질문을 생성하세요.

## 컨텍스트
- 오늘 날짜: {today}
- 이전 기록: {today_events}
- 마지막 대화: {last_conversation}

## 요구사항
1. 시간적 단서 제공 ("오늘 점심", "어제 저녁")
2. 회상 후 재인 전략 (자유 회상 → 힌트 제공)
3. 이미지 업로드 유도

## 출력 형식
초기 질문: [개방형 질문]
재인 질문: [객관식 또는 힌트 포함 질문]
""",
    
    "naming": """
사물, 인물, 개념의 이름대기 능력을 평가하는 질문을 생성하세요.

## 컨텍스트
- 난이도: {difficulty}  # easy/medium/hard
- 카테고리: {category}  # 음식/동물/직업/가족 등

## 요구사항
1. 자연스러운 문맥 속 질문 ("손녀분 이름이 뭐였죠?")
2. 의미적 단서 제공 ("김치를 담그는 채소는?")
3. 음소적 단서 준비 ("'배'로 시작하는...")

## 출력 형식
질문: [자연스러운 질문]
의미 단서: [뜻으로 유도]
음소 단서: [첫 음절 힌트]
""",
    
    "temporal": """
시간적 지남력을 확인하는 질문을 생성하세요.

## 컨텍스트
- 오늘: {today}  # 2025-01-15 수요일
- 계절: {season}
- 최근 명절: {recent_holiday}

## 요구사항
1. 직접 질문 지양 ("오늘 무슨 요일인지 아세요?" ?)
2. 맥락 속 확인 ("내일 목요일에 병원 가시죠?") ?
3. 계절 감각 확인 ("요즘 날씨가 많이 추워졌죠?")

## 출력 형식
질문: [맥락 속 질문]
정답: {correct_answer}
허용 범위: {acceptable_answers}
"""
}

# config/prompts.py

ANALYSIS_PROMPTS = {
    "semantic_drift": """
다음 대화에서 의미적 표류(semantic drift)를 평가하세요.

## 입력
질문: {question}
사용자 응답: {user_response}

## 평가 기준
1. 관련성 (0-5점): 질문과 응답의 연관성
2. 주제 유지 (0-5점): 대화 주제를 일관되게 유지했는가
3. 논리성 (0-5점): 문장 간 인과관계가 명확한가

## 출력 형식 (JSON)
{{
  "relevance_score": 4,
  "topic_coherence_score": 3,
  "logical_flow_score": 5,
  "total_score": 80,  # 0-100 정규화
  "rationale": "사용자가 질문에 직접 답하지 않고 다른 주제로 이동함"
}}
""",
    
    "narrative_coherence": """
사용자 응답의 서사 일관성을 평가하세요.

## 입력
{user_response}

## 평가 기준
1. 5W1H 포함도: 누가, 언제, 어디서, 무엇을, 왜, 어떻게
2. 시간 순서: 사건 전개가 논리적 순서인가
3. 인과관계: 접속사 사용 ("그래서", "왜냐하면")
4. 반복성: 같은 내용을 불필요하게 반복하는가

## 출력 형식 (JSON)
{{
  "5w1h_coverage": ["who", "when", "what"],  # 포함된 요소
  "temporal_order_correct": true,
  "causal_markers_count": 2,
  "repetition_ratio": 0.1,
  "total_score": 75
}}
"""
}

# config/prompts.py

FACT_EXTRACTION_PROMPT = """
대화에서 저장할 가치가 있는 사실(fact)을 추출하세요.

## 입력
{conversation_history}

## 추출 대상
1. 전기적 사실 (Biographical Facts)
   - 불변: 이름, 생년월일, 출생지, 자녀 이름
   - 반불변: 거주지, 직업, 종교
   - 선호: 좋아하는 음식, 취미

2. 일화적 사실 (Episodic Facts)
   - 사건: "2025-01-15 점심에 된장찌개 먹음"
   - 감정: "딸과 통화해서 기분 좋음"
   - 인물: "손녀 이름은 지우"

## 카테고리 (반드시 아래 중 하나 사용)
- person: 인물
- place: 장소
- food: 음식 (meal, 식사 포함)
- event: 사건
- time: 시간
- emotion: 감정
- activity: 활동
- object: 사물
- health: 건강 상태

## 출력 형식 (JSON)
{{
  "biographical_facts": [
    {{
      "entity": "daughter_name",
      "value": "수진",
      "confidence": 0.95,
      "fact_type": "immutable"
    }}
  ],
  "episodic_facts": [
    {{
      "content": "2025-01-15 점심에 된장찌개와 김치, 멸치볶음 먹음",
      "timestamp": "2025-01-15T12:30:00Z",
      "category": "food",
      "confidence": 0.9
    }}
  ]
}}
"""

# ============================================
# NLP 분석 프롬프트
# ============================================

EMOTION_DETECTION_PROMPT = """
다음 텍스트에서 화자의 감정을 분석하세요.

## 입력
{text}

## 감정 카테고리
- joy (기쁨): 행복, 즐거움, 만족
- sadness (슬픔): 우울, 외로움, 그리움
- anger (분노): 짜증, 불만, 화남
- fear (두려움): 불안, 걱정, 두려움
- surprise (놀람): 놀라움, 의외
- neutral (중립): 감정 표현 없음

## 평가 기준
1. 명시적 감정 표현 (이모티콘, 감정 단어)
2. 암묵적 감정 표현 (어조, 문맥)
3. 강도 (0.0~1.0)
   - 0.0~0.3: 약함
   - 0.3~0.7: 보통
   - 0.7~1.0: 강함

## 출력 형식 (JSON)
{{
  "primary_emotion": "joy",
  "intensity": 0.8,
  "secondary_emotions": [
    {{"emotion": "surprise", "intensity": 0.3}}
  ],
  "keywords": ["기쁘다", "좋았다"],
  "rationale": "텍스트에서 긍정적인 감정 표현이 명확함"
}}
"""

KEYWORD_EXTRACTION_PROMPT = """
다음 텍스트에서 핵심 키워드와 주제를 추출하세요.

## 입력
{text}

## 추출 기준
1. 명사 우선 (인물, 장소, 사물, 개념)
2. 중요도 기준:
   - 빈도 (반복 출현)
   - 위치 (문장 앞부분)
   - 문맥적 중요성
3. 최대 10개 키워드

## 출력 형식 (JSON)
{{
  "keywords": [
    {{
      "word": "된장찌개",
      "importance": 0.9,
      "category": "food",
      "context": "점심 메뉴"
    }},
    {{
      "word": "딸",
      "importance": 0.85,
      "category": "person",
      "context": "가족 관계"
    }}
  ],
  "main_topic": "식사 및 가족",
  "sub_topics": ["음식", "일상"]
}}
"""

SENTIMENT_ANALYSIS_PROMPT = """
다음 텍스트의 감정 극성(sentiment)을 분석하세요.

## 입력
{text}

## 극성 분류
- positive (긍정): 좋음, 만족, 행복
- negative (부정): 나쁨, 불만, 슬픔
- neutral (중립): 감정 없음, 객관적 서술

## 출력 형식 (JSON)
{{
  "sentiment": "positive",
  "score": 0.75,
  "confidence": 0.9
}}
"""
