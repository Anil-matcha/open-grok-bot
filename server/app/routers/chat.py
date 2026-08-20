import json
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional

from app.schemas.contracts import TurnRequest, Message
from app.services.storage_service import storage_service
from app.services.muapi_service import muapi_service
from app.services.approval_broker import approval_broker
from app.services.workspace_service import (
    WorkspaceToolError,
    parse_workspace_command,
    workspace_service,
)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.get("/history/{thread_id}", response_model=List[Message])
async def get_history(thread_id: str):
    return storage_service.get_messages(thread_id=thread_id)

@router.post("/send")
async def send_message(req: TurnRequest):
    # Store user message
    user_msg = {
        "id": f"msg-{uuid.uuid4().hex[:6]}",
        "thread_id": req.thread_id,
        "bot_id": req.bot_id,
        "sender": "user",
        "text": req.user_text,
        "image_url": req.image_url,
        "created_at": datetime.now().isoformat(),
        "model": req.model or "grok-4-5",
        "item_type": "user_text"
    }

    storage_service.add_message(user_msg)
    return {"status": "ok", "message": user_msg}

@router.get("/stream/{thread_id}")
async def stream_turn(thread_id: str, model: Optional[str] = Query("grok-4-5")):
    """
    SSE stream endpoint broadcasting real-time tokens & tool events for a given thread.
    """
    history = storage_service.get_messages(thread_id=thread_id)
    bots = storage_service.get_bots()
    current_bot = next((b for b in bots if b["id"] == thread_id), None)
    
    raw_prompt = current_bot["system_prompt"] if current_bot else "You are a helpful AI assistant."
    current_time_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    system_prompt = f"Current Date & Time: {current_time_str}.\n\n{raw_prompt}"
    selected_model = model or (current_bot["model"] if current_bot else "grok-4-5")

    formatted_history = []
    for m in history:
        if m["sender"] in ["user", "bot"]:
            formatted_history.append({
                "role": "user" if m["sender"] == "user" else "assistant",
                "content": m.get("text", ""),
                "image_url": m.get("image_url")
            })


    async def event_generator():
        bot_msg_id = f"msg-{uuid.uuid4().hex[:6]}"
        accumulated_text = ""
        tool_context = ""

        # Emit turn started
        yield {
            "event": "message",
            "data": json.dumps({"type": "turn.started", "botMsgId": bot_msg_id, "model": selected_model})
        }

        last_user_text = formatted_history[-1]["content"] if formatted_history else ""
        try:
            workspace_call = parse_workspace_command(last_user_text)
        except WorkspaceToolError as exc:
            workspace_call = None
            tool_context = f"A workspace request was rejected before execution: {exc}"
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "tool.failed",
                    "tool": "workspace",
                    "error": str(exc),
                }),
            }

        if workspace_call:
            approval = approval_broker.open(thread_id, thread_id, workspace_call)
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "request.opened",
                    "requestType": "permission",
                    "requestId": approval["request_id"],
                    "tool": approval["tool"],
                    "summary": approval["summary"],
                    "arguments": approval["arguments"],
                }),
            }

            decision = await approval_broker.wait(approval["request_id"])
            if decision == "allow":
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "tool.started",
                        "tool": workspace_call.name,
                        "requestId": approval["request_id"],
                    }),
                }
                try:
                    result = workspace_service.execute(workspace_call)
                    tool_context = f"Workspace tool result ({workspace_call.name}): {json.dumps(result)}"
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "tool.completed",
                            "tool": workspace_call.name,
                            "requestId": approval["request_id"],
                            "result": result,
                        }),
                    }
                    storage_service.add_audit_event({
                        "event": "tool.completed",
                        "request_id": approval["request_id"],
                        "tool": workspace_call.name,
                        "created_at": datetime.now().isoformat(),
                    })
                except WorkspaceToolError as exc:
                    tool_context = f"Workspace tool failed ({workspace_call.name}): {exc}"
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "tool.failed",
                            "tool": workspace_call.name,
                            "requestId": approval["request_id"],
                            "error": str(exc),
                        }),
                    }
                    storage_service.add_audit_event({
                        "event": "tool.failed",
                        "request_id": approval["request_id"],
                        "tool": workspace_call.name,
                        "error": str(exc),
                        "created_at": datetime.now().isoformat(),
                    })
            elif decision == "deny":
                tool_context = f"Workspace tool denied by the user: {workspace_call.name}"
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "tool.denied",
                        "tool": workspace_call.name,
                        "requestId": approval["request_id"],
                    }),
                }
            else:
                tool_context = f"Workspace tool expired before approval: {workspace_call.name}"
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "tool.expired",
                        "tool": workspace_call.name,
                        "requestId": approval["request_id"],
                    }),
                }

        if tool_context:
            system_prompt = f"{system_prompt}\n\n{tool_context}"

        # Stream content from MUAPI service
        try:
            async for event in muapi_service.stream_chat_completion(
                model=selected_model,
                messages=formatted_history,
                system_prompt=system_prompt
            ):
                if event["type"] == "content.delta":
                    accumulated_text += event["delta"]
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "content.delta",
                            "botMsgId": bot_msg_id,
                            "delta": event["delta"]
                        })
                    }
                elif event["type"] == "turn.completed":
                    bot_msg = {
                        "id": bot_msg_id,
                        "thread_id": thread_id,
                        "bot_id": thread_id,
                        "sender": "bot",
                        "text": accumulated_text,
                        "created_at": datetime.now().isoformat(),
                        "model": selected_model,
                        "item_type": "assistant_text"
                    }
                    storage_service.add_message(bot_msg)
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "turn.completed", "ok": True, "botMsgId": bot_msg_id})
                    }
        except asyncio.CancelledError:
            raise

    return EventSourceResponse(event_generator())
