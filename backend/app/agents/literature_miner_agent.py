import json
from typing import Any

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.evidence import EvidenceItem
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.planner import PerspectiveQuestion


SYSTEM_PROMPT = """You are the Literature Miner Agent for TrustSci-Agent.
Extract structured scientific facts only from the provided verified papers and evidence snippets.
Return JSON only. Do not invent citations, paper ids, evidence ids, datasets, metrics, or results.

Required JSON shape:
{
  "knowledge_cards": [
    {
      "card_id": "kc_001",
      "title": "short source-grounded title",
      "perspective": "domain_mechanism | ml_data | experimental_validation | skeptical_reviewer | literature",
      "research_problem": "problem stated by the sources",
      "method": "method or technical approach in the sources",
      "dataset": "dataset or data source, or empty string",
      "metric": "metric, or empty string",
      "key_finding": "source-grounded finding",
      "limitation": "source-grounded limitation, or evidence insufficient",
      "future_work": "future work from sources, or evidence insufficient",
      "transferable_idea": "how this fact may transfer to hypothesis generation",
      "uncertainty": "uncertainty or evidence insufficient note",
      "evidence_ids": ["existing evidence ids only"],
      "paper_ids": ["existing paper ids only"],
      "confidence": 0.0
    }
  ]
}
Every card must include at least one evidence_id and one paper_id from the input.
"""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)


class LiteratureMinerAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        perspectives: list[PerspectiveQuestion],
        *,
        run_id: str | None = None,
    ) -> list[KnowledgeCard]:
        fallback_cards = self.run(evidence, papers, perspectives)
        if self.llm is None:
            return fallback_cards
        fallback = {"knowledge_cards": [card.model_dump() for card in fallback_cards]}
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run_id, agent="literature_miner")
            | FallbackParser(
                lambda content: _normalize_qwen_cards(content, fallback_cards, evidence, papers),
                fallback_cards,
            )
        )
        return await chain.ainvoke({"user_prompt": _build_user_prompt(evidence, papers, perspectives)})

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


def _build_user_prompt(
    evidence: list[EvidenceItem],
    papers: list[Paper],
    perspectives: list[PerspectiveQuestion],
) -> str:
    paper_by_id = {paper.paper_id: paper for paper in papers}
    source_evidence = [item for item in evidence if item.eligible_for_report] or evidence
    payload = {
        "papers": [
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "year": paper.year,
                "doi": paper.doi,
                "abstract": paper.abstract[:1200],
                "verification_status": paper.verification_status,
                "report_eligible": paper.report_eligible,
            }
            for paper in papers[:12]
        ],
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "paper_id": item.paper_id,
                "source_title": item.source_title or _paper_title(paper_by_id.get(item.paper_id or "")),
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "section": item.section,
                "page": item.page,
                "verified": item.verified,
                "eligible_for_report": item.eligible_for_report,
                "confidence": item.verification_confidence or item.confidence,
            }
            for item in source_evidence[:16]
        ],
        "perspectives": [
            {
                "perspective": item.perspective,
                "role": item.role,
                "question": item.question,
                "evidence_requirement": item.evidence_requirement,
            }
            for item in perspectives[:8]
        ],
        "instructions": [
            "Use only input evidence_ids and paper_ids.",
            "If evidence is thin, write evidence insufficient in uncertainty or limitation.",
            "Prefer specific scientific facts over generic summaries.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_qwen_cards(
    content: object,
    fallback: list[KnowledgeCard],
    evidence: list[EvidenceItem],
    papers: list[Paper],
) -> list[KnowledgeCard]:
    if not isinstance(content, dict):
        return fallback
    raw_cards = content.get("knowledge_cards")
    if not isinstance(raw_cards, list):
        return fallback

    evidence_by_id = {item.evidence_id: item for item in evidence}
    paper_ids = {paper.paper_id for paper in papers}
    cards: list[KnowledgeCard] = []
    for index, raw in enumerate(raw_cards[:8], start=1):
        if not isinstance(raw, dict):
            continue
        evidence_ids = _known_ids(raw.get("evidence_ids"), set(evidence_by_id))
        if not evidence_ids:
            continue
        inferred_paper_ids = {
            evidence_by_id[evidence_id].paper_id
            for evidence_id in evidence_ids
            if evidence_by_id[evidence_id].paper_id
        }
        provided_paper_ids = _known_ids(raw.get("paper_ids"), paper_ids)
        selected_paper_ids = sorted((set(provided_paper_ids) | inferred_paper_ids) & paper_ids)
        if not selected_paper_ids:
            continue
        finding = _fact_text(raw)
        if not finding:
            continue
        cards.append(
            KnowledgeCard(
                card_id=str(raw.get("card_id") or f"kc_{index:03d}"),
                title=_clean(raw.get("title")) or f"Qwen-mined fact {index}",
                perspective=_clean(raw.get("perspective")) or "literature",
                finding=finding,
                method=_clean(raw.get("method")),
                dataset=_clean(raw.get("dataset")),
                limitation=_limitation_text(raw),
                transferability=_clean(raw.get("transferable_idea")),
                evidence_ids=evidence_ids,
                paper_ids=selected_paper_ids,
                confidence=_confidence(raw.get("confidence")),
                report_eligible=all(evidence_by_id[evidence_id].eligible_for_report for evidence_id in evidence_ids),
            )
        )
    return cards or fallback


def _fact_text(raw: dict[str, Any]) -> str:
    parts = [
        ("research problem", raw.get("research_problem")),
        ("key finding", raw.get("key_finding") or raw.get("finding")),
        ("metric", raw.get("metric")),
        ("uncertainty", raw.get("uncertainty")),
    ]
    return "; ".join(f"{label}: {_clean(value)}" for label, value in parts if _clean(value))


def _limitation_text(raw: dict[str, Any]) -> str:
    parts = [
        ("limitation", raw.get("limitation")),
        ("future work", raw.get("future_work")),
        ("uncertainty", raw.get("uncertainty")),
    ]
    return "; ".join(f"{label}: {_clean(value)}" for label, value in parts if _clean(value))


def _known_ids(value: object, allowed: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in [str(raw).strip() for raw in value] if item in allowed]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _paper_title(paper: Paper | None) -> str:
    return paper.title if paper else ""


def _confidence(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.6
    return max(0.0, min(1.0, score))


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
