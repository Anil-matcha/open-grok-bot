from fastapi import APIRouter
from typing import Dict, Any
from app.schemas.contracts import AppSettingsSchema
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

@router.get("", response_model=AppSettingsSchema)
async def get_settings():
    data = storage_service.get_public_settings()
    return AppSettingsSchema(**data)

@router.post("", response_model=AppSettingsSchema)
async def save_settings(new_settings: AppSettingsSchema):
    storage_service.save_settings(new_settings.model_dump())
    return AppSettingsSchema(**storage_service.get_public_settings())
