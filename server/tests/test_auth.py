import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.services.auth_service import AuthService

try:
    from app.main import app
except ModuleNotFoundError:
    app = None


class AuthServiceTests(unittest.TestCase):
    def test_local_token_is_generated_once_with_restricted_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {"APP_AUTH_TOKEN": ""}, clear=False):
                first = AuthService(root)
                second = AuthService(root)

            self.assertEqual(first.token, second.token)
            self.assertTrue(first.authenticate_token(first.token))
            self.assertFalse(first.authenticate_token("wrong-token"))
            self.assertEqual((root / ".auth-token").stat().st_mode & 0o777, 0o600)

    def test_configured_token_does_not_create_a_local_token_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {"APP_AUTH_TOKEN": "configured-token"}, clear=False):
                service = AuthService(root)

            self.assertTrue(service.authenticate_token("configured-token"))
            self.assertFalse((root / ".auth-token").exists())


class AuthMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipIf(app is None, "FastAPI dependencies are not installed")
    async def test_api_requires_a_session_and_loopback_can_bootstrap(self):
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 43123))
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            unauthenticated = await client.get("/api/v1/models")
            self.assertEqual(unauthenticated.status_code, 401)

            status = await client.get("/api/v1/auth/status")
            self.assertFalse(status.json()["authenticated"])
            self.assertTrue(status.json()["bootstrap_available"])

            session = await client.get("/api/v1/auth/session")
            self.assertEqual(session.status_code, 200)
            self.assertTrue(session.json()["authenticated"])
            self.assertEqual(session.json()["user"]["id"], "local-user")

            authenticated = await client.get("/api/v1/models")
            self.assertEqual(authenticated.status_code, 200)

            await client.post("/api/v1/auth/logout")
            logged_out = await client.get("/api/v1/models")
            self.assertEqual(logged_out.status_code, 401)


if __name__ == "__main__":
    unittest.main()
