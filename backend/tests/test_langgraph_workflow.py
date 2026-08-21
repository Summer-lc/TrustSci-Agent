import pytest

from app.config import Settings
from app.schemas.citation import CitationVerificationReport, CitationVerificationResult
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.langgraph_workflow import LangGraphWorkflow, build_workflow
from app.workflows.scientist_workflow import ScientistWorkflow


def _fake_search_factory(*, enable_arxiv_assertion=None):
    async def fake_search(queries, *, max_papers: int, enable_semantic_scholar: bool = False, enable_arxiv: bool = True, domain: str = ""):
        if enable_arxiv_assertion is not None:
            assert enable_arxiv is enable_arxiv_assertion
        return [
            Paper(
                paper_id="paper_001",
                title="Solid-state electrolytes for lithium batteries",
                doi="10.1038/example",
                abstract="Solid-state electrolyte studies connect structure and ionic transport.",
                verification_status="candidate",
                verified_by=["openalex"],
            )
        ]

    return fake_search


async def _fake_verify_many(papers, *, enable_semantic_scholar: bool = False):
    for paper in papers:
        paper.verification_status = "verified"
        paper.verified_by.append("crossref")
        paper.title_match_score = 0.95
        paper.verification_method = "crossref_doi"
        paper.verification_confidence = 0.95
        paper.report_eligible = True
    return papers, CitationVerificationReport(
        total=len(papers),
        verified=len(papers),
        integrity_score=1,
        results=[
            CitationVerificationResult(
                paper_id=paper.paper_id,
                title=paper.title,
                status="verified",
                confidence=0.95,
                method="crossref_doi",
                doi=paper.doi,
            )
            for paper in papers
        ],
    )


def _make_langgraph_workflow(monkeypatch) -> LangGraphWorkflow:
    settings = Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph")
    workflow = LangGraphWorkflow(settings)
    calls = {"openalex": 0, "arxiv": 0, "crossref": 0}

    async def fake_openalex_search(query: str, limit: int):
        calls["openalex"] += 1
        return await _fake_search_factory()([query], max_papers=limit)

    async def fake_arxiv_search(query: str, limit: int):
        calls["arxiv"] += 1
        return []

    async def fake_crossref_verify(paper: Paper):
        calls["crossref"] += 1
        paper.verification_status = "verified"
        paper.verified_by.append("crossref")
        paper.title_match_score = 0.95
        paper.verification_method = "crossref_doi"
        paper.verification_confidence = 0.95
        paper.report_eligible = True
        return paper

    monkeypatch.setattr(workflow.openalex, "search", fake_openalex_search)
    monkeypatch.setattr(workflow.arxiv, "search", fake_arxiv_search)
    monkeypatch.setattr(workflow.crossref, "verify", fake_crossref_verify)
    workflow._test_tool_calls = calls
    return workflow


def test_build_workflow_default_is_classic() -> None:
    # Explicit workflow_engine so the assertion does not depend on the host
    # .env / compose interpolation (which may set WORKFLOW_ENGINE=langgraph).
    settings = Settings(dashscope_api_key="", workflow_engine="classic")
    workflow = build_workflow(settings)
    assert isinstance(workflow, ScientistWorkflow)
    assert not isinstance(workflow, LangGraphWorkflow)


def test_build_workflow_langgraph_when_configured() -> None:
    settings = Settings(dashscope_api_key="", workflow_engine="langgraph")
    workflow = build_workflow(settings)
    assert isinstance(workflow, LangGraphWorkflow)
    assert build_workflow(settings) is workflow


@pytest.mark.asyncio
async def test_langgraph_workflow_completes_sync_run(monkeypatch) -> None:
    workflow = _make_langgraph_workflow(monkeypatch)
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )

    result = await workflow.run(run)

    assert result.status == "completed"
    assert result.current_stage == "completed"
    assert result.progress == 1.0
    assert result.report is not None
    assert result.claim_audit is not None
    assert result.perspectives
    assert result.knowledge_cards
    assert result.workspace_path
    assert "research_log" in result.workspace_artifacts
    assert result.hypotheses[0].selected is True
    assert result.hypotheses[0].selection_rationale
    assert result.evidence[0].verified is True
    assert workflow._test_tool_calls["openalex"] > 0
    assert workflow._test_tool_calls["arxiv"] > 0
    assert workflow._test_tool_calls["crossref"] > 0
    assert workflow._checkpointer is not None

    # The full step chain ran through LangGraph in order.
    step_names = [step.name for step in result.steps if step.status == "completed"]
    assert step_names == [
        "intent_router",
        "planner",
        "literature_search",
        "citation_verification",
        "evidence_ledger",
        "literature_mining",
        "paper_classification",
        "scientific_data_profile",
        "hypothesis_debate",
        "experiment_design",
        "code_experiment",
        "experiment_result_gate",
        "result_evaluation",
        "ablation_analysis",
        "result_interpretation",
        "report_writer",
        "claim_verification",
        "report_revision",
        "claim_reverification",
        "report_translation",
    ]
    assert "LangChain Tools" in next(step.summary for step in result.steps if step.name == "literature_search")
    assert "LangChain Tool nodes" in next(step.summary for step in result.steps if step.name == "citation_verification")


