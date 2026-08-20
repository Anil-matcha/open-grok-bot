"""Explicit connector action definitions and chat command parsing."""

import shlex
from typing import Optional

from app.services.action_gateway import ActionDefinition, ActionInvocation, action_gateway
from app.services.composio_service import ConnectorServiceError, composio_service


class ConnectorCommandError(ValueError):
    """Raised when an explicit connector command is malformed."""


def parse_connector_command(prompt: str) -> Optional[ActionInvocation]:
    """Parse the first governed connector command.

    Supported form:
      /connector github issues <owner>/<repo> [open|closed|all]
    """

    text = (prompt or "").strip()
    if not text.lower().startswith("/connector"):
        return None

    try:
        parts = shlex.split(text)
    except ValueError as exc:
        raise ConnectorCommandError(f"Invalid connector command: {exc}") from exc

    if len(parts) not in {4, 5} or parts[0].lower() != "/connector":
        raise ConnectorCommandError(
            "Use /connector github issues <owner>/<repo> [open|closed|all]."
        )
    if parts[1].lower() != "github" or parts[2].lower() != "issues":
        raise ConnectorCommandError("The first supported connector action is GitHub issue listing.")

    repository = parts[3].split("/")
    if len(repository) != 2 or not all(repository):
        raise ConnectorCommandError("Repository must use the owner/repo form.")
    owner, repo = repository
    state = parts[4].lower() if len(parts) == 5 else "open"
    if state not in {"open", "closed", "all"}:
        raise ConnectorCommandError("Issue state must be open, closed, or all.")

    return ActionInvocation(
        name="connector.github_list_issues",
        arguments={"owner": owner, "repo": repo, "state": state, "per_page": 10},
        target={"connector": "github", "repository": f"{owner}/{repo}"},
        preview=f"List {state} GitHub issues in {owner}/{repo}",
    )


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
