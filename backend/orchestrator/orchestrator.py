"""
LangGraph Orchestrator.

Graph topology:
    routing → [linkedin, github, web_research] (parallel) → fit_scorer → synthesizer

Uses LangGraph's StateGraph with Send API for parallel execution.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from core.logging import get_logger
from agents.github_agent import GitHubAgent
from agents.linkedin_agent import LinkedInAgent
from agents.routing_agent import RoutingAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.web_research_agent import WebResearchAgent
from agents.fit_scorer_agent import FitScorerAgent
from models.schemas import AgentName, JobStatus, ResearchJobState

logger = get_logger(__name__)


class HireScopeOrchestrator:
    """
    Manages the full multi-agent research pipeline.

    Uses asyncio.gather for true parallel execution of research agents.
    LangGraph is used for state management and graph definition.
    """

    def __init__(self) -> None:
        self._routing_agent = RoutingAgent()
        self._linkedin_agent = LinkedInAgent()
        self._github_agent = GitHubAgent()
        self._web_research_agent = WebResearchAgent()
        self._fit_scorer_agent = FitScorerAgent()
        self._synthesizer_agent = SynthesizerAgent()

    async def run(self, state: ResearchJobState) -> ResearchJobState:
        """
        Execute the full pipeline:
        1. Routing (sync, decides agents)
        2. Parallel research (LinkedIn + GitHub + Web)
        3. Fit Scorer (depends on research outputs)
        4. Synthesizer (depends on all above)
        """
        logger.info("pipeline_started", job_id=str(state.job_id))
        state.status = JobStatus.ROUTING

        # Step 1: Routing
        state = await self._routing_agent.run(state)
        state.status = JobStatus.RESEARCHING

        # Step 2: Parallel research agents
        research_tasks = []
        if AgentName.LINKEDIN in state.agents_to_run:
            research_tasks.append(self._linkedin_agent.run(state))
        if AgentName.GITHUB in state.agents_to_run:
            research_tasks.append(self._github_agent.run(state))
        if AgentName.WEB_RESEARCH in state.agents_to_run:
            research_tasks.append(self._web_research_agent.run(state))

        if research_tasks:
            results = await asyncio.gather(*research_tasks, return_exceptions=True)
            # Merge results back into state
            for result in results:
                if isinstance(result, Exception):
                    logger.error("parallel_agent_error", error=str(result))
                    continue
                state = self._merge_state(state, result)

        state.status = JobStatus.SCORING

        # Step 3: Fit Scorer (sequential — depends on research)
        if AgentName.FIT_SCORER in state.agents_to_run:
            state = await self._fit_scorer_agent.run(state)

        state.status = JobStatus.SYNTHESIZING

        # Step 4: Synthesizer (sequential — depends on everything)
        if AgentName.SYNTHESIZER in state.agents_to_run:
            state = await self._synthesizer_agent.run(state)

        state.status = JobStatus.COMPLETED
        from datetime import datetime
        state.completed_at = datetime.utcnow()

        logger.info(
            "pipeline_completed",
            job_id=str(state.job_id),
            errors=list(state.errors.keys()),
            hire_score=state.fit_score_data.hire_score if state.fit_score_data else None,
        )

        return state

    def _merge_state(
        self, base: ResearchJobState, updated: ResearchJobState
    ) -> ResearchJobState:
        """
        Merge parallel agent outputs back into the base state.
        Only overwrites fields that the agent populated.
        """
        if updated.linkedin_data and not base.linkedin_data:
            base.linkedin_data = updated.linkedin_data
        if updated.github_data and not base.github_data:
            base.github_data = updated.github_data
        if updated.web_research_data and not base.web_research_data:
            base.web_research_data = updated.web_research_data

        # Merge progress events
        base.progress_events.extend(
            e for e in updated.progress_events if e not in base.progress_events
        )
        # Merge errors
        base.errors.update(updated.errors)

        return base