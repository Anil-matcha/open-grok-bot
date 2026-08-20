"""Computer actions registered with the shared policy gateway."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.services.action_gateway import ActionDefinition, ActionGateway, ActionInvocation, action_gateway
from app.services.computer_provider import (
    ComputerProvider,
    ComputerProviderError,
    computer_provider,
)


def _status_for(call: ActionInvocation, provider: ComputerProvider):
    bot_id = call.arguments.get("bot_id")
    if not isinstance(bot_id, str) or not bot_id.strip():
        raise ComputerProviderError("Computer actions require a bot id.")
    status = provider.get_or_create(bot_id)
    requested_id = call.arguments.get("computer_id")
    if requested_id and requested_id != status.computer_id:
        raise ComputerProviderError("The computer id does not belong to the requested bot.")
    return status


def register_computer_actions(
    gateway: Optional[ActionGateway] = None,
    provider: Optional[ComputerProvider] = None,
) -> None:
    """Register computer operations on a gateway instance.

    The explicit parameters make the adapter easy to test with an isolated
    gateway and fake provider. The module registers the application defaults
    on import below.
    """

    target_gateway = gateway or action_gateway
    target_provider = provider or computer_provider

    async def create(call: ActionInvocation) -> Dict[str, Any]:
        bot_id = call.arguments.get("bot_id")
        if not isinstance(bot_id, str) or not bot_id.strip():
            raise ComputerProviderError("Computer creation requires a bot id.")
        return (await target_provider.create(bot_id)).to_dict()

    async def start(call: ActionInvocation) -> Dict[str, Any]:
        return (await target_provider.start(_status_for(call, target_provider).computer_id)).to_dict()

    async def stop(call: ActionInvocation) -> Dict[str, Any]:
        return (await target_provider.stop(_status_for(call, target_provider).computer_id)).to_dict()

    async def pause(call: ActionInvocation) -> Dict[str, Any]:
        return (await target_provider.pause(_status_for(call, target_provider).computer_id)).to_dict()

    async def reset(call: ActionInvocation) -> Dict[str, Any]:
        return (await target_provider.reset(_status_for(call, target_provider).computer_id)).to_dict()

    async def health(call: ActionInvocation) -> Dict[str, Any]:
        return (await target_provider.health(_status_for(call, target_provider).computer_id)).to_dict()

    async def screenshot(call: ActionInvocation) -> Dict[str, Any]:
        return await target_provider.screenshot(_status_for(call, target_provider).computer_id)

    async def browser_navigate(call: ActionInvocation) -> Dict[str, Any]:
        status = _status_for(call, target_provider)
        return await target_provider.browser_navigate(status.computer_id, str(call.arguments.get("url") or ""))

    async def terminal_execute(call: ActionInvocation) -> Dict[str, Any]:
        status = _status_for(call, target_provider)
        return await target_provider.terminal_execute(status.computer_id, str(call.arguments.get("command") or ""))

    async def files_list(call: ActionInvocation) -> Dict[str, Any]:
        status = _status_for(call, target_provider)
        return await target_provider.files_list(status.computer_id, str(call.arguments.get("path") or "/workspace"))

    async def send_input(call: ActionInvocation) -> Dict[str, Any]:
        status = _status_for(call, target_provider)
        event = call.arguments.get("event")
        if not isinstance(event, dict):
            raise ComputerProviderError("Computer input requires an event object.")
        return await target_provider.send_input(status.computer_id, event)

    async def cleanup(call: ActionInvocation) -> Dict[str, Any]:
        return await target_provider.cleanup(_status_for(call, target_provider).computer_id)

    definitions: Dict[str, tuple[ActionDefinition, Callable[[ActionInvocation], Any]]] = {
        "computer.create": (
            ActionDefinition(
                name="computer.create",
                tool="computer",
                action="create",
                intent="Create the computer assigned to a bot.",
                risk="write",
                requires_approval=False,
            ),
            create,
        ),
        "computer.start": (
            ActionDefinition(
                name="computer.start",
                tool="computer",
                action="start",
                intent="Start the computer assigned to a bot.",
                risk="write",
                requires_approval=False,
            ),
            start,
        ),
        "computer.stop": (
            ActionDefinition(
                name="computer.stop",
                tool="computer",
                action="stop",
                intent="Stop the computer assigned to a bot.",
                risk="write",
                requires_approval=False,
            ),
            stop,
        ),
        "computer.pause": (
            ActionDefinition(
                name="computer.pause",
                tool="computer",
                action="pause",
                intent="Pause the computer assigned to a bot.",
                risk="write",
                requires_approval=False,
            ),
            pause,
        ),
        "computer.reset": (
            ActionDefinition(
                name="computer.reset",
                tool="computer",
                action="reset",
                intent="Reset the computer assigned to a bot.",
                risk="write",
                requires_approval=False,
            ),
            reset,
        ),
        "computer.health": (
            ActionDefinition(
                name="computer.health",
                tool="computer",
                action="health",
                intent="Read the computer health state.",
                risk="read",
                requires_approval=False,
            ),
            health,
        ),
        "computer.screenshot": (
            ActionDefinition(
                name="computer.screenshot",
                tool="computer",
                action="screenshot",
                intent="Capture the current computer screen state.",
                risk="read",
                requires_approval=False,
            ),
            screenshot,
        ),
        "computer.browser_navigate": (
            ActionDefinition(
                name="computer.browser_navigate",
                tool="computer",
                action="browser_navigate",
                intent="Navigate the bot computer browser to an external URL.",
                risk="external",
                requires_approval=True,
            ),
            browser_navigate,
        ),
        "computer.terminal_execute": (
            ActionDefinition(
                name="computer.terminal_execute",
                tool="computer",
                action="terminal_execute",
                intent="Run a command inside the bot computer.",
                risk="write",
                requires_approval=True,
            ),
            terminal_execute,
        ),
        "computer.files_list": (
            ActionDefinition(
                name="computer.files_list",
                tool="computer",
                action="files_list",
                intent="List files inside the bot computer workspace.",
                risk="read",
                requires_approval=False,
            ),
            files_list,
        ),
        "computer.send_input": (
            ActionDefinition(
                name="computer.send_input",
                tool="computer",
                action="send_input",
                intent="Send keyboard or pointer input to the bot computer.",
                risk="write",
                requires_approval=True,
            ),
            send_input,
        ),
        "computer.cleanup": (
            ActionDefinition(
                name="computer.cleanup",
                tool="computer",
                action="cleanup",
                intent="Remove the bot computer and its runtime state.",
                risk="write",
                requires_approval=True,
            ),
            cleanup,
        ),
    }

    for definition, executor in definitions.values():
        target_gateway.register_action(definition, executor)


register_computer_actions()
