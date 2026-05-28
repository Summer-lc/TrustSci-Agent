from httpx import HTTPError

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.browser import BrowserCaptureRequest, BrowserCaptureResult
from app.tools.browser_client import BrowserWorkerClient

router = APIRouter(prefix="/api/browser", tags=["browser"])


@router.post("/capture", response_model=BrowserCaptureResult)
async def capture_page(payload: BrowserCaptureRequest) -> BrowserCaptureResult:
    settings = get_settings()
    try:
        return await BrowserWorkerClient(settings.browser_worker_url).capture(payload)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"browser worker request failed: {exc}") from exc

