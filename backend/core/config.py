"""
Application configuration using Pydantic BaseSettings.
Follows Single Responsibility Principle — only manages config.
All settings are strongly typed and validated at startup.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings loaded from environment variables.
    Validated at startup — app will fail fast on missing required keys.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM ---
    groq_api_key: str = Field(..., description="Groq API key for LLM calls")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier",
    )
    groq_max_tokens: int = Field(default=2048)
    groq_temperature: float = Field(default=0.2)

    # --- Search ---
    tavily_api_key: str = Field(..., description="Tavily API key for web search")
    tavily_max_results: int = Field(default=5)

    # --- GitHub ---
    github_token: str = Field(default="", description="GitHub personal access token")

    # --- LinkedIn ---
    linkedin_email: str = Field(default="", description="LinkedIn email for scraper")
    linkedin_password: str = Field(default="", description="LinkedIn password for scraper")

    # --- Vector Store ---
    chroma_persist_path: str = Field(default="./chroma_db")
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="SentenceTransformer model for local embeddings",
    )

    # --- App ---
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    # --- Research Job ---
    max_concurrent_agents: int = Field(default=3)
    research_timeout_seconds: int = Field(default=120)

    @field_validator("groq_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def linkedin_scraper_enabled(self) -> bool:
        return bool(self.linkedin_email and self.linkedin_password)

    @property
    def github_authenticated(self) -> bool:
        return bool(self.github_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns cached Settings instance.
    Use dependency injection in FastAPI: Depends(get_settings)
    """
    return Settings()