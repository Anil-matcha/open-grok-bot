import asyncio
import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timezone
from app.config import settings
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

BACKEND_URL = "https://backend.composio.dev/api/v3"
CONNECT_URL = "https://connect.composio.dev/mcp"

# ─── Curated fallback catalog ────────────────────────────────────────────────
CURATED = [
    {"slug": "slack",          "label": "Slack",           "blurb": "Post updates and read channels",       "domain": "slack.com",            "logo": None},
    {"slug": "github",         "label": "GitHub",          "blurb": "Issues, pull requests, and code",     "domain": "github.com",           "logo": None},
    {"slug": "gmail",          "label": "Gmail",           "blurb": "Read and send email",                  "domain": "gmail.com",            "logo": None},
    {"slug": "googlecalendar", "label": "Google Calendar", "blurb": "Read and create events",              "domain": "calendar.google.com",  "logo": None},
    {"slug": "googlesheets",   "label": "Google Sheets",   "blurb": "Read and update spreadsheets",        "domain": "sheets.google.com",    "logo": None},
    {"slug": "googledocs",     "label": "Google Docs",     "blurb": "Read and write documents",             "domain": "docs.google.com",      "logo": None},
    {"slug": "googledrive",    "label": "Google Drive",    "blurb": "Browse and manage files",              "domain": "drive.google.com",     "logo": None},
    {"slug": "notion",         "label": "Notion",          "blurb": "Pages and databases",                  "domain": "notion.so",            "logo": None},
    {"slug": "linear",         "label": "Linear",          "blurb": "Issues and project tracking",         "domain": "linear.app",           "logo": None},
    {"slug": "discord",        "label": "Discord",         "blurb": "Messages and channels",               "domain": "discord.com",          "logo": None},
    {"slug": "x",              "label": "X (Twitter)",     "blurb": "Post and read on X",                  "domain": "x.com",                "logo": None},
    {"slug": "hubspot",        "label": "HubSpot",         "blurb": "CRM search & updates",                "domain": "hubspot.com",          "logo": None},
    {"slug": "salesforce",     "label": "Salesforce",      "blurb": "CRM records and reports",             "domain": "salesforce.com",       "logo": None},
    {"slug": "jira",           "label": "Jira",            "blurb": "Issues and sprints",                   "domain": "atlassian.com",        "logo": None},
    {"slug": "asana",          "label": "Asana",           "blurb": "Tasks and projects",                  "domain": "asana.com",            "logo": None},
    {"slug": "trello",         "label": "Trello",          "blurb": "Boards and cards",                    "domain": "trello.com",           "logo": None},
    {"slug": "dropbox",        "label": "Dropbox",         "blurb": "Files and folders",                   "domain": "dropbox.com",          "logo": None},
    {"slug": "airtable",       "label": "Airtable",        "blurb": "Bases and records",                   "domain": "airtable.com",         "logo": None},
    {"slug": "figma",          "label": "Figma",           "blurb": "Files and comments",                  "domain": "figma.com",            "logo": None},
    {"slug": "stripe",         "label": "Stripe",          "blurb": "Payments and customers",              "domain": "stripe.com",           "logo": None},
    {"slug": "zapier",         "label": "Zapier",          "blurb": "Connect 9,000+ apps",                 "domain": "zapier.com",           "logo": None},
    {"slug": "reddit",         "label": "Reddit",          "blurb": "Browse and post",                     "domain": "reddit.com",           "logo": None},
    {"slug": "sentry",         "label": "Sentry",          "blurb": "Errors and alerts",                   "domain": "sentry.io",            "logo": None},
    {"slug": "posthog",        "label": "PostHog",         "blurb": "Analytics and feature flags",         "domain": "posthog.com",          "logo": None},
]

# ─── In-memory toolkit cache (10 min) ────────────────────────────────────────
_toolkit_cache: Optional[dict] = None
_toolkit_cache_at: float = 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _parse_mcp_response(text: str) -> dict:
    import json
    line = text if text.startswith("{") else next(
        (l[6:] for l in text.splitlines() if l.startswith("data: ")), None
    )
    if not line:
        raise ValueError("empty MCP response")
    msg = json.loads(line)
    if msg.get("error"):
        raise ValueError(msg["error"].get("message", "MCP error"))
    content = next(
        (c.get("text") for c in (msg.get("result", {}).get("content") or []) if c.get("type") == "text"),
        None
    )
    if not content:
        return msg.get("result") or {}
    try:
        return json.loads(content)
    except Exception:
        return {"text": content}


