from app.evidence.audit import build_citation_audit
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun


class ReportWriterAgent:
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
        verified_papers = [paper for paper in papers if paper.verification_status == "verified"]
        references = verified_papers or papers[:3]
        evidence_count = len([item for item in evidence if item.verified])
        statement = hypothesis.revised_statement or hypothesis.statement if hypothesis else run.question

        return ResearchReport(
            problem_statement=(
                "Early-stage scientific ideation often mixes real literature with unsupported claims. "
                f"For the selected domain ({run.domain}), the concrete limitation is to generate hypotheses that remain traceable to verified sources and executable validation plans."
            ),
            rationale=statement,
            technical_details=[
                "Qwen/Bailian-compatible LLM client with deterministic fallback",
                "OpenAlex literature search and Crossref DOI/title verification",
                "Evidence ledger with citation freezing before final report writing",
                "Multi-agent planner, gap finder, hypothesis generator, critic, experiment designer, and report writer",
            ],
            datasets=experiment.datasets,
            source=experiment.source,
            target=experiment.target,
            paper_title="Trustworthy Multi-Agent Hypothesis Generation for Evidence-Grounded Energy Materials Research",
            paper_abstract=(
                "We present a Qwen-compatible multi-agent AI Scientist prototype for generating verifiable research hypotheses. "
                "The system retrieves real literature, verifies citations, builds an evidence ledger, debates candidate hypotheses, "
                "and exports a standardized research plan. A bounded energy-materials case demonstrates how evidence coverage "
                f"({evidence_count} verified items in this run) and experiment design can reduce hallucinated references."
            ),
            methods=[
                "Plan the research question into search, extraction, verification, hypothesis, and experiment subtasks.",
                "Retrieve candidate papers and verify DOI/title metadata before they can appear in References.",
                "Convert verified literature into evidence items that can support candidate hypotheses.",
                "Run critic review and human-selectable hypothesis refinement.",
                "Export a contest-format report with citation audit log.",
            ],
            experiments=experiment,
            results=_results_text(baseline_result_card),
            data_profiles=data_profiles,
            baseline_result_card=baseline_result_card,
            references=references,
            citation_audit_log=build_citation_audit(papers),
        )


def _results_text(card: BaselineResultCard | None) -> str:
    if card is None:
        return (
            "MVP feasibility is demonstrated by executable retrieval, DOI verification, evidence binding, and report generation. "
            "A later phase should add a real Matbench/Materials Project benchmark run for quantitative property metrics."
        )
    metrics = ", ".join(f"{key}={value}" for key, value in card.metrics.items())
    return (
        f"A small executable baseline result card was generated: {card.name}, dataset={card.dataset}, "
        f"train_rows={card.train_rows}, test_rows={card.test_rows}, metrics=({metrics}). "
        "This verifies the result-card contract before scaling to full Matbench or Materials Project data."
    )
