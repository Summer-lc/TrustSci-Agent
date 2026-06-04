from app.schemas.evidence import EvidenceItem
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.planner import PerspectiveQuestion


class LiteratureMinerAgent:
    def run(
        self,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        perspectives: list[PerspectiveQuestion],
    ) -> list[KnowledgeCard]:
        eligible = [item for item in evidence if item.eligible_for_report]
        source_evidence = eligible or evidence
        paper_by_id = {paper.paper_id: paper for paper in papers}
        cards: list[KnowledgeCard] = []

        for index, item in enumerate(source_evidence[:8], start=1):
            paper = paper_by_id.get(item.paper_id or "")
            perspective = _select_perspective(item, perspectives)
            cards.append(
                KnowledgeCard(
                    card_id=f"kc_{index:03d}",
                    title=_title(item, paper),
                    perspective=perspective.perspective if perspective else "literature",
                    finding=item.claim,
                    method=_method(item, paper),
                    dataset=_dataset(item),
                    limitation=_limitation(item),
                    transferability=_transferability(item, perspective),
                    evidence_ids=[item.evidence_id],
                    paper_ids=[item.paper_id] if item.paper_id else [],
                    confidence=item.verification_confidence or item.confidence,
                    report_eligible=item.eligible_for_report,
                )
            )
        return cards


def _select_perspective(
    item: EvidenceItem,
    perspectives: list[PerspectiveQuestion],
) -> PerspectiveQuestion | None:
    text = " ".join([item.claim, item.quote_or_summary, item.source_title]).lower()
    for perspective in perspectives:
        terms = set(perspective.search_query.lower().split()) | set(perspective.question.lower().split())
        if any(term.strip(".,:;()") in text for term in terms if len(term) > 5):
            return perspective
    return perspectives[0] if perspectives else None


def _title(item: EvidenceItem, paper: Paper | None) -> str:
    source = paper.title if paper else item.source_title
    return source[:120] if source else f"Knowledge card for {item.evidence_id}"


def _method(item: EvidenceItem, paper: Paper | None) -> str:
    if item.evidence_type == "pdf_page":
        return f"PDF page evidence from page {item.page or 'n/a'}"
    if paper and paper.work_type:
        return f"Literature metadata and abstract from {paper.work_type}"
    return "Verified literature metadata and evidence summary"


def _dataset(item: EvidenceItem) -> str:
    text = f"{item.claim} {item.quote_or_summary}".lower()
    if "matbench" in text:
        return "Matbench-compatible benchmark"
    if "materials project" in text:
        return "Materials Project"
    if "dataset" in text or "database" in text:
        return "Open scientific dataset mentioned in evidence"
    return ""


def _limitation(item: EvidenceItem) -> str:
    text = item.quote_or_summary.lower()
    if "limitation" in text or "limited" in text:
        return "Evidence text explicitly mentions a limitation; verify scope before using as general support."
    if not item.eligible_for_report:
        return "Evidence is not eligible for final report references until source verification improves."
    return "Mechanism and dataset claims should remain bounded to the verified source context."


def _transferability(item: EvidenceItem, perspective: PerspectiveQuestion | None) -> str:
    if perspective is None:
        return "Can support downstream hypothesis generation if kept tied to its source."
    return (
        f"Useful for the {perspective.role} perspective when answering: "
        f"{perspective.question}"
    )
