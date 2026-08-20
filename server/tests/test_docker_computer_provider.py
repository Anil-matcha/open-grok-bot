import tempfile
import unittest
from pathlib import Path

from app.services.computer_provider import ComputerProviderError
from app.services.docker_computer_provider import DockerComputerProvider


class FakeDockerCommand:
    def __init__(self):
        self.calls = []

    def __call__(self, args, timeout):
        self.calls.append((tuple(args), timeout))
        if args[0] == "run":
            return "container-test"
        if args[0] == "port":
            return "127.0.0.1:45678"
        return ""


class DockerComputerProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.docker = FakeDockerCommand()
        self.provider = DockerComputerProvider(
            image="open-grok-bot-computer:test",
            workspace_root=self.root / "computers",
            seccomp_profile=self.root / "missing-seccomp.json",
            start_timeout=0.5,
            docker_command=self.docker,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_start_builds_a_restricted_per_bot_container(self):
        status = self.provider.get_or_create("bot-test")

        async def ready(_record):
            return {"status": "healthy", "width": 1280, "height": 720}

        self.provider._wait_until_ready = ready
        started = await self.provider.start(status.computer_id)

        self.assertEqual(started.state, "running")
        self.assertEqual(started.provider, "docker-playwright")
        self.assertTrue((self.root / "computers" / status.computer_id).is_dir())
        run_args = self.docker.calls[0][0]
        self.assertEqual(run_args[0], "run")
        self.assertIn("--read-only", run_args)
        self.assertIn("--cap-drop", run_args)
        self.assertIn("ALL", run_args)
        self.assertIn("--security-opt", run_args)
        self.assertIn("no-new-privileges:true", run_args)
        self.assertIn("--pids-limit", run_args)
        self.assertIn("--publish", run_args)
        self.assertIn("127.0.0.1::3000", run_args)
        self.assertNotIn("COMPUTER_TOKEN", started.to_dict())
        self.assertNotIn("token", started.to_dict())

    async def test_browser_terminal_files_input_and_screenshot_use_scoped_runtime(self):
        status = self.provider.get_or_create("bot-test")

        async def ready(_record):
            return {"status": "healthy"}

        async def request(_record, method, route, payload=None):
            if route == "/health":
                return {"status": "healthy"}
            if route == "/navigate":
                return {"url": payload["url"], "title": "Example"}
            if route == "/terminal":
                return {"exit_code": 0, "stdout": "ok", "stderr": ""}
            if route == "/files":
                return {"path": payload["path"], "entries": []}
            if route == "/input":
                return {"accepted": True, "type": payload["event"]["type"]}
            if route == "/screenshot":
                return {
                    "frame_id": "frame-real-1",
                    "format": "jpeg",
                    "width": 1280,
                    "height": 720,
                    "data": "base64-jpeg",
                }
            raise AssertionError(route)

        self.provider._wait_until_ready = ready
        self.provider._request = request
        await self.provider.start(status.computer_id)

        navigated = await self.provider.browser_navigate(status.computer_id, "https://example.test")
        self.assertEqual(navigated["title"], "Example")
        terminal = await self.provider.terminal_execute(status.computer_id, "printf safe")
        self.assertEqual(terminal["stdout"], "ok")
        files = await self.provider.files_list(status.computer_id, "/workspace")
        self.assertEqual(files["entries"], [])
        input_result = await self.provider.send_input(
            status.computer_id,
            {"type": "click", "x": 4, "y": 5},
        )
        self.assertTrue(input_result["accepted"])
        screen = await self.provider.screenshot(status.computer_id)
        self.assertTrue(screen["available"])
        self.assertEqual(screen["frame_id"], "frame-real-1")
        self.assertEqual(self.provider.describe("bot-test").frame_id, "frame-real-1")

    async def test_docker_failure_is_reported_and_marks_runtime_unhealthy(self):
        def failing_docker(_args, _timeout):
            raise ComputerProviderError("Docker daemon is unavailable.")

        provider = DockerComputerProvider(
            workspace_root=self.root / "computers",
            docker_command=failing_docker,
        )
        status = provider.get_or_create("bot-test")
        with self.assertRaisesRegex(ComputerProviderError, "daemon is unavailable"):
            await provider.start(status.computer_id)
        self.assertEqual(provider.describe("bot-test").state, "error")
        self.assertEqual(provider.describe("bot-test").health, "unhealthy")


if __name__ == "__main__":
    unittest.main()
