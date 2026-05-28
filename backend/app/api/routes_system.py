from fastapi import APIRouter

from app.config import get_settings
from app.schemas.system import HealthResponse, PublicConfigResponse

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def system_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", llm_enabled=settings.llm_enabled, model=settings.qwen_model)


@router.get("/config", response_model=PublicConfigResponse)
async def public_config() -> PublicConfigResponse:
    settings = get_settings()
    return PublicConfigResponse(
        qwen_model=settings.qwen_model,
        llm_enabled=settings.llm_enabled,
        dashscope_base_url=settings.dashscope_base_url,
        max_papers=settings.max_papers,
        data_dir=str(settings.data_dir),
        browser_worker_url=settings.browser_worker_url,
        materials_project_configured=bool(settings.materials_project_api_key),
        cors_origins=settings.cors_origin_list,
    )

