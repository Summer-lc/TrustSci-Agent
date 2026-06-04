from app.evidence.audit import build_citation_audit
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun


class ReportWriterAgent:
    """Deterministic report writer for the MVP workflow.

    This mock writer assembles a complete contest-format research plan from
    structured agent outputs. It intentionally does not create new citations.
    """

    def run(
        self,
        run: ResearchRun,
        hypothesis: Hypothesis | None,
        experiment: ExperimentPlan,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        data_profiles: list[DatasetProfile],
        baseline_result_card: BaselineResultCard | None,
    ) -> ResearchReport:
        verified_papers = [
            paper for paper in papers if paper.verification_status == "verified" and paper.report_eligible
        ]
        verified_evidence = [item for item in evidence if item.verified and item.eligible_for_report]
        evidence_count = len(verified_evidence)
        statement = hypothesis.revised_statement or hypothesis.statement if hypothesis else run.question
        title = _paper_title(run, hypothesis)
        abstract = _paper_abstract(run, evidence_count, verified_papers, baseline_result_card)

        return ResearchReport(
            problem_statement=_problem_statement(run, verified_papers, verified_evidence),
            rationale=_rationale(statement, hypothesis, verified_evidence),
            technical_details=_technical_details(),
            datasets=experiment.datasets,
            source=experiment.source,
            target=experiment.target,
            paper_title=title,
            paper_abstract=abstract,
            methods=_methods(run, verified_evidence, data_profiles, baseline_result_card),
            experiments=experiment,
            results=_results_text(baseline_result_card, len(verified_papers), evidence_count),
            data_profiles=data_profiles,
            baseline_result_card=baseline_result_card,
            references=verified_papers,
            citation_audit_log=build_citation_audit(papers),
        )


def _problem_statement(
    run: ResearchRun,
    verified_papers: list[Paper],
    verified_evidence: list[EvidenceItem],
) -> str:
    if not verified_papers:
        citation_note = "No verified reference is available yet; literature claims must remain verification pending."
    else:
        citation_note = (
            f"The current run has {len(verified_papers)} verified references and "
            f"{len(verified_evidence)} verified evidence items."
        )
    return (
        "Early-stage scientific ideation often mixes real literature with unsupported claims. "
        f"For the selected domain ({run.domain}), the concrete task is to answer: {run.question} "
        "The report must keep every scientific claim traceable to verified evidence and an executable validation path. "
        f"{citation_note}"
    )


def _rationale(
    statement: str,
    hypothesis: Hypothesis | None,
    verified_evidence: list[EvidenceItem],
) -> str:
    evidence_summary = _evidence_summary(verified_evidence)
    critic_note = ""
    if hypothesis and hypothesis.critic:
        critic_note = (
            " Critic review scores: "
            f"novelty={hypothesis.critic.novelty}, "
            f"verifiability={hypothesis.critic.verifiability}, "
            f"data_availability={hypothesis.critic.data_availability}. "
            f"Revision advice: {hypothesis.critic.revision_advice}"
        )
    return f"Selected hypothesis: {statement}. Evidence basis: {evidence_summary}.{critic_note}"


def _technical_details() -> list[str]:
    return [
        "Qwen/Bailian-compatible LLM client behind a provider-neutral LLM interface.",
        "Planner output with sub-questions, search queries, tools, evidence requirements, and risk controls.",
        "Unified literature router over OpenAlex, Semantic Scholar, and arXiv with DOI/arXiv/title deduplication.",
        "Layered citation verification across arXiv ID, Crossref DOI, DataCite DOI, OpenAlex title, Semantic Scholar title, and arXiv title search before references are allowed.",
        "Evidence ledger with verification method, confidence, matched source, report eligibility, and citation freezing before final report writing.",
        "PDF page chunks can be ingested into the evidence ledger for page-level support after browser or local PDF capture.",
        "Claim audit verifies final report claims against eligible evidence and flags unsupported claims for review.",
        "Scientific data profiling for Materials Project and Matbench-compatible result cards.",
        "Deterministic Report Writer mock that assembles structured outputs without inventing citations.",
    ]


def _methods(
    run: ResearchRun,
    verified_evidence: list[EvidenceItem],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> list[str]:
    browser_step = (
        "Use browser captures and PDF parsing only as supporting evidence until citation metadata is verified."
        if run.constraints.enable_browser_worker
        else "Use scholarly API retrieval first; browser/PDF evidence can be enabled in later runs."
    )
    result_card_step = (
        f"Attach baseline result card {baseline_result_card.name} to separate executable mock results from expected outcomes."
        if baseline_result_card
        else "Mark quantitative results as verification pending until a baseline result card is generated."
    )
    return [
        "Plan the research question into search, extraction, verification, hypothesis, and experiment subtasks.",
        "Retrieve candidate papers from the literature router and verify arXiv ID, DOI, title, and source metadata before they can appear in References.",
        f"Convert {len(verified_evidence)} verified evidence items into hypothesis support and gap analysis.",
        f"Profile {len(data_profiles)} scientific datasets for availability, target variable, and task type.",
        "Run critic review and select or revise the hypothesis before experiment design.",
        result_card_step,
        browser_step,
        "Export the contest-format report with a citation audit log covering accepted, suspicious, hallucinated, skipped, and audit-only papers.",
    ]


def _paper_title(run: ResearchRun, hypothesis: Hypothesis | None) -> str:
    if hypothesis:
        short = hypothesis.statement.strip().rstrip(".")
        return f"Evidence-Grounded Research Plan: {short[:90]}"
    return f"Evidence-Grounded Research Plan for {run.domain}"


def _paper_abstract(
    run: ResearchRun,
    evidence_count: int,
    verified_papers: list[Paper],
    card: BaselineResultCard | None,
) -> str:
    result_card_note = (
        f" It includes an executable baseline result card ({card.name}) as a bounded MVP validation artifact."
        if card
        else " Quantitative results are marked verification pending until a baseline run is attached."
    )
    return (
        "This mock report is generated by TrustSci-Agent's Report Writer Agent. "
        f"It addresses the domain '{run.domain}' by combining planner output, citation verification, "
        f"{evidence_count} verified evidence items, and an explicit experiment design. "
        f"References are restricted to {len(verified_papers)} verified papers; unverified or rejected papers only appear in the audit log."
        f"{result_card_note}"
    )


def _evidence_summary(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "verification pending; no verified evidence item is available yet"
    snippets = []
    for item in evidence[:3]:
        source = item.source_title or item.paper_id or "unknown source"
        snippets.append(f"{item.claim} ({source})")
    return "; ".join(snippets)


def _results_text(card: BaselineResultCard | None, verified_reference_count: int, verified_evidence_count: int) -> str:
    if card is None:
        return (
            "MVP feasibility is demonstrated by executable planning, citation verification, evidence binding, and report generation. "
            f"This run has {verified_reference_count} verified references and {verified_evidence_count} verified evidence items. "
            "Quantitative model performance is verification pending until a Matbench or Materials Project baseline card is attached."
        )
    metrics = ", ".join(f"{key}={value}" for key, value in card.metrics.items())
    return (
        f"A small executable baseline result card was generated: {card.name}, dataset={card.dataset}, "
        f"train_rows={card.train_rows}, test_rows={card.test_rows}, metrics=({metrics}). "
        f"The report references {verified_reference_count} verified papers and {verified_evidence_count} verified evidence items. "
        "This verifies the result-card contract before scaling to full Matbench or Materials Project data."
    )
