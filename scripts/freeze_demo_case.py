#!/usr/bin/env python3
"""Freeze a completed TrustSci-Agent run into a submission-ready folder."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.report_writer_agent import ReportWriterAgent  # noqa: E402
from app.evidence.selection import reportable_evidence  # noqa: E402
from app.storage.workspace import RunWorkspace  # noqa: E402
from app.tools.claim_verifier import ClaimVerifier  # noqa: E402
from app.schemas.run import ResearchRun  # noqa: E402
from app.tools.report_pdf_exporter import export_markdown_pdf  # noqa: E402
from app.workflows.scientist_workflow import _write_markdown_report  # noqa: E402


def freeze_demo_case(run_id: str, data_dir: Path, output_root: Path, *, strict: bool = False) -> dict[str, Any]:
    data_dir = data_dir.resolve()
    output_dir = (output_root / run_id).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    run = _load_run_snapshot(data_dir, run_id)
    artifacts = _collect_artifacts(run, data_dir, output_dir)
    manifest = _build_manifest(run, data_dir, output_dir, artifacts)
    _write_json(output_dir / "manifest.json", manifest)
    _write_readme(output_dir / "README.md", run, manifest)
    if strict and manifest["warnings"]:
        raise RuntimeError("demo freeze strict checks failed: " + "; ".join(manifest["warnings"]))
    return manifest


def list_demo_candidates(data_dir: Path) -> list[dict[str, Any]]:
    data_dir = data_dir.resolve()
    candidates = []
    for snapshot_path in sorted((data_dir / "workspace").glob("*/run.json")):
        try:
            run = ResearchRun.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        output_dir = data_dir / "submission" / run.run_id
        manifest = _build_manifest(run, data_dir, output_dir, _existing_artifacts(run, data_dir))
        candidates.append(
            {
                "run_id": run.run_id,
                "status": manifest["status"],
                "question": run.question,
                "updated_at": run.updated_at.isoformat() if hasattr(run.updated_at, "isoformat") else str(run.updated_at),
                "papers": manifest["counts"]["papers"],
                "verified_papers": manifest["counts"]["verified_papers"],
                "evidence": manifest["counts"]["evidence"],
                "report_generated": manifest["checks"]["report_generated"],
                "citation_frozen": manifest["checks"]["citation_frozen"],
                "evidence_frozen": manifest["checks"]["evidence_frozen"],
                "qwen_log_present": manifest["checks"]["qwen_log_present"],
                "ready": not manifest["warnings"],
                "warnings": manifest["warnings"],
            }
        )
    return sorted(candidates, key=lambda item: str(item.get("updated_at") or ""), reverse=True)


def accept_current_verified(run_id: str, data_dir: Path) -> ResearchRun:
    data_dir = data_dir.resolve()
    run = _load_run_snapshot(data_dir, run_id)
    run.citation_frozen = True
    run.frozen_paper_ids = [
        paper.paper_id
        for paper in run.papers
        if paper.verification_status == "verified" and paper.report_eligible and paper.human_decision != "rejected"
    ]
    frozen_paper_ids = set(run.frozen_paper_ids)
    run.evidence_frozen = True
    run.frozen_evidence_ids = [
        item.evidence_id
        for item in run.evidence
        if item.verified
        and item.eligible_for_report
        and item.human_decision != "rejected"
        and (not item.paper_id or item.paper_id in frozen_paper_ids)
    ]
    _sync_frozen_markers(run)
    if run.experiment_plan is not None:
        selected = _selected_hypothesis(run)
        run.report = ReportWriterAgent().run(
            run,
            selected,
            run.experiment_plan,
            run.evidence,
            run.papers,
            run.knowledge_cards,
            run.data_profiles,
            run.baseline_result_card,
        )
        run.claim_audit = ClaimVerifier().audit(run, run.report, reportable_evidence(run), selected)
        _write_markdown_report(run, data_dir)
    workspace = RunWorkspace(data_dir)
    run.workspace_path = str(workspace.ensure(run))
    run.workspace_artifacts = workspace.write_snapshot(run)
    return run


def _load_run_snapshot(data_dir: Path, run_id: str) -> ResearchRun:
    snapshot_path = data_dir / "workspace" / run_id / "run.json"
    if not snapshot_path.exists():
        raise FileNotFoundError(f"workspace snapshot not found: {snapshot_path}")
    run = ResearchRun.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
    if run.run_id != run_id:
        raise ValueError(f"snapshot run_id mismatch: expected {run_id}, found {run.run_id}")
    return run


def _collect_artifacts(run: ResearchRun, data_dir: Path, output_dir: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if run.report is not None:
        _write_markdown_report(run, data_dir)
        report_json = reports_dir / f"{run.run_id}.json"
        _write_json(report_json, run.report.model_dump(mode="json"))
        artifacts["report_json"] = _relative(report_json, output_dir)

        source_md = data_dir / "outputs" / "reports" / f"{run.run_id}.md"
        if source_md.exists():
            target_md = reports_dir / source_md.name
            shutil.copy2(source_md, target_md)
            artifacts["report_markdown"] = _relative(target_md, output_dir)

            target_pdf = reports_dir / f"{run.run_id}.pdf"
            export_markdown_pdf(source_md.read_text(encoding="utf-8"), target_pdf)
            artifacts["report_pdf"] = _relative(target_pdf, output_dir)

    workspace_dir = data_dir / "workspace" / run.run_id
    if workspace_dir.exists():
        workspace_zip = output_dir / f"{run.run_id}-workspace.zip"
        _zip_directory(workspace_dir, workspace_zip, root_name=run.run_id)
        artifacts["workspace_bundle"] = _relative(workspace_zip, output_dir)

    llm_log = data_dir / "outputs" / "llm_calls" / f"{run.run_id}.jsonl"
    if llm_log.exists():
        target_log = output_dir / "logs" / llm_log.name
        target_log.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(llm_log, target_log)
        artifacts["qwen_llm_log"] = _relative(target_log, output_dir)

    return artifacts


def _existing_artifacts(run: ResearchRun, data_dir: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    if (data_dir / "outputs" / "reports" / f"{run.run_id}.md").exists():
        artifacts["report_markdown"] = f"outputs/reports/{run.run_id}.md"
    if (data_dir / "outputs" / "reports" / f"{run.run_id}.pdf").exists():
        artifacts["report_pdf"] = f"outputs/reports/{run.run_id}.pdf"
    if (data_dir / "workspace" / run.run_id).exists():
        artifacts["workspace_bundle"] = f"workspace/{run.run_id}"
    if (data_dir / "outputs" / "llm_calls" / f"{run.run_id}.jsonl").exists():
        artifacts["qwen_llm_log"] = f"outputs/llm_calls/{run.run_id}.jsonl"
    return artifacts


def _build_manifest(
    run: ResearchRun,
    data_dir: Path,
    output_dir: Path,
    artifacts: dict[str, str],
) -> dict[str, Any]:
    verified_papers = [paper for paper in run.papers if paper.verification_status == "verified"]
    report_refs = run.report.references if run.report else []
    frozen_reference_ids = set(run.frozen_paper_ids)
    reference_ids = {paper.paper_id for paper in report_refs}
    citation_integrity = run.citation_report.integrity_score if run.citation_report else None
    claim_support = run.claim_audit.support_score if run.claim_audit else None
    selected = next((item for item in run.hypotheses if item.selected), None)

    checks = {
        "report_generated": run.report is not None,
        "citation_report_present": run.citation_report is not None,
        "claim_audit_present": run.claim_audit is not None,
        "no_unsupported_claims": run.claim_audit is not None and run.claim_audit.unsupported == 0,
        "evidence_frozen": run.evidence_frozen,
        "citation_frozen": run.citation_frozen,
        "references_within_frozen_papers": not frozen_reference_ids or reference_ids.issubset(frozen_reference_ids),
        "workspace_bundle_present": "workspace_bundle" in artifacts,
        "qwen_log_present": "qwen_llm_log" in artifacts,
    }
    return {
        "schema": "trustsci.demo_freeze.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run.run_id,
        "domain": run.domain,
        "question": run.question,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "current_stage": run.current_stage,
        "progress": run.progress,
        "data_dir": str(data_dir),
        "output_dir": str(output_dir),
        "counts": {
            "papers": len(run.papers),
            "verified_papers": len(verified_papers),
            "report_references": len(report_refs),
            "evidence": len(run.evidence),
            "frozen_evidence": len(run.frozen_evidence_ids),
            "knowledge_cards": len(run.knowledge_cards),
            "hypotheses": len(run.hypotheses),
        },
        "selected_hypothesis": selected.hypothesis_id if selected else None,
        "citation_integrity_score": citation_integrity,
        "claim_support_score": claim_support,
        "checks": checks,
        "artifacts": artifacts,
        "warnings": _warnings(checks),
    }


def _warnings(checks: dict[str, bool]) -> list[str]:
    labels = {
        "report_generated": "Final report has not been generated.",
        "citation_report_present": "Citation verification report is missing.",
        "claim_audit_present": "Claim audit report is missing.",
        "no_unsupported_claims": "Claim audit still contains unsupported claims.",
        "evidence_frozen": "Evidence set is not frozen.",
        "citation_frozen": "Citation set is not frozen.",
        "references_within_frozen_papers": "Report references exceed the frozen citation set.",
        "workspace_bundle_present": "Workspace bundle is missing.",
        "qwen_log_present": "Qwen/Bailian LLM log is missing.",
    }
    return [message for key, message in labels.items() if not checks.get(key, False)]


def _sync_frozen_markers(run: ResearchRun) -> None:
    frozen_evidence_ids = set(run.frozen_evidence_ids)
    frozen_paper_ids = set(run.frozen_paper_ids)
    for item in run.evidence:
        item.frozen = item.evidence_id in frozen_evidence_ids
    for paper in run.papers:
        paper.frozen = paper.paper_id in frozen_paper_ids


def _selected_hypothesis(run: ResearchRun):
    return next((hypothesis for hypothesis in run.hypotheses if hypothesis.selected), run.hypotheses[0] if run.hypotheses else None)


def _write_readme(path: Path, run: ResearchRun, manifest: dict[str, Any]) -> None:
    artifacts = "\n".join(f"- `{name}`: `{rel_path}`" for name, rel_path in manifest["artifacts"].items())
    warnings = "\n".join(f"- {item}" for item in manifest["warnings"]) or "- None"
    path.write_text(
        f"# TrustSci-Agent Demo Freeze: {run.run_id}\n\n"
        f"Question: {run.question}\n\n"
        "## Artifacts\n\n"
        f"{artifacts or '- No artifacts copied.'}\n\n"
        "## Freeze Checks\n\n"
        f"- Evidence frozen: {manifest['checks']['evidence_frozen']}\n"
        f"- Citation frozen: {manifest['checks']['citation_frozen']}\n"
        f"- References within frozen papers: {manifest['checks']['references_within_frozen_papers']}\n"
        f"- No unsupported claims: {manifest['checks']['no_unsupported_claims']}\n"
        f"- Citation integrity score: {manifest['citation_integrity_score']}\n"
        f"- Claim support score: {manifest['claim_support_score']}\n\n"
        "## Warnings\n\n"
        f"{warnings}\n\n"
        "Use this folder as the fixed demo evidence package for screenshots, video recording, and submission review.\n",
        encoding="utf-8",
    )


def _zip_directory(source_dir: Path, zip_path: Path, *, root_name: str) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(root_name) / path.relative_to(source_dir))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze a TrustSci-Agent run for demo submission.")
    parser.add_argument("run_id", nargs="?", help="Run id, for example run_123abc.")
    parser.add_argument("--data-dir", default="data", type=Path, help="TrustSci-Agent DATA_DIR.")
    parser.add_argument("--output-root", default=Path("data/submission"), type=Path, help="Freeze output root.")
    parser.add_argument("--strict", action="store_true", help="Fail if the run is not final-submission ready.")
    parser.add_argument(
        "--accept-current-verified",
        action="store_true",
        help="Freeze the current verified, non-rejected citations/evidence before packaging.",
    )
    parser.add_argument("--list-candidates", action="store_true", help="List workspace snapshots and readiness checks.")
    args = parser.parse_args()

    if args.list_candidates:
        print(json.dumps(list_demo_candidates(args.data_dir), ensure_ascii=False, indent=2))
        return 0
    if not args.run_id:
        parser.error("run_id is required unless --list-candidates is used")
    if args.accept_current_verified:
        accept_current_verified(args.run_id, args.data_dir)
    manifest = freeze_demo_case(args.run_id, args.data_dir, args.output_root, strict=args.strict)
    print(json.dumps({"run_id": args.run_id, "output_dir": manifest["output_dir"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
