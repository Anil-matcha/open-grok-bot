"""Policy and execution boundary for all governed actions.

The gateway is intentionally small and explicit. New action families must be
registered here before they can be proposed or executed; an unknown action is
always rejected.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import inspect
import uuid
import re
from typing import Any, Callable, Dict, Literal, Mapping, Optional, Tuple

from app.schemas.contracts import ActionRequest, ActionResult
from app.services.approval_broker import ApprovalBroker, approval_broker
from app.services.storage_service import StorageService, storage_service
from app.services.workspace_service import (
    WorkspaceService,
    WorkspaceToolCall,
    WorkspaceToolError,
    workspace_service,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_id() -> str:
    return f"req-{uuid.uuid4().hex[:10]}"


_SENSITIVE_TEXT = re.compile(
    r"(?i)\b(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|authorization|password|secret|token)\b"
    r"\s*[:=]\s*['\"]?([^\s,'\"]+)"
)


def redact_sensitive(value: Any, key: str = "") -> Any:
    """Return a JSON-safe copy with credential-like fields removed."""

    sensitive_markers = (
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credential",
        "password",
        "secret",
        "token",
    )
    if key and any(marker in key.lower() for marker in sensitive_markers):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): redact_sensitive(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item, key) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_TEXT.sub(r"\1=[REDACTED]", value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _split_action_name(name: str) -> Tuple[str, str]:
    if "." not in name:
        return name, ""
    return name.split(".", 1)


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    tool: str
    action: str
    intent: str
    risk: Literal["read", "write", "external"]
    requires_approval: bool = True


@dataclass(frozen=True)
class ActionInvocation:
    """Provider-neutral action input for future connector/computer adapters."""

    name: str
    arguments: Dict[str, Any]
    target: Dict[str, Any]
    preview: str
    display_arguments: Optional[Dict[str, Any]] = None

    @property
    def summary(self) -> str:
        return self.preview

    @property
    def arguments_for_display(self) -> Dict[str, Any]:
        return self.display_arguments if self.display_arguments is not None else self.arguments


class ActionPolicyError(ValueError):
    """Raised when an action is not registered or fails gateway validation."""

    def __init__(self, message: str, request_id: Optional[str] = None):
        super().__init__(message)
        self.request_id = request_id


class ActionGatewayError(ValueError):
    """Raised when a caller attempts to bypass the action lifecycle."""


class ActionGateway:
    """Central registry, policy check, approval handoff, and executor."""

    def __init__(
        self,
        workspace: WorkspaceService = workspace_service,
        approvals: ApprovalBroker = approval_broker,
        audit: StorageService = storage_service,
    ):
        self.workspace = workspace
        self.approvals = approvals
        self.audit = audit
        self.definitions: Dict[str, ActionDefinition] = {
            "workspace.list": ActionDefinition(
                name="workspace.list",
                tool="workspace",
                action="list",
                intent="Inspect entries in the local workspace.",
                risk="read",
            ),
            "workspace.read": ActionDefinition(
                name="workspace.read",
                tool="workspace",
                action="read",
                intent="Read a file from the local workspace.",
                risk="read",
            ),
            "workspace.write": ActionDefinition(
                name="workspace.write",
                tool="workspace",
                action="write",
                intent="Write a file in the local workspace.",
                risk="write",
            ),
        }
        self.executors: Dict[str, Callable[[Any], Dict[str, Any]]] = {
            "workspace.list": self._execute_workspace,
            "workspace.read": self._execute_workspace,
            "workspace.write": self._execute_workspace,
        }
        self._pending: Dict[str, Tuple[ActionRequest, Any]] = {}
        self._decisions: Dict[str, str] = {}

    def register_action(
        self,
        definition: ActionDefinition,
        executor: Callable[[Any], Dict[str, Any]],
    ) -> None:
        """Register a trusted action implementation before it can run."""

        if not definition.name or not definition.tool or not definition.action:
            raise ValueError("An action definition requires a name, tool, and action.")
        if definition.name != f"{definition.tool}.{definition.action}":
            raise ValueError("An action name must match its tool and action fields.")
        if not callable(executor):
            raise ValueError("An action executor must be callable.")
        self.definitions[definition.name] = definition
        self.executors[definition.name] = executor

    def _normalize(self, call: Any) -> ActionInvocation:
        if isinstance(call, WorkspaceToolCall):
            return ActionInvocation(
                name=call.name,
                arguments=call.arguments_for_display,
                target={"path": call.path},
                preview=call.summary,
            )
        if isinstance(call, ActionInvocation):
            return call
        raise ActionPolicyError("The action input is not a supported invocation type.")

    def _policy_check(
        self,
        invocation: ActionInvocation,
        definition: Optional[ActionDefinition],
    ) -> Optional[str]:
        if definition is None:
            return f"Action is not registered: {invocation.name}"
        if definition.tool != _split_action_name(invocation.name)[0]:
            return "Action tool does not match its registered definition."
        if definition.action != _split_action_name(invocation.name)[1]:
            return "Action name does not match its registered definition."
        if not isinstance(invocation.arguments, dict):
            return "Action arguments must be a JSON object."
        if not isinstance(invocation.target, dict):
            return "Action target must be a JSON object."
        if not invocation.preview or not isinstance(invocation.preview, str):
            return "Action preview is required."
        return None

    def _audit_action(
        self,
        event: str,
        request: Optional[ActionRequest],
        invocation: Optional[ActionInvocation] = None,
        **extra: Any,
    ) -> None:
        if request is not None:
            payload: Dict[str, Any] = {
                "event": event,
                "request_id": request.request_id,
                "thread_id": request.thread_id,
                "bot_id": request.bot_id,
                "tool": request.tool,
                "action": request.action,
                "intent": request.intent,
                "target": redact_sensitive(request.target),
                "arguments": redact_sensitive(request.arguments),
                "preview": redact_sensitive(request.preview),
                "risk": request.risk,
                "requires_approval": request.requires_approval,
                "state": request.state,
                "created_at": _now(),
            }
        else:
            name = invocation.name if invocation else "unknown"
            tool, action = _split_action_name(name)
            payload = {
                "event": event,
                "request_id": extra.pop("request_id", None) or _request_id(),
                "tool": tool,
                "action": action,
                "target": redact_sensitive(invocation.target if invocation else {}),
                "arguments": redact_sensitive(invocation.arguments if invocation else {}),
                "preview": redact_sensitive(invocation.preview if invocation else ""),
                "state": "denied",
                "created_at": _now(),
            }
        payload.update({key: redact_sensitive(value, key) for key, value in extra.items()})
        self.audit.add_audit_event(payload)

    def open(self, thread_id: str, bot_id: str, call: Any) -> Tuple[ActionRequest, Optional[Dict[str, Any]]]:
        """Validate, record, and prepare an action for approval or execution."""

        request_id = _request_id()
        try:
            invocation = self._normalize(call)
        except ActionPolicyError as exc:
            exc.request_id = request_id
            self._audit_action("action.denied", None, request_id=request_id, reason=str(exc))
            raise

        definition = self.definitions.get(invocation.name)
        reason = self._policy_check(invocation, definition)
        if reason or definition is None:
            self._audit_action(
                "action.denied",
                None,
                invocation,
                request_id=request_id,
                reason=reason or "Action policy denied the request.",
                state="denied",
            )
            raise ActionPolicyError(reason or "Action policy denied the request.", request_id=request_id)

        request = ActionRequest(
            request_id=request_id,
            thread_id=thread_id,
            bot_id=bot_id,
            tool=definition.tool,
            action=definition.action,
            intent=definition.intent,
            target=redact_sensitive(invocation.target),
            arguments=redact_sensitive(invocation.arguments_for_display),
            preview=redact_sensitive(invocation.preview),
            risk=definition.risk,
            requires_approval=definition.requires_approval,
            state="pending_approval" if definition.requires_approval else "approved",
            created_at=_now(),
        )
        self._pending[request_id] = (request, call)
        self._audit_action("action.requested", request)

        approval = None
        if definition.requires_approval:
            approval = self.approvals.open(
                thread_id,
                bot_id,
                call,
                request_id=request_id,
            )
        else:
            self._decisions[request_id] = "allow"
            self._audit_action("action.approved", request, decision="allow", state="approved")
        return request, approval

    async def wait_for_decision(self, request: ActionRequest) -> str:
        if not request.requires_approval:
            return "allow"
        if request.request_id in self._decisions:
            return self._decisions[request.request_id]
        if request.request_id not in self._pending:
            self._audit_action("action.expired", request, state="expired")
            self._decisions[request.request_id] = "expired"
            return "expired"

        decision = await self.approvals.wait(request.request_id)
        self._decisions[request.request_id] = decision
        if decision == "allow":
            self._audit_action("action.approved", request, decision=decision, state="approved")
        elif decision == "deny":
            self._audit_action("action.denied", request, decision=decision, state="denied")
        else:
            self._audit_action("action.expired", request, decision=decision, state="expired")
        if decision != "allow":
            self._pending.pop(request.request_id, None)
            self._decisions.pop(request.request_id, None)
        return decision

    def get_pending_request(self, request_id: str) -> Optional[ActionRequest]:
        """Return a pending request for an authenticated continuation endpoint."""

        pending = self._pending.get(request_id)
        return pending[0] if pending else None

    def _execute_workspace(self, call: Any) -> Dict[str, Any]:
        if not isinstance(call, WorkspaceToolCall):
            raise ActionGatewayError("Workspace actions require a workspace tool call.")
        return self.workspace.execute(call)

    @staticmethod
    def _result_summary(result: Mapping[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for key, value in result.items():
            if str(key).lower() in {"content", "body", "data", "token", "secret"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                summary[key] = value
            elif isinstance(value, list):
                summary[key] = {"count": len(value)}
            elif isinstance(value, dict):
                summary[key] = {"keys": sorted(str(item) for item in value.keys())}
            else:
                summary[key] = str(value)
        return redact_sensitive(summary)

    async def execute(self, request: ActionRequest) -> ActionResult:
        pending = self._pending.get(request.request_id)
        if pending is None:
            raise ActionGatewayError("Action request is no longer available for execution.")
        decision = self._decisions.get(request.request_id)
        if request.requires_approval and decision != "allow":
            raise ActionGatewayError("Action must be approved before execution.")

        call = pending[1]
        executor = self.executors.get(f"{request.tool}.{request.action}")
        if executor is None:
            self._audit_action("action.failed", request, state="failed", error="Action executor is not registered.")
            self._pending.pop(request.request_id, None)
            self._decisions.pop(request.request_id, None)
            return ActionResult(
                request_id=request.request_id,
                status="failed",
                error="Action executor is not registered.",
                created_at=_now(),
            )

        self._audit_action("action.started", request, state="running")
        try:
            result = executor(call)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                raise ActionGatewayError("Action executors must return a JSON object.")
            self._audit_action(
                "action.completed",
                request,
                state="completed",
                result_summary=self._result_summary(result),
            )
            self._pending.pop(request.request_id, None)
            self._decisions.pop(request.request_id, None)
            return ActionResult(
                request_id=request.request_id,
                status="completed",
                result=result,
                created_at=_now(),
            )
        except WorkspaceToolError as exc:
            error = str(exc)
        except Exception as exc:  # Keep the lifecycle auditable for adapter failures.
            error = str(exc)

        safe_error = str(redact_sensitive(error))
        self._audit_action("action.failed", request, state="failed", error=safe_error)
        self._pending.pop(request.request_id, None)
        self._decisions.pop(request.request_id, None)
        return ActionResult(
            request_id=request.request_id,
            status="failed",
            error=safe_error,
            created_at=_now(),
        )


action_gateway = ActionGateway()
