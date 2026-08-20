from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class Bot(BaseModel):
    id: str
    name: str
    role: str
    description: str
    avatar: str
    model: str = "grok-4-5"
    accent_color: str = "cyan"
    system_prompt: str
    tools: List[str] = []
    pinned: bool = False
    unread_count: int = 0
    created_at: str

class Message(BaseModel):
    id: str
    thread_id: str
    bot_id: str
    sender: str  # "user" | "bot" | "system"
    text: str
    created_at: str
    model: Optional[str] = None
    item_type: Optional[str] = "assistant_text"  # assistant_text, tool_call, approval_card
    image_url: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

class TurnRequest(BaseModel):
    thread_id: str
    bot_id: str
    user_text: str
    model: Optional[str] = None
    image_url: Optional[str] = None


class ApprovalDecision(BaseModel):
    request_id: str
    action: Literal["allow", "deny"]


class ActionRequest(BaseModel):
    """The stable envelope used before a side-effecting action executes."""

    request_id: str
    thread_id: str
    bot_id: str
    tool: str
    action: str
    intent: str
    target: Dict[str, Any] = Field(default_factory=dict)
    arguments: Dict[str, Any] = Field(default_factory=dict)
    preview: str
    risk: Literal["read", "write", "external"] = "read"
    requires_approval: bool = True
    state: Literal["pending_approval", "approved"] = "pending_approval"
    created_at: str


class ActionResult(BaseModel):
    """The normalized result returned after an action is decided and run."""

    request_id: str
    status: Literal["completed", "failed", "denied", "expired"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    recommended: bool = False
    is_available: bool = True

class AppSettingsSchema(BaseModel):
    muapi_api_key: str = ""
    muapi_base_url: str = "https://api.muapi.ai/api/v1"
    composio_api_key: str = ""
    default_model: str = "grok-4-5"
    theme: str = "dark"
