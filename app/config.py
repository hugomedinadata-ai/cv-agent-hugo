"""Configuración leída de variables de entorno (nunca se suben llaves al repositorio)."""
import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-flash-latest")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
TOP_K = int(os.getenv("TOP_K", "6"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "2000"))
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", "65536"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))

LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "gemini-flash-lite-latest")
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low")
LLM_ATTEMPT_TIMEOUT_S = float(os.getenv("LLM_ATTEMPT_TIMEOUT_S", "12"))
LLM_TOTAL_BUDGET_S = float(os.getenv("LLM_TOTAL_BUDGET_S", "42"))
LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "3"))
LLM_RETRY_BASE_DELAY_S = float(os.getenv("LLM_RETRY_BASE_DELAY_S", "0.5"))
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", os.path.join(os.path.dirname(__file__), "..", "knowledge"))

REDIS_URL = os.getenv("REDIS_URL", "")
RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
