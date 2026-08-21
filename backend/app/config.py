from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    qwen_temperature: float = 0.2
    qwen_timeout_seconds: float = 60
    qwen_max_retries: int = Field(default=1, ge=0, le=5)

    openalex_email: str = ""
    crossref_email: str = ""
    semantic_scholar_api_key: str = ""
    max_papers: int = Field(default=6, ge=1, le=20)
    materials_project_api_key: str = ""
    github_token: str = ""
    browser_worker_url: str = "http://browser-worker:8010"

    # Orchestration engine switch. "classic" keeps the hand-written
    # ScientistWorkflow (default, stable); "langgraph" drives the LangGraph
    # StateGraph implementation. See app/workflows/langgraph_workflow.py.
    workflow_engine: str = "classic"

    data_dir: Path = Path("data")
    experiments_dir: Path = Path("experiments/seismic_event_classification")
    code_experiment_timeout_seconds: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.dashscope_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
