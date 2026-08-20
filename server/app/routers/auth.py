from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.services.auth_service import auth_service


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    token: str = Field(min_length=1)


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _session_payload():
    return {
        "authenticated": True,
        "user": auth_service.user,
    }


@router.get("/status")
async def auth_status(request: Request):
    user = auth_service.authenticate_request(request)
    return {
        "auth_required": True,
        "authenticated": bool(user),
        "bootstrap_available": auth_service.can_bootstrap(request),
        "user": user,
    }


@router.get("/session")
async def establish_session(request: Request, response: Response):
    user = auth_service.authenticate_request(request)
    if not user and auth_service.can_bootstrap(request):
        user = auth_service.user
    if not user:
        raise _authentication_error()
    auth_service.set_session_cookie(response)
    return _session_payload()


@router.post("/login")
async def login(credentials: LoginRequest, response: Response):
    if not auth_service.authenticate_token(credentials.token):
        raise _authentication_error()
    auth_service.set_session_cookie(response)
    return _session_payload()


@router.post("/logout")
async def logout(response: Response):
    auth_service.clear_session_cookie(response)
    return {"authenticated": False}
