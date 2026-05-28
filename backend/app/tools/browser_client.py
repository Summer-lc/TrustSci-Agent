import httpx

from app.schemas.browser import BrowserCaptureRequest, BrowserCaptureResult


class BrowserWorkerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def capture(self, payload: BrowserCaptureRequest) -> BrowserCaptureResult:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{self.base_url}/capture", json=payload.model_dump(mode="json"))
            response.raise_for_status()
        return BrowserCaptureResult.model_validate(response.json())

