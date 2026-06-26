import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.agents.experiment_designer_agent import ExperimentDesignerAgent
from app.agents.report_writer_agent import ReportWriterAgent
from app.config import get_settings
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.evidence.ledger import evidence_from_pdf_chunks
from app.evidence.selection import reportable_evidence
from app.schemas.claim import ClaimAuditReport
from app.schemas.common import RunStatus
from app.schemas.evidence import EvidenceDecisionRequest, EvidenceItem, PaperChunk, PdfEvidenceIngestRequest
from app.schemas.hypothesis import Hypothesis
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper, PaperDecisionRequest
from app.schemas.planner import PerspectiveQuestion
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun, ResearchRunCreate
from app.storage.in_memory import run_store
from app.storage.workspace import RunWorkspace
from app.tools.claim_verifier import ClaimVerifier
from app.tools.llm_logger import read_llm_logs
from app.tools.pdf_parser import parse_pdf_chunks
from app.tools.report_pdf_exporter import export_markdown_pdf
from app.workflows.scientist_workflow import ScientistWorkflow, _write_markdown_report

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=ResearchRun)
async def create_run(payload: ResearchRunCreate) -> ResearchRun:
    run = ResearchRun(domain=payload.domain, question=payload.question, constraints=payload.constraints)
    _write_workspace(run)
    return run_store.create(run)


@router.get("", response_model=list[ResearchRun])
async def list_runs() -> list[ResearchRun]:
    return run_store.list()


@router.get("/workspaces")
async def list_restorable_workspaces() -> list[dict]:
    return RunWorkspace(get_settings().data_dir).list_snapshots()


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


@router.post("/{run_id}/continue", response_model=ResearchRun)
async def continue_run(run_id: str) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.current_stage == "awaiting_citation_review" and not run.citation_frozen:
        raise HTTPException(status_code=400, detail="freeze citations before continuing")
    if run.current_stage == "awaiting_evidence_review" and not run.evidence_frozen:
        raise HTTPException(status_code=400, detail="freeze evidence before continuing")
    return await ScientistWorkflow(get_settings()).continue_run(run)


@router.get("/{run_id}/papers", response_model=list[Paper])
async def get_papers(run_id: str) -> list[Paper]:
    return _must_get_run(run_id).papers


@router.post("/{run_id}/papers/{paper_id}/decision", response_model=ResearchRun)
async def decide_paper(run_id: str, paper_id: str, payload: PaperDecisionRequest) -> ResearchRun:
    run = _must_get_run(run_id)
    paper = next((entry for entry in run.papers if entry.paper_id == paper_id), None)
    if paper is None:
        raise HTTPException(status_code=404, detail="paper not found")
    paper.human_decision = payload.decision
    paper.human_note = payload.note
    paper.report_eligible = paper.verification_status == "verified" and payload.decision != "rejected"
    _sync_evidence_for_paper(run, paper)
    if run.citation_frozen and payload.decision == "rejected":
        run.frozen_paper_ids = [item_id for item_id in run.frozen_paper_ids if item_id != paper_id]
    _sync_frozen_markers(run)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.post("/{run_id}/papers/freeze", response_model=ResearchRun)
