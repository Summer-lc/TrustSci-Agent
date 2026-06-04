from app.agents.literature_miner_agent import LiteratureMinerAgent
from app.schemas.evidence import EvidenceItem
from app.schemas.paper import Paper
from app.schemas.planner import PerspectiveQuestion


def test_literature_miner_generates_report_ready_knowledge_cards() -> None:
    evidence = [
        EvidenceItem(
            evidence_id="ev_001",
            paper_id="paper_001",
            claim="Solid electrolyte structure descriptors support ionic conductivity prioritization.",
            source_title="Verified solid electrolyte paper",
            quote_or_summary="The paper links structure descriptors to ionic conductivity.",
            verified=True,
            eligible_for_report=True,
            verification_confidence=0.93,
        )
    ]
    papers = [
        Paper(
            paper_id="paper_001",
            title="Verified solid electrolyte paper",
            work_type="journal-article",
        )
    ]
    perspectives = [
        PerspectiveQuestion(
            perspective="ml_data",
            role="Machine-learning scientist",
            question="Which descriptors and metrics make the hypothesis testable?",
            search_query="solid electrolyte structure descriptors ionic conductivity metrics",
            evidence_requirement="Dataset claims must name target and metric.",
            risk_control="Separate baseline results from expected outcomes.",
        )
    ]

    cards = LiteratureMinerAgent().run(evidence, papers, perspectives)

    assert len(cards) == 1
    assert cards[0].card_id == "kc_001"
    assert cards[0].report_eligible is True
    assert cards[0].evidence_ids == ["ev_001"]
    assert cards[0].paper_ids == ["paper_001"]
    assert cards[0].perspective == "ml_data"
