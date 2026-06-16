"""
In-memory job store for research jobs.

Production note: Replace with Redis for multi-worker deployments.
For the current single-worker setup, this is sufficient and zero-cost.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from models.schemas import JobStatus, ResearchJobState
from core.logging import get_logger

logger = get_logger(__name__)


class JobStore:
    """
    Thread-safe in-memory store for research job states.
    Singleton pattern — one store per process.
    """

    def __init__(self) -> None:
        self._jobs: dict[UUID, ResearchJobState] = {}
        self._lock = asyncio.Lock()
        # SSE subscriber queues: job_id → list of queues
        self._subscribers: dict[UUID, list[asyncio.Queue]] = {}

    async def create(self, state: ResearchJobState) -> None:
        async with self._lock:
            self._jobs[state.job_id] = state
            self._subscribers[state.job_id] = []
            logger.info("job_created", job_id=str(state.job_id))

    async def get(self, job_id: UUID) -> ResearchJobState | None:
        return self._jobs.get(job_id)

    async def update(self, state: ResearchJobState) -> None:
        async with self._lock:
            self._jobs[state.job_id] = state
            # Notify all SSE subscribers
            for queue in self._subscribers.get(state.job_id, []):
                await queue.put(state)

    async def subscribe(self, job_id: UUID) -> asyncio.Queue:
        """Create and register a new SSE subscriber queue for a job."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = []
            self._subscribers[job_id].append(queue)
        return queue

    async def unsubscribe(self, job_id: UUID, queue: asyncio.Queue) -> None:
        async with self._lock:
            if job_id in self._subscribers:
                self._subscribers[job_id] = [
                    q for q in self._subscribers[job_id] if q is not queue
                ]

    def get_all_job_ids(self) -> list[UUID]:
        return list(self._jobs.keys())


# Singleton instance
_job_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store