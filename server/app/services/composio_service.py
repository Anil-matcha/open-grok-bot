"""Small Composio adapter used by governed connector actions."""

import json
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.services.storage_service import StorageService, storage_service


CONNECT_URL = "https://connect.composio.dev/mcp"
GITHUB_LIST_ISSUES_TOOL = "GITHUB_LIST_REPOSITORY_ISSUES"
GITHUB_CREATE_ISSUE_TOOL = "GITHUB_CREATE_AN_ISSUE"
_SAFE_GITHUB_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


class ConnectorServiceError(ValueError):
    """Raised when a connector action cannot be validated or completed."""


def parse_mcp_response(text: str) -> Dict[str, Any]:
    line = text if text.lstrip().startswith("{") else next(
        (item[6:] for item in text.splitlines() if item.startswith("data: ")), None
    )
    if not line:
        raise ConnectorServiceError("The connector returned an empty response.")

    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ConnectorServiceError("The connector returned invalid JSON.") from exc
    if message.get("error"):
        error = message["error"]
        raise ConnectorServiceError(error.get("message", "The connector returned an error."))

    content = next(
        (
            item.get("text")
            for item in (message.get("result", {}).get("content") or [])
            if item.get("type") == "text"
        ),
        None,
    )
    if not content:
        result = message.get("result") or {}
        return result if isinstance(result, dict) else {"data": result}
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return {"text": content}
    return decoded if isinstance(decoded, dict) else {"data": decoded}


class ComposioService:
    def __init__(self, storage: StorageService = storage_service):
        self.storage = storage

    def get_api_key(self) -> str:
        config = self.storage.get_settings()
        return str(
            config.get("composio_api_key")
            or config.get("composio_key")
            or settings.COMPOSIO_API_KEY
            or ""
        )

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = api_key or self.get_api_key()
        if not key:
            raise ConnectorServiceError(
                "Configure a Composio API key and connect GitHub before using connector actions."
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                CONNECT_URL,
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                    "x-consumer-api-key": key,
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            response.raise_for_status()
            return parse_mcp_response(response.text)

    @staticmethod
    def _validate_github_part(value: str, label: str) -> str:
        if not isinstance(value, str) or not _SAFE_GITHUB_PART.fullmatch(value):
            raise ConnectorServiceError(f"GitHub {label} is invalid.")
        return value

    async def list_github_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 10,
    ) -> Dict[str, Any]:
        owner = self._validate_github_part(owner, "owner")
        repo = self._validate_github_part(repo, "repository")
        if state not in {"open", "closed", "all"}:
            raise ConnectorServiceError("Issue state must be open, closed, or all.")
        if not isinstance(per_page, int) or not 1 <= per_page <= 20:
            raise ConnectorServiceError("Issue page size must be between 1 and 20.")

        response = await self.call_tool(
            GITHUB_LIST_ISSUES_TOOL,
            {
                "owner": owner,
                "repo": repo,
                "state": state,
                "per_page": per_page,
            },
        )
        payload = response.get("data", response)
        if isinstance(payload, dict) and payload.get("successful") is False:
            raise ConnectorServiceError(payload.get("error") or "GitHub issue lookup failed.")
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]

        if isinstance(payload, list):
            raw_issues = payload
        elif isinstance(payload, dict):
            raw_issues = payload.get("issues") or payload.get("items") or []
        else:
            raw_issues = []

        issues = []
        for item in raw_issues[:per_page]:
            if not isinstance(item, dict):
                continue
            labels = item.get("labels") or []
            issues.append(
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "url": item.get("html_url") or item.get("url"),
                    "author": (item.get("user") or {}).get("login"),
                    "labels": [
                        label.get("name")
                        for label in labels
                        if isinstance(label, dict) and label.get("name")
                    ],
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
            )

        return {
            "connector": "github",
            "operation": "list_issues",
            "repository": f"{owner}/{repo}",
            "state": state,
            "count": len(issues),
            "issues": issues,
        }

    async def create_github_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
    ) -> Dict[str, Any]:
        owner = self._validate_github_part(owner, "owner")
        repo = self._validate_github_part(repo, "repository")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 256:
            raise ConnectorServiceError("Issue title must be between 1 and 256 characters.")
        if not isinstance(body, str) or len(body) > 10000:
            raise ConnectorServiceError("Issue body must be at most 10000 characters.")

        response = await self.call_tool(
            GITHUB_CREATE_ISSUE_TOOL,
            {
                "owner": owner,
                "repo": repo,
                "title": title.strip(),
                "body": body,
            },
        )
        payload = response.get("data", response)
        if isinstance(payload, dict) and payload.get("successful") is False:
            raise ConnectorServiceError(payload.get("error") or "GitHub issue creation failed.")
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            payload = {}

        return {
            "connector": "github",
            "operation": "create_issue",
            "repository": f"{owner}/{repo}",
            "created": True,
            "issue": {
                "number": payload.get("number"),
                "title": payload.get("title") or title.strip(),
                "state": payload.get("state") or "open",
                "url": payload.get("html_url") or payload.get("url"),
            },
        }


composio_service = ComposioService()
