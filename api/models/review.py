import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


class Review(Base):
    """
    One row per PR review job.
    status lifecycle: pending → running → done | failed
    """
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo = Column(String(255), nullable=False)       # "owner/repo"
    pr_number = Column(Integer, nullable=False)
    pr_title = Column(Text)
    status = Column(String(32), default="pending")   # pending|running|done|failed
    provider = Column(String(64), nullable=False)    # openai|anthropic|ollama
    model = Column(String(128), nullable=False)
    comments = Column(JSON)                          # structured review output
    summary = Column(Text)
    error = Column(Text)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ProviderConfig(Base):
    """
    Which LLM provider is active — switchable at runtime from the dashboard.
    """
    __tablename__ = "provider_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(64), unique=True, nullable=False)
    model = Column(String(128), nullable=False)
    is_active = Column(String(1), default="0")       # "1" = active
    updated_at = Column(DateTime, default=datetime.utcnow)
