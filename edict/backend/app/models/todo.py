"""Todo model — structured sub-tasks.

Follows Edict Architecture §4 Todo JSON Schema.
Supports hierarchical structure (parent_id) and checkpoint tracking.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..db import Base


class Todo(Base):
    """Structured sub-task table."""
    __tablename__ = "todos"

    todo_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(32), nullable=False, index=True, comment="Associated task ID")
    parent_id = Column(UUID(as_uuid=True), nullable=True, comment="Parent todo_id (tree structure)")

    title = Column(String(256), nullable=False, comment="Sub-task title")
    description = Column(Text, default="", comment="Detailed description")
    owner = Column(String(64), default="", comment="Responsible department")
    assignee_agent = Column(String(32), default="", comment="Executing Agent")

    status = Column(String(32), nullable=False, default="open", index=True,
                    comment="Status: open|in_progress|done|cancelled")
    priority = Column(String(16), default="normal", comment="Priority: low|normal|high|urgent")
    estimated_cost = Column(Float, default=0.0, comment="Estimated token cost")

    created_by = Column(String(64), default="", comment="Creator")
    checkpoints = Column(JSONB, default=list, comment="Checkpoints [{name, status}]")
    metadata_ = Column("metadata", JSONB, default=dict, comment="Extended metadata")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_todos_trace_status", "trace_id", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "todo_id": str(self.todo_id),
            "trace_id": self.trace_id,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "title": self.title,
            "description": self.description,
            "owner": self.owner,
            "assignee_agent": self.assignee_agent,
            "status": self.status,
            "priority": self.priority,
            "estimated_cost": self.estimated_cost,
            "created_by": self.created_by,
            "checkpoints": self.checkpoints or [],
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
