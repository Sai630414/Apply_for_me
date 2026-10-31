import os
from typing import List, Union, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ApplyForMe"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # MongoDB Atlas (or local)
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI (local or MongoDB Atlas Azure)"
    )
    MONGODB_DB_NAME: str = "applyforme"

    # JWT Security
    JWT_SECRET_KEY: str = "dev_secret_key_applyforme_local_2026_secure_key_for_testing"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # LLM Provider configuration (ollama or groq)
    LLM_PROVIDER: str = "groq"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.4
    LLM_TIMEOUT_SECONDS: float = 120.0
    LLM_CONCURRENCY: int = 3
    # OmniRoute LLM Gateway (deprecated)
    OMNIROUTE_BASE_URL: str = "https://api.omniroute.ai/v1"
    OMNIROUTE_API_KEY: str = ""
    OMNIROUTE_MODEL: str = "gemini-1.5-flash"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "chrome-extension://dccdppkggcalleledhmbclldddnokhok",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = r"^chrome-extension://.*$"

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            origins = [i.strip() for i in v.split(",") if i.strip()]
        else:
            origins = list(v)
        # Never mix wildcard '*' with credentials
        return [o for o in origins if o != "*"]

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