async def _composio_tool(key: str, name: str, args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            CONNECT_URL,
            headers={
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "x-consumer-api-key": key,
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": name, "arguments": args}},
        )
        res.raise_for_status()
        return await _parse_mcp_response(res.text)


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/catalog")
async def catalog():
    """Return toolkit catalog. Tries Composio backend API; falls back to curated list."""
    import time
    global _toolkit_cache, _toolkit_cache_at

    cfg = storage_service.get_settings()
    composio_key = cfg.get("composio_api_key") or cfg.get("composio_key") or settings.COMPOSIO_API_KEY

    # Serve cache if fresh
    if _toolkit_cache and (time.time() - _toolkit_cache_at) < 600:
        return {**_toolkit_cache, "configured": bool(composio_key)}

    if composio_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(
                    f"{BACKEND_URL}/toolkits?limit=200&sort_by=usage",
                    headers={"x-api-key": composio_key},
                )
                if res.ok:
                    data = res.json()
                    items = data.get("items") or data.get("data") or []
                    if items:
                        cards = [
                            {
                                "slug": (t.get("slug") or t.get("key") or t.get("name") or "").lower(),
                                "label": t.get("name") or t.get("slug") or "",
                                "blurb": (t.get("meta", {}).get("description") or t.get("description") or "")[:90],
                                "logo": t.get("meta", {}).get("logo") or t.get("logo"),
                                "domain": None,
                            }
                            for t in items
                        ]
                        _toolkit_cache = {"cards": cards, "source": "api"}
                        _toolkit_cache_at = time.time()
                        return {**_toolkit_cache, "configured": True}
        except Exception:
            pass

    return {"cards": CURATED, "source": "curated", "configured": bool(composio_key)}


@router.get("")
async def connection_status(services: str = ""):
    """Check connection status for a comma-separated list of slugs."""
    cfg = storage_service.get_settings()
    composio_key = cfg.get("composio_api_key") or cfg.get("composio_key") or settings.COMPOSIO_API_KEY
    slugs = [s.strip() for s in services.split(",") if s.strip()]

    if not composio_key or not slugs:
        return {"services": {slug: {"connected": False} for slug in slugs}}

    try:
        out = await _composio_tool(composio_key, "COMPOSIO_MANAGE_CONNECTIONS",
                                   {"toolkits": [{"name": s, "action": "list"} for s in slugs]})
        results = (out or {}).get("data", {}).get("results", {})
        status = {}
        for slug in slugs:
            r = results.get(slug, {})
            accounts = r.get("accounts") or []
            active = any((a.get("status") or "").lower() == "active" for a in accounts) \
                     or (r.get("status") or "").lower() == "active"
            status[slug] = {"connected": active}
        return {"services": status}
    except Exception as e:
        return {"services": {slug: {"connected": False} for slug in slugs}, "error": str(e)}


@router.post("/{slug}/authorize")
async def authorize(slug: str):
    """Get OAuth URL to connect a service."""
    cfg = storage_service.get_settings()
    composio_key = cfg.get("composio_api_key") or cfg.get("composio_key") or settings.COMPOSIO_API_KEY
    if not composio_key:
        return JSONResponse({"error": "No Composio key configured"}, status_code=400)
    try:
        out = await _composio_tool(composio_key, "COMPOSIO_MANAGE_CONNECTIONS",
                                   {"toolkits": [{"name": slug, "action": "add"}]})
        import re, json as jsonlib
        raw = jsonlib.dumps(out)
        urls = re.findall(r"https://[^\"\\\s]+", raw)
        url = next((u for u in urls if any(k in u.lower() for k in ["composio", "connect", "auth"])), None) or (urls[0] if urls else None)
        if not url:
            return JSONResponse({"error": f"No auth link returned for {slug}"}, status_code=502)
        storage_service.add_audit_event({
            "event": "connector.authorization_requested",
            "connector": slug,
            "created_at": _now(),
        })
        return {"url": url}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@router.delete("/{slug}")
async def disconnect(slug: str):
    """Disconnect a service by removing all connected accounts."""
    cfg = storage_service.get_settings()
    composio_key = cfg.get("composio_api_key") or cfg.get("composio_key") or settings.COMPOSIO_API_KEY
    if not composio_key:
        return JSONResponse({"error": "No Composio key configured"}, status_code=400)
    try:
        out = await _composio_tool(composio_key, "COMPOSIO_MANAGE_CONNECTIONS",
                                   {"toolkits": [{"name": slug, "action": "list"}]})
        accounts = (out or {}).get("data", {}).get("results", {}).get(slug, {}).get("accounts", [])
        ids = [a.get("id") or a.get("account_id") or a.get("nanoid") for a in accounts]
        ids = [i for i in ids if i]
        for acc_id in ids:
            await _composio_tool(composio_key, "COMPOSIO_MANAGE_CONNECTIONS",
                                 {"toolkits": [{"name": slug, "action": "remove", "account_id": acc_id}]})
        storage_service.add_audit_event({
            "event": "connector.disconnected",
            "connector": slug,
            "removed": len(ids),
            "created_at": _now(),
        })
        return {"removed": len(ids), "slug": slug}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)
