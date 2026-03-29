# 📊 Analysis Module Guide

> **core/analysis/** 디렉토리 완전 가이드
> 감정 분석, 정원 매핑, 리포트 생성 모듈 사용법

---

## 📚 목차

1. [개요](#1-개요)
2. [EmotionAnalyzer](#2-emotionanalyzer)
3. [GardenMapper](#3-gardenmapper)
4. [ReportGenerator](#4-reportgenerator)
5. [실전 통합 예시](#5-실전-통합-예시)
6. [API 레퍼런스](#6-api-레퍼런스)

---

## 1. 개요

### 1.1 모듈 구조

```
core/analysis/
├── emotion_analyzer.py     # 감정 트렌드 분석
├── garden_mapper.py        # 정원 시각화 매핑
├── report_generator.py     # 주간/월간 리포트
└── __init__.py            # 모듈 export
```

### 1.2 주요 기능

| 모듈 | 주요 기능 | 출력 |
|------|----------|------|
| **EmotionAnalyzer** | 감정 추이 분석, 패턴 감지 | EmotionTrendAnalysis |
| **GardenMapper** | 게이미피케이션, 정원 상태 | GardenVisualizationData |
| **ReportGenerator** | 주간/월간 요약 리포트 | WeeklyReport, MonthlyReport |

### 1.3 핵심 게임 메카닉 (SPEC.md 2.2.1)

```python
# 정원 성장 규칙
🌸 꽃 심기: 1회 대화 = 1송이
🦋 나비 방문: 3일 연속 = 나비 1마리
🌳 정원 확장: 7일 연속 = 레벨 업
🏅 계절 뱃지: 30일 참여 = 뱃지 획득
```

---

## 2. EmotionAnalyzer

### 2.1 개요

일간/주간/월간 감정 변화를 추적하고 패턴을 감지합니다.

**주요 기능:**
- 감정 분포 계산 (joy, sadness, anger 등)
- 추세 판정 (improving, stable, declining, volatile)
- 패턴 인식 (consistent, daily_cycle, weekly_cycle, random)
- 두 기간 비교

### 2.2 기본 사용법

```python
from core.analysis import EmotionAnalyzer, EmotionTrend

# 1. 초기화
analyzer = EmotionAnalyzer()

# 2. 감정 이력 준비 (TimescaleDB에서 조회)
emotion_history = [
    {
        "emotion": "joy",
        "intensity": 0.8,
        "timestamp": "2025-02-03T10:00:00Z"
    },
    {
        "emotion": "joy",
        "intensity": 0.7,
        "timestamp": "2025-02-04T10:00:00Z"
    },
    # ... more entries
]

# 3. 주간 트렌드 분석
result = await analyzer.analyze_trend(
    user_id="user123",
    emotion_history=emotion_history,
    period="weekly"
)

# 4. 결과 활용
print(f"Dominant emotion: {result.dominant_emotion}")
print(f"Trend: {result.trend.value}")  # improving/stable/declining/volatile
print(f"Volatility: {result.volatility:.2f}")
print(f"Positive ratio: {result.positive_ratio:.2%}")

# 5. 감정 분포
for emotion, ratio in result.emotion_distribution.items():
    print(f"{emotion}: {ratio:.2%}")
```

### 2.3 출력 모델

```python
class EmotionTrendAnalysis(BaseModel):
    """감정 트렌드 분석 결과"""
    user_id: str
    period: str  # "daily", "weekly", "monthly"

    # 감정 분포
    emotion_distribution: Dict[str, float]  # {"joy": 0.6, "sadness": 0.2, ...}
    dominant_emotion: str  # "joy"

    # 추세
    trend: EmotionTrend  # IMPROVING/STABLE/DECLINING/VOLATILE
    pattern: EmotionPattern  # CONSISTENT/DAILY_CYCLE/WEEKLY_CYCLE/RANDOM

    # 지표
    volatility: float  # 0.0~1.0
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float

    # 메타
    start_date: datetime
    end_date: datetime
    total_entries: int
```

### 2.4 기간 비교

```python
# 지난주 vs 이번주 비교
comparison = await analyzer.compare_periods(
    user_id="user123",
    period1_history=last_week_emotions,
    period2_history=this_week_emotions
)

print(f"Change: {comparison['change']}")  # "improved", "worsened", "stable"
print(f"Positive change: {comparison['positive_change']:.2%}")
```

---

## 3. GardenMapper

### 3.1 개요

MCDI 점수와 위험도를 정원 시각화 데이터로 변환합니다.

**주요 기능:**
- 대화 횟수 → 꽃 개수
- 연속 일수 → 나비, 정원 레벨
- 위험도 → 날씨 상태
- 업적 달성 체크

### 3.2 기본 사용법

```python
from core.analysis import GardenMapper, RiskLevel, GardenWeather

# 1. 초기화
mapper = GardenMapper()

# 2. 첫 방문: 기본 정원 생성
garden_status = await mapper.get_garden_status("user123")
print(f"Flowers: {garden_status.flower_count}")  # 0
print(f"Level: {garden_status.garden_level}")    # 1

# 3. 대화 완료 시 정원 업데이트
update = await mapper.update_garden_status(
    user_id="user123",
    mcdi_score=75.0,
    risk_level="GREEN",
    emotion="joy"
)

# 4. 업데이트 결과 확인
print(f"New flowers: {update.current_status.flower_count}")  # +1
print(f"Consecutive days: {update.current_status.consecutive_days}")
print(f"Level up: {update.level_up}")  # False (7일 필요)
print(f"Achievements: {update.achievements_unlocked}")  # ["first_flower"]

# 5. 업적 메시지 표시
if update.current_status.achievement_message:
    print(update.current_status.achievement_message)  # "🌸 첫 번째 꽃이 피었어요!"
```

### 3.3 위험도 → 날씨 매핑

```python
# SPEC.md 2.1.3 기준
risk_to_weather = {
    "GREEN": GardenWeather.SUNNY,    # ☀️ "정원이 건강하게 자라고 있어요!"
    "YELLOW": GardenWeather.CLOUDY,  # ☁️ "정원에 구름이 조금 낀 것 같아요"
    "ORANGE": GardenWeather.RAINY,   # 🌧️ "정원에 비가 내리고 있어요"
    "RED": GardenWeather.STORMY      # ⛈️ "정원에 폭풍이 불고 있어요"
}
```

### 3.4 업적 시스템

```python
# 자동으로 체크되는 업적들
achievements = {
    "first_flower": "🌸 첫 번째 꽃이 피었어요!",
    "butterfly_visit": "🦋 나비가 날아왔어요!",  # 3일 연속
    "garden_expansion": "🌳 정원이 확장되었어요!",  # 7일 연속
    "flowers_10": "🌺 꽃 10송이 달성!",
    "flowers_50": "🌻 꽃 50송이 달성!",
    "streak_7days": "⭐ 7일 연속 참여!",
    "streak_30days": "🏅 한 달 연속 참여!",
}
```

### 3.5 출력 모델

```python
class GardenVisualizationData(BaseModel):
    """정원 시각화 데이터 (프론트엔드용)"""
    user_id: str

    # 게임 메카닉
    flower_count: int  # 총 꽃 개수
    butterfly_count: int  # 나비 방문 횟수
    garden_level: int  # 1~10
    consecutive_days: int  # 연속 참여 일수
    total_conversations: int

    # 정원 상태
    weather: GardenWeather  # sunny/cloudy/rainy/stormy
    season_badge: Optional[SeasonBadge]  # spring/summer/autumn/winter

    # 메시지
    status_message: str  # "정원이 건강하게 자라고 있어요! ☀️"
    achievement_message: Optional[str]  # "🌸 첫 번째 꽃이 피었어요!"
    next_milestone: str  # "🦋 2일 더 참여하면 나비가 날아와요!"
```

---

## 4. ReportGenerator

### 4.1 개요

주간/월간 감정 요약 및 성장 지표 리포트를 생성합니다.

**주요 기능:**
- 주간 리포트 (보호자용)
- 월간 리포트 (의료기관용)
- 인지 기능 지표 계산
- 참여도 지표 계산
- 권장 조치 생성

### 4.2 주간 리포트 (보호자용)

```python
from core.analysis import ReportGenerator, ReportType

# 1. 초기화
generator = ReportGenerator()

# 2. 주간 리포트 생성
report = await generator.generate_weekly_report(
    user_id="user123",
    user_name="홍길동",
    report_type=ReportType.GUARDIAN  # 보호자용 친근한 표현
)

# 3. 인지 기능 지표
print(f"평균 MCDI: {report.cognitive_metrics.mcdi_average}")
print(f"추세: {report.cognitive_metrics.mcdi_trend}")  # improving/stable/declining
print(f"변화율: {report.cognitive_metrics.slope}/week")

# 4. 참여도 지표
print(f"총 대화: {report.engagement_metrics.total_conversations}회")
print(f"일평균: {report.engagement_metrics.conversation_per_day}회")
print(f"연속 일수: {report.engagement_metrics.consecutive_days}일")

# 5. 성장 지표
print(f"꽃: {report.growth_metrics.flowers_earned}송이")
print(f"나비: {report.growth_metrics.butterflies_earned}마리")
print(f"정원 레벨: {report.growth_metrics.garden_level}")

# 6. 관찰 사항 (보호자용 친근한 표현)
for observation in report.observations:
    print(f"📝 {observation}")
# "이번 주 주된 감정은 'joy' 이었어요"
# "감정 상태가 점점 좋아지고 있어요 😊"

# 7. 우려 사항
for concern in report.concerns:
    print(f"⚠️ {concern}")
# "인지 기능 점수가 빠르게 낮아지고 있어요"

# 8. 권장 조치
for recommendation in report.recommendations:
    print(f"💡 {recommendation}")
# "매일 규칙적인 시간에 대화해보세요"
```

### 4.3 월간 리포트 (의료기관용)

```python
# 1. 월간 리포트 생성 (전문 용어)
report = await generator.generate_monthly_report(
    user_id="user123",
    user_name="홍길동",
    report_type=ReportType.CLINICAL  # 의료기관용
)

# 2. 주간 요약 포함
print(f"주간 리포트 수: {len(report.weekly_summaries)}")

# 3. 상세 관찰 (임상 데이터)
print(report.detailed_observations)
"""
## Cognitive Function
- Average MCDI: 75.5
- Trend: stable (slope: -0.2/week)

## Emotional State
- Dominant emotion: joy
- Trend: stable
- Volatility: 0.15

## Engagement
- Total conversations: 42
- Average per day: 2.1
- Consecutive days: 15
"""

# 4. 임상 요약
print(report.clinical_summary)
"""
Patient demonstrates:
- MCDI score: 75.5 (stable)
- Emotional state: stable
- Pattern: consistent

Clinical interpretation:
Normal cognitive function maintained.
"""

# 5. 의료 권장 조치
for rec in report.medical_recommendations:
    print(f"🏥 {rec}")
# "Continue routine monitoring"
# "Consider mood disorder screening" (volatility 높을 때)
```

### 4.4 출력 모델

```python
class WeeklyReport(BaseModel):
    """주간 리포트"""
    user_id: str
    user_name: str
    period_start: datetime
    period_end: datetime
    report_type: ReportType  # GUARDIAN/CLINICAL

    # 분석 결과
    emotion_analysis: EmotionTrendAnalysis
    cognitive_metrics: CognitiveMetrics
    engagement_metrics: EngagementMetrics
    growth_metrics: GrowthMetrics

    # 관찰 및 권장
    observations: List[str]  # 보호자용 친근한 표현
    concerns: List[str]      # 우려 사항
    recommendations: List[str]  # 권장 조치

    # 위험도
    current_risk_level: str
    risk_change: Optional[str]  # "improved", "worsened", "stable"

class CognitiveMetrics(BaseModel):
    """인지 기능 지표"""
    mcdi_average: float
    mcdi_min: float
    mcdi_max: float
    mcdi_trend: str  # "improving", "stable", "declining"
    slope: float     # 주간 변화율
```

---

## 5. 실전 통합 예시

### 5.1 대화 완료 시 통합 플로우

```python
from core.analysis import EmotionAnalyzer, GardenMapper, ReportGenerator

async def process_conversation_complete(
    user_id: str,
    message: str,
    response: str,
    analysis_result: Dict[str, Any]
):
    """대화 완료 후 분석 및 정원 업데이트"""

    # 1. 감정 분석 (실시간 추가)
    emotion_analyzer = EmotionAnalyzer()

    # 현재 감정 저장 (TimescaleDB)
    await save_emotion_to_db(
        user_id=user_id,
        emotion=analysis_result["emotion"],
        intensity=analysis_result["emotion_intensity"],
        timestamp=datetime.now()
    )

    # 2. 정원 상태 업데이트
    mapper = GardenMapper()
    garden_update = await mapper.update_garden_status(
        user_id=user_id,
        mcdi_score=analysis_result["mcdi_score"],
        risk_level=analysis_result["risk_level"],
        emotion=analysis_result["emotion"]
    )

    # 3. 업적 알림 (카카오톡)
    if garden_update.achievements_unlocked:
        achievement_msg = garden_update.current_status.achievement_message
        await send_kakao_message(user_id, achievement_msg)

    # 4. 레벨 업 축하
    if garden_update.level_up:
        await send_kakao_message(
            user_id,
            f"🎉 정원이 레벨 {garden_update.current_status.garden_level}로 확장되었어요!"
        )

    # 5. 주간 리포트 체크 (매주 일요일)
    if datetime.now().weekday() == 6:  # 일요일
        report_gen = ReportGenerator()
        report = await report_gen.generate_weekly_report(
            user_id=user_id,
            user_name=user_name,
            report_type=ReportType.GUARDIAN
        )

        # 보호자에게 전송
        await send_guardian_report(user_id, report)

    return garden_update
```

### 5.2 보호자 대시보드 데이터

```python
async def get_guardian_dashboard_data(user_id: str):
    """보호자 대시보드용 데이터 조합"""

    # 1. 정원 상태
    mapper = GardenMapper()
    garden_status = await mapper.get_garden_status(user_id)

    # 2. 최근 감정 트렌드
    emotion_analyzer = EmotionAnalyzer()
    emotion_history = await get_emotion_history(user_id, days=7)
    emotion_trend = await emotion_analyzer.analyze_trend(
        user_id=user_id,
        emotion_history=emotion_history,
        period="weekly"
    )

    # 3. 주간 리포트
    report_gen = ReportGenerator()
    weekly_report = await report_gen.generate_weekly_report(
        user_id=user_id,
        user_name=user_name,
        report_type=ReportType.GUARDIAN
    )

    # 4. 통합 데이터 반환
    return {
        "garden": {
            "flower_count": garden_status.flower_count,
            "butterfly_count": garden_status.butterfly_count,
            "level": garden_status.garden_level,
            "weather": garden_status.weather.value,
            "status_message": garden_status.status_message,
            "next_milestone": garden_status.next_milestone
        },
        "emotion": {
            "dominant_emotion": emotion_trend.dominant_emotion,
            "trend": emotion_trend.trend.value,
            "positive_ratio": emotion_trend.positive_ratio,
            "distribution": emotion_trend.emotion_distribution
        },
        "cognitive": {
            "mcdi_average": weekly_report.cognitive_metrics.mcdi_average,
            "mcdi_trend": weekly_report.cognitive_metrics.mcdi_trend,
            "risk_level": weekly_report.current_risk_level
        },
        "engagement": {
            "total_conversations": weekly_report.engagement_metrics.total_conversations,
            "consecutive_days": weekly_report.engagement_metrics.consecutive_days,
            "conversation_per_day": weekly_report.engagement_metrics.conversation_per_day
        },
        "observations": weekly_report.observations,
        "concerns": weekly_report.concerns,
        "recommendations": weekly_report.recommendations
    }
```

---

## 6. API 레퍼런스

### 6.1 EmotionAnalyzer

```python
class EmotionAnalyzer:
    async def analyze_trend(
        self,
        user_id: str,
        emotion_history: List[Dict[str, Any]],
        period: str = "weekly"  # "daily", "weekly", "monthly"
    ) -> EmotionTrendAnalysis

    async def compare_periods(
        self,
        user_id: str,
        period1_history: List[Dict[str, Any]],
        period2_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]
```

### 6.2 GardenMapper

```python
class GardenMapper:
    async def get_garden_status(
        self,
        user_id: str
    ) -> GardenVisualizationData

    async def update_garden_status(
        self,
        user_id: str,
        mcdi_score: Optional[float] = None,
        risk_level: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> GardenStatusUpdate

    async def reset_garden(
        self,
        user_id: str
    ) -> None  # 테스트/관리자용
```

### 6.3 ReportGenerator

```python
class ReportGenerator:
    async def generate_weekly_report(
        self,
        user_id: str,
        user_name: str,
        period: str = "last_week",
        report_type: ReportType = ReportType.GUARDIAN
    ) -> WeeklyReport

    async def generate_monthly_report(
        self,
        user_id: str,
        user_name: str,
        report_type: ReportType = ReportType.CLINICAL
    ) -> MonthlyReport
```

---

## 📌 다음 단계

1. ✅ **완료:** EmotionAnalyzer, GardenMapper, ReportGenerator 구현
2. **TODO:** TimescaleDB integration for emotion/MCDI history
3. **TODO:** PostgreSQL integration for user/conversation data
4. **TODO:** API 엔드포인트 추가 (`/api/v1/garden`, `/api/v1/reports`)
5. **TODO:** core/workflow/message_processor.py 통합
6. **TODO:** 프론트엔드 시각화 (정원 렌더링)

---

**작성일:** 2025-02-10
**버전:** 1.0.0
**작성자:** Memory Garden Team
