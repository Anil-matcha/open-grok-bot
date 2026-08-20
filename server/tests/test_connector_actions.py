import unittest

from app.services.action_gateway import ActionGateway, ActionInvocation
from app.services.composio_service import (
    ComposioService,
    ConnectorServiceError,
    GITHUB_LIST_ISSUES_TOOL,
)
from app.services.connector_actions import ConnectorCommandError, parse_connector_command


class EmptyStorage:
    def get_settings(self):
        return {}


class FakeComposioService(ComposioService):
    async def call_tool(self, name, arguments, api_key=None):
        self.called = (name, arguments)
        return {
            "data": {
                "successful": True,
                "data": [
                    {
                        "number": 12,
                        "title": "Improve the connector flow",
                        "state": "open",
                        "html_url": "https://github.com/example/project/issues/12",
                        "user": {"login": "octocat"},
                        "labels": [{"name": "enhancement"}],
                        "body": "This large body should not be copied into the result.",
                    }
                ],
            }
        }


class ConnectorActionTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_accepts_explicit_github_issue_lookup(self):
        call = parse_connector_command("/connector github issues example/project closed")

        self.assertEqual(call.name, "connector.github_list_issues")
        self.assertEqual(call.arguments["owner"], "example")
        self.assertEqual(call.arguments["repo"], "project")
        self.assertEqual(call.arguments["state"], "closed")
        self.assertEqual(call.target["repository"], "example/project")

    def test_parser_rejects_unknown_connector_or_shape(self):
        with self.assertRaises(ConnectorCommandError):
            parse_connector_command("/connector slack send hello")
        with self.assertRaises(ConnectorCommandError):
            parse_connector_command("/connector github issues not-a-repository")

    async def test_composio_adapter_normalizes_read_only_results(self):
        provider = FakeComposioService(EmptyStorage())
        result = await provider.list_github_issues("example", "project", "open", 10)

        self.assertEqual(provider.called[0], GITHUB_LIST_ISSUES_TOOL)
        self.assertEqual(provider.called[1]["per_page"], 10)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["issues"][0]["number"], 12)
        self.assertNotIn("body", result["issues"][0])

    async def test_composio_adapter_requires_server_side_configuration(self):
        provider = ComposioService(EmptyStorage())

        with self.assertRaises(ConnectorServiceError):
            await provider.call_tool("GITHUB_LIST_REPOSITORY_ISSUES", {})

    async def test_async_connector_executor_can_use_gateway_contract(self):
        provider = FakeComposioService(EmptyStorage())
        audit = type("Audit", (), {"events": [], "add_audit_event": lambda self, event: self.events.append(event)})()
        gateway = ActionGateway(audit=audit)

        async def execute(call):
            return await provider.list_github_issues(
                call.arguments["owner"],
                call.arguments["repo"],
            )

        from app.services.action_gateway import ActionDefinition

        gateway.register_action(
            ActionDefinition(
                name="connector.github_list_issues",
                tool="connector",
                action="github_list_issues",
                intent="Read GitHub issues.",
                risk="read",
                requires_approval=False,
            ),
            execute,
        )
        request, approval = gateway.open(
            "thread-test",
            "bot-test",
            ActionInvocation(
                name="connector.github_list_issues",
                arguments={"owner": "example", "repo": "project"},
                target={"connector": "github", "repository": "example/project"},
                preview="List open GitHub issues in example/project",
            ),
        )

        self.assertIsNone(approval)
        result = await gateway.execute(request)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result["connector"], "github")
        self.assertEqual(
            [event["event"] for event in audit.events],
            ["action.requested", "action.approved", "action.started", "action.completed"],
        )


if __name__ == "__main__":
    unittest.main()
