from fastapi import APIRouter, Query
from typing import List, Dict, Any

from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=List[Dict[str, Any]])
async def get_audit_events(limit: int = Query(100, ge=1, le=500)):
    return storage_service.get_audit_events(limit)
