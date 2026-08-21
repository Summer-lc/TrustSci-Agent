import hashlib
import json
from pathlib import Path

from httpx import HTTPError

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.browser import BrowserCaptureRequest, BrowserCaptureResult
from app.schemas.run_control import PaperPreviewRequest, PaperPreviewResult
from app.tools.browser_client import BrowserWorkerClient

router = APIRouter(prefix="/api/browser", tags=["browser"])


@router.post("/capture", response_model=BrowserCaptureResult)
async def capture_page(payload: BrowserCaptureRequest) -> BrowserCaptureResult:
    settings = get_settings()
    try:
        return await BrowserWorkerClient(settings.browser_worker_url).capture(payload)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"browser worker request failed: {exc}") from exc


@router.post("/paper-preview", response_model=PaperPreviewResult)
async def preview_paper(payload: PaperPreviewRequest) -> PaperPreviewResult:
    settings = get_settings()
    preview_dir = Path(settings.data_dir) / "browser_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(
        f"{payload.paper_id}\n{payload.source_url}".encode("utf-8")
    ).hexdigest()
    cache_path = preview_dir / f"{cache_key}.json"
    if cache_path.exists():
        try:
            cached = PaperPreviewResult.model_validate_json(
                cache_path.read_text(encoding="utf-8")
            )
            if cached.kind == "web_snapshot" and _looks_like_access_challenge(cached.title):
                cached = cached.model_copy(
                    update={
                        "kind": "metadata_only",
                        "screenshot_url": None,
                        "error_summary": "来源网站要求人机验证，已移除旧的验证页面快照；请使用原文链接打开。",
                    }
                )
                cache_path.write_text(cached.model_dump_json(indent=2), encoding="utf-8")
            return cached.model_copy(update={"cached": True})
        except (OSError, ValueError):
            cache_path.unlink(missing_ok=True)

    try:
        capture = await BrowserWorkerClient(settings.browser_worker_url).capture(
            BrowserCaptureRequest(
                url=payload.source_url,
                download_pdfs=False,
                max_pdf_downloads=0,
            )
        )
        if capture.blocked_reason or _looks_like_access_challenge(capture.title):
            result = PaperPreviewResult(
                paper_id=payload.paper_id,
                source_url=payload.source_url,
                kind="metadata_only",
                title=capture.title,
                original_url=capture.url or payload.source_url,
                cached=False,
                error_summary="来源网站要求人机验证，系统已停止自动抓取；请使用原文链接打开。",
            )
            cache_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            return result
        screenshot_name = Path(capture.screenshot_path).name
        if not screenshot_name:
            raise RuntimeError("browser worker did not return a readable screenshot")
        result = PaperPreviewResult(
            paper_id=payload.paper_id,
            source_url=payload.source_url,
            kind="web_snapshot",
            title=capture.title,
            screenshot_url=f"/api/browser/artifacts/{screenshot_name}",
            original_url=capture.url or payload.source_url,
            cached=False,
        )
        cache_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result
    except Exception as exc:
        return PaperPreviewResult(
            paper_id=payload.paper_id,
            source_url=payload.source_url,
            kind="metadata_only",
            original_url=payload.source_url,
            cached=False,
            error_summary=f"论文网页抓取失败：{exc}",
        )


@router.get("/artifacts/{filename}")
async def get_browser_artifact(filename: str) -> FileResponse:
    if Path(filename).name != filename or Path(filename).suffix.lower() != ".png":
        raise HTTPException(status_code=404, detail="browser artifact not found")
    trace_dir = (Path(get_settings().data_dir) / "browser_traces").resolve()
    artifact = (trace_dir / filename).resolve()
    if artifact.parent != trace_dir or not artifact.is_file():
        raise HTTPException(status_code=404, detail="browser artifact not found")
    return FileResponse(artifact, media_type="image/png")


def _looks_like_access_challenge(title: str) -> bool:
    normalized = " ".join(title.lower().split())
    return any(
        marker in normalized
        for marker in (
            "just a moment",
            "attention required",
            "verify you are human",
            "security verification",
            "人机验证",
            "安全验证",
        )
    )
