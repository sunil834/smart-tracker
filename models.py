from sqlalchemy import Column, String, Date, Integer, JSON, UniqueConstraint
from db import Base

class LogEntry(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    notes = Column(String, nullable=True)
    completed_tasks = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint('date', name='unique_log_date'),
    )
