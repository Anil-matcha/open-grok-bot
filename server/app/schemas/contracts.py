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
