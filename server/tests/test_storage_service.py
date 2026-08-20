import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.services.storage_service import StorageService
from app.schemas.contracts import AppSettingsSchema
from app.routers import settings as settings_router


class StorageServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = StorageService(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_state_and_encrypted_settings_survive_reopen(self):
        self.service.save_bots([{"id": "bot-test", "name": "Persistent bot"}])
        self.service.add_message(
            {
                "id": "message-test",
                "thread_id": "thread-test",
                "sender": "user",
                "text": "remember this",
            }
        )
        self.service.add_approval(
            {"request_id": "request-test", "thread_id": "thread-test", "status": "pending"}
        )
        self.service.add_audit_event({"event": "test.completed", "request_id": "request-test"})
        self.service.save_settings({"muapi_api_key": "super-secret", "theme": "light"})

        self.service.save_settings({"muapi_api_key": "", "theme": "dark"})
        reopened = StorageService(self.root)

        self.assertEqual(reopened.get_bots(), [{"id": "bot-test", "name": "Persistent bot"}])
        self.assertEqual(reopened.get_messages("thread-test")[0]["text"], "remember this")
        self.assertEqual(reopened.get_approvals("thread-test")[0]["request_id"], "request-test")
        self.assertEqual(reopened.get_audit_events(10)[-1]["event"], "test.completed")
        self.assertEqual(reopened.get_settings()["muapi_api_key"], "super-secret")
        self.assertEqual(reopened.get_settings()["theme"], "dark")

        public = reopened.get_public_settings()
        self.assertEqual(public["muapi_api_key"], "")
        self.assertTrue(public["muapi_api_key_configured"])
        self.assertNotIn(b"super-secret", self._database_bytes())

        with sqlite3.connect(reopened.db_path) as connection:
            version = connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0]
        self.assertEqual(version, 1)

    def test_legacy_json_is_imported_and_plaintext_keys_are_scrubbed(self):
        legacy_root = self.root / "legacy"
        legacy_root.mkdir()
        legacy_secret = "legacy-secret-value"
        self._write_json(
            legacy_root,
            "bots.json",
            [{"id": "legacy-bot", "name": "Imported bot"}],
        )
        self._write_json(
            legacy_root,
            "messages.json",
            [
                {
                    "id": "legacy-message",
                    "thread_id": "legacy-thread",
                    "text": "Imported message",
                }
            ],
        )
        self._write_json(
            legacy_root,
            "settings.json",
            {
                "muapi_api_key": legacy_secret,
                "muapi_base_url": "https://example.test/api/v1",
                "theme": "light",
            },
        )
        self._write_json(
            legacy_root,
            "approvals.json",
            [{"request_id": "legacy-request", "thread_id": "legacy-thread"}],
        )
        self._write_json(
            legacy_root,
            "audit.json",
            [{"event": "legacy.imported", "created_at": "2026-08-20T00:00:00+00:00"}],
        )

        imported = StorageService(legacy_root)

        self.assertEqual(imported.get_bots()[0]["id"], "legacy-bot")
        self.assertEqual(imported.get_messages("legacy-thread")[0]["text"], "Imported message")
        self.assertEqual(imported.get_settings()["muapi_api_key"], legacy_secret)
        self.assertTrue(imported.get_public_settings()["muapi_api_key_configured"])
        self.assertEqual(imported.get_approvals()[0]["request_id"], "legacy-request")
        self.assertEqual(imported.get_audit_events()[0]["event"], "legacy.imported")

        scrubbed = (legacy_root / "settings.json").read_text(encoding="utf-8")
        self.assertNotIn(legacy_secret, scrubbed)
        self.assertIn('"muapi_api_key": ""', scrubbed)
        self.assertEqual((legacy_root / ".encryption.key").stat().st_mode & 0o777, 0o600)

        reopened = StorageService(legacy_root)
        self.assertEqual(reopened.get_settings()["muapi_api_key"], legacy_secret)

    def test_settings_routes_never_return_provider_credentials(self):
        self.service.save_settings({"muapi_api_key": "route-secret"})
        original_storage = settings_router.storage_service
        settings_router.storage_service = self.service
        try:
            fetched = asyncio.run(settings_router.get_settings())
            self.assertEqual(fetched.muapi_api_key, "")
            self.assertTrue(fetched.muapi_api_key_configured)

            saved = asyncio.run(
                settings_router.save_settings(
                    AppSettingsSchema(
                        muapi_api_key="",
                        muapi_base_url="https://example.test/api/v1",
                    )
                )
            )
            self.assertEqual(saved.muapi_api_key, "")
            self.assertTrue(saved.muapi_api_key_configured)
            self.assertEqual(self.service.get_settings()["muapi_api_key"], "route-secret")
        finally:
            settings_router.storage_service = original_storage

    def _write_json(self, root: Path, name: str, value):
        (root / name).write_text(json.dumps(value), encoding="utf-8")

    def _database_bytes(self) -> bytes:
        paths = [
            self.root / "open-grok-bot.sqlite3",
            self.root / "open-grok-bot.sqlite3-wal",
            self.root / "open-grok-bot.sqlite3-shm",
        ]
        return b"".join(path.read_bytes() for path in paths if path.exists())


if __name__ == "__main__":
    unittest.main()
