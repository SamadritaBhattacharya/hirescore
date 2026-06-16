"""
Base agent abstraction.

Design:
- Open/Closed: new agents extend BaseAgent without modifying core
- Liskov Substitution: all agents interchangeable via BaseAgent interface
- Single Responsibility: each agent does ONE research task
- Dependency Inversion: agents depend on injected clients, not concrete impls
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from core.logging import get_logger
from models.schemas import AgentName, AgentProgress, JobStatus, ResearchJobState

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all HireScope research agents.

    All agents:
    1. Receive the full ResearchJobState (read what they need)
    2. Execute their research
    3. Write their specific output back to state
    4. Emit progress events

    Subclasses must implement `execute()` only.
    Error handling, logging, and progress emission are handled here.
    """

    def __init__(self, name: AgentName, timeout_seconds: int = 60) -> None:
        self.name = name
        self.timeout_seconds = timeout_seconds
        self._logger = get_logger(f"agent.{name.value}")

    @abstractmethod
    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        """
        Core agent logic. Reads from state, writes output to state.
        Must not raise — use state.errors[self.name] for failures.
        """
        ...

    async def run(self, state: ResearchJobState) -> ResearchJobState:
        """
        Public entry point. Wraps execute() with:
        - Progress event emission
        - Timeout enforcement
        - Structured error capture
        """
        self._emit_progress(state, "started", f"Starting {self.name.value} research")
        self._logger.info("agent_started", agent=self.name.value, job_id=str(state.job_id))

        try:
            state = await asyncio.wait_for(
                self.execute(state),
                timeout=self.timeout_seconds,
            )
            self._emit_progress(state, "completed", f"{self.name.value} research done")
            self._logger.info(
                "agent_completed", agent=self.name.value, job_id=str(state.job_id)
            )
        except asyncio.TimeoutError:
            msg = f"{self.name.value} timed out after {self.timeout_seconds}s"
            state.errors[self.name.value] = msg
            self._emit_progress(state, "failed", msg)
            self._logger.warning(
                "agent_timeout", agent=self.name.value, job_id=str(state.job_id)
            )
        except Exception as exc:
            msg = f"{self.name.value} failed: {type(exc).__name__}: {exc}"
            state.errors[self.name.value] = msg
            self._emit_progress(state, "failed", msg)
            self._logger.exception(
                "agent_error",
                agent=self.name.value,
                job_id=str(state.job_id),
                error=str(exc),
            )

        return state

    def _emit_progress(
        self, state: ResearchJobState, status: str, message: str
    ) -> None:
        event = AgentProgress(
            agent=self.name,
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
        )
        state.progress_events.append(event)

    def _is_enabled(self, state: ResearchJobState) -> bool:
        """Check if this agent was selected by the routing agent."""
        return self.name in state.agents_to_run