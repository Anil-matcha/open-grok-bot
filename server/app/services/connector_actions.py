"""Explicit connector action definitions and chat command parsing."""

import shlex
import re
from typing import Optional

from app.services.action_gateway import ActionDefinition, ActionInvocation, action_gateway
from app.services.composio_service import ConnectorServiceError, composio_service


class ConnectorCommandError(ValueError):
    """Raised when an explicit connector command is malformed."""


_SAFE_REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def _validate_repository(owner: str, repo: str) -> None:
    if not _SAFE_REPOSITORY_PART.fullmatch(owner) or not _SAFE_REPOSITORY_PART.fullmatch(repo):
        raise ConnectorCommandError("Repository owner and name may contain only letters, numbers, dots, dashes, and underscores.")


def parse_connector_command(prompt: str) -> Optional[ActionInvocation]:
    """Parse the first governed connector command.

    Supported forms:
      /connector github issues <owner>/<repo> [open|closed|all]
      /connector github create-issue <owner>/<repo> <title>
      /connector github create-issue <owner>/<repo>\n<title>\n[body]
    """

    text = (prompt or "").strip()
    if not text.lower().startswith("/connector"):
        return None

    lines = text.split("\n", 1)
    try:
        parts = shlex.split(lines[0])
    except ValueError as exc:
        raise ConnectorCommandError(f"Invalid connector command: {exc}") from exc

    if len(parts) < 4 or parts[0].lower() != "/connector":
        raise ConnectorCommandError(
            "Use /connector github issues <owner>/<repo> [open|closed|all] or /connector github create-issue <owner>/<repo> <title>."
        )
    if parts[1].lower() != "github":
        raise ConnectorCommandError("The supported connector actions currently target GitHub.")

    repository = parts[3].split("/")
    if len(repository) != 2 or not all(repository):
        raise ConnectorCommandError("Repository must use the owner/repo form.")
    owner, repo = repository
    _validate_repository(owner, repo)
    operation = parts[2].lower()
    if operation == "issues":
        if len(parts) not in {4, 5} or len(lines) != 1:
            raise ConnectorCommandError(
                "Use /connector github issues <owner>/<repo> [open|closed|all]."
            )
        state = parts[4].lower() if len(parts) == 5 else "open"
        if state not in {"open", "closed", "all"}:
            raise ConnectorCommandError("Issue state must be open, closed, or all.")

        return ActionInvocation(
            name="connector.github_list_issues",
            arguments={"owner": owner, "repo": repo, "state": state, "per_page": 10},
            target={"connector": "github", "repository": f"{owner}/{repo}"},
            preview=f"List {state} GitHub issues in {owner}/{repo}",
        )

    if operation == "create-issue":
        if len(parts) == 4:
            if len(lines) != 2:
                raise ConnectorCommandError(
                    "Add the issue title after the repository, either quoted or on the next line."
                )
            title_and_body = lines[1].split("\n", 1)
            title = title_and_body[0].strip()
            body = title_and_body[1] if len(title_and_body) == 2 else ""
        else:
            title = " ".join(parts[4:]).strip()
            body = lines[1] if len(lines) == 2 else ""
        if not title:
            raise ConnectorCommandError("A GitHub issue title is required.")
        if len(title) > 256:
            raise ConnectorCommandError("A GitHub issue title must be at most 256 characters.")
        if len(body) > 10000:
            raise ConnectorCommandError("A GitHub issue body must be at most 10000 characters.")
        return ActionInvocation(
            name="connector.github_create_issue",
            arguments={"owner": owner, "repo": repo, "title": title, "body": body},
            target={"connector": "github", "repository": f"{owner}/{repo}"},
            preview=f"Create a GitHub issue in {owner}/{repo}: {title}",
            display_arguments={
                "owner": owner,
                "repo": repo,
                "title": title,
                "body_bytes": len(body.encode("utf-8")),
            },
        )

    raise ConnectorCommandError("Supported GitHub actions are issues and create-issue.")


async def execute_github_list_issues(call: ActionInvocation):
    try:
        return await composio_service.list_github_issues(
            owner=call.arguments["owner"],
            repo=call.arguments["repo"],
            state=call.arguments["state"],
            per_page=call.arguments["per_page"],
        )
    except (KeyError, TypeError) as exc:
        raise ConnectorServiceError("The GitHub issue action arguments are invalid.") from exc


async def execute_github_create_issue(call: ActionInvocation):
    try:
        return await composio_service.create_github_issue(
            owner=call.arguments["owner"],
            repo=call.arguments["repo"],
            title=call.arguments["title"],
            body=call.arguments.get("body", ""),
        )
    except (KeyError, TypeError) as exc:
        raise ConnectorServiceError("The GitHub create-issue arguments are invalid.") from exc


action_gateway.register_action(
    ActionDefinition(
        name="connector.github_list_issues",
        tool="connector",
        action="github_list_issues",
        intent="Read issue summaries from a connected GitHub repository.",
        risk="read",
        requires_approval=False,
    ),
    execute_github_list_issues,
)

action_gateway.register_action(
    ActionDefinition(
        name="connector.github_create_issue",
        tool="connector",
        action="github_create_issue",
        intent="Create an issue in a connected GitHub repository.",
        risk="write",
        requires_approval=True,
    ),
    execute_github_create_issue,
)
