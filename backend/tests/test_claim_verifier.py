import pytest

from app.agents.report_writer_agent import ReportWriterAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.data import BaselineResultCard
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.run import ResearchConstraints, ResearchRun
from app.tools.claim_verifier import ClaimVerifier


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model")


def test_claim_verifier_audits_report_against_eligible_evidence() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a solid electrolyte conductivity research plan.",
        constraints=ResearchConstraints(max_papers=1),
    )
    hypothesis = Hypothesis(
        hypothesis_id="H1",
        statement="Solid electrolyte structure descriptors can support ionic conductivity prioritization.",
        rationale="A bounded MVP hypothesis.",
        supporting_evidence=["ev_001"],
        novelty_claim="Traceable evidence workflow.",
        verification_path="Compare baseline metrics.",
    )
    experiment = ExperimentPlan(
        datasets=["solid_electrolyte_candidates"],
        source="Materials profile",
        target="ionic conductivity",
        baselines=["mean_baseline"],
        metrics=["MAE"],
        experiment_steps=["Load data", "Run baseline"],
        expected_results="Expected improvement must be verified.",
        failure_modes=["Sparse labels"],
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_001",
            claim="Solid electrolyte structure descriptors connect to ionic conductivity prioritization.",
            source_title="Verified paper",
            quote_or_summary="The paper links solid electrolyte structure descriptors and ionic conductivity.",
            verified=True,
            eligible_for_report=True,
        )
    ]
    report = ReportWriterAgent().run(
        run,
        hypothesis,
        experiment,
        evidence,
        [],
        [],
        [],
        BaselineResultCard(
            name="mean_baseline",
            dataset="solid_electrolyte_candidates",
            target="ionic conductivity",
            model="mean",
            train_rows=4,
            test_rows=2,
            metrics={"MAE": 1.0},
            result_summary="small baseline",
        ),
    )

    audit = ClaimVerifier().audit(run, report, evidence, hypothesis)

    assert audit.total > 0
    assert audit.supported >= 1
    assert audit.support_score > 0
    assert any("ev_001" in item.matched_evidence_ids for item in audit.items)


def test_claim_verifier_marks_claims_unsupported_without_eligible_evidence() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a battery materials plan.",
        constraints=ResearchConstraints(max_papers=1),
    )
    experiment = ExperimentPlan(
        datasets=["none"],
        source="none",
        target="none",
        baselines=[],
        metrics=[],
        experiment_steps=[],
        expected_results="none",
        failure_modes=[],
    )
    report = ReportWriterAgent().run(run, None, experiment, [], [], [], [], None)

    audit = ClaimVerifier().audit(run, report, [], None)

    assert audit.total > 0
    assert audit.unsupported == audit.total
    assert audit.support_score == 0


@pytest.mark.asyncio
async def test_qwen_claim_verifier_uses_sentence_level_evidence_audit() -> None:
    run, report, evidence, hypothesis = _qwen_audit_fixture()
    llm = FakeLLM(
        {
            "claim_audits": [
                {
                    "claim_id": "claim_001",
                    "status": "weakly_supported",
                    "confidence": 0.48,
                    "matched_evidence_ids": ["ev_semantic"],
                    "reason": "The evidence is relevant but does not directly answer the user question.",
                },
                {
                    "claim_id": "claim_002",
                    "status": "supported",
                    "confidence": 0.91,
                    "matched_evidence_ids": ["ev_semantic"],
                    "reason": "The sentence is directly supported by the supplied NASICON evidence.",
                },
            ]
        }
    )

    audit = await ClaimVerifier(llm).arun(run, report, evidence, hypothesis)

    assert llm.requests[0].agent == "claim_verifier"
    assert any(item.status == "supported" for item in audit.items)
    assert any("ev_semantic" in item.matched_evidence_ids for item in audit.items)
    assert audit.support_score > 0


@pytest.mark.asyncio
async def test_qwen_claim_verifier_rejects_invented_evidence_ids() -> None:
    run, report, evidence, hypothesis = _qwen_audit_fixture()
    llm = FakeLLM(
        {
            "claim_audits": [
                {
                    "claim_id": "claim_002",
                    "status": "supported",
                    "confidence": 0.99,
                    "matched_evidence_ids": ["ev_hallucinated"],
                    "reason": "This tries to use an evidence id that was not provided.",
                }
            ]
        }
    )

    audit = await ClaimVerifier(llm).arun(run, report, evidence, hypothesis)
    claim_002 = next(item for item in audit.items if item.claim_id == "claim_002")

    assert claim_002.status == "unsupported"
    assert claim_002.matched_evidence_ids == []
    assert claim_002.confidence < 0.1


@pytest.mark.asyncio
async def test_qwen_claim_verifier_falls_back_for_bad_json() -> None:
    run, report, evidence, hypothesis = _qwen_audit_fixture()

    audit = await ClaimVerifier(FakeLLM("not-json")).arun(run, report, evidence, hypothesis)
    fallback = ClaimVerifier().audit(run, report, evidence, hypothesis)

    assert audit == fallback


def _qwen_audit_fixture() -> tuple[ResearchRun, object, list[EvidenceItem], Hypothesis]:
    run = ResearchRun(
        domain="energy_materials",
        question="Audit activation-barrier claims.",
        constraints=ResearchConstraints(max_papers=1),
    )
    hypothesis = Hypothesis(
        hypothesis_id="H1",
        statement="NASICON framework tuning may lower migration barriers in solid electrolytes.",
        rationale="The hypothesis is bounded and evidence-linked.",
        supporting_evidence=["ev_semantic"],
        novelty_claim="A verification plan, not a discovered material.",
        verification_path="Compare descriptor baselines against evidence-derived features.",
    )
    experiment = ExperimentPlan(
        datasets=["to be collected: NASICON conductivity table"],
        source="Verified literature evidence.",
        target="migration barrier and ionic conductivity proxy",
        baselines=["descriptor-only baseline"],
        metrics=["MAE"],
        experiment_steps=["Extract descriptors", "Run ablation"],
        expected_results="Any improvement is verification pending.",
        failure_modes=["Sparse labels"],
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_semantic",
            paper_id="paper_001",
            claim="NASICON framework composition affects lithium migration barrier and ionic transport.",
            source_title="Verified NASICON electrolyte study",
            quote_or_summary="The study reports that framework tuning changes activation barriers for lithium transport.",
            verified=True,
            eligible_for_report=True,
        )
    ]
    report = ReportWriterAgent().run(run, hypothesis, experiment, evidence, [], [], [], None)
    return run, report, evidence, hypothesis
