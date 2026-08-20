import json
import asyncio
import httpx
from typing import AsyncGenerator, Dict, Any, List
from app.config import settings
from app.services.storage_service import storage_service

class MuapiService:
    def __init__(self):
        pass

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system_prompt: str = ""
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completions from MUAPI API endpoint.
        Uses exact user-selected model slug without any model remapping or fallback.
        """
        app_settings = storage_service.get_settings()
        api_key = app_settings.get("muapi_api_key") or settings.MUAPI_API_KEY
        base_url = (app_settings.get("muapi_base_url") or settings.MUAPI_BASE_URL).rstrip("/")

        if not api_key:
            yield {
                "type": "content.delta",
                "delta": "Error: MUAPI API Key is missing. Please configure your key in App Settings & API Credentials."
            }
            yield {"type": "turn.completed", "ok": False}
            return

        # Target EXACT model slug passed by user without any alias remapping or fallback
        target_endpoint = (model or "grok-4-5").strip()

        # Extract latest user prompt and image_url
        user_prompt = ""
        image_url = None
        for m in reversed(messages):
            if m.get("role") == "user":
                if not user_prompt:
                    user_prompt = m.get("content", "")
                if not image_url and m.get("image_url"):
                    image_url = m.get("image_url")
                break

        # Format last 10 previous conversation messages into system_prompt so MUAPI maintains memory
        previous_messages = messages[:-1] if len(messages) > 1 else []
        last_10_messages = previous_messages[-10:] if len(previous_messages) > 10 else previous_messages

        history_blocks = []
        for m in last_10_messages:
            role_name = "User" if m.get("role") == "user" else "Assistant"
            content = m.get("content", "").strip()
            msg_img = m.get("image_url")
            if msg_img:
                content = f"{content} [Attached Image: {msg_img}]".strip()
            if content:
                history_blocks.append(f"{role_name}: {content}")

        formatted_history = "\n".join(history_blocks)

        full_system_prompt = system_prompt.strip() if system_prompt else ""
        if formatted_history:
            context_prefix = f"### Recent Conversation History (Last {len(last_10_messages)} Messages):\n{formatted_history}\n\n### Instructions:\nRespond to the latest user prompt keeping the conversation context above in mind."
            if full_system_prompt:
                full_system_prompt = f"{full_system_prompt}\n\n{context_prefix}"
            else:
                full_system_prompt = context_prefix

        # Standard MUAPI headers matching muapiapp protocol
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        # Format input payload matching MUAPI's exact image_url input schema
        input_body = {
            "prompt": user_prompt,
            "image_url": image_url if image_url else None,
            "system_prompt": full_system_prompt if full_system_prompt else None,
            "reasoning_effort": "low",
            "web_search": False
        }

        # Direct model endpoint submission URL (POST {base_url}/{target_endpoint})
        request_attempts = [
            (f"{base_url}/{target_endpoint}", input_body)
        ]




        last_error = ""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for endpoint_url, body_data in request_attempts:
                    try:
                        response = await client.post(endpoint_url, json=body_data, headers=headers)

                        if response.status_code == 200:
                            res_data = response.json()

                            # Check for Task Prediction Submission (returns request_id)
                            request_id = res_data.get("request_id") or res_data.get("id")
                            if request_id:
                                # Async Polling Loop for predictions result (GET /predictions/{request_id}/result)
                                poll_url = f"{base_url}/predictions/{request_id}/result"
                                poll_deadline = asyncio.get_event_loop().time() + 180

                                while asyncio.get_event_loop().time() < poll_deadline:
                                    try:
                                        poll_res = await client.get(poll_url, headers=headers)
                                        if poll_res.status_code == 200:
                                            poll_data = poll_res.json()
                                            status = poll_data.get("status")
                                            error_text = poll_data.get("error")

                                            if status == "completed":
                                                # Safely parse outputs array (handles strings like ["Hi there! 😊"] or objects)
                                                output_text = ""
                                                outputs = poll_data.get("outputs", [])
                                                if isinstance(outputs, list) and len(outputs) > 0:
                                                    first_out = outputs[0]
                                                    if isinstance(first_out, str):
                                                        output_text = first_out
                                                    elif isinstance(first_out, dict):
                                                        output_text = first_out.get("text") or first_out.get("url") or str(first_out)
                                                
                                                if not output_text:
                                                    output_text = poll_data.get("result") or poll_data.get("output") or "Task completed."

                                                # Stream the real response text back to the frontend UI
                                                words = str(output_text).split(" ")
                                                for i, w in enumerate(words):
                                                    yield {"type": "content.delta", "delta": w + (" " if i < len(words) - 1 else "")}
                                                    await asyncio.sleep(0.02)
                                                yield {"type": "turn.completed", "ok": True}
                                                return

                                            elif status in ["failed", "cancelled", "error"] or error_text:
                                                err_msg = error_text or f"Task ended with status: {status}"
                                                yield {"type": "content.delta", "delta": f"Error: {err_msg}"}
                                                yield {"type": "turn.completed", "ok": False}
                                                return
                                        else:
                                            # Catch non-200 polling HTTP errors immediately (e.g. 404, 401, 500)
                                            poll_err = f"Error polling prediction result ({poll_url}) - HTTP {poll_res.status_code}: {poll_res.text}"
                                            yield {"type": "content.delta", "delta": f"Error: {poll_err}"}
                                            yield {"type": "turn.completed", "ok": False}
                                            return

                                    except Exception as poll_exc:
                                        yield {"type": "content.delta", "delta": f"Error during polling: {str(poll_exc)}"}
                                        yield {"type": "turn.completed", "ok": False}
                                        return

                                    await asyncio.sleep(0.5)


                            # Direct output in initial POST response
                            direct_output = ""
                            outputs = res_data.get("outputs", [])
                            if isinstance(outputs, list) and len(outputs) > 0:
                                first_out = outputs[0]
                                if isinstance(first_out, str):
                                    direct_output = first_out
                                elif isinstance(first_out, dict):
                                    direct_output = first_out.get("text") or first_out.get("url") or str(first_out)

                            if not direct_output:
                                direct_output = res_data.get("result") or res_data.get("output") or res_data.get("choices", [{}])[0].get("message", {}).get("content", "")

                            if direct_output:
                                words = str(direct_output).split(" ")
                                for i, w in enumerate(words):
                                    yield {"type": "content.delta", "delta": w + (" " if i < len(words) - 1 else "")}
                                    await asyncio.sleep(0.02)
                                yield {"type": "turn.completed", "ok": True}
                                return

                        else:
                            last_error = f"MUAPI Endpoint ({endpoint_url}) returned HTTP {response.status_code}: {response.text}"
                    except Exception as exc:
                        last_error = f"Connection error on ({endpoint_url}): {str(exc)}"

        except Exception as exc:
            last_error = f"MUAPI Client Error: {str(exc)}"

        # Output exact backend error message to frontend UI without any fallback mockup
        error_display = last_error if last_error else "Error: Unable to connect to MUAPI service."
        yield {"type": "content.delta", "delta": error_display}
        yield {"type": "turn.completed", "ok": False}

muapi_service = MuapiService()



