from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_runs import router as runs_router
from app.config import get_settings

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "llm_enabled": settings.llm_enabled, "model": settings.qwen_model}

