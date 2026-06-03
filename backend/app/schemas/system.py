from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    llm_enabled: bool
    model: str


class PublicConfigResponse(BaseModel):
    qwen_model: str
    llm_enabled: bool
    dashscope_base_url: str
    max_papers: int
    data_dir: str
    browser_worker_url: str
    materials_project_configured: bool
    semantic_scholar_configured: bool
    arxiv_available: bool = True
    cors_origins: list[str]


class QwenPingResponse(BaseModel):
    configured: bool
    status: str
    model: str
    message: str
    response_preview: str | None = None
    token_usage: dict = {}
    error: str | None = None
