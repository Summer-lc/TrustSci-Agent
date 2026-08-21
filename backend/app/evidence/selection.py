from app.schemas.evidence import EvidenceItem
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.run import ResearchRun


def reportable_evidence(run: ResearchRun, evidence: list[EvidenceItem] | None = None) -> list[EvidenceItem]:
    human_reviewed = run.citation_frozen or run.evidence_frozen
    items = [
        item
        for item in (evidence if evidence is not None else run.evidence)
        if item.verified and item.eligible_for_report and item.human_decision != "rejected"
    ]
    if human_reviewed:
        accepted_paper_ids = {
            paper.paper_id
            for paper in run.papers
            if paper.human_decision == "accepted"
        }
        items = [
            item
            for item in items
            if item.human_decision == "accepted"
            and (not item.paper_id or item.paper_id in accepted_paper_ids)
        ]
    if not run.evidence_frozen:
        if run.citation_frozen:
            frozen_paper_ids = set(run.frozen_paper_ids)
            return [item for item in items if item.paper_id in frozen_paper_ids]
        return items
    frozen_ids = set(run.frozen_evidence_ids)
    items = [item for item in items if item.evidence_id in frozen_ids]
    if run.citation_frozen:
        frozen_paper_ids = set(run.frozen_paper_ids)
        return [item for item in items if item.paper_id in frozen_paper_ids]
    return items


def reportable_papers(
    run: ResearchRun,
    papers: list[Paper] | None = None,
    evidence: list[EvidenceItem] | None = None,
) -> list[Paper]:
    items = reportable_evidence(run, evidence)
    frozen_or_evidence_paper_ids = set(run.frozen_paper_ids)
    frozen_or_evidence_paper_ids.update(item.paper_id for item in items if item.paper_id)
    human_reviewed = run.citation_frozen or run.evidence_frozen
    verified = [
        paper
        for paper in (papers if papers is not None else run.papers)
        if paper.verification_status == "verified" and paper.report_eligible and paper.human_decision != "rejected"
    ]
    if human_reviewed:
        verified = [paper for paper in verified if paper.human_decision == "accepted"]
    if run.evidence_frozen or run.citation_frozen:
        return [paper for paper in verified if paper.paper_id in frozen_or_evidence_paper_ids]
    return verified


def reportable_knowledge_cards(
    run: ResearchRun,
    cards: list[KnowledgeCard] | None = None,
) -> list[KnowledgeCard]:
    items = cards if cards is not None else run.knowledge_cards
    report_ready = [card for card in items if card.report_eligible]
    if not run.evidence_frozen:
        return report_ready
    frozen_ids = set(run.frozen_evidence_ids)
    return [card for card in report_ready if frozen_ids.intersection(card.evidence_ids)]
