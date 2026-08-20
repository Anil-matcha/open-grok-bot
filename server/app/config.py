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
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
