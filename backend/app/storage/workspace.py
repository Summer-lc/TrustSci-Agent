import json
from pathlib import Path
from typing import Any

from app.schemas.run import ResearchRun


class RunWorkspace:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "workspace"

    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def ensure(self, run: ResearchRun) -> Path:
        run_dir = self.run_dir(run.run_id)
        for name in ("papers", "evidence", "hypotheses", "experiments", "reports", "to_human"):
            (run_dir / name).mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_snapshot(self, run: ResearchRun) -> dict[str, str]:
        run_dir = self.ensure(run)
        paths = {
            "research_state": run_dir / "research-state.json",
            "research_log": run_dir / "research-log.md",
            "run_snapshot": run_dir / "run.json",
            "papers": run_dir / "papers" / "papers.json",
            "evidence": run_dir / "evidence" / "evidence.json",
            "knowledge_cards": run_dir / "evidence" / "knowledge-cards.json",
            "hypotheses": run_dir / "hypotheses" / "hypotheses.json",
            "experiment_plan": run_dir / "experiments" / "experiment-plan.json",
            "report": run_dir / "reports" / "report.json",
            "to_human": run_dir / "to_human" / "next-actions.md",
        }
        _write_json(paths["research_state"], _research_state(run))
        _write_text(paths["research_log"], _research_log(run))
        _write_json(paths["run_snapshot"], run.model_dump(mode="json"))
        _write_json(paths["papers"], [item.model_dump(mode="json") for item in run.papers])
        _write_json(paths["evidence"], [item.model_dump(mode="json") for item in run.evidence])
        _write_json(paths["knowledge_cards"], [item.model_dump(mode="json") for item in run.knowledge_cards])
        _write_json(paths["hypotheses"], [item.model_dump(mode="json") for item in run.hypotheses])
        _write_json(
            paths["experiment_plan"],
            run.experiment_plan.model_dump(mode="json") if run.experiment_plan else {},
        )
        _write_json(paths["report"], run.report.model_dump(mode="json") if run.report else {})
        _write_text(paths["to_human"], _to_human(run))
        return {name: str(path) for name, path in paths.items() if path.exists()}

    def list_artifacts(self, run_id: str) -> list[str]:
        run_dir = self.run_dir(run_id)
        if not run_dir.exists():
            return []
        return [str(path) for path in sorted(run_dir.rglob("*")) if path.is_file()]


def _research_state(run: ResearchRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "domain": run.domain,
        "question": run.question,
        "status": run.status,
        "current_stage": run.current_stage,
        "progress": run.progress,
        "constraints": run.constraints.model_dump(mode="json"),
        "counts": {
            "perspectives": len(run.perspectives),
            "papers": len(run.papers),
            "verified_papers": len([item for item in run.papers if item.report_eligible]),
            "evidence": len(run.evidence),
            "report_ready_evidence": len([item for item in run.evidence if item.eligible_for_report]),
            "frozen_evidence": len(run.frozen_evidence_ids),
            "knowledge_cards": len(run.knowledge_cards),
            "hypotheses": len(run.hypotheses),
        },
        "human_gate": {
            "evidence_frozen": run.evidence_frozen,
            "frozen_evidence_ids": run.frozen_evidence_ids,
            "frozen_paper_ids": run.frozen_paper_ids,
        },
        "citation_integrity_score": run.citation_report.integrity_score if run.citation_report else None,
        "claim_support_score": run.claim_audit.support_score if run.claim_audit else None,
        "updated_at": run.updated_at.isoformat() if hasattr(run.updated_at, "isoformat") else str(run.updated_at),
    }


def _research_log(run: ResearchRun) -> str:
    lines = [
        f"# Research Log: {run.run_id}",
        "",
        f"- Domain: {run.domain}",
        f"- Question: {run.question}",
        f"- Status: {run.status} / {run.current_stage}",
        "",
        "## Timeline",
    ]
    for step in run.steps:
        started = step.started_at.isoformat() if step.started_at else "n/a"
        finished = step.finished_at.isoformat() if step.finished_at else "n/a"
        lines.append(f"- {step.name}: {step.status} ({started} -> {finished}) {step.summary}")
    lines.extend(
        [
            "",
            "## Evidence Summary",
            f"- Papers: {len(run.papers)}",
            f"- Evidence items: {len(run.evidence)}",
            f"- Evidence frozen: {run.evidence_frozen} ({len(run.frozen_evidence_ids)} items)",
            f"- Knowledge cards: {len(run.knowledge_cards)}",
            f"- Hypotheses: {len(run.hypotheses)}",
        ]
    )
    if run.citation_report:
        lines.append(f"- Citation integrity: {run.citation_report.integrity_score}")
    if run.claim_audit:
        lines.append(f"- Claim support: {run.claim_audit.support_score}")
    return "\n".join(lines) + "\n"


def _to_human(run: ResearchRun) -> str:
    actions = [
        "# Human Checkpoints",
        "",
        "- Review suspicious or audit-only citations before final submission.",
        "- Accept or reject evidence, then freeze the evidence set before final report export.",
        "- Confirm the selected hypothesis is scientifically reasonable.",
        "- Inspect unsupported claims and downgrade them before demo freeze.",
        "- Verify baseline result cards are presented as actual results, not broad scientific conclusions.",
    ]
    if run.claim_audit and run.claim_audit.unsupported:
        actions.append(f"- Claim audit found {run.claim_audit.unsupported} unsupported claims.")
    if run.citation_report and run.citation_report.suspicious:
        actions.append(f"- Citation verifier found {run.citation_report.suspicious} suspicious papers.")
    if not run.evidence_frozen and run.evidence:
        actions.append("- Evidence set is not frozen yet.")
    if run.evidence_frozen:
        actions.append(f"- Frozen evidence set contains {len(run.frozen_evidence_ids)} items.")
    return "\n".join(actions) + "\n"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
