"""
Application configuration using Pydantic Settings.

Responsibilities:
- Load environment variables
- Validate configuration
- Provide a singleton settings object

Follows SRP (Single Responsibility Principle)
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings loaded from .env
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =====================================================
    # GROQ LLM
    # =====================================================

    groq_api_key: str = Field(
        ...,
        description="Groq API Key"
    )

    groq_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq model name"
    )

    groq_temperature: float = Field(
        default=0.0,
        description="LLM temperature"
    )

    groq_max_tokens: int = Field(
        default=2000,
        description="Maximum output tokens"
    )

    # =====================================================
    # EMBEDDINGS
    # =====================================================

    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence Transformer model"
    )

    # =====================================================
    # CHROMADB
    # =====================================================

    chroma_persist_path: str = Field(
        default="./chroma_db"
    )

    # =====================================================
    # APP
    # =====================================================

    app_env: str = Field(
        default="development"
    )

    log_level: str = Field(
        default="INFO"
    )

    # =====================================================
    # VALIDATORS
    # =====================================================

    @field_validator("groq_temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError(
                "groq_temperature must be between 0 and 1"
            )
        return value

    # =====================================================
    # HELPERS
    # =====================================================

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    """

    return Settings()