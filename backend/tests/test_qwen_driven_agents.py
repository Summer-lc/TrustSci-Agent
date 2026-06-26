import pytest

from app.agents.critic_agent import CriticAgent
from app.agents.experiment_designer_agent import ExperimentDesignerAgent
from app.agents.gap_finder_agent import GapFinderAgent
from app.agents.hypothesis_agent import HypothesisAgent
from app.agents.literature_miner_agent import LiteratureMinerAgent
from app.agents.report_writer_agent import ReportWriterAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper
from app.schemas.planner import PerspectiveQuestion
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model")


@pytest.mark.asyncio
async def test_literature_miner_uses_qwen_knowledge_cards() -> None:
    llm = FakeLLM(
        {
            "knowledge_cards": [
                {
                    "card_id": "kc_qwen_001",
                    "title": "Mechanism card",
                    "perspective": "ml_data",
                    "research_problem": "Transport bottlenecks are hard to screen.",
                    "method": "structure-property descriptor analysis",
                    "dataset": "Materials Project",
                    "metric": "MAE",
                    "key_finding": "Descriptors can prioritize ionic conductivity candidates.",
                    "limitation": "Evidence is limited to the provided paper.",
                    "future_work": "Validate on a bounded benchmark.",
                    "transferable_idea": "Use evidence tags as features.",
                    "uncertainty": "verification pending beyond cited evidence",
                    "evidence_ids": ["ev_001"],
                    "paper_ids": ["paper_001"],
                    "confidence": 0.88,
                }
            ]
        }
    )

    cards = await LiteratureMinerAgent(llm).arun(_evidence(), _papers(), _perspectives(), run_id="run_qwen")

    assert cards[0].card_id == "kc_qwen_001"
    assert cards[0].evidence_ids == ["ev_001"]
    assert cards[0].paper_ids == ["paper_001"]
    assert "Descriptors can prioritize" in cards[0].finding
    assert llm.requests[0].agent == "literature_miner"


@pytest.mark.asyncio
async def test_literature_miner_falls_back_for_bad_qwen_json() -> None:
    cards = await LiteratureMinerAgent(FakeLLM("not-json")).arun(_evidence(), _papers(), _perspectives())

    assert cards[0].card_id == "kc_001"
    assert cards[0].finding == _evidence()[0].claim


@pytest.mark.asyncio
async def test_gap_finder_uses_qwen_evidence_bound_gaps() -> None:
    llm = FakeLLM(
        {
            "gaps": [
                {
                    "gap_id": "gap_qwen_001",
                    "unresolved_gap": "Mechanism text is not yet tested against structured descriptors.",
                    "what_literature_shows": "Evidence links descriptors and transport.",
                    "what_is_not_solved": "Whether evidence-derived tags improve ranking.",
                    "why_worth_exploring": "It makes hypothesis generation auditable.",
                    "verification_opportunity": "Compare descriptor-only and evidence-tag baselines.",
                    "underexplored_method_combination": "literature tags plus structure descriptors",
                    "data_availability_opportunity": "Use bundled solid electrolyte candidates.",
                    "risk_uncertainty": "small sample size",
                    "supporting_evidence_ids": ["ev_001"],
                }
            ]
        }
    )

    gaps = await GapFinderAgent(llm).arun([], _evidence(), [_data_profile()])

    assert gaps[0]["gap_id"] == "gap_qwen_001"
    assert gaps[0]["supporting_evidence_ids"] == ["ev_001"]
    assert "descriptor" in gaps[0]["verification_opportunity"]


@pytest.mark.asyncio
async def test_hypothesis_agent_marks_evidence_insufficient_without_ids() -> None:
    llm = FakeLLM(
        {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "statement": "Evidence-derived tags may improve candidate ranking.",
                    "rationale": "The gap suggests a measurable comparison.",
                    "supporting_evidence_ids": [],
                    "novelty_boundary": "A bounded workflow hypothesis, not a new material claim.",
                    "verification_path": "Run baseline and ablation on the profiled dataset.",
                    "required_dataset": "bundled_solid_electrolyte_candidates",
                    "expected_contribution": "Improved auditability if metrics improve.",
                    "risk": "Evidence coverage may be weak.",
                    "evidence_sufficiency_note": "evidence insufficient",
                }
            ]
        }
    )

    hypotheses = await HypothesisAgent(llm).arun([{"gap": "test", "evidence": []}], _evidence(), [_data_profile()])

    assert hypotheses[0].supporting_evidence == []
    assert "Evidence sufficiency: evidence insufficient" in hypotheses[0].rationale
    assert "not a new material claim" in hypotheses[0].novelty_claim


@pytest.mark.asyncio
async def test_critic_agent_uses_specific_qwen_reviewer_comments() -> None:
    llm = FakeLLM(
        {
            "reviews": [
                {
                    "hypothesis_id": "H1",
                    "novelty": 7,
                    "self_consistency": 8,
                    "verifiability": 9,
                    "data_availability": 8,
                    "feasibility": 8,
                    "evidence_support": 7,
                    "risk": "May overlap with descriptor-only baselines.",
                    "revision_advice": "Add an ablation that removes evidence tags.",
                    "reviewers": [
                        _review("domain expert", "Strong mechanism framing, but cite the exact transport evidence before claiming relevance."),
                        _review("machine learning expert", "The comparison is testable, but leakage controls and a descriptor-only baseline are required."),
                        _review("experimental validation expert", "The hypothesis is falsifiable if conductivity proxy labels and splits are specified."),
                        _review("skeptical reviewer", "The novelty is weak unless evidence tags are separated from generic feature engineering."),
                    ],
                }
            ]
        }
    )

    reviewed = await CriticAgent(llm).arun([_hypothesis()], _evidence())

    comments = [comment.comment for comment in reviewed[0].reviewer_comments]
    assert len(comments) == 4
    assert any("descriptor-only baseline" in comment for comment in comments)
    assert reviewed[0].critic is not None
    assert reviewed[0].critic.revision_advice == "Add an ablation that removes evidence tags."


@pytest.mark.asyncio
async def test_experiment_designer_uses_qwen_baselines_and_metrics() -> None:
    llm = FakeLLM(
        {
            "experiment_plan": {
                "datasets": ["bundled_solid_electrolyte_candidates"],
                "source": "Verified papers plus local profile.",
                "target": "ionic_conductivity_proxy",
                "baselines": ["descriptor-only ridge regression", "evidence-tag ablation"],
                "metrics": ["MAE", "R2", "top-k hit rate"],
                "methods": ["ridge regression with evidence tags"],
                "experiment_steps": ["Create splits", "Train baselines"],
                "expected_results": "Bounded feasibility: improvements remain verification pending.",
                "failure_modes": ["small data", "feature leakage"],
                "possible_ablation": ["remove evidence tags"],
            }
        }
    )

    plan = await ExperimentDesignerAgent(llm).arun(_hypothesis(), [_data_profile()], _evidence())

    assert plan.datasets == ["bundled_solid_electrolyte_candidates"]
    assert "descriptor-only ridge regression" in plan.baselines
    assert "top-k hit rate" in plan.metrics
    assert any("Ablation: remove evidence tags" == step for step in plan.experiment_steps)


@pytest.mark.asyncio
async def test_report_writer_never_accepts_qwen_invented_references() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate an evidence-grounded plan.",
        constraints=ResearchConstraints(max_papers=2),
    )
    llm = FakeLLM(
        {
            "report": {
                "problem_statement": "Use ev_001 to bound the current limitation.",
                "rationale": "The selected hypothesis is grounded in ev_001.",
                "technical_details": ["Qwen-driven agents", "citation audit"],
                "datasets": ["invented dataset should be ignored"],
                "source": "Verified evidence only.",
                "target": "ionic_conductivity_proxy",
                "paper_title": "Evidence-Grounded Conductivity Screening",
                "paper_abstract": "We propose a bounded verification plan.",
                "methods": ["Use only reportable evidence."],
                "experiments": _experiment().model_dump(),
                "results": "Expected results are verification pending.",
                "references": [{"title": "Invented Reference"}],
            }
        }
    )
    papers = _papers() + [
        Paper(paper_id="paper_bad", title="Unverified Reference", verification_status="candidate")
    ]

    report = await ReportWriterAgent(llm).arun(
        run,
        _hypothesis(),
        _experiment(),
        _evidence(),
        papers,
        [],
        [_data_profile()],
        _baseline_card(),
    )

    assert [paper.paper_id for paper in report.references] == ["paper_001"]
    assert "Invented Reference" not in [paper.title for paper in report.references]
    assert report.datasets == _experiment().datasets
    assert any("paper_bad: candidate" in line for line in report.citation_audit_log)


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            evidence_id="ev_001",
            paper_id="paper_001",
            claim="Structure descriptors support ionic conductivity prioritization.",
            source_title="Verified solid electrolyte paper",
            quote_or_summary="The paper links descriptors to conductivity ranking.",
            verified=True,
            eligible_for_report=True,
            verification_confidence=0.92,
        )
    ]


def _papers() -> list[Paper]:
    return [
        Paper(
            paper_id="paper_001",
            title="Verified solid electrolyte paper",
            year=2024,
            doi="10.1234/verified",
            abstract="Solid electrolyte descriptors can support transport screening.",
            verification_status="verified",
            report_eligible=True,
        )
    ]


def _perspectives() -> list[PerspectiveQuestion]:
    return [
        PerspectiveQuestion(
            perspective="ml_data",
            role="Machine-learning scientist",
            question="Which descriptors and metrics make the hypothesis testable?",
            search_query="solid electrolyte descriptors metrics",
            evidence_requirement="Dataset claims must name target and metric.",
            risk_control="Separate expected outcomes from verified results.",
        )
    ]


def _data_profile() -> DatasetProfile:
    return DatasetProfile(
        name="bundled_solid_electrolyte_candidates",
        source="local fixture",
        rows=12,
        fields=["formula", "ionic_conductivity_proxy"],
        target="ionic_conductivity_proxy",
        task_type="regression",
    )


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        hypothesis_id="H1",
        statement="Evidence-derived mechanism tags may improve ranking of solid electrolyte candidates.",
        rationale="This is grounded in ev_001 and remains verification pending.",
        supporting_evidence=["ev_001"],
        novelty_claim="The novelty is a bounded evidence-tag ablation, not a new material discovery.",
        verification_path="Compare descriptor-only and evidence-tag baselines.",
    )


def _experiment() -> ExperimentPlan:
    return ExperimentPlan(
        datasets=["bundled_solid_electrolyte_candidates"],
        source="Verified literature metadata and local profile.",
        target="ionic_conductivity_proxy",
        baselines=["descriptor-only ridge regression"],
        metrics=["MAE", "R2"],
        experiment_steps=["Create split", "Train baseline"],
        expected_results="Expected improvements are verification pending.",
        failure_modes=["small data"],
    )


def _baseline_card() -> BaselineResultCard:
    return BaselineResultCard(
        name="solid_electrolyte_mean_baseline",
        dataset="bundled_solid_electrolyte_candidates",
        target="ionic_conductivity_proxy",
        model="mean_baseline",
        train_rows=8,
        test_rows=4,
        metrics={"mae": 0.12},
        result_summary="Toy baseline completed.",
    )


def _review(reviewer: str, comment: str) -> dict:
    return {
        "reviewer": reviewer,
        "score": 8,
        "stance": "cautious_support",
        "comment": comment,
        "required_action": f"{reviewer} requires a concrete evidence-bound revision.",
    }
