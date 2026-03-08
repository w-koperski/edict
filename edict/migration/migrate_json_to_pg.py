#!/usr/bin/env python3
"""JSON → Postgres data migration script.

Reads legacy data/tasks_source.json and imports it into the Edict Postgres database.

Usage:
  # Ensure Postgres is running and schema is created (alembic upgrade head)
  python3 migrate_json_to_pg.py

  # Specify data file
  python3 migrate_json_to_pg.py --file /path/to/tasks_source.json

  # Dry run (analyze only, no writes)
  python3 migrate_json_to_pg.py --dry-run
"""

import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import text
from app.db import engine, async_session, Base
from app.models.task import Task, TaskState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("migrate")

# Legacy state → Edict TaskState
STATE_MAP = {
    "Taizi": TaskState.TAIZI,
    "Zhongshu": TaskState.ZHONGSHU,
    "Menxia": TaskState.MENXIA,
    "Assigned": TaskState.ASSIGNED,
    "Next": TaskState.NEXT,
    "Doing": TaskState.DOING,
    "Review": TaskState.REVIEW,
    "Done": TaskState.DONE,
    "Blocked": TaskState.BLOCKED,
    "Cancelled": TaskState.CANCELLED,
    "Pending": TaskState.PENDING,
    # Fallbacks
    "Inbox": TaskState.TAIZI,
    "": TaskState.TAIZI,
}


def parse_old_task(old: dict) -> dict:
    """Convert legacy task JSON to Edict Task parameters."""
    state_str = old.get("state", "Taizi")
    state = STATE_MAP.get(state_str, TaskState.TAIZI)

    legacy_id = old.get("id", "")
    title = old.get("title", "Untitled task")

    # Parse timestamp
    updated_str = old.get("updatedAt", "")
    try:
        updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        updated_at = datetime.now(timezone.utc)

    return {
        "trace_id": str(uuid.uuid4()),
        "title": title,
        "description": old.get("now", ""),
        "priority": "normal",
        "state": state,
        "assignee_org": old.get("org", None),
        "creator": old.get("official", "emperor"),
        "tags": [legacy_id] if legacy_id else [],
        "flow_log": old.get("flow_log", []),
        "progress_log": old.get("progress_log", []),
        "todos": old.get("todos", []),
        "scheduler": old.get("scheduler", None),
        "meta": {
            "legacy_id": legacy_id,
            "legacy_state": state_str,
            "legacy_output": old.get("output", ""),
            "legacy_ac": old.get("ac", ""),
            "legacy_eta": old.get("eta", ""),
            "legacy_block": old.get("block", ""),
        },
        "created_at": updated_at,  # Legacy data has no created_at, approximating with updated_at
        "updated_at": updated_at,
    }


async def migrate(file_path: Path, dry_run: bool = False):
    """Execute migration."""
    if not file_path.exists():
        log.error(f"Data file not found: {file_path}")
        return

    # Read legacy data
    raw = file_path.read_text(encoding="utf-8")
    old_tasks = json.loads(raw)
    log.info(f"Read {len(old_tasks)} legacy tasks")

    # Statistics
    stats = {"total": len(old_tasks), "migrated": 0, "skipped": 0, "errors": 0}
    by_state = {}

    for old in old_tasks:
        state_str = old.get("state", "?")
        by_state[state_str] = by_state.get(state_str, 0) + 1

    log.info(f"State distribution: {by_state}")

    if dry_run:
        log.info("=== DRY RUN mode, not writing to database ===")
        for old in old_tasks:
            params = parse_old_task(old)
            log.info(f"  [{params['meta']['legacy_id']}] {params['title'][:40]} → {params['state'].value}")
        log.info(f"Dry run complete: {stats['total']} tasks pending migration")
        return

    # Write to Postgres
    async with async_session() as db:
        for old in old_tasks:
            try:
                params = parse_old_task(old)
                legacy_id = params["meta"]["legacy_id"]

                # Check if already migrated
                from sqlalchemy import select
                existing = await db.execute(
                    select(Task).where(Task.tags.contains([legacy_id]))
                )
                if existing.scalars().first():
                    log.debug(f"Skipping already migrated: {legacy_id}")
                    stats["skipped"] += 1
                    continue

                task = Task(**params)
                db.add(task)
                stats["migrated"] += 1
                log.info(f"✅ Migrated: [{legacy_id}] {params['title'][:40]} → {params['state'].value}")

            except Exception as e:
                log.error(f"❌ Migration failed: {old.get('id', '?')}: {e}")
                stats["errors"] += 1

        await db.commit()

    log.info(f"Migration complete: total {stats['total']}, migrated {stats['migrated']}, "
             f"skipped {stats['skipped']}, errors {stats['errors']}")


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON tasks to Postgres")
    parser.add_argument(
        "--file", "-f",
        default=str(Path(__file__).parent.parent.parent / "data" / "tasks_source.json"),
        help="Path to tasks_source.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only analyze, don't write")
    args = parser.parse_args()

    asyncio.run(migrate(Path(args.file), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