@pytest.mark.asyncio
async def test_langgraph_workflow_preserves_bilingual_report_and_provenance(monkeypatch) -> None:
    workflow = _make_langgraph_workflow(monkeypatch)
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )

    result = await workflow.run(run)

    report = result.report
    assert report is not None
    # English formal report is present.
    assert report.english_report is not None
    assert report.english_report.paper_title
    assert report.english_report.datasets.source
    # Chinese report logic is preserved: with no LLM key the translator falls
    # back to the deterministic Chinese placeholder translation.
    assert report.chinese_report is not None
    assert report.chinese_report.paper_title.startswith("待翻译标题")
    assert report.chinese_report.datasets.source.startswith("待人工确认")
    # Audit appendix / provenance is attached.
    assert report.system_provenance is not None
    assert report.system_provenance.agent_workflow
    assert report.citation_audit_log


@pytest.mark.asyncio
async def test_langgraph_guided_workflow_pauses_for_citation_review(monkeypatch) -> None:
    workflow = _make_langgraph_workflow(monkeypatch)
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a guided solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1, workflow_mode="guided"),
    )

    first_pause = await workflow.run(run)

    assert first_pause.status == "paused"
    assert first_pause.current_stage == "awaiting_citation_review"
    assert first_pause.report is None
    # The guided pause happens after intent_router -> planner -> literature_search -> citation_verification.
    completed = [step.name for step in first_pause.steps if step.status == "completed"]
    assert completed == ["intent_router", "planner", "literature_search", "citation_verification"]
    assert any(step.name == "awaiting_citation_review" and step.status == "paused" for step in first_pause.steps)

    # Resuming without freezing citations fails (same guard as the classic engine).
    first_pause.citation_frozen = False
    blocked = await workflow.continue_run(first_pause)
    assert blocked.status == "failed"

    # Freeze citations, then resume to the evidence-review pause. Restore the
    # pause stage first: the blocked attempt above left current_stage="failed".
    first_pause.status = "paused"
    first_pause.current_stage = "awaiting_citation_review"
    first_pause.citation_frozen = True
    first_pause.papers[0].human_decision = "accepted"
    first_pause.papers[0].report_eligible = True
    first_pause.frozen_paper_ids = ["paper_001"]
    second_pause = await workflow.continue_run(first_pause)

    assert second_pause.status == "paused"
    assert second_pause.current_stage == "awaiting_evidence_review"
    assert second_pause.evidence
    assert second_pause.report is None

    # Freeze evidence, then resume to completion.
    second_pause.evidence_frozen = True
    second_pause.evidence[0].human_decision = "accepted"
    second_pause.evidence[0].eligible_for_report = True
    second_pause.frozen_evidence_ids = [second_pause.evidence[0].evidence_id]
    completed_run = await workflow.continue_run(second_pause)

    assert completed_run.status == "completed"
    assert completed_run.report is not None
    assert completed_run.claim_audit is not None


@pytest.mark.asyncio
async def test_langgraph_intent_router_routes_by_mode(monkeypatch) -> None:
    workflow = _make_langgraph_workflow(monkeypatch)
    # _route_by_mode returns the run's mode, which maps to the matching branch node.
    discovery = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")
    assert workflow._route_by_mode({"run": discovery}) == "discovery"
    refinement = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="idea_refinement")
    assert workflow._route_by_mode({"run": refinement}) == "idea_refinement"
    assistance = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="experiment_assistance")
    assert workflow._route_by_mode({"run": assistance}) == "experiment_assistance"


@pytest.mark.asyncio
async def test_classic_workflow_still_completes(monkeypatch) -> None:
    """Regression guard: the default classic engine remains usable and unchanged."""
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)
    monkeypatch.setattr(workflow.literature_router, "search", _fake_search_factory())
    monkeypatch.setattr(workflow.citation_verifier, "verify_many", _fake_verify_many)

    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )
    result = await workflow.run(run)

    assert result.status == "completed"
    assert result.report is not None
    assert result.report.chinese_report is not None
