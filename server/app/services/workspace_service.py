import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings


class WorkspaceToolError(ValueError):
    """Raised when a workspace request is invalid or outside the workspace root."""


@dataclass(frozen=True)
class WorkspaceToolCall:
    name: str
    path: str
    content: Optional[str] = None

    @property
    def arguments_for_display(self) -> Dict[str, Any]:
        args: Dict[str, Any] = {"path": self.path}
        if self.content is not None:
            args["bytes"] = len(self.content.encode("utf-8"))
        return args

    @property
    def summary(self) -> str:
        if self.name == "workspace.read":
            return f"Read the workspace file: {self.path}"
        if self.name == "workspace.write":
            return f"Write {len(self.content or '')} characters to: {self.path}"
        return f"List the workspace directory: {self.path}"


def parse_workspace_command(prompt: str) -> Optional[WorkspaceToolCall]:
    """Parse an explicit, non-shell workspace command from a user turn.

    Supported forms:
      /workspace list [path]
      /workspace read <path>
      /workspace write <path>\n<content>
    """
    text = (prompt or "").strip()
    if not text.lower().startswith("/workspace"):
        return None

    lines = text.split("\n", 1)
    try:
        header = shlex.split(lines[0])
    except ValueError as exc:
        raise WorkspaceToolError(f"Invalid workspace command: {exc}") from exc

    if len(header) < 2 or header[0].lower() != "/workspace":
        raise WorkspaceToolError("Use /workspace list, /workspace read, or /workspace write.")

    action = header[1].lower()
    if action not in {"list", "read", "write"}:
        raise WorkspaceToolError("Supported workspace actions are list, read, and write.")

    if action == "write":
        if len(header) != 3 or len(lines) != 2 or not lines[1]:
            raise WorkspaceToolError(
                "Write syntax: /workspace write <path> followed by file content on the next line."
            )
        return WorkspaceToolCall("workspace.write", header[2], lines[1])

    if len(header) > 3:
        raise WorkspaceToolError(f"{action.title()} accepts one path argument.")

    path = header[2] if len(header) == 3 else "."
    return WorkspaceToolCall(f"workspace.{action}", path)


class WorkspaceService:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _resolve(self, user_path: str, must_exist: bool = False) -> Path:
        if not user_path or "\x00" in user_path:
            raise WorkspaceToolError("A workspace-relative path is required.")

        candidate = Path(user_path).expanduser()
        if candidate.is_absolute():
            raise WorkspaceToolError("Absolute paths are not allowed.")

        resolved = (self.root / candidate).resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise WorkspaceToolError("That path is outside the configured workspace.")
        if must_exist and not resolved.exists():
            raise WorkspaceToolError(f"Workspace path does not exist: {user_path}")
        if resolved == self.root:
            return resolved
        return resolved

    def execute(self, call: WorkspaceToolCall) -> Dict[str, Any]:
        if call.name == "workspace.list":
            return self._list(call.path)
        if call.name == "workspace.read":
            return self._read(call.path)
        if call.name == "workspace.write":
            return self._write(call.path, call.content or "")
        raise WorkspaceToolError(f"Unknown workspace tool: {call.name}")

    def _list(self, user_path: str) -> Dict[str, Any]:
        directory = self._resolve(user_path, must_exist=True)
        if not directory.is_dir():
            raise WorkspaceToolError(f"Not a directory: {user_path}")

        entries = []
        for child in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
            safe_child = self._resolve(str(child.relative_to(self.root)))
            kind = "dir" if safe_child.is_dir() else "file"
            entries.append({"name": safe_child.name, "kind": kind})
        return {"path": user_path, "entries": entries}

    def _read(self, user_path: str) -> Dict[str, Any]:
        path = self._resolve(user_path, must_exist=True)
        if not path.is_file():
            raise WorkspaceToolError(f"Not a file: {user_path}")
        size = path.stat().st_size
        if size > settings.WORKSPACE_MAX_FILE_BYTES:
            raise WorkspaceToolError(
                f"File is larger than the {settings.WORKSPACE_MAX_FILE_BYTES}-byte limit."
            )
        return {"path": user_path, "content": path.read_text(encoding="utf-8"), "bytes": size}

    def _write(self, user_path: str, content: str) -> Dict[str, Any]:
        path = self._resolve(user_path)
        if path == self.root:
            raise WorkspaceToolError("A file path is required for workspace.write.")
        if path.exists() and path.is_dir():
            raise WorkspaceToolError(f"Cannot write to a directory: {user_path}")

        encoded = content.encode("utf-8")
        if len(encoded) > settings.WORKSPACE_MAX_FILE_BYTES:
            raise WorkspaceToolError(
                f"Content is larger than the {settings.WORKSPACE_MAX_FILE_BYTES}-byte limit."
            )
        if not path.parent.exists() or not path.parent.is_dir():
            raise WorkspaceToolError("The destination directory must already exist.")

        path.write_text(content, encoding="utf-8")
        return {"path": user_path, "bytes": len(encoded), "written": True}


workspace_service = WorkspaceService(settings.WORKSPACE_ROOT)