async def freeze_papers(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    run.citation_frozen = True
    run.frozen_paper_ids = [
        paper.paper_id
        for paper in run.papers
        if paper.verification_status == "verified"
        and paper.report_eligible
        and paper.human_decision != "rejected"
    ]
    _sync_frozen_markers(run)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.post("/{run_id}/papers/unfreeze", response_model=ResearchRun)
async def unfreeze_papers(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    run.citation_frozen = False
    if not run.evidence_frozen:
        run.frozen_paper_ids = []
    else:
        run.frozen_paper_ids = _paper_ids_for_frozen_evidence(run)
    _sync_frozen_markers(run)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.get("/{run_id}/evidence", response_model=list[EvidenceItem])
async def get_evidence(run_id: str) -> list[EvidenceItem]:
    return _must_get_run(run_id).evidence


@router.post("/{run_id}/evidence/{evidence_id}/decision", response_model=ResearchRun)
async def decide_evidence(run_id: str, evidence_id: str, payload: EvidenceDecisionRequest) -> ResearchRun:
    run = _must_get_run(run_id)
    item = next((entry for entry in run.evidence if entry.evidence_id == evidence_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    item.human_decision = payload.decision
    item.human_note = payload.note
    item.eligible_for_report = item.verified and payload.decision != "rejected"
    if run.evidence_frozen and payload.decision == "rejected":
        run.frozen_evidence_ids = [item_id for item_id in run.frozen_evidence_ids if item_id != evidence_id]
        run.frozen_paper_ids = _paper_ids_for_frozen_evidence(run)
    _sync_frozen_markers(run)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.post("/{run_id}/evidence/freeze", response_model=ResearchRun)
async def freeze_evidence(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    frozen_ids = [
        item.evidence_id
        for item in run.evidence
        if item.verified and item.eligible_for_report and item.human_decision != "rejected"
    ]
    run.evidence_frozen = True
    run.frozen_evidence_ids = frozen_ids
    run.frozen_paper_ids = _paper_ids_for_frozen_evidence(run)
    _sync_frozen_markers(run)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.post("/{run_id}/evidence/unfreeze", response_model=ResearchRun)
async def unfreeze_evidence(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    run.evidence_frozen = False
    run.frozen_evidence_ids = []
    run.frozen_paper_ids = []
    _sync_frozen_markers(run)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.get("/{run_id}/perspectives", response_model=list[PerspectiveQuestion])
async def get_perspectives(run_id: str) -> list[PerspectiveQuestion]:
    return _must_get_run(run_id).perspectives


@router.get("/{run_id}/knowledge-cards", response_model=list[KnowledgeCard])
async def get_knowledge_cards(run_id: str) -> list[KnowledgeCard]:
    return _must_get_run(run_id).knowledge_cards


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
    _write_workspace(run)
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
        "workspace_bundles": settings.data_dir / "outputs" / "workspace_bundles",
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
    artifacts["workspace"] = RunWorkspace(settings.data_dir).list_artifacts(run_id)
    return {"run_id": run_id, "artifacts": artifacts}


@router.get("/{run_id}/workspace/export")
async def export_workspace(run_id: str):
    run = _must_get_run(run_id)
    zip_path = _build_workspace_bundle(run)
    return FileResponse(zip_path, media_type="application/zip", filename=f"{run_id}-workspace.zip")


@router.post("/{run_id}/workspace/restore", response_model=ResearchRun)
async def restore_workspace(run_id: str) -> ResearchRun:
    workspace = RunWorkspace(get_settings().data_dir)
    try:
        run = workspace.load_snapshot(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="workspace snapshot not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run_store.save(run)


@router.post("/{run_id}/hypotheses/{hypothesis_id}/select", response_model=ResearchRun)
async def select_hypothesis(run_id: str, hypothesis_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    selected: Hypothesis | None = None
    for hypothesis in run.hypotheses:
        hypothesis.selected = hypothesis.hypothesis_id == hypothesis_id
        if hypothesis.selected:
            hypothesis.selection_rationale = _selection_rationale(hypothesis)
            selected = hypothesis
        else:
            hypothesis.selection_rationale = ""
    if selected is None:
        raise HTTPException(status_code=404, detail="hypothesis not found")
    run.experiment_plan = ExperimentDesignerAgent().run(selected, run.data_profiles)
    _refresh_report_if_possible(run)
    _write_workspace(run)
    return run_store.save(run)


@router.post("/{run_id}/report", response_model=ResearchRun)
async def regenerate_report(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    return await ScientistWorkflow(get_settings()).run(run)


@router.post("/{run_id}/report/rebuild", response_model=ResearchRun)
async def rebuild_report(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    _refresh_report_if_possible(run, require_experiment=True)
    _write_workspace(run)
    return run_store.save(run)


@router.get("/{run_id}/report/export")
async def export_report(run_id: str, format: str = "md"):
    run = _must_get_run(run_id)
    if format == "json":
        if run.report is None:
            raise HTTPException(status_code=404, detail="report not generated")
        return run.report
    if format not in {"md", "pdf"}:
        raise HTTPException(status_code=400, detail="format must be md, json, or pdf")
    settings = get_settings()
    md_path = settings.data_dir / "outputs" / "reports" / f"{run_id}.md"
    if not md_path.exists() and run.report is not None:
        _write_markdown_report(run, settings.data_dir)
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="markdown report not found")
    if format == "pdf":
        pdf_path = settings.data_dir / "outputs" / "reports" / f"{run_id}.pdf"
        export_markdown_pdf(md_path.read_text(encoding="utf-8"), pdf_path)
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"{run_id}.pdf")
    return FileResponse(md_path, media_type="text/markdown", filename=f"{run_id}.md")


def _must_get_run(run_id: str) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


def _write_workspace(run: ResearchRun) -> None:
    workspace = RunWorkspace(get_settings().data_dir)
    run.workspace_path = str(workspace.ensure(run))
    run.workspace_artifacts = workspace.write_snapshot(run)


def _build_workspace_bundle(run: ResearchRun) -> Path:
    settings = get_settings()
    workspace = RunWorkspace(settings.data_dir)
    _write_workspace(run)
    source_dir = workspace.run_dir(run.run_id)
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="workspace not found")

    bundle_dir = settings.data_dir / "outputs" / "workspace_bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    zip_path = bundle_dir / f"{run.run_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(run.run_id) / path.relative_to(source_dir))
    return zip_path


def _refresh_report_if_possible(run: ResearchRun, *, require_experiment: bool = False) -> None:
    if run.experiment_plan is None:
        if require_experiment:
            raise HTTPException(status_code=400, detail="experiment plan is required before rebuilding report")
        return
    run.report = ReportWriterAgent().run(
        run,
        _selected_hypothesis(run),
        run.experiment_plan,
        run.evidence,
        run.papers,
        run.knowledge_cards,
        run.data_profiles,
        run.baseline_result_card,
    )
    run.claim_audit = ClaimVerifier().audit(run, run.report, reportable_evidence(run), _selected_hypothesis(run))
    _write_markdown_report(run, get_settings().data_dir)


def _selected_hypothesis(run: ResearchRun) -> Hypothesis | None:
    return next((hypothesis for hypothesis in run.hypotheses if hypothesis.selected), run.hypotheses[0] if run.hypotheses else None)


def _selection_rationale(hypothesis: Hypothesis) -> str:
    if hypothesis.critic is None:
        return "Selected by the user for downstream experiment design and report rebuild."
    return (
        "Selected by the user after reviewer debate; current scores are "
        f"novelty={hypothesis.critic.novelty}, "
        f"verifiability={hypothesis.critic.verifiability}, "
        f"evidence_support={hypothesis.critic.evidence_support}, "
        f"reproducibility={hypothesis.critic.reproducibility}, "
        f"competition_fit={hypothesis.critic.competition_fit}."
    )


def _sync_frozen_markers(run: ResearchRun) -> None:
    frozen_ids = set(run.frozen_evidence_ids) if run.evidence_frozen else set()
    for item in run.evidence:
        item.frozen = item.evidence_id in frozen_ids
    frozen_paper_ids = set(run.frozen_paper_ids) if (run.evidence_frozen or run.citation_frozen) else set()
    for paper in run.papers:
        paper.frozen = paper.paper_id in frozen_paper_ids


def _sync_evidence_for_paper(run: ResearchRun, paper: Paper) -> None:
    for item in run.evidence:
        if item.paper_id != paper.paper_id:
            continue
        if paper.human_decision == "rejected":
            item.eligible_for_report = False
            continue
        item.eligible_for_report = item.verified and item.human_decision != "rejected"


def _paper_ids_for_frozen_evidence(run: ResearchRun) -> list[str]:
    frozen_ids = set(run.frozen_evidence_ids)
    evidence_paper_ids = {
        item.paper_id
        for item in run.evidence
        if item.evidence_id in frozen_ids and item.paper_id
    }
    ordered = [paper.paper_id for paper in run.papers if paper.paper_id in evidence_paper_ids]
    extras = sorted(evidence_paper_ids - set(ordered))
    return ordered + extras


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
