"""Authentication primitives for the single-owner local deployment."""

import ipaddress
import os
import secrets
from pathlib import Path
from typing import Dict, Optional

from fastapi import Request, Response

from app.config import settings


LOCAL_USER_ID = "local-user"
LOCAL_USERNAME = "local"
SESSION_COOKIE = "open_grok_session"


class AuthService:
    """Validate a configured bearer token or a mode-0600 local token file.

    When no environment token is supplied, a local token is generated once and
    loopback requests may exchange it for an HttpOnly session cookie. A
    deployment exposed beyond the local machine should set APP_AUTH_TOKEN and
    provide that token through a secure deployment or client integration.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = (data_dir or settings.DATA_DIR).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.token_path = self.data_dir / ".auth-token"
        self.configured_token = os.getenv("APP_AUTH_TOKEN", "").strip()
        self.token = self.configured_token or self._load_or_create_token()

    @property
    def user(self) -> Dict[str, str]:
        return {"id": LOCAL_USER_ID, "username": LOCAL_USERNAME, "role": "owner"}

    def _load_or_create_token(self) -> str:
        if self.token_path.exists():
            existing = self.token_path.read_text(encoding="utf-8").strip()
            if existing:
                os.chmod(self.token_path, 0o600)
                return existing

        token = secrets.token_urlsafe(32)
        self.token_path.write_text(token + "\n", encoding="utf-8")
        os.chmod(self.token_path, 0o600)
        return token

    def authenticate_token(self, token: Optional[str]) -> bool:
        return bool(token) and secrets.compare_digest(token, self.token)

    def authenticate_request(self, request: Request) -> Optional[Dict[str, str]]:
        authorization = request.headers.get("authorization", "")
        scheme, _, bearer = authorization.partition(" ")
        if scheme.lower() == "bearer" and self.authenticate_token(bearer.strip()):
            return self.user

        if self.authenticate_token(request.cookies.get(SESSION_COOKIE)):
            return self.user
        return None

    def can_bootstrap(self, request: Request) -> bool:
        if self.configured_token:
            return False
        host = request.client.host if request.client else ""
        if host in {"localhost", "localhost.localdomain"}:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def set_session_cookie(self, response: Response) -> None:
        response.set_cookie(
            SESSION_COOKIE,
            self.token,
            max_age=settings.AUTH_SESSION_MAX_AGE,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite="lax",
        )

    @staticmethod
    def clear_session_cookie(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")


auth_service = AuthService()
