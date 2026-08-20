import base64
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1", tags=["upload"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}

@router.post("/upload")
async def upload_image_file(file: UploadFile = File(...)):
    """
    Direct file upload endpoint for images.
    Strictly validates image MIME types and dispatches to MUAPI /upload_file endpoint.
    """
    content_type = file.content_type or ""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Validate image ONLY constraint
    if content_type not in ALLOWED_IMAGE_TYPES and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only image files (JPEG, PNG, WEBP, GIF, AVIF) are allowed."
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty.")

    app_settings = storage_service.get_settings()
    api_key = app_settings.get("muapi_api_key") or settings.MUAPI_API_KEY
    base_url = (app_settings.get("muapi_base_url") or settings.MUAPI_BASE_URL).rstrip("/")

    # If valid MUAPI API Key is available, dispatch to MUAPI direct upload_file endpoint
    if api_key and not api_key.startswith("mock_"):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                files_payload = {"file": (filename or "image.png", file_bytes, content_type or "image/png")}
                headers = {"x-api-key": api_key}

                res = await client.post(f"{base_url}/upload_file", files=files_payload, headers=headers)
                if res.status_code == 200:
                    res_data = res.json()
                    hosted_url = res_data.get("url") or res_data.get("file_url") or res_data.get("link")
                    if hosted_url:
                        return {"url": hosted_url, "filename": filename}
        except Exception as err:
            print(f"MUAPI upload_file dispatch notice: {err}")

    # Fallback base64 data URL for local offline image previews
    b64_str = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{content_type or 'image/png'};base64,{b64_str}"
    return {"url": data_url, "filename": filename}
