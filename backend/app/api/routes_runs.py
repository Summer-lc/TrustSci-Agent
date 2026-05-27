import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.common import RunStatus
from app.schemas.run import ResearchRun, ResearchRunCreate
from app.storage.in_memory import run_store
from app.workflows.scientist_workflow import ScientistWorkflow
from app.tools.llm_logger import read_llm_logs

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=ResearchRun)
async def create_run(payload: ResearchRunCreate) -> ResearchRun:
    run = ResearchRun(domain=payload.domain, question=payload.question, constraints=payload.constraints)
    return run_store.create(run)


@router.get("", response_model=list[ResearchRun])
async def list_runs() -> list[ResearchRun]:
    return run_store.list()


@router.get("/{run_id}", response_model=ResearchRun)
async def get_run(run_id: str) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.post("/{run_id}/start", response_model=ResearchRun)
async def start_run(run_id: str, background_tasks: BackgroundTasks) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status == RunStatus.running:
        return run
    workflow = ScientistWorkflow(get_settings())
    background_tasks.add_task(workflow.run, run)
    run.status = RunStatus.running
    run.current_stage = "queued"
    return run_store.save(run)


@router.post("/{run_id}/run-sync", response_model=ResearchRun)
async def run_sync(run_id: str) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return await ScientistWorkflow(get_settings()).run(run)


@router.get("/{run_id}/evidence")
async def get_evidence(run_id: str):
    return _must_get_run(run_id).evidence


@router.get("/{run_id}/hypotheses")
async def get_hypotheses(run_id: str):
    return _must_get_run(run_id).hypotheses


@router.get("/{run_id}/llm-calls")
async def get_llm_calls(run_id: str):
    _must_get_run(run_id)
    return read_llm_logs(get_settings().data_dir, run_id)


@router.post("/{run_id}/hypotheses/{hypothesis_id}/select", response_model=ResearchRun)
async def select_hypothesis(run_id: str, hypothesis_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    found = False
    for hypothesis in run.hypotheses:
        hypothesis.selected = hypothesis.hypothesis_id == hypothesis_id
        found = found or hypothesis.selected
    if not found:
        raise HTTPException(status_code=404, detail="hypothesis not found")
    return run_store.save(run)


@router.post("/{run_id}/report", response_model=ResearchRun)
async def regenerate_report(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    return await ScientistWorkflow(get_settings()).run(run)


@router.get("/{run_id}/report/export")
async def export_report(run_id: str, format: str = "md"):
    run = _must_get_run(run_id)
    if format == "json":
        if run.report is None:
            raise HTTPException(status_code=404, detail="report not generated")
        return run.report
    path = Path("data/outputs/reports") / f"{run_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="markdown report not found")
    return FileResponse(path, media_type="text/markdown", filename=f"{run_id}.md")


def _must_get_run(run_id: str) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run
