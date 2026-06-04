from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.claim import ClaimAuditReport
from app.schemas.common import RunStatus
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.evidence.ledger import evidence_from_pdf_chunks
from app.schemas.evidence import EvidenceItem, PaperChunk, PdfEvidenceIngestRequest
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun, ResearchRunCreate
from app.storage.in_memory import run_store
from app.tools.llm_logger import read_llm_logs
from app.tools.pdf_parser import parse_pdf_chunks
from app.workflows.scientist_workflow import ScientistWorkflow

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


@router.get("/{run_id}/papers", response_model=list[Paper])
async def get_papers(run_id: str) -> list[Paper]:
    return _must_get_run(run_id).papers


@router.get("/{run_id}/evidence", response_model=list[EvidenceItem])
async def get_evidence(run_id: str) -> list[EvidenceItem]:
    return _must_get_run(run_id).evidence


@router.get("/{run_id}/paper-chunks", response_model=list[PaperChunk])
async def get_paper_chunks(run_id: str) -> list[PaperChunk]:
    return _must_get_run(run_id).paper_chunks


@router.get("/{run_id}/claim-audit", response_model=ClaimAuditReport | None)
async def get_claim_audit(run_id: str) -> ClaimAuditReport | None:
    return _must_get_run(run_id).claim_audit


@router.post("/{run_id}/pdf-evidence", response_model=ResearchRun)
async def ingest_pdf_evidence(run_id: str, payload: PdfEvidenceIngestRequest) -> ResearchRun:
    run = _must_get_run(run_id)
    pdf_path = _safe_pdf_path(payload.pdf_path, get_settings().data_dir)
    paper = next((item for item in run.papers if item.paper_id == payload.paper_id), None)
    chunks = parse_pdf_chunks(
        pdf_path,
        paper_id=payload.paper_id,
        source_title=payload.source_title or (paper.title if paper else ""),
        source_url=payload.source_url or (paper.source_url if paper else None),
        max_pages=payload.max_pages,
    )
    run.paper_chunks.extend(chunks)
    run.evidence.extend(
        evidence_from_pdf_chunks(
            chunks,
            domain=run.domain,
            start_index=len(run.evidence) + 1,
            verified=paper.verification_status == "verified" if paper else False,
            verification_method=paper.verification_method if paper else None,
            verification_confidence=paper.verification_confidence if paper else None,
            matched_source=paper.matched_source if paper else None,
        )
    )
    return run_store.save(run)


@router.get("/{run_id}/data-profiles", response_model=list[DatasetProfile])
async def get_run_data_profiles(run_id: str) -> list[DatasetProfile]:
    return _must_get_run(run_id).data_profiles


@router.get("/{run_id}/baseline-result", response_model=BaselineResultCard | None)
async def get_run_baseline_result(run_id: str) -> BaselineResultCard | None:
    return _must_get_run(run_id).baseline_result_card


@router.get("/{run_id}/hypotheses", response_model=list[Hypothesis])
async def get_hypotheses(run_id: str) -> list[Hypothesis]:
    return _must_get_run(run_id).hypotheses


@router.get("/{run_id}/llm-calls")
async def get_llm_calls(run_id: str):
    _must_get_run(run_id)
    return read_llm_logs(get_settings().data_dir, run_id)


@router.get("/{run_id}/report", response_model=ResearchReport)
async def get_report(run_id: str) -> ResearchReport:
    run = _must_get_run(run_id)
    if run.report is None:
        raise HTTPException(status_code=404, detail="report not generated")
    return run.report


@router.get("/{run_id}/artifacts")
async def list_artifacts(run_id: str) -> dict:
    _must_get_run(run_id)
    settings = get_settings()
    artifact_roots = {
        "reports": settings.data_dir / "outputs" / "reports",
        "llm_calls": settings.data_dir / "outputs" / "llm_calls",
        "result_cards": settings.data_dir / "outputs" / "result_cards",
        "browser_traces": settings.data_dir / "browser_traces",
    }
    artifacts = {}
    for name, root in artifact_roots.items():
        if not root.exists():
            artifacts[name] = []
            continue
        artifacts[name] = [
            str(path)
            for path in sorted(root.glob(f"*{run_id}*") if name != "result_cards" else root.glob("*"))
            if path.is_file()
        ]
    return {"run_id": run_id, "artifacts": artifacts}


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
    if format != "md":
        raise HTTPException(status_code=400, detail="format must be md or json")
    path = get_settings().data_dir / "outputs" / "reports" / f"{run_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="markdown report not found")
    return FileResponse(path, media_type="text/markdown", filename=f"{run_id}.md")


def _must_get_run(run_id: str) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


def _safe_pdf_path(raw_path: str, data_dir: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    data_root = data_dir if data_dir.is_absolute() else Path.cwd() / data_dir
    data_root = data_root.resolve()
    if not path.is_relative_to(data_root):
        raise HTTPException(status_code=400, detail="pdf path must be under DATA_DIR")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="pdf not found")
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="path must point to a pdf file")
    return path
