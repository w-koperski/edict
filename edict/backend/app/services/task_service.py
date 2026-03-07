"""Task service layer — CRUD + state machine logic.

All business rules are centralized here:
- Create task → publish task.created event
- State transition → validate legality + publish state event
- Query, filter, aggregate
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task, TaskState, STATE_TRANSITIONS, TERMINAL_STATES
from .event_bus import (
    EventBus,
    TOPIC_TASK_CREATED,
    TOPIC_TASK_STATUS,
    TOPIC_TASK_COMPLETED,
    TOPIC_TASK_DISPATCH,
)

log = logging.getLogger("edict.task_service")


class TaskService:
    def __init__(self, db: AsyncSession, event_bus: EventBus):
        self.db = db
        self.bus = event_bus

    # ── Create ──

    async def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        assignee_org: str | None = None,
        creator: str = "emperor",
        tags: list[str] | None = None,
        initial_state: TaskState = TaskState.TAIZI,
        meta: dict | None = None,
    ) -> Task:
        """Create a task and publish the task.created event."""
        now = datetime.now(timezone.utc)
        trace_id = str(uuid.uuid4())

        task = Task(
            trace_id=trace_id,
            title=title,
            description=description,
            priority=priority,
            state=initial_state,
            assignee_org=assignee_org,
            creator=creator,
            tags=tags or [],
            flow_log=[
                {
                    "from": None,
                    "to": initial_state.value,
                    "agent": "system",
                    "reason": "Task created",
                    "ts": now.isoformat(),
                }
            ],
            progress_log=[],
            todos=[],
            scheduler=None,
            meta=meta or {},
        )
        self.db.add(task)
        await self.db.flush()

        # Publish event
        await self.bus.publish(
            topic=TOPIC_TASK_CREATED,
            trace_id=trace_id,
            event_type="task.created",
            producer="task_service",
            payload={
                "task_id": str(task.task_id),
                "title": title,
                "state": initial_state.value,
                "priority": priority,
                "assignee_org": assignee_org,
            },
        )

        await self.db.commit()
        log.info(f"Created task {task.task_id}: {title} [{initial_state.value}]")
        return task

    # ── State transition ──

    async def transition_state(
        self,
        task_id: uuid.UUID,
        new_state: TaskState,
        agent: str = "system",
        reason: str = "",
    ) -> Task:
        """Execute a state transition, validating its legality."""
        task = await self._get_task(task_id)
        old_state = task.state

        # Validate legal transition
        allowed = STATE_TRANSITIONS.get(old_state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {old_state.value} → {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        task.state = new_state
        task.updated_at = datetime.now(timezone.utc)

        # Record in flow_log
        flow_entry = {
            "from": old_state.value,
            "to": new_state.value,
            "agent": agent,
            "reason": reason,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if task.flow_log is None:
            task.flow_log = []
        task.flow_log = [*task.flow_log, flow_entry]

        # Publish state change event
        topic = TOPIC_TASK_COMPLETED if new_state in TERMINAL_STATES else TOPIC_TASK_STATUS
        await self.bus.publish(
            topic=topic,
            trace_id=str(task.trace_id),
            event_type=f"task.state.{new_state.value}",
            producer=agent,
            payload={
                "task_id": str(task_id),
                "from": old_state.value,
                "to": new_state.value,
                "reason": reason,
            },
        )

        await self.db.commit()
        log.info(f"Task {task_id} state: {old_state.value} → {new_state.value} by {agent}")
        return task

    # ── Dispatch request ──

    async def request_dispatch(
        self,
        task_id: uuid.UUID,
        target_agent: str,
        message: str = "",
    ):
        """Publish a task.dispatch event, consumed and executed by DispatchWorker."""
        task = await self._get_task(task_id)
        await self.bus.publish(
            topic=TOPIC_TASK_DISPATCH,
            trace_id=str(task.trace_id),
            event_type="task.dispatch.request",
            producer="task_service",
            payload={
                "task_id": str(task_id),
                "agent": target_agent,
                "message": message,
                "state": task.state.value,
            },
        )
        log.info(f"Dispatch requested: task {task_id} → agent {target_agent}")

    # ── Progress/note update ──

    async def add_progress(
        self,
        task_id: uuid.UUID,
        agent: str,
        content: str,
    ) -> Task:
        task = await self._get_task(task_id)
        entry = {
            "agent": agent,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if task.progress_log is None:
            task.progress_log = []
        task.progress_log = [*task.progress_log, entry]
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_todos(
        self,
        task_id: uuid.UUID,
        todos: list[dict],
    ) -> Task:
        task = await self._get_task(task_id)
        task.todos = todos
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_scheduler(
        self,
        task_id: uuid.UUID,
        scheduler: dict,
    ) -> Task:
        task = await self._get_task(task_id)
        task.scheduler = scheduler
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    # ── Queries ──

    async def get_task(self, task_id: uuid.UUID) -> Task:
        return await self._get_task(task_id)

    async def list_tasks(
        self,
        state: TaskState | None = None,
        assignee_org: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        stmt = select(Task)
        conditions = []
        if state is not None:
            conditions.append(Task.state == state)
        if assignee_org is not None:
            conditions.append(Task.assignee_org == assignee_org)
        if priority is not None:
            conditions.append(Task.priority == priority)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_live_status(self) -> dict[str, Any]:
        """Generate global status compatible with the legacy live_status.json format."""
        tasks = await self.list_tasks(limit=200)
        active_tasks = {}
        completed_tasks = {}
        for t in tasks:
            d = t.to_dict()
            if t.state in TERMINAL_STATES:
                completed_tasks[str(t.task_id)] = d
            else:
                active_tasks[str(t.task_id)] = d
        return {
            "tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def count_tasks(self, state: TaskState | None = None) -> int:
        stmt = select(func.count(Task.task_id))
        if state is not None:
            stmt = stmt.where(Task.state == state)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── Internal ──

    async def _get_task(self, task_id: uuid.UUID) -> Task:
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task
