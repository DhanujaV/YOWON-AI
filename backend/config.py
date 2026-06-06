"""
config.py — Central configuration for Project Sentinel.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
CHROMA_DIR = BASE_DIR / "chroma_db"

UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3:8b")

OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

OLLAMA_SPECIALIST_MODEL: str = os.getenv("OLLAMA_SPECIALIST_MODEL", "qwen2.5:3b")
OLLAMA_CHIEF_MODEL: str = os.getenv("OLLAMA_CHIEF_MODEL", "qwen3:8b")
OLLAMA_FAST_MODEL: str = os.getenv("OLLAMA_FAST_MODEL", "qwen2.5:3b")
OLLAMA_FALLBACK_MODEL: str = os.getenv("OLLAMA_FALLBACK_MODEL", "qwen2.5:3b")

AGENT_MODEL_PROFILES: dict[str, str] = {
    "coordinator": "specialist",
    "technical": "specialist",
    "engineering": "specialist",
    "security": "specialist",
    "presentation": "specialist",
    "innovation": "specialist",
    "risk": "specialist",
    "chief": "chief",
}

OLLAMA_PARALLEL: int = int(os.getenv("OLLAMA_PARALLEL", "2"))
AGENT_MAX_RETRIES: int = int(os.getenv("AGENT_MAX_RETRIES", "2"))
AGENT_RETRY_DELAY_SEC: float = float(os.getenv("AGENT_RETRY_DELAY_SEC", "1.5"))

# CrewAI agent limits — single LLM pass, up to 10 minutes per agent
AGENT_MAX_ITER: int = int(os.getenv("AGENT_MAX_ITER", "1"))
AGENT_MAX_EXECUTION_TIME: int = int(os.getenv("AGENT_MAX_EXECUTION_TIME", "600"))
CHIEF_MAX_EXECUTION_TIME: int = int(os.getenv("CHIEF_MAX_EXECUTION_TIME", "600"))

# Ollama generation (specialist / chief)
OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_SPECIALIST_NUM_PREDICT: int = int(os.getenv("OLLAMA_SPECIALIST_NUM_PREDICT", "200"))
OLLAMA_CHIEF_NUM_PREDICT: int = int(os.getenv("OLLAMA_CHIEF_NUM_PREDICT", "300"))
OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))

# Chief model fallback chain (comma-separated models). First item is primary.
CHIEF_MODEL_CHAIN: str = os.getenv(
    "CHIEF_MODEL_CHAIN",
    "deepseek-r1:8b,qwen2.5:7b,qwen2.5:3b",
)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR}/sentinel.db",
)

CHROMA_COLLECTION_NAME: str = "sentinel_projects"

CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")

MAX_GITHUB_FILE_BYTES: int = 1_000_000
MAX_PDF_PAGES: int = 100
MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
MAX_BRIEF_CHARS: int = int(os.getenv("MAX_BRIEF_CHARS", "1200"))
MAX_AGENT_DIGEST_CHARS: int = int(os.getenv("MAX_AGENT_DIGEST_CHARS", "2500"))

# Thread pool / futures must allow full agent runtime
AGENT_TIMEOUT_SEC: int = int(os.getenv("AGENT_TIMEOUT_SEC", "600"))
EVALUATION_TIMEOUT_SEC: int = int(os.getenv("EVALUATION_TIMEOUT_SEC", "3600"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

FAILED_AGENT_SCORE: int = int(os.getenv("FAILED_AGENT_SCORE", "35"))

# Prefer direct Ollama call when CrewAI returns abort text (faster, no iteration loop)
USE_DIRECT_LLM_PRIMARY: bool = os.getenv("USE_DIRECT_LLM_PRIMARY", "true").lower() in (
    "1",
    "true",
    "yes",
)
