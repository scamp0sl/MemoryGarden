# core/memory/episodic_memory.py
from typing import List, Dict
from qdrant_client.http import models
from database.vector_db import vector_db_client
from services.embedding_service import embedding_service

class EpisodicMemory:
    """
    [일화 기억]
    - 역할: 과거의 대화 내용 저장 및 유사 상황 검색
    - 저장소: Qdrant (Vector DB)
    """
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.collection_name = "episodic_memory"
        self.client = vector_db_client.get_client()

    async def save_episode(self, text: str, metadata: Dict):
        """대화 내용(Episode)을 벡터로 변환해 저장

        C1-1: 서사 강화 필드 추가
        - samantha_emotion: 사만다의 당시 감정
        - follow_up_notes: 후속 화제
        - relationship_impact: 관계 영향력 (-1.0~+1.0)
        """
        # C1-1: 서사 강화 필드 추가 (metadata에서 추출 또는 기본값)
        samantha_emotion = metadata.pop("samantha_emotion", None)
        follow_up_notes = metadata.pop("follow_up_notes", None)
        relationship_impact = metadata.pop("relationship_impact", 0.0)

        # 1. 텍스트 -> 벡터 변환
        vector = await embedding_service.get_embedding(text)

        # 2. Qdrant에 저장 (C1-1: 새 필드 포함)
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=metadata.get("message_id"), # UUID 권장
                    vector=vector,
                    payload={
                        "user_id": self.user_id,
                        "text": text,
                        "samantha_emotion": samantha_emotion,  # C1-1 신규
                        "follow_up_notes": follow_up_notes,      # C1-1 신규
                        "relationship_impact": relationship_impact, # C1-1 신규
                        **metadata  # 기존 메타데이터
                    }
                )
            ]
        )

    async def retrieve_similar(self, query: str, top_k: int = 3) -> List[Dict]:
        """현재 발화와 비슷한 과거 기억 검색"""
        query_vector = await embedding_service.get_embedding(query)
        
        search_result = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=self.user_id)
                    )
                ]
            ),
            limit=top_k
        )
        
        return [hit.payload for hit in search_result]:1

