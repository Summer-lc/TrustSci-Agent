import json

from app.agents.report_writer_agent import _enforce_report_layers, _report_payload
from app.evidence.audit import build_citation_audit
from app.evidence.selection import reportable_evidence, reportable_knowledge_cards, reportable_papers
from app.llm.interface import LLMClient, LLMRequest
from app.schemas.claim import ClaimAuditReport
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun


SYSTEM_PROMPT = """You are the Report Reviser Agent for TrustSci-Agent.
Revise a competition-format research report after claim verification.
Return JSON only. Do not invent references, citations, datasets, evidence ids, metrics, or completed experimental results.
Write and preserve bilingual report content. For every narrative field and list item, write clear English first, then add a faithful Chinese translation prefixed with "中文翻译：".

Required JSON shape:
{
  "report": {
    "problem_statement": "Evidence-backed / Inference / To validate layered paragraph",
    "rationale": "Evidence-backed / Inference / To validate layered paragraph",
    "technical_details": ["labeled technical detail"],
    "datasets": ["existing datasets only"],
    "source": "existing source basis",
    "target": "existing target data/features",
    "paper_title": "academic title",
    "paper_abstract": "Evidence-backed / Inference / To validate layered abstract",
    "methods": ["labeled implementation step"],
    "experiments": {
      "datasets": [],
      "source": "",
      "target": "",
      "baselines": [],
      "metrics": [],
      "experiment_steps": [],
      "expected_results": "",
      "failure_modes": []
    },
    "results": "bounded feasibility or verification-pending result statement"
  }
}

Revision rules:
- Keep directly supported claims as Evidence-backed and cite evidence ids when available.
- Rewrite weakly_supported claims as Inference, with cautious language.
- Rewrite unsupported factual claims as To validate, proposed experiment, or verification-pending statement.
- Preserve the selected hypothesis as a hypothesis, not a completed discovery.
- Preserve existing Chinese translations and add missing Chinese translations when revising English report text.
- References are not accepted from the model. The backend will attach verified references only.
"""


class ReportReviserAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        run: ResearchRun,
        report: ResearchReport,
        audit: ClaimAuditReport,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        knowledge_cards: list[KnowledgeCard],
        hypothesis: Hypothesis | None,
    ) -> ResearchReport:
        fallback = self.run(run, report, audit, evidence, papers, knowledge_cards)
        if self.llm is None:
            return fallback
        response = await self.llm.complete(
            LLMRequest(
                system=SYSTEM_PROMPT,
                user=_build_revision_prompt(run, report, audit, evidence, hypothesis),
                fallback={"report": _report_payload(fallback)},
                run_id=run.run_id,
                agent="report_reviser",
            )
        )
        return _normalize_revised_report(response.content, fallback, run, evidence, papers, knowledge_cards)

    def run(
        self,
        run: ResearchRun,
        report: ResearchReport,
        audit: ClaimAuditReport,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        knowledge_cards: list[KnowledgeCard],
    ) -> ResearchReport:
        revised = _enforce_report_layers(report)
        unsupported = [item for item in audit.items if item.status == "unsupported"]
        weak = [item for item in audit.items if item.status == "weakly_supported"]
        if unsupported or weak:
            revised.rationale = _append_audit_caveat(
                revised.rationale,
                unsupported=unsupported,
                weak=weak,
            )
            revised.results = _append_audit_caveat(
                revised.results,
                unsupported=unsupported,
                weak=weak,
            )
        revised.references = reportable_papers(run, papers, evidence)
        revised.knowledge_cards = reportable_knowledge_cards(run, knowledge_cards)
        revised.citation_audit_log = build_citation_audit(papers)
        return _enforce_report_layers(revised)


def _build_revision_prompt(
    run: ResearchRun,
    report: ResearchReport,
    audit: ClaimAuditReport,
    evidence: list[EvidenceItem],
    hypothesis: Hypothesis | None,
) -> str:
    eligible_evidence = reportable_evidence(run, evidence)
    payload = {
        "run": {
            "run_id": run.run_id,
            "domain": run.domain,
            "question": run.question,
        },
        "current_report": _report_payload(report),
        "claim_audit": audit.model_dump(mode="json"),
        "selected_hypothesis": hypothesis.model_dump(mode="json") if hypothesis else None,
        "eligible_evidence": [
            {
                "evidence_id": item.evidence_id,
                "paper_id": item.paper_id,
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "source_title": item.source_title,
                "tags": item.tags,
            }
            for item in eligible_evidence[:32]
        ],
        "instructions": [
            "Do not remove required report fields.",
            "Do not add references; backend attaches verified references only.",
            "Downgrade unsupported factual wording into To validate statements.",
            "Keep methods, expected results, and proposed experiments verification pending unless backed by a result card.",
            "Use Evidence-backed:, Inference:, and To validate: labels in major paragraphs and bullets.",
            "Keep every revised field bilingual: English first, then 中文翻译： with a faithful Chinese translation.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_revised_report(
    content: object,
    fallback: ResearchReport,
    run: ResearchRun,
    evidence: list[EvidenceItem],
    papers: list[Paper],
    knowledge_cards: list[KnowledgeCard],
) -> ResearchReport:
    if not isinstance(content, dict) or not isinstance(content.get("report"), dict):
        return fallback
    raw = content["report"]
    try:
        experiment = _normalize_experiment(raw.get("experiments"), fallback.experiments)
        report = ResearchReport(
            problem_statement=_clean(raw.get("problem_statement")) or fallback.problem_statement,
            rationale=_clean(raw.get("rationale")) or fallback.rationale,
            technical_details=_string_list(raw.get("technical_details")) or fallback.technical_details,
            datasets=fallback.datasets,
            source=_clean(raw.get("source")) or fallback.source,
            target=_clean(raw.get("target")) or fallback.target,
            paper_title=_clean(raw.get("paper_title")) or fallback.paper_title,
            paper_abstract=_clean(raw.get("paper_abstract")) or fallback.paper_abstract,
            methods=_string_list(raw.get("methods")) or fallback.methods,
            experiments=experiment,
            results=_clean(raw.get("results")) or fallback.results,
            data_profiles=fallback.data_profiles,
            baseline_result_card=fallback.baseline_result_card,
            knowledge_cards=reportable_knowledge_cards(run, knowledge_cards),
            references=reportable_papers(run, papers, evidence),
            citation_audit_log=build_citation_audit(papers),
        )
        return _enforce_report_layers(report)
    except Exception:
        return fallback


def _normalize_experiment(value: object, fallback: ExperimentPlan) -> ExperimentPlan:
    if not isinstance(value, dict):
        return fallback
    return ExperimentPlan(
        datasets=_string_list(value.get("datasets")) or fallback.datasets,
        source=_clean(value.get("source")) or fallback.source,
        target=_clean(value.get("target")) or fallback.target,
        baselines=_string_list(value.get("baselines")) or fallback.baselines,
        metrics=_string_list(value.get("metrics")) or fallback.metrics,
        experiment_steps=_string_list(value.get("experiment_steps")) or fallback.experiment_steps,
        expected_results=_clean(value.get("expected_results")) or fallback.expected_results,
        failure_modes=_string_list(value.get("failure_modes")) or fallback.failure_modes,
    )


def _append_audit_caveat(
    text: str,
    *,
    unsupported: list,
    weak: list,
) -> str:
    flagged = unsupported[:3] + weak[:2]
    if not flagged:
        return text
    summary = "; ".join(f"{item.claim_id}={item.status}" for item in flagged)
    return (
        f"{text}\n"
        "To validate: Claim audit flagged the following statements for cautious treatment "
        f"({summary}); these are retained only as hypotheses, planned validation targets, or bounded inferences."
    )


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in [_clean(raw) for raw in value] if item]


def _clean(value: object) -> str:
    return str(value or "").strip()
