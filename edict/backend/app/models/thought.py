"""Thought model — Agent thought stream persistence.

Follows Edict Architecture §4 Thought JSON Schema.
Supports streaming partial thoughts and real-time dashboard display.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID

from ..db import Base


class Thought(Base):
    """Agent thought record."""
    __tablename__ = "thoughts"

    thought_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(32), nullable=False, index=True, comment="Associated task ID")
    agent = Column(String(32), nullable=False, index=True, comment="Agent identifier")
    step = Column(Integer, nullable=False, default=0, comment="Thought step index")
    type = Column(
        String(32),
        nullable=False,
        default="reasoning",
        comment="Thought type: reasoning|query|action_intent|summary",
    )
    source = Column(String(16), default="llm", comment="Source: llm|tool|human")
    content = Column(Text, nullable=False, default="", comment="Thought content")
    tokens = Column(Integer, default=0, comment="Token count consumed")
    confidence = Column(Float, default=0.0, comment="Confidence score 0-1")
    sensitive = Column(Boolean, default=False, comment="Whether content is sensitive")
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_thoughts_trace_agent", "trace_id", "agent"),
        Index("ix_thoughts_timestamp", "timestamp"),
    )

    def to_dict(self) -> dict:
        return {
            "thought_id": str(self.thought_id),
            "trace_id": self.trace_id,
            "agent": self.agent,
            "step": self.step,
            "type": self.type,
            "source": self.source,
            "content": self.content,
            "tokens": self.tokens,
            "confidence": self.confidence,
            "sensitive": self.sensitive,
            "timestamp": self.timestamp.isoformat() if self.timestamp else "",
        }
