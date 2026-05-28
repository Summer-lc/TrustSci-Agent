from fastapi import APIRouter

from app.config import get_settings
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.tools.materials_data import build_materials_profiles, run_mean_baseline

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/profiles", response_model=list[DatasetProfile])
async def get_data_profiles() -> list[DatasetProfile]:
    settings = get_settings()
    return build_materials_profiles(settings.data_dir, settings.materials_project_api_key)


@router.post("/baseline", response_model=BaselineResultCard)
async def run_baseline() -> BaselineResultCard:
    return run_mean_baseline(get_settings().data_dir)

