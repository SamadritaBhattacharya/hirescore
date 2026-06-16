"""
Routing Agent.

Responsibilities:
- Inspect available inputs
- Decide which research agents to activate
- Set state.agents_to_run
- Log routing decisions for observability
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from models.schemas import AgentName, ResearchJobState
from core.logging import get_logger

logger = get_logger(__name__)


class RoutingAgent(BaseAgent):
    """
    Determines which agents fire based on available inputs.
    Always runs first — single pass, synchronous decision logic.
    """

    def __init__(self) -> None:
        super().__init__(name=AgentName.ROUTING, timeout_seconds=5)

    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        agents: list[AgentName] = []

        # LinkedIn always runs (required input)
        if state.input.linkedin_url or state.input.linkedin_text:
            agents.append(AgentName.LINKEDIN)

        # GitHub runs only if URL provided
        if state.input.github_url:
            agents.append(AgentName.GITHUB)

        # Web research always runs (searches are general enough)
        agents.append(AgentName.WEB_RESEARCH)

        # Fit scorer always runs (handles both JD and no-JD modes)
        agents.append(AgentName.FIT_SCORER)

        # Synthesizer always runs last
        agents.append(AgentName.SYNTHESIZER)

        state.agents_to_run = agents

        logger.info(
            "routing_decided",
            job_id=str(state.job_id),
            agents=[a.value for a in agents],
            has_linkedin=bool(state.input.linkedin_url or state.input.linkedin_text),
            has_github=bool(state.input.github_url),
            has_jd=bool(state.input.jd_text),
            has_resume=bool(state.input.resume_text),
            has_culture=bool(state.input.culture_doc_text),
        )

        return state