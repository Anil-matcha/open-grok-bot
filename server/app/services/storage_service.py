import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

class StorageService:
    def __init__(self):
        self.data_dir = settings.DATA_DIR
        self.bots_file = self.data_dir / "bots.json"
        self.messages_file = self.data_dir / "messages.json"
        self.settings_file = self.data_dir / "settings.json"
        self.approvals_file = self.data_dir / "approvals.json"
        self.audit_file = self.data_dir / "audit.json"
        self._ensure_defaults()

    @staticmethod
    def _default_settings() -> Dict[str, Any]:
        return {
            "muapi_api_key": settings.MUAPI_API_KEY,
            "muapi_base_url": settings.MUAPI_BASE_URL,
            "composio_api_key": settings.COMPOSIO_API_KEY,
            "default_model": settings.DEFAULT_MODEL,
            "theme": "dark"
        }

    def _ensure_defaults(self):
        if not self.bots_file.exists():
            default_bots = [
                {
                    "id": "bot-grok-1",
                    "name": "Grok 4.5 Analyst",
                    "role": "Real-time Reasoning & Intelligence",
                    "description": "Powered by MUAPI grok-4-5 model. Deep analysis, real-time web intelligence, & precise technical problem solving.",
                    "avatar": "🚀",
                    "model": "grok-4-5",
                    "accent_color": "#3b82f6",
                    "system_prompt": "You are Grok 4.5, an advanced AI analyst. Provide direct, highly accurate, and helpful answers with real-time insight.",
                    "tools": ["web_search", "code_interpreter", "computer_preview"],
                    "pinned": True,
                    "unread_count": 0,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "bot-claude-1",
                    "name": "Claude Architect",
                    "role": "Full-Stack Code & Refactoring",
                    "description": "Specialized in software design, clean architectural patterns, and elegant React/Next.js code.",
                    "avatar": "⚡",
                    "model": "claude-sonnet-4-5",
                    "accent_color": "#d97757",
                    "system_prompt": "You are Claude Architect, an expert software engineer. Write clean, modular, modern code.",
                    "tools": ["file_editor", "terminal"],
                    "pinned": True,
                    "unread_count": 0,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "bot-codex-1",
                    "name": "Codex Builder",
                    "role": "Automated Execution & Workflows",
                    "description": "Executes shell tasks, runs automated builds, and manages local computer environment.",
                    "avatar": "💻",
                    "model": "gpt-5-mini",

                    "accent_color": "#10b981",
                    "system_prompt": "You are Codex Builder, a devops and execution specialist. Help run commands safely.",
                    "tools": ["terminal", "approval_broker"],
                    "pinned": False,
                    "unread_count": 0,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "bot-supa-1",
                    "name": "Grok Connector Assistant",
                    "role": "General Assistant & App Connector",
                    "description": "Friendly assistant connected to the app marketplace (Slack, Gmail, GitHub).",
                    "avatar": "🐭",
                    "model": "grok-4-5",
                    "accent_color": "#a855f7",
                    "system_prompt": "You are a super-powered assistant. Be friendly, fast, and proactive.",
                    "tools": ["composio_apps", "dictation"],
                    "pinned": False,
                    "unread_count": 0,
                    "created_at": datetime.now().isoformat()
                }
            ]
            self.save_bots(default_bots)

        if not self.messages_file.exists():
            default_messages = [
                {
                    "id": "msg-welcome-1",
                    "thread_id": "bot-grok-1",
                    "bot_id": "bot-grok-1",
                    "sender": "bot",
                    "text": "Hello! I am **Grok 4.5 Analyst**, running via MUAPI endpoints. Ask me anything, or give me a task to analyze!",
                    "created_at": datetime.now().isoformat(),
                    "model": "grok-4-5",
                    "item_type": "assistant_text"
                }
            ]
            self.save_messages(default_messages)

        if not self.settings_file.exists():
            self.save_settings(self._default_settings())

        if not self.approvals_file.exists():
            self._write_json(self.approvals_file, [])

        if not self.audit_file.exists():
            self._write_json(self.audit_file, [])

    @staticmethod
    def _write_json(path: Path, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _read_json(path: Path, default: Any):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def get_bots(self) -> List[Dict[str, Any]]:
        try:
            with open(self.bots_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_bots(self, bots: List[Dict[str, Any]]):
        self._write_json(self.bots_file, bots)

    def get_messages(self, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with open(self.messages_file, "r", encoding="utf-8") as f:
                msgs = json.load(f)
                if thread_id:
                    return [m for m in msgs if m.get("thread_id") == thread_id]
                return msgs
        except Exception:
            return []

    def add_message(self, message: Dict[str, Any]):
        msgs = self.get_messages()
        msgs.append(message)
        self._write_json(self.messages_file, msgs)

    def save_messages(self, messages: List[Dict[str, Any]]):
        self._write_json(self.messages_file, messages)

    def get_settings(self) -> Dict[str, Any]:
        stored = self._read_json(self.settings_file, {})
        defaults = self._default_settings()
        if isinstance(stored, dict):
            defaults.update(stored)
        return defaults

    def save_settings(self, data: Dict[str, Any]):
        self._write_json(self.settings_file, data)

    def get_approvals(self, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        approvals = self._read_json(self.approvals_file, [])
        if thread_id:
            return [a for a in approvals if a.get("thread_id") == thread_id]
        return approvals

    def add_approval(self, approval: Dict[str, Any]):
        approvals = self.get_approvals()
        approvals.append(approval)
        self._write_json(self.approvals_file, approvals)

    def update_approval(self, request_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        approvals = self.get_approvals()
        for approval in approvals:
            if approval.get("request_id") == request_id:
                approval.update(updates)
                self._write_json(self.approvals_file, approvals)
                return approval
        return None

    def get_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        events = self._read_json(self.audit_file, [])
        return events[-max(1, min(limit, 500)):]

    def add_audit_event(self, event: Dict[str, Any]):
        events = self._read_json(self.audit_file, [])
        events.append(event)
        self._write_json(self.audit_file, events[-5000:])

storage_service = StorageService()
