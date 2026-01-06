from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

class CaseHistory(Base):
    __tablename__ = "case_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symptoms = Column(Text, nullable=False)
    suggested_remedies = Column(String(500))
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime)
