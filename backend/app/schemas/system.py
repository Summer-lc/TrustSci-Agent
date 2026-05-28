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
    cors_origins: list[str]

