from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import uuid

from app.schemas.contracts import Bot
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1/bots", tags=["bots"])

@router.get("", response_model=List[Bot])
async def get_bots():
    return storage_service.get_bots()

@router.post("", response_model=Bot)
async def create_bot(bot_data: Dict[str, Any]):
    new_id = f"bot-{uuid.uuid4().hex[:6]}"
    bot = {
        "id": new_id,
        "name": bot_data.get("name", "New Bot"),
        "role": bot_data.get("role", "AI Assistant"),
        "description": bot_data.get("description", "Custom AI agent persona"),
        "avatar": bot_data.get("avatar", "🤖"),
        "model": bot_data.get("model", "grok-4-5"),
        "accent_color": bot_data.get("accent_color", "#3b82f6"),
        "system_prompt": bot_data.get("system_prompt", "You are a helpful AI assistant."),
        "tools": bot_data.get("tools", []),
        "pinned": False,
        "unread_count": 0,
        "created_at": datetime.now().isoformat()
    }
    bots = storage_service.get_bots()
    bots.append(bot)
    storage_service.save_bots(bots)
    return bot

@router.put("/{bot_id}", response_model=Bot)
async def update_bot(bot_id: str, updates: Dict[str, Any]):
    bots = storage_service.get_bots()
    for i, b in enumerate(bots):
        if b["id"] == bot_id:
            bots[i].update(updates)
            storage_service.save_bots(bots)
            return bots[i]
    raise HTTPException(status_code=404, detail="Bot not found")

@router.delete("/{bot_id}")
async def delete_bot(bot_id: str):
    bots = storage_service.get_bots()
    updated = [b for b in bots if b["id"] != bot_id]
    if len(updated) == len(bots):
        raise HTTPException(status_code=404, detail="Bot not found")
    storage_service.save_bots(updated)
    return {"status": "ok", "deleted_id": bot_id}
