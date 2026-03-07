"""Dispatch Worker — consumes task.dispatch events and executes OpenClaw agent calls.

Core fix for old architecture pain points:
- Old: daemon thread + subprocess.run → kill -9 loses everything
- New: Redis Streams ACK guarantee → automatic redelivery after crash

Flow:
1. Consume events from task.dispatch stream
2. Call OpenClaw CLI: `openclaw agent --agent xxx -m "..."`
3. Parse agent output (kanban_update.py call result)
4. ACK event
"""

import asyncio
import logging
import os
import signal
import subprocess
import uuid
from datetime import datetime, timezone

from ..config import get_settings
from ..services.event_bus import (
    EventBus,
    TOPIC_TASK_DISPATCH,
    TOPIC_TASK_STATUS,
    TOPIC_AGENT_THOUGHTS,
    TOPIC_AGENT_HEARTBEAT,
)

log = logging.getLogger("edict.dispatcher")

GROUP = "dispatcher"
CONSUMER = "disp-1"


class DispatchWorker:
    """Agent dispatch Worker — calls OpenClaw CLI to execute agent tasks."""

    def __init__(self, max_concurrent: int = 3):
        self.bus = EventBus()
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: dict[str, asyncio.Task] = {}

    async def start(self):
        await self.bus.connect()
        await self.bus.ensure_consumer_group(TOPIC_TASK_DISPATCH, GROUP)
        self._running = True
        log.info("🚀 Dispatch worker started")

        # Recover any crash leftovers
        await self._recover_pending()

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                log.error(f"Dispatch poll error: {e}", exc_info=True)
                await asyncio.sleep(2)

    async def stop(self):
        self._running = False
        # Wait for in-progress agent calls to complete
        if self._active_tasks:
            log.info(f"Waiting for {len(self._active_tasks)} active dispatches...")
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        await self.bus.close()
        log.info("Dispatch worker stopped")

    async def _recover_pending(self):
        events = await self.bus.claim_stale(
            TOPIC_TASK_DISPATCH, GROUP, CONSUMER, min_idle_ms=60000, count=20
        )
        if events:
            log.info(f"Recovering {len(events)} stale dispatch events")
            for entry_id, event in events:
                await self._dispatch(entry_id, event)

    async def _poll_cycle(self):
        events = await self.bus.consume(
            TOPIC_TASK_DISPATCH, GROUP, CONSUMER, count=3, block_ms=2000
        )
        for entry_id, event in events:
            # Each dispatch runs in an independent task with concurrency control
            task = asyncio.create_task(self._dispatch(entry_id, event))
            task_id = event.get("payload", {}).get("task_id", entry_id)
            self._active_tasks[task_id] = task
            task.add_done_callback(lambda t, tid=task_id: self._active_tasks.pop(tid, None))

    async def _dispatch(self, entry_id: str, event: dict):
        """Execute one agent dispatch."""
        async with self._semaphore:
            payload = event.get("payload", {})
            task_id = payload.get("task_id", "")
            agent = payload.get("agent", "")
            message = payload.get("message", "")
            trace_id = event.get("trace_id", "")
            state = payload.get("state", "")

            log.info(f"🔄 Dispatching task {task_id} → agent '{agent}' state={state}")

            # Publish heartbeat
            await self.bus.publish(
                topic=TOPIC_AGENT_HEARTBEAT,
                trace_id=trace_id,
                event_type="agent.dispatch.start",
                producer="dispatcher",
                payload={"task_id": task_id, "agent": agent},
            )

            try:
                result = await self._call_openclaw(agent, message, task_id, trace_id)

                # Publish agent output
                await self.bus.publish(
                    topic=TOPIC_AGENT_THOUGHTS,
                    trace_id=trace_id,
                    event_type="agent.output",
                    producer=f"agent.{agent}",
                    payload={
                        "task_id": task_id,
                        "agent": agent,
                        "output": result.get("stdout", ""),
                        "return_code": result.get("returncode", -1),
                    },
                )

                if result.get("returncode") == 0:
                    log.info(f"✅ Agent '{agent}' completed task {task_id}")
                else:
                    log.warning(
                        f"⚠️ Agent '{agent}' returned non-zero for task {task_id}: "
                        f"rc={result.get('returncode')}"
                    )

                # ACK — event processing complete
                await self.bus.ack(TOPIC_TASK_DISPATCH, GROUP, entry_id)

            except Exception as e:
                log.error(f"❌ Dispatch failed: task {task_id} → {agent}: {e}", exc_info=True)
                # Do not ACK → Redis will redeliver to another consumer

    async def _call_openclaw(
        self,
        agent: str,
        message: str,
        task_id: str,
        trace_id: str,
    ) -> dict:
        """Asynchronously call the OpenClaw CLI — executed in a thread pool."""
        settings = get_settings()
        cmd = [
            "openclaw", "agent",
            "--agent", agent,
            "-m", message,
        ]

        env = os.environ.copy()
        env["EDICT_TASK_ID"] = task_id
        env["EDICT_TRACE_ID"] = trace_id
        env["EDICT_API_URL"] = f"http://localhost:{settings.port}"

        log.debug(f"Executing: {' '.join(cmd)}")

        def _run():
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env,
                    cwd=settings.openclaw_project_dir or None,
                )
                return {
                    "returncode": proc.returncode,
                    "stdout": proc.stdout[-5000:] if proc.stdout else "",
                    "stderr": proc.stderr[-2000:] if proc.stderr else "",
                }
            except subprocess.TimeoutExpired:
                return {"returncode": -1, "stdout": "", "stderr": "TIMEOUT after 300s"}
            except FileNotFoundError:
                return {"returncode": -1, "stdout": "", "stderr": "openclaw command not found"}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)


async def run_dispatcher():
    """Entry function — for running the worker directly."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    worker = DispatchWorker()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    await worker.start()
