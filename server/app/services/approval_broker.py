import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict
import uuid

from app.config import settings
from app.services.storage_service import storage_service
from app.services.workspace_service import WorkspaceToolCall


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PendingApproval:
    request_id: str
    future: asyncio.Future


class ApprovalBroker:
    """In-process approval coordinator for the local single-user server."""

    def __init__(self):
        self.pending: Dict[str, PendingApproval] = {}

    def open(self, thread_id: str, bot_id: str, call: WorkspaceToolCall) -> Dict[str, Any]:
        request_id = f"req-{uuid.uuid4().hex[:10]}"
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending[request_id] = PendingApproval(request_id, future)

        approval = {
            "request_id": request_id,
            "thread_id": thread_id,
            "bot_id": bot_id,
            "tool": call.name,
            "summary": call.summary,
            "arguments": call.arguments_for_display,
            "status": "pending",
            "created_at": _now(),
        }
        storage_service.add_approval(approval)
        storage_service.add_audit_event({
            "event": "approval.opened",
            "request_id": request_id,
            "thread_id": thread_id,
            "tool": call.name,
            "created_at": approval["created_at"],
        })
        return approval

    async def wait(self, request_id: str) -> str:
        pending = self.pending.get(request_id)
        if not pending:
            return "expired"

        try:
            return await asyncio.wait_for(
                asyncio.shield(pending.future),
                timeout=settings.APPROVAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            if not pending.future.done():
                pending.future.set_result("expired")
            storage_service.update_approval(request_id, {
                "status": "expired",
                "resolved_at": _now(),
            })
            storage_service.add_audit_event({
                "event": "approval.expired",
                "request_id": request_id,
                "created_at": _now(),
            })
            return "expired"
        finally:
            self.pending.pop(request_id, None)

    def resolve(self, request_id: str, action: str) -> bool:
        pending = self.pending.get(request_id)
        if not pending or pending.future.done():
            return False

        pending.future.set_result(action)
        storage_service.update_approval(request_id, {
            "status": action,
            "resolved_at": _now(),
        })
        storage_service.add_audit_event({
            "event": f"approval.{action}",
            "request_id": request_id,
            "created_at": _now(),
        })
        return True


approval_broker = ApprovalBroker()
