from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import bots, models, chat, approvals, upload, settings as settings_router, connectors, audit

app = FastAPI(
    title="Open Grok Bot API",
    description="FastAPI backend for Open Grok Bot powered by MUAPI LLM endpoints",
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bots.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(approvals.router)
app.include_router(settings_router.router)
app.include_router(connectors.router)
app.include_router(audit.router)


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "online",
        "service": "Open Grok Bot FastAPI Backend",
        "provider": "MUAPI API Endpoints",
        "default_model": "grok-4-5"
    }
