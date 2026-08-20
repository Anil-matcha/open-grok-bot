import os
from pathlib import Path

class Settings:
    MUAPI_API_KEY: str = os.getenv("MUAPI_API_KEY", "")
    MUAPI_BASE_URL: str = os.getenv("MUAPI_BASE_URL", "https://api.muapi.ai/api/v1").rstrip("/")
    COMPOSIO_API_KEY: str = os.getenv("COMPOSIO_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "grok-4-5")
    DATA_DIR: Path = Path(
        os.getenv("DATA_DIR", str(Path.home() / ".open-grok-bot"))
    ).expanduser().resolve()
    WORKSPACE_ROOT: Path = Path(
        os.getenv("WORKSPACE_ROOT", str(Path(__file__).resolve().parents[2]))
    ).expanduser().resolve()
    WORKSPACE_MAX_FILE_BYTES: int = int(os.getenv("WORKSPACE_MAX_FILE_BYTES", "131072"))
    APPROVAL_TIMEOUT_SECONDS: int = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "120"))
    AUTH_SESSION_MAX_AGE: int = int(os.getenv("AUTH_SESSION_MAX_AGE", "86400"))
    AUTH_COOKIE_SECURE: bool = os.getenv("AUTH_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    COMPUTER_PROVIDER: str = os.getenv("COMPUTER_PROVIDER", "fake").strip().lower()
    COMPUTER_DOCKER_IMAGE: str = os.getenv(
        "COMPUTER_DOCKER_IMAGE", "open-grok-bot-computer:1.62.1"
    ).strip()
    COMPUTER_DOCKER_BINARY: str = os.getenv("COMPUTER_DOCKER_BINARY", "docker").strip()
    COMPUTER_DOCKER_WORKSPACE_ROOT: Path = Path(
        os.getenv("COMPUTER_DOCKER_WORKSPACE_ROOT", str(DATA_DIR / "computers"))
    ).expanduser().resolve()
    COMPUTER_DOCKER_CPU_LIMIT: str = os.getenv("COMPUTER_DOCKER_CPU_LIMIT", "2.0").strip()
    COMPUTER_DOCKER_MEMORY_LIMIT: str = os.getenv("COMPUTER_DOCKER_MEMORY_LIMIT", "2g").strip()
    COMPUTER_DOCKER_PIDS_LIMIT: int = int(os.getenv("COMPUTER_DOCKER_PIDS_LIMIT", "512"))
    COMPUTER_DOCKER_START_TIMEOUT: float = float(
        os.getenv("COMPUTER_DOCKER_START_TIMEOUT", "20")
    )
    COMPUTER_DOCKER_COMMAND_TIMEOUT: float = float(
        os.getenv("COMPUTER_DOCKER_COMMAND_TIMEOUT", "30")
    )
    COMPUTER_DOCKER_RUNTIME_PORT: int = int(os.getenv("COMPUTER_DOCKER_RUNTIME_PORT", "3000"))
    COMPUTER_DOCKER_SECCOMP_PROFILE: Path = Path(
        os.getenv(
            "COMPUTER_DOCKER_SECCOMP_PROFILE",
            str(Path(__file__).resolve().parents[2] / "runtime" / "seccomp_profile.json"),
        )
    ).expanduser().resolve()
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:3000,http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.COMPUTER_DOCKER_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

settings = Settings()
