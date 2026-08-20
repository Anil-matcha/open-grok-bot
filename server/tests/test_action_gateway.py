import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.action_gateway import (
    ActionDefinition,
    ActionGateway,
    ActionInvocation,
    ActionPolicyError,
)
from app.services.workspace_service import WorkspaceService, parse_workspace_command


class RecordingAudit:
    def __init__(self):
        self.events = []

    def add_audit_event(self, event: Dict[str, Any]):
        self.events.append(event)


class ImmediateApprovalBroker:
    def __init__(self, decision: str = "allow"):
        self.decision = decision
        self.opened = []

    def open(
        self,
        thread_id: str,
        bot_id: str,
        call: Any,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        approval = {
            "request_id": request_id,
            "thread_id": thread_id,
            "bot_id": bot_id,
            "tool": call.name,
            "summary": call.summary,
            "arguments": call.arguments_for_display,
            "status": "pending",
        }
        self.opened.append(approval)
        return approval

    async def wait(self, request_id: str) -> str:
        return self.decision


class ActionGatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.audit = RecordingAudit()
        self.approvals = ImmediateApprovalBroker()
        self.gateway = ActionGateway(
            workspace=WorkspaceService(self.root),
            approvals=self.approvals,
            audit=self.audit,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_workspace_action_has_contract_and_redacted_lifecycle(self):
        (self.root / "notes.txt").write_text("private workspace content", encoding="utf-8")
        call = parse_workspace_command("/workspace read notes.txt")

        request, approval = self.gateway.open("thread-test", "bot-test", call)
        self.assertEqual(request.tool, "workspace")
        self.assertEqual(request.action, "read")
        self.assertEqual(request.target, {"path": "notes.txt"})
        self.assertTrue(request.requires_approval)
        self.assertEqual(request.state, "pending_approval")
        self.assertEqual(approval["request_id"], request.request_id)

        self.assertEqual(await self.gateway.wait_for_decision(request), "allow")
        action_result = await self.gateway.execute(request)

        self.assertEqual(action_result.status, "completed")
        self.assertEqual(action_result.result["content"], "private workspace content")
        event_names = [event["event"] for event in self.audit.events]
        self.assertEqual(
            event_names,
            [
                "action.requested",
                "action.approved",
                "action.started",
                "action.completed",
            ],
        )
        audit_text = json.dumps(self.audit.events)
        self.assertNotIn("private workspace content", audit_text)

    async def test_unregistered_action_is_denied_by_default(self):
        call = ActionInvocation(
            name="shell.exec",
            arguments={"password": "do-not-store", "command": "rm -rf /"},
            target={},
            preview="Run a shell command",
        )

        with self.assertRaises(ActionPolicyError) as context:
            self.gateway.open("thread-test", "bot-test", call)

        self.assertTrue(context.exception.request_id)
        self.assertEqual(self.audit.events[-1]["event"], "action.denied")
        self.assertEqual(self.audit.events[-1]["state"], "denied")
        audit_text = json.dumps(self.audit.events)
        self.assertNotIn("do-not-store", audit_text)

    async def test_registered_provider_action_uses_same_gateway(self):
        self.gateway.register_action(
            ActionDefinition(
                name="connector.lookup",
                tool="connector",
                action="lookup",
                intent="Read a connected app record.",
                risk="read",
                requires_approval=False,
            ),
            lambda invocation: {"found": True, "query": invocation.arguments["query"]},
        )
        call = ActionInvocation(
            name="connector.lookup",
            arguments={"api_key": "do-not-store", "query": "status"},
            target={"account_id": "acct-test"},
            preview="Look up the connected app status",
        )

        request, approval = self.gateway.open("thread-test", "bot-test", call)
        self.assertIsNone(approval)
        self.assertEqual(request.state, "approved")
        self.assertEqual(await self.gateway.wait_for_decision(request), "allow")
        result = await self.gateway.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertTrue(result.result["found"])
        self.assertIn("action.requested", [event["event"] for event in self.audit.events])
        self.assertNotIn("do-not-store", json.dumps(self.audit.events))

    async def test_registered_computer_action_uses_same_gateway(self):
        self.gateway.register_action(
            ActionDefinition(
                name="computer.screenshot",
                tool="computer",
                action="screenshot",
                intent="Capture the current computer view.",
                risk="read",
                requires_approval=True,
            ),
            lambda invocation: {"image_ref": "fake-screen-1", "width": 1280},
        )
        call = ActionInvocation(
            name="computer.screenshot",
            arguments={"session_id": "session-test"},
            target={"computer_id": "computer-test"},
            preview="Capture the current computer view",
        )

        request, approval = self.gateway.open("thread-test", "bot-test", call)
        self.assertEqual(approval["request_id"], request.request_id)
        self.assertEqual(await self.gateway.wait_for_decision(request), "allow")
        result = await self.gateway.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result["image_ref"], "fake-screen-1")
        self.assertEqual(
            [event["event"] for event in self.audit.events],
            [
                "action.requested",
                "action.approved",
                "action.started",
                "action.completed",
            ],
        )


if __name__ == "__main__":
    unittest.main()
