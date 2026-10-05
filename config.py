"""Central, env-driven settings for Milestone 3 (read once, import everywhere)."""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://persona:persona@localhost:5432/persona_platform")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "").strip()
    EMBEDDING_DIM = _int("EMBEDDING_DIM", 1536)
    LLM_TIMEOUT_SECONDS = _int("LLM_TIMEOUT_SECONDS", 90)
    LLM_MAX_CONCURRENCY = _int("LLM_MAX_CONCURRENCY", 5)
    PERSONA_CONCURRENCY = _int("PERSONA_CONCURRENCY", 4)
    SURVEY_LLM_VALIDATION = _bool("SURVEY_LLM_VALIDATION", True)
    MAX_RESPONSE_ATTEMPTS = _int("MAX_RESPONSE_ATTEMPTS", 2)
    MEMORY_TOP_K = _int("MEMORY_TOP_K", 6)
    INTERVIEW_WINDOW_TURNS = _int("INTERVIEW_WINDOW_TURNS", 4)
    API_KEY = os.getenv("API_KEY", "").strip()
    RATE_LIMIT_PER_MINUTE = _int("RATE_LIMIT_PER_MINUTE", 120)
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 10)
    MAX_DOC_CONTEXT_CHARS = _int("MAX_DOC_CONTEXT_CHARS", 4000)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    ENV = os.getenv("NODE_ENV", os.getenv("APP_ENV", "development"))


settings = Settings()
