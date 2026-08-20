"""Provider-neutral computer runtime contract and deterministic local adapter.

The application talks to a computer through this contract rather than through
vendor-specific browser, desktop, or container APIs. The fake adapter keeps
the lifecycle and action shapes usable in local development and tests without
launching processes; the optional Docker adapter supplies the isolated runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import posixpath
import re
from typing import Any, Dict, Literal, Optional, Protocol, Tuple
from urllib.parse import urlparse


ComputerState = Literal["stopped", "starting", "running", "paused", "resetting", "error"]
ComputerHealth = Literal["unknown", "healthy", "unhealthy"]

COMPUTER_CAPABILITIES: Tuple[str, ...] = (
    "browser.navigate",
    "terminal.exec",
    "files.list",
    "screenshot",
    "input",
    "cleanup",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _computer_id(bot_id: str) -> str:
    if not isinstance(bot_id, str) or not bot_id.strip():
        raise ComputerProviderError("A bot id is required to create a computer.")
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", bot_id.strip()).strip("-")
    if not normalized:
        raise ComputerProviderError("The bot id cannot produce a valid computer id.")
    return f"computer-{normalized[:80]}"


def computer_id_for_bot(bot_id: str) -> str:
    """Return the stable provider id without creating a runtime."""

    return _computer_id(bot_id)


@dataclass
class ComputerStatus:
    computer_id: str
    bot_id: str
    provider: str
    state: ComputerState
    health: ComputerHealth
    width: int
    height: int
    fps: int
    generation: int
    capabilities: Tuple[str, ...]
    updated_at: str
    frame_id: Optional[str] = None
    url: Optional[str] = None
    last_operation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["capabilities"] = list(self.capabilities)
        return value


class ComputerProviderError(RuntimeError):
    """Raised when a computer adapter cannot satisfy a requested operation."""


class ComputerProvider(Protocol):
    """The contract a real browser/desktop provider must implement."""

    def describe(self, bot_id: str) -> ComputerStatus:
        ...

    def get_or_create(self, bot_id: str) -> ComputerStatus:
        ...

    async def create(self, bot_id: str) -> ComputerStatus:
        ...

    async def start(self, computer_id: str) -> ComputerStatus:
        ...

    async def stop(self, computer_id: str) -> ComputerStatus:
        ...

    async def pause(self, computer_id: str) -> ComputerStatus:
        ...

    async def reset(self, computer_id: str) -> ComputerStatus:
        ...

    async def health(self, computer_id: str) -> ComputerStatus:
        ...

    async def browser_navigate(self, computer_id: str, url: str) -> Dict[str, Any]:
        ...

    async def terminal_execute(self, computer_id: str, command: str) -> Dict[str, Any]:
        ...

    async def files_list(self, computer_id: str, path: str = "/workspace") -> Dict[str, Any]:
        ...

    async def screenshot(self, computer_id: str) -> Dict[str, Any]:
        ...

    async def send_input(self, computer_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        ...

    async def cleanup(self, computer_id: str) -> Dict[str, Any]:
        ...


class FakeComputerProvider:
    """Deterministic in-memory provider used until an isolated runtime exists."""

    provider_name = "fake"

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self._computers: Dict[str, ComputerStatus] = {}
        self._frame_counts: Dict[str, int] = {}

    def get_or_create(self, bot_id: str) -> ComputerStatus:
        computer_id = _computer_id(bot_id)
        existing = self._computers.get(computer_id)
        if existing is not None:
            return existing
        status = ComputerStatus(
            computer_id=computer_id,
            bot_id=bot_id.strip(),
            provider=self.provider_name,
            state="stopped",
            health="unknown",
            width=self.width,
            height=self.height,
            fps=self.fps,
            generation=1,
            capabilities=COMPUTER_CAPABILITIES,
            updated_at=_now(),
        )
        self._computers[computer_id] = status
        self._frame_counts[computer_id] = 0
        return status

    def describe(self, bot_id: str) -> ComputerStatus:
        """Return status without creating a runtime or starting a process."""

        existing = self._computers.get(_computer_id(bot_id))
        if existing is not None:
            return existing
        return ComputerStatus(
            computer_id=_computer_id(bot_id),
            bot_id=bot_id.strip(),
            provider=self.provider_name,
            state="stopped",
            health="unknown",
            width=self.width,
            height=self.height,
            fps=self.fps,
            generation=0,
            capabilities=COMPUTER_CAPABILITIES,
            updated_at=_now(),
        )

    def _get(self, computer_id: str) -> ComputerStatus:
        if not isinstance(computer_id, str) or not computer_id.strip():
            raise ComputerProviderError("A computer id is required.")
        status = self._computers.get(computer_id)
        if status is None:
            raise ComputerProviderError("The requested computer does not exist.")
        return status

    @staticmethod
    def _touch(status: ComputerStatus, operation: str) -> ComputerStatus:
        status.last_operation = operation
        status.updated_at = _now()
        return status

    def _require_active(self, computer_id: str) -> ComputerStatus:
        status = self._get(computer_id)
        if status.state not in {"running", "paused"}:
            raise ComputerProviderError(
                f"Computer is not active; current state is {status.state}."
            )
        return status

    async def create(self, bot_id: str) -> ComputerStatus:
        return self.get_or_create(bot_id)

    async def start(self, computer_id: str) -> ComputerStatus:
        status = self._get(computer_id)
        if status.state == "running":
            return self._touch(status, "start")
        status.state = "starting"
        status.health = "unknown"
        self._touch(status, "start")
        status.state = "running"
        status.health = "healthy"
        return self._touch(status, "start")

    async def stop(self, computer_id: str) -> ComputerStatus:
        status = self._get(computer_id)
        status.state = "stopped"
        status.health = "unknown"
        status.frame_id = None
        return self._touch(status, "stop")

    async def pause(self, computer_id: str) -> ComputerStatus:
        status = self._get(computer_id)
        if status.state not in {"running", "paused"}:
            raise ComputerProviderError(
                f"Computer must be running before it can be paused; current state is {status.state}."
            )
        status.state = "paused"
        status.health = "healthy"
        return self._touch(status, "pause")

    async def reset(self, computer_id: str) -> ComputerStatus:
        status = self._get(computer_id)
        status.state = "resetting"
        status.health = "unknown"
        status.generation += 1
        status.frame_id = None
        status.url = None
        self._frame_counts[computer_id] = 0
        status.state = "stopped"
        return self._touch(status, "reset")

    async def health(self, computer_id: str) -> ComputerStatus:
        status = self._get(computer_id)
        status.health = "healthy" if status.state in {"running", "paused"} else "unknown"
        return self._touch(status, "health")

    async def browser_navigate(self, computer_id: str, url: str) -> Dict[str, Any]:
        status = self._require_active(computer_id)
        if not isinstance(url, str) or len(url.strip()) > 2048:
            raise ComputerProviderError("A browser URL is required and must be at most 2048 characters.")
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ComputerProviderError("Browser navigation only accepts absolute HTTP(S) URLs.")
        status.url = url.strip()
        self._touch(status, "browser.navigate")
        return {
            "computer_id": status.computer_id,
            "provider": self.provider_name,
            "operation": "browser.navigate",
            "url": status.url,
            "state": status.state,
        }

    async def terminal_execute(self, computer_id: str, command: str) -> Dict[str, Any]:
        status = self._require_active(computer_id)
        if not isinstance(command, str) or not command.strip():
            raise ComputerProviderError("A terminal command is required.")
        if len(command) > 4000:
            raise ComputerProviderError("Terminal commands must be at most 4000 characters.")
        self._touch(status, "terminal.exec")
        return {
            "computer_id": status.computer_id,
            "provider": self.provider_name,
            "operation": "terminal.exec",
            "command": command,
            "exit_code": 0,
            "stdout": "[fake computer] command accepted; no process was started.",
            "stderr": "",
        }

    async def files_list(self, computer_id: str, path: str = "/workspace") -> Dict[str, Any]:
        status = self._require_active(computer_id)
        if not isinstance(path, str) or len(path) > 512:
            raise ComputerProviderError("A file path is required and must be at most 512 characters.")
        normalized = posixpath.normpath(path.strip() or "/workspace")
        if not normalized.startswith("/"):
            raise ComputerProviderError("Computer file paths must be absolute.")
        self._touch(status, "files.list")
        return {
            "computer_id": status.computer_id,
            "provider": self.provider_name,
            "operation": "files.list",
            "path": normalized,
            "entries": [
                {"name": "workspace", "kind": "directory"},
                {"name": "README.md", "kind": "file"},
            ],
        }

    async def screenshot(self, computer_id: str) -> Dict[str, Any]:
        status = self._get(computer_id)
        available = status.state in {"running", "paused"}
        if available:
            self._frame_counts[computer_id] = self._frame_counts.get(computer_id, 0) + 1
            status.frame_id = f"frame-{status.generation}-{self._frame_counts[computer_id]}"
        self._touch(status, "screenshot")
        return {
            "computer_id": status.computer_id,
            "provider": self.provider_name,
            "available": available,
            "frame_id": status.frame_id,
            "format": "placeholder",
            "width": status.width,
            "height": status.height,
            "state": status.state,
            "generation": status.generation,
            "data": None,
            "message": (
                "A real screen stream is not configured."
                if not available
                else "Fake provider frame metadata; no desktop process is running."
            ),
        }

    async def send_input(self, computer_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        status = self._require_active(computer_id)
        if not isinstance(event, dict):
            raise ComputerProviderError("Computer input must be a JSON object.")
        event_type = str(event.get("type") or "").lower()
        if event_type not in {"click", "keypress", "type", "scroll"}:
            raise ComputerProviderError("Supported input types are click, keypress, type, and scroll.")
        self._touch(status, "input")
        return {
            "computer_id": status.computer_id,
            "provider": self.provider_name,
            "operation": "input",
            "accepted": True,
            "type": event_type,
        }

    async def cleanup(self, computer_id: str) -> Dict[str, Any]:
        status = self._get(computer_id)
        self._computers.pop(computer_id, None)
        self._frame_counts.pop(computer_id, None)
        return {
            "computer_id": status.computer_id,
            "bot_id": status.bot_id,
            "provider": self.provider_name,
            "state": "cleaned",
            "generation": status.generation,
        }


def build_computer_provider() -> ComputerProvider:
    """Select the configured adapter without making Docker a test prerequisite."""

    from app.config import settings

    if settings.COMPUTER_PROVIDER == "docker":
        from app.services.docker_computer_provider import DockerComputerProvider

        return DockerComputerProvider()
    return FakeComputerProvider()


computer_provider = build_computer_provider()
