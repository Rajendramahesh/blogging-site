import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Request
from dependencies import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_SAFE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}


@router.post("/image")
async def upload_image(
    request: Request,
    image: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Receive a file from the Editor.js image plugin (byFile endpoint).
    Returns Editor.js-compatible success payload.
    """
    if image.content_type not in _ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, GIF, and WebP are allowed")

    data = await image.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(400, "File exceeds 10 MB limit")

    raw_ext = (image.filename or "image").rsplit(".", 1)[-1].lower()
    ext = raw_ext if raw_ext in _SAFE_EXTS else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"

    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(data)

    url = str(request.base_url) + f"uploads/{filename}"
    return {"success": 1, "file": {"url": url}}


@router.post("/by-url")
async def upload_by_url(
    body: dict = Body(...),
    current_user=Depends(get_current_user),
):
    """
    Receive a URL from the Editor.js image plugin (byUrl endpoint).
    Validates and passes through the URL so images from external hosts
    (e.g. Unsplash CDN) are served directly without re-uploading.
    """
    url: str = body.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Invalid URL")
    return {"success": 1, "file": {"url": url}}
