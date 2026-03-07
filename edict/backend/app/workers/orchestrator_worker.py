"""Orchestrator Worker — consumes the event bus and drives the task state machine.

Listens on topics:
- task.created → automatically dispatches to Taizi agent
- task.planning.complete → Zhongshu deliberation complete → transitions to Menxia
- task.review.result → Menxia review → Assigned if approved, Replan if rejected
- task.status → handles various state changes
- task.stalled → handles stalled tasks

This is the core orchestrator of the system, replacing the daemon thread + periodic scan role in the old architecture.
Thanks to Redis Streams ACK mechanism: even if a worker crashes, unACKed events
are automatically claimed by other consumers and never lost.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from ..config import get_settings
from ..db import async_session
from ..models.task import TaskState, STATE_AGENT_MAP, ORG_AGENT_MAP
from ..services.event_bus import (
    EventBus,
    TOPIC_TASK_CREATED,
    TOPIC_TASK_STATUS,
    TOPIC_TASK_DISPATCH,
    TOPIC_TASK_COMPLETED,
    TOPIC_TASK_STALLED,
)
from ..services.task_service import TaskService

log = logging.getLogger("edict.orchestrator")

GROUP = "orchestrator"
CONSUMER = "orch-1"

# Topics to monitor
WATCHED_TOPICS = [
    TOPIC_TASK_CREATED,
    TOPIC_TASK_STATUS,
    TOPIC_TASK_COMPLETED,
    TOPIC_TASK_STALLED,
]


class OrchestratorWorker:
    """Event-driven orchestrator Worker."""

    def __init__(self):
        self.bus = EventBus()
        self._running = False

    async def start(self):
        """Start the worker main loop."""
        await self.bus.connect()

        # Ensure all consumer groups
        for topic in WATCHED_TOPICS:
            await self.bus.ensure_consumer_group(topic, GROUP)

        self._running = True
        log.info("🏛️ Orchestrator worker started")

        # First process any pending events left over from a crash
        await self._recover_pending()

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                log.error(f"Orchestrator poll error: {e}", exc_info=True)
                await asyncio.sleep(2)

    async def stop(self):
        self._running = False
        await self.bus.close()
        log.info("Orchestrator worker stopped")

    async def _recover_pending(self):
        """Recover unACKed events from before a crash."""
        for topic in WATCHED_TOPICS:
            events = await self.bus.claim_stale(
                topic, GROUP, CONSUMER, min_idle_ms=30000, count=50
            )
            if events:
                log.info(f"Recovering {len(events)} stale events from {topic}")
                for entry_id, event in events:
                    await self._handle_event(topic, entry_id, event)

    async def _poll_cycle(self):
        """One polling cycle: consume events from all topics."""
        for topic in WATCHED_TOPICS:
            events = await self.bus.consume(
                topic, GROUP, CONSUMER, count=5, block_ms=1000
            )
            for entry_id, event in events:
                try:
                    await self._handle_event(topic, entry_id, event)
                    await self.bus.ack(topic, GROUP, entry_id)
                except Exception as e:
                    log.error(
                        f"Error handling event {entry_id} from {topic}: {e}",
                        exc_info=True,
                    )
                    # Do not ACK → event will be redelivered

    async def _handle_event(self, topic: str, entry_id: str, event: dict):
        """Dispatch handling based on topic and event_type."""
        event_type = event.get("event_type", "")
        trace_id = event.get("trace_id", "")
        payload = event.get("payload", {})

        log.info(f"📨 {topic}/{event_type} trace={trace_id}")

        if topic == TOPIC_TASK_CREATED:
            await self._on_task_created(payload, trace_id)
        elif topic == TOPIC_TASK_STATUS:
            await self._on_task_status(event_type, payload, trace_id)
        elif topic == TOPIC_TASK_COMPLETED:
            await self._on_task_completed(payload, trace_id)
        elif topic == TOPIC_TASK_STALLED:
            await self._on_task_stalled(payload, trace_id)

    async def _on_task_created(self, payload: dict, trace_id: str):
        """Task created → dispatch to Taizi agent for drafting."""
        task_id = payload.get("task_id")
        state = payload.get("state", "taizi")
        agent = STATE_AGENT_MAP.get(TaskState(state), "taizi")

        await self.bus.publish(
            topic=TOPIC_TASK_DISPATCH,
            trace_id=trace_id,
            event_type="task.dispatch.request",
            producer="orchestrator",
            payload={
                "task_id": task_id,
                "agent": agent,
                "state": state,
                "message": f"New task created: {payload.get('title', '')}",
            },
        )

    async def _on_task_status(self, event_type: str, payload: dict, trace_id: str):
        """State change → automatically dispatch to the next agent."""
        task_id = payload.get("task_id")
        new_state_str = payload.get("to", "")

        try:
            new_state = TaskState(new_state_str)
        except ValueError:
            log.warning(f"Unknown state: {new_state_str}")
            return

        # If the new state has a corresponding agent, auto-dispatch
        agent = STATE_AGENT_MAP.get(new_state)

        # If entering assigned state, look up the Six Ministries agent
        if new_state == TaskState.ASSIGNED:
    # Get assignee_org from payload
            org = payload.get("assignee_org", "")
            agent = ORG_AGENT_MAP.get(org, agent)

        if agent:
            await self.bus.publish(
                topic=TOPIC_TASK_DISPATCH,
                trace_id=trace_id,
                event_type="task.dispatch.request",
                producer="orchestrator",
                payload={
                    "task_id": task_id,
                    "agent": agent,
                    "state": new_state_str,
                    "message": f"Task transitioned to {new_state_str}",
                },
            )

    async def _on_task_completed(self, payload: dict, trace_id: str):
        """Task completed → log it."""
        task_id = payload.get("task_id")
        log.info(f"🎉 Task {task_id} completed. trace={trace_id}")

    async def _on_task_stalled(self, payload: dict, trace_id: str):
        """Task stalled → notify Shangshu or re-dispatch."""
        task_id = payload.get("task_id")
        log.warning(f"⏸️ Task {task_id} stalled! Requesting intervention. trace={trace_id}")
        # TODO: implement automatic recovery strategy for stalled tasks


async def run_orchestrator():
    """Entry function — for running the worker directly."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    worker = OrchestratorWorker()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    await worker.start()
