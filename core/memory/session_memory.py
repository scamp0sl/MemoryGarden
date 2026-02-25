# core/memory/session_memory.py
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from database.redis_client import redis_client

class SessionMemory:
    """
    [단기 기억]
    - 역할: 현재 대화 턴의 맥락 유지
    - 저장소: Redis
    - 특징: 빠름, 휘발성 (TTL 적용)
    """
    def __init__(self, user_id: int, ttl: int = 1800):
        self.user_id = user_id
        self.ttl = ttl  # 기본 30분 유지
        # 키 패턴: session:{user_id}
        self.redis_key = f"session:{user_id}"

    async def save_context(self, context: Dict[str, Any]):
        """컨텍스트 전체 저장 (덮어쓰기)"""
        client = await redis_client.get_client()
        await client.set(
            self.redis_key,
            json.dumps(context, ensure_ascii=False),
            ex=self.ttl
        )

    async def get_context(self) -> Dict[str, Any]:
        """컨텍스트 조회"""
        client = await redis_client.get_client()
        data = await client.get(self.redis_key)
        if data:
            return json.loads(data)
        return {} # 없으면 빈 딕셔너리 반환

    async def update_context(self, updates: Dict[str, Any]):
        """특정 필드만 업데이트"""
        current = await self.get_context()
        current.update(updates)
        await self.save_context(current)

    async def clear(self):
        """세션 초기화 (대화 종료 시)"""
        client = await redis_client.get_client()
        await client.delete(self.redis_key)

    # ============================================
    # 확장 메서드 (Task 5용)
    # ============================================

    async def add_turn(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        대화 턴 추가

        Args:
            session_id: 세션 ID
            role: 역할 (user/assistant)
            content: 메시지 내용
            metadata: 추가 메타데이터
        """
        client = await redis_client.get_client()

        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }

        # List에 턴 추가
        turns_key = f"session:{session_id}:turns"
        await client.rpush(turns_key, json.dumps(turn, ensure_ascii=False))

        # TTL 설정 (24시간)
        await client.expire(turns_key, 86400)

        # 세션 메타데이터 업데이트
        await self._update_session_metadata(session_id)

    async def get_all_turns(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        세션의 모든 대화 턴 조회

        Args:
            session_id: 세션 ID
            limit: 최대 조회 개수

        Returns:
            대화 턴 리스트 (최신순)
        """
        client = await redis_client.get_client()

        turns_key = f"session:{session_id}:turns"

        # 최근 limit개 조회 (음수 인덱스로 끝에서부터)
        turns_data = await client.lrange(turns_key, -limit, -1)

        turns = []
        for turn_data in turns_data:
            if isinstance(turn_data, bytes):
                turn_data = turn_data.decode('utf-8')
            turns.append(json.loads(turn_data))

        # 최신순 정렬 (reverse)
        turns.reverse()

        return turns

    async def get_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 메타데이터 조회

        Args:
            session_id: 세션 ID

        Returns:
            메타데이터 dict 또는 None
        """
        client = await redis_client.get_client()

        metadata_key = f"session:{session_id}:metadata"
        metadata = await client.hgetall(metadata_key)

        if not metadata:
            return None

        # bytes를 str로 변환
        result = {}
        for key, value in metadata.items():
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            value_str = value.decode('utf-8') if isinstance(value, bytes) else value
            result[key_str] = value_str

        return result

    async def exists(self, session_id: str) -> bool:
        """
        세션 존재 확인

        Args:
            session_id: 세션 ID

        Returns:
            존재 여부
        """
        client = await redis_client.get_client()

        turns_key = f"session:{session_id}:turns"
        exists = await client.exists(turns_key)

        return exists > 0

    async def _update_session_metadata(self, session_id: str):
        """
        세션 메타데이터 업데이트 (내부 메서드)

        Args:
            session_id: 세션 ID
        """
        client = await redis_client.get_client()

        metadata_key = f"session:{session_id}:metadata"

        # 기존 메타데이터 조회
        existing = await client.hgetall(metadata_key)

        # created_at이 없으면 현재 시간으로 설정
        if not existing or b"created_at" not in existing:
            await client.hset(metadata_key, "created_at", datetime.now().isoformat())

        # updated_at 항상 갱신
        await client.hset(metadata_key, "updated_at", datetime.now().isoformat())

        # 턴 개수 카운트
        turns_key = f"session:{session_id}:turns"
        turn_count = await client.llen(turns_key)
        await client.hset(metadata_key, "turn_count", str(turn_count))

        # TTL 설정 (24시간)
        await client.expire(metadata_key, 86400)