"""Controlled async job runner for surveys (in-process). Request returns immediately; work runs as a tracked asyncio task.
Redis/BullMQ-style queues are deliberately NOT used yet (see docs/technology-decisions.md); `execute_survey` is idempotent
and resumable, so moving it behind a real queue later only means calling it from a worker process."""
import asyncio

from agents import survey_execution_agent as sa
from utils.logging import get_logger, log_event

log = get_logger("survey_worker")
_tasks: dict[str, asyncio.Task] = {}


async def _job(survey_id: str) -> dict:
    try:
        return await sa.execute_survey(survey_id)
    except Exception as e:  # noqa: BLE001 - never leave a survey stuck in 'running'
        log_event(log, "survey_job_crashed", level=40, survey_id=survey_id, error=str(e))
        return await sa.finalize(survey_id, expected=-1)
    finally:
        _tasks.pop(survey_id, None)


def launch(survey_id: str) -> asyncio.Task:
    task = asyncio.create_task(_job(survey_id))
    _tasks[survey_id] = task
    return task


async def wait_all() -> None:
    while _tasks:
        await asyncio.gather(*list(_tasks.values()), return_exceptions=True)
