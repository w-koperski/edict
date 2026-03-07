"""Task model — core task table for the Three Departments & Six Ministries.

Corresponds to each task record in tasks_source.json.
state maps to the Three Departments & Six Ministries state machine:
  Taizi → Zhongshu → Menxia → Assigned → Doing → Review → Done
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    Boolean,
    Integer,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..db import Base


class TaskState(str, enum.Enum):
    """Task state enum — maps to the Three Departments & Six Ministries workflow."""
    Taizi = "Taizi"           # Taizi triage
    Zhongshu = "Zhongshu"     # Zhongshu drafting
    Menxia = "Menxia"         # Menxia review
    Assigned = "Assigned"     # Shangshu has dispatched the task
    Next = "Next"             # Pending execution
    Doing = "Doing"           # Six Ministries executing
    Review = "Review"         # Review & summary
    Done = "Done"             # Completed
    Blocked = "Blocked"       # Blocked
    Cancelled = "Cancelled"   # Cancelled
    Pending = "Pending"       # Pending


# Terminal state set
TERMINAL_STATES = {TaskState.Done, TaskState.Cancelled}

# Valid state transition paths
STATE_TRANSITIONS = {
    TaskState.Taizi: {TaskState.Zhongshu, TaskState.Cancelled},
    TaskState.Zhongshu: {TaskState.Menxia, TaskState.Cancelled, TaskState.Blocked},
    TaskState.Menxia: {TaskState.Assigned, TaskState.Zhongshu, TaskState.Cancelled},  # rejected/vetoed back to Zhongshu
    TaskState.Assigned: {TaskState.Doing, TaskState.Next, TaskState.Cancelled, TaskState.Blocked},
    TaskState.Next: {TaskState.Doing, TaskState.Cancelled},
    TaskState.Doing: {TaskState.Review, TaskState.Done, TaskState.Blocked, TaskState.Cancelled},
    TaskState.Review: {TaskState.Done, TaskState.Doing, TaskState.Cancelled},  # failed review returns to Doing
    TaskState.Blocked: {TaskState.Taizi, TaskState.Zhongshu, TaskState.Menxia, TaskState.Assigned, TaskState.Doing},
}

# State → Agent mapping
STATE_AGENT_MAP = {
    TaskState.Taizi: "taizi",
    TaskState.Zhongshu: "zhongshu",
    TaskState.Menxia: "menxia",
    TaskState.Assigned: "shangshu",
    TaskState.Review: "shangshu",
}

# Organization → Agent mapping (Six Ministries)
ORG_AGENT_MAP = {
    "户部": "hubu",
    "礼部": "libu",
    "兵部": "bingbu",
    "刑部": "xingbu",
    "工部": "gongbu",
    "吏部": "libu_hr",
}


class Task(Base):
    """Three Departments & Six Ministries task table."""
    __tablename__ = "tasks"

    id = Column(String(32), primary_key=True, comment="Task ID, e.g. JJC-20260301-001")
    title = Column(Text, nullable=False, comment="Task title")
    state = Column(Enum(TaskState, name="task_state"), nullable=False, default=TaskState.Taizi, index=True)
    org = Column(String(32), nullable=False, default="太子", comment="Current executing department")
    official = Column(String(32), default="", comment="Responsible official")
    now = Column(Text, default="", comment="Current progress description")
    eta = Column(String(64), default="-", comment="Estimated completion time")
    block = Column(Text, default="none", comment="Blocking reason")
    output = Column(Text, default="", comment="Final output")
    priority = Column(String(16), default="normal", comment="Priority")
    archived = Column(Boolean, default=False, index=True)

    # JSONB flexible fields
    flow_log = Column(JSONB, default=list, comment="Flow log [{at, from, to, remark}]")
    progress_log = Column(JSONB, default=list, comment="Progress log [{at, agent, text, todos}]")
    todos = Column(JSONB, default=list, comment="Sub-tasks [{id, title, status, detail}]")
    scheduler = Column(JSONB, default=dict, comment="Scheduler metadata")
    template_id = Column(String(64), default="", comment="Template ID")
    template_params = Column(JSONB, default=dict, comment="Template parameters")
    ac = Column(Text, default="", comment="Acceptance criteria")
    target_dept = Column(String(64), default="", comment="Target department")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_tasks_state_archived", "state", "archived"),
        Index("ix_tasks_updated_at", "updated_at"),
    )

    def to_dict(self) -> dict:
        """Serialize to API response format (compatible with legacy live_status format)."""
        return {
            "id": self.id,
            "title": self.title,
            "state": self.state.value if self.state else "",
            "org": self.org,
            "official": self.official,
            "now": self.now,
            "eta": self.eta,
            "block": self.block,
            "output": self.output,
            "priority": self.priority,
            "archived": self.archived,
            "flow_log": self.flow_log or [],
            "progress_log": self.progress_log or [],
            "todos": self.todos or [],
            "templateId": self.template_id,
            "templateParams": self.template_params or {},
            "ac": self.ac,
            "targetDept": self.target_dept,
            "_scheduler": self.scheduler or {},
            "createdAt": self.created_at.isoformat() if self.created_at else "",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else "",
        }
