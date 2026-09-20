import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Intelligent Knowledge Archive"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/historical_archive"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/historical_archive"

    # Storage
    STORAGE_BACKEND: str = "local"  # local or s3
    STORAGE_LOCAL_DIR: str = "./storage/data"
    S3_BUCKET_NAME: str = ""
    S3_ENDPOINT_URL: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    # AI & Embeddings
    AI_PROVIDER: str = "mock"  # gemini, openai, or mock
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    OPENAI_API_KEY: str = ""

    EMBEDDING_PROVIDER: str = "gemini"  # gemini, sentence_transformers, or mock
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768

    # Processing
    OCR_ENABLED: bool = True
    MAX_CHUNK_TOKENS: int = 500
    CHUNK_OVERLAP_TOKENS: int = 50

    # Jobs & Workers
    WORKER_CONCURRENCY: int = 2
    JOB_LEASE_SECONDS: int = 300
    MAX_JOB_RETRIES: int = 3

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
