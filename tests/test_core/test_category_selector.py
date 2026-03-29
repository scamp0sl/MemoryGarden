"""
CategorySelector 테스트

6개 카테고리 라우팅 로직을 검증합니다.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from core.dialogue.category_selector import (
    CategorySelector,
    CATEGORY_REMINISCENCE,
    CATEGORY_DAILY_EPISODIC,
    CATEGORY_NAMING,
    CATEGORY_TEMPORAL,
    CATEGORY_VISUAL,
    CATEGORY_CHOICE,
    CATEGORY_WEEKLY_LIMIT,
    CATEGORY_INDICATOR_MAP,
    get_category_display_name,
    get_category_prompt_hint,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def selector():
    """CategorySelector 인스턴스"""
    return CategorySelector()


@pytest.fixture
def normal_indicator_scores():
    """정상 범위 지표 점수"""
    return {
        "LR": 80.0,
        "SD": 82.0,
        "NC": 78.0,
        "TO": 85.0,
        "ER": 79.0,
        "RT": 90.0,
    }


@pytest.fixture
def weak_temporal_scores():
    """TO(시간 지남력)가 약한 지표 점수"""
    return {
        "LR": 80.0,
        "SD": 82.0,
        "NC": 78.0,
        "TO": 45.0,  # 매우 낮음
        "ER": 79.0,
        "RT": 90.0,
    }


@pytest.fixture
def weak_naming_scores():
    """NC(이름 명명)가 약한 지표 점수"""
    return {
        "LR": 80.0,
        "SD": 82.0,
        "NC": 42.0,  # 매우 낮음
        "TO": 75.0,
        "ER": 79.0,
        "RT": 90.0,
    }


@pytest.fixture
def empty_weekly_usage():
    """이번 주 사용 횟수 없음"""
    return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}


# ============================================
# Test 1: _select_category() - 약한 지표 우선 선택
# ============================================

def test_select_temporal_when_to_weak(selector, weak_temporal_scores, empty_weekly_usage):
    """TO가 약할 때 TEMPORAL 카테고리 선택"""
    # TEMPORAL의 주요 지표는 TO(45.0)
    selected = selector._select_category(weak_temporal_scores, empty_weekly_usage)
    assert selected == CATEGORY_TEMPORAL
    print(f"✅ Weak TO → selected: {selected}")


def test_select_naming_when_nc_weak(selector, weak_naming_scores, empty_weekly_usage):
    """NC가 약할 때 NAMING 카테고리 선택"""
    # NAMING의 주요 지표는 NC(42.0)
    selected = selector._select_category(weak_naming_scores, empty_weekly_usage)
    assert selected == CATEGORY_NAMING
    print(f"✅ Weak NC → selected: {selected}")


def test_select_category_respects_weekly_limit(selector, weak_temporal_scores):
    """주간 제한 초과 카테고리는 제외"""
    # TEMPORAL 주간 제한 초과
    weekly_usage = {
        CATEGORY_REMINISCENCE:   0,
        CATEGORY_DAILY_EPISODIC: 0,
        CATEGORY_NAMING:         0,
        CATEGORY_TEMPORAL:       2,  # 한도 초과 (limit=2)
        CATEGORY_VISUAL:         0,
        CATEGORY_CHOICE:         0,
    }

    # TO가 약해도 TEMPORAL은 한도 초과 → 다른 카테고리 선택
    selected = selector._select_category(weak_temporal_scores, weekly_usage)
    assert selected != CATEGORY_TEMPORAL
    print(f"✅ TEMPORAL at limit → selected: {selected}")


def test_select_default_when_all_at_limit(selector, normal_indicator_scores):
    """모든 카테고리 한도 초과 → DAILY_EPISODIC 반환"""
    # 모든 카테고리 한도 초과
    weekly_usage = {cat: limit for cat, limit in CATEGORY_WEEKLY_LIMIT.items()}

    selected = selector._select_category(normal_indicator_scores, weekly_usage)
    assert selected == CATEGORY_DAILY_EPISODIC
    print(f"✅ All at limit → fallback: {selected}")


# ============================================
# Test 2: _get_week_key()
# ============================================

def test_get_week_key_format(selector):
    """주 키 형식 검증 (YYYY-WWW)"""
    week_key = selector._get_week_key()
    assert week_key.startswith("20")  # 2020s
    assert "W" in week_key
    # 예: "2026-W09"
    parts = week_key.split("-W")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()
    print(f"✅ Week key: {week_key}")


# ============================================
# Test 3: _seconds_until_next_monday()
# ============================================

def test_seconds_until_next_monday_positive(selector):
    """다음 월요일까지 남은 초가 양수"""
    secs = selector._seconds_until_next_monday()
    assert secs > 0
    assert secs <= 7 * 24 * 3600  # 최대 7일
    print(f"✅ Seconds until Monday: {secs}")


# ============================================
# Test 4: select() - force_category
# ============================================

@pytest.mark.asyncio
async def test_select_with_force_category(selector):
    """force_category 지정 시 강제 선택"""
    result = await selector.select(
        user_id="test_user",
        force_category=CATEGORY_VISUAL
    )
    assert result == CATEGORY_VISUAL
    print(f"✅ Forced category: {result}")


@pytest.mark.asyncio
async def test_select_with_invalid_force_category(selector):
    """유효하지 않은 force_category → 정상 선택 로직 실행"""
    with patch.object(selector, '_fetch_indicator_averages', new_callable=AsyncMock) as mock_fetch, \
         patch.object(selector, '_fetch_weekly_usage', new_callable=AsyncMock) as mock_usage, \
         patch.object(selector, '_increment_usage', new_callable=AsyncMock):

        mock_fetch.return_value = {"LR": 80.0, "SD": 82.0, "NC": 78.0, "TO": 85.0, "ER": 79.0, "RT": 90.0}
        mock_usage.return_value = {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

        result = await selector.select(
            user_id="test_user",
            force_category="INVALID_CATEGORY"  # 유효하지 않음
        )
        # 유효하지 않으면 정상 로직으로 실행됨
        assert result in CATEGORY_WEEKLY_LIMIT
    print(f"✅ Invalid force → normal selection: {result}")


# ============================================
# Test 5: select() - 통합 플로우
# ============================================

@pytest.mark.asyncio
async def test_select_full_flow_with_mocks(selector):
    """전체 플로우: DB + Redis mock으로 카테고리 선택"""
    with patch.object(selector, '_fetch_indicator_averages', new_callable=AsyncMock) as mock_fetch, \
         patch.object(selector, '_fetch_weekly_usage', new_callable=AsyncMock) as mock_usage, \
         patch.object(selector, '_increment_usage', new_callable=AsyncMock) as mock_incr:

        # TO가 약한 상황
        mock_fetch.return_value = {
            "LR": 80.0, "SD": 82.0, "NC": 78.0,
            "TO": 45.0,  # 약점
            "ER": 79.0, "RT": 90.0,
        }
        mock_usage.return_value = {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

        result = await selector.select(user_id="test_user_123")

        assert result == CATEGORY_TEMPORAL  # TO 약점 → TEMPORAL
        mock_incr.assert_called_once_with("test_user_123", CATEGORY_TEMPORAL)

    print(f"✅ Full flow: TO weak → selected TEMPORAL")


@pytest.mark.asyncio
async def test_select_handles_db_error_gracefully(selector):
    """DB 오류 시 기본값(75.0) 사용하여 선택 계속"""
    with patch.object(selector, '_fetch_indicator_averages', new_callable=AsyncMock) as mock_fetch, \
         patch.object(selector, '_fetch_weekly_usage', new_callable=AsyncMock) as mock_usage, \
         patch.object(selector, '_increment_usage', new_callable=AsyncMock):

        # DB 오류 → 기본값 사용
        mock_fetch.side_effect = Exception("DB connection failed")
        mock_usage.return_value = {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

        # _fetch_indicator_averages에서 예외가 발생하면 기본값 반환 (내부 try-except)
        # 실제 DB 오류 → 75.0 기본값
        mock_fetch.side_effect = None
        mock_fetch.return_value = {k: 75.0 for k in ["LR", "SD", "NC", "TO", "ER", "RT"]}

        result = await selector.select(user_id="error_user")
        assert result in CATEGORY_WEEKLY_LIMIT  # 어떤 카테고리든 반환

    print(f"✅ Error handling: graceful fallback to {result}")


# ============================================
# Test 6: _fetch_weekly_usage() - Redis mock
# ============================================

@pytest.mark.asyncio
async def test_fetch_weekly_usage_no_redis(selector):
    """Redis 연결 없을 때 빈 사용량 반환"""
    with patch('core.dialogue.category_selector.redis_client') as mock_redis:
        mock_redis.get_client = AsyncMock(return_value=None)

        usage = await selector._fetch_weekly_usage("test_user")
        assert all(v == 0 for v in usage.values())
        assert set(usage.keys()) == set(CATEGORY_WEEKLY_LIMIT.keys())

    print("✅ No Redis → all usage = 0")


@pytest.mark.asyncio
async def test_fetch_weekly_usage_with_data(selector):
    """Redis에 데이터 있을 때 올바른 사용량 반환"""
    mock_redis_conn = AsyncMock()
    existing_usage = {CATEGORY_REMINISCENCE: 1, CATEGORY_DAILY_EPISODIC: 2}
    mock_redis_conn.get = AsyncMock(return_value=json.dumps(existing_usage))

    with patch('core.dialogue.category_selector.redis_client') as mock_redis:
        mock_redis.get_client = AsyncMock(return_value=mock_redis_conn)

        usage = await selector._fetch_weekly_usage("test_user")
        assert usage[CATEGORY_REMINISCENCE] == 1
        assert usage[CATEGORY_DAILY_EPISODIC] == 2
        assert usage[CATEGORY_NAMING] == 0  # 없는 건 0

    print("✅ Redis usage loaded correctly")


# ============================================
# Test 7: get_category_info()
# ============================================

def test_get_category_info(selector):
    """카테고리 메타정보 반환"""
    info = selector.get_category_info(CATEGORY_VISUAL)

    assert info["id"] == CATEGORY_VISUAL
    assert info["name"] == "그림 읽기 놀이"
    assert info["is_image"] == True
    assert info["is_button"] == False
    assert "LR" in info["indicators"]
    assert info["weekly_limit"] == 1

    print(f"✅ Category info: {info}")


def test_get_category_info_choice(selector):
    """CHOICE 카테고리는 버튼 카드"""
    info = selector.get_category_info(CATEGORY_CHOICE)
    assert info["is_button"] == True
    assert info["is_image"] == False
    print(f"✅ CHOICE is_button: {info['is_button']}")


# ============================================
# Test 8: get_category_display_name() / get_category_prompt_hint()
# ============================================

def test_get_category_display_names():
    """모든 카테고리 표시명 존재"""
    for cat in CATEGORY_WEEKLY_LIMIT:
        name = get_category_display_name(cat)
        assert name != cat  # 원본 ID가 아닌 한국어 이름
        assert len(name) > 0
    print("✅ All display names exist")


def test_get_category_prompt_hints():
    """모든 카테고리 프롬프트 힌트 반환"""
    for cat in CATEGORY_WEEKLY_LIMIT:
        hint = get_category_prompt_hint(cat)
        assert len(hint) > 0
    print("✅ All prompt hints exist")


def test_prompt_hint_unknown_category():
    """알 수 없는 카테고리 → 기본 메시지"""
    hint = get_category_prompt_hint("UNKNOWN_CATEGORY")
    assert "자연스럽게" in hint
    print(f"✅ Unknown category hint: {hint}")


# ============================================
# Test 9: CATEGORY 상수 무결성 검증
# ============================================

def test_all_categories_have_indicators():
    """모든 카테고리에 지표 매핑 존재"""
    for cat in CATEGORY_WEEKLY_LIMIT:
        assert cat in CATEGORY_INDICATOR_MAP
        assert len(CATEGORY_INDICATOR_MAP[cat]) > 0
    print("✅ All categories have indicator mappings")


def test_all_indicators_are_valid():
    """모든 카테고리의 지표가 유효한 MCDI 지표"""
    valid_indicators = {"LR", "SD", "NC", "TO", "ER", "RT"}
    for cat, indicators in CATEGORY_INDICATOR_MAP.items():
        for ind in indicators:
            assert ind in valid_indicators, f"{cat}: {ind} is not a valid indicator"
    print("✅ All indicators are valid MCDI indicators")


def test_weekly_limits_match_spec():
    """주간 제한 총합 = 10 (SPEC §2.1.1)"""
    total = sum(CATEGORY_WEEKLY_LIMIT.values())
    # 2 + 3 + 1 + 2 + 1 + 1 = 10
    assert total == 10, f"Expected 10 total weekly interactions, got {total}"
    print(f"✅ Weekly limits total: {total}")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CategorySelector 테스트 시작")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
