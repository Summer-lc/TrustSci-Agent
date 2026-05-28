from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_browser import router as browser_router
from app.api.routes_data import router as data_router
from app.api.routes_runs import router as runs_router
from app.api.routes_system import router as system_router
from app.config import get_settings
from app.schemas.system import HealthResponse

settings = get_settings()

app = FastAPI(
    title="TrustSci-Agent API",
    description="Qwen-compatible multi-agent AI Scientist MVP with evidence ledger and citation verification.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router)
app.include_router(data_router)
app.include_router(browser_router)
app.include_router(system_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", llm_enabled=settings.llm_enabled, model=settings.qwen_model)
