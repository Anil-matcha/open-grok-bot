import asyncio
import tempfile
import unittest
from pathlib import Path

from app.services.workspace_service import (
    WorkspaceService,
    WorkspaceToolError,
    parse_workspace_command,
)
from app.services.approval_broker import approval_broker

try:
    from app.main import app
except ModuleNotFoundError:
    app = None


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = WorkspaceService(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_write_and_list(self):
        (self.root / "readme.txt").write_text("hello", encoding="utf-8")

        read_call = parse_workspace_command("/workspace read readme.txt")
        self.assertEqual(self.service.execute(read_call)["content"], "hello")

        write_call = parse_workspace_command("/workspace write new.txt\nworld")
        self.assertTrue(self.service.execute(write_call)["written"])
        self.assertEqual((self.root / "new.txt").read_text(encoding="utf-8"), "world")

        list_call = parse_workspace_command("/workspace list")
        names = {entry["name"] for entry in self.service.execute(list_call)["entries"]}
        self.assertEqual(names, {"readme.txt", "new.txt"})

    def test_paths_cannot_escape_workspace(self):
        call = parse_workspace_command("/workspace read ../outside")
        with self.assertRaises(WorkspaceToolError):
            self.service.execute(call)

    def test_invalid_command_is_rejected(self):
        with self.assertRaises(WorkspaceToolError):
            parse_workspace_command("/workspace execute rm -rf .")


class ApiRouteTests(unittest.TestCase):
    @unittest.skipIf(app is None, "FastAPI dependencies are not installed")
    def test_audit_route_is_registered(self):
        self.assertIn("/api/v1/audit", app.openapi()["paths"])


class ApprovalBrokerTests(unittest.IsolatedAsyncioTestCase):
    async def test_allow_resolves_pending_request(self):
        call = parse_workspace_command("/workspace read README.md")
        approval = approval_broker.open("thread-test", "bot-test", call)
        waiting = asyncio.create_task(approval_broker.wait(approval["request_id"]))
        await asyncio.sleep(0)

        self.assertTrue(approval_broker.resolve(approval["request_id"], "allow"))
        self.assertEqual(await waiting, "allow")


if __name__ == "__main__":
    unittest.main()
