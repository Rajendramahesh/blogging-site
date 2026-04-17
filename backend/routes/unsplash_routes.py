from fastapi import APIRouter, Query, HTTPException, Body
import httpx
from config import settings

router = APIRouter(prefix="/unsplash", tags=["unsplash"])


def _check_configured():
    if not settings.unsplash_access_key:
        raise HTTPException(503, "Unsplash integration not configured")


@router.get("/search")
async def search_photos(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=30),
):
    _check_configured()
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": query,
                    "page": page,
                    "per_page": per_page,
                    "client_id": settings.unsplash_access_key,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(exc.response.status_code, "Unsplash API error")
        except httpx.RequestError:
            raise HTTPException(503, "Could not reach Unsplash API")


@router.post("/download")
async def trigger_download(body: dict = Body(...)):
    """
    Trigger the Unsplash download endpoint — required by Unsplash API guidelines
    whenever a user selects/downloads a photo.
    """
    _check_configured()
    download_location: str = body.get("download_location", "")
    if not download_location.startswith("https://api.unsplash.com/"):
        raise HTTPException(400, "Invalid download_location")

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.get(
                download_location,
                params={"client_id": settings.unsplash_access_key},
            )
        except Exception:
            pass  # best-effort; don't block the user if tracking fails

    return {"success": True}
