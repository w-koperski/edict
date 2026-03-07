"""Event model — event persistence table supporting replay and audit.

Each event corresponds to a system action: task creation, state change, Agent thought, Todo update, etc.
Follows Edict Architecture §3 event structure specification.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..db import Base


class Event(Base):
    """Event table — persistent record of all system events."""
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(32), nullable=False, index=True, comment="Associated task ID")
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Event classification
    topic = Column(String(128), nullable=False, index=True, comment="Event topic, e.g. task.created")
    event_type = Column(String(128), nullable=False, comment="Event type, e.g. state.changed")
    producer = Column(String(128), nullable=False, comment="Event producer, e.g. orchestrator:v1")

    # Event data
    payload = Column(JSONB, default=dict, comment="Event payload")
    meta = Column(JSONB, default=dict, comment="Metadata {priority, model, version}")

    __table_args__ = (
        Index("ix_events_trace_topic", "trace_id", "topic"),
        Index("ix_events_timestamp", "timestamp"),
    )

    def to_dict(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else "",
            "topic": self.topic,
            "event_type": self.event_type,
            "producer": self.producer,
            "payload": self.payload or {},
            "meta": self.meta or {},
        }
