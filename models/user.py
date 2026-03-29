# models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.sql import func
from database.postgres import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(String, unique=True, index=True, nullable=False) # 카카오톡 사용자 식별자
    name = Column(String, nullable=True)
    birth_year = Column(Integer, nullable=True) # 나이 계산용
    gender = Column(String, nullable=True)
    
    # 보호자 연락처 (선택)
    guardian_phone = Column(String, nullable=True)
    
    # 메타 데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 동의 여부 (개인정보 처리 방침 등)
    is_active = Column(Boolean, default=True)
    terms_agreed = Column(Boolean, default=False)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name})>"