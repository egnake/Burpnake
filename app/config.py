"""BurpNake configuration management."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Ollama (Primary)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:14b"
    OLLAMA_FALLBACK_MODEL: str = "gemma2:9b"

    # Gemini Free (Secondary)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Gemini Pro (Google One)
    GEMINI_PRO_ENABLED: bool = False
    GEMINI_PRO_MODEL: str = "gemini-1.5-pro"

    # g4f (Tertiary)
    G4F_ENABLED: bool = True

    # Application
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8899
    DEBUG: bool = False

    # Security
    API_KEY: str = ""  # Empty = dev mode (no auth)

    # Agent
    AGENT_MAX_ITERATIONS: int = 12
    AGENT_ITER_DELAY: float = 2.0
    AGENT_TIMEOUT: int = 300

    # Collaborator
    INTERACTSH_SERVER: str = "oast.fun"
    INTERACTSH_TOKEN: str = ""

    # Fuzzer  
    FUZZER_CONCURRENCY: int = 10
    FUZZER_RATE_LIMIT: float = 0.5  # seconds between requests

    # Recon
    SECURITYTRAILS_API_KEY: str = ""

    # Proxy (for outgoing requests)
    OUTBOUND_PROXY: str = ""  # e.g. http://127.0.0.1:8080

    # Licensing
    LICENSE_KEY: str = ""
    LICENSE_TIER: str = "community"  # community, pro, elite

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
