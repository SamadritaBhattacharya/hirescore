"""
LLM Factory.

Responsible only for creating and configuring LLM clients.

Follows:
- Single Responsibility Principle
- Dependency Injection
- Centralized LLM configuration
"""

from functools import lru_cache

from langchain_groq import ChatGroq

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """
    Returns a cached Groq LLM instance.

    Usage:
        llm = get_llm()
        response = llm.invoke("Hello")
    """

    settings = get_settings()

    logger.info(
        "Initializing Groq LLM",
        model=settings.groq_model,
        temperature=settings.groq_temperature,
    )

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.groq_temperature,
        max_tokens=settings.groq_max_tokens,
    )