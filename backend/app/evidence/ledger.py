import re

from app.schemas.evidence import EvidenceItem, PaperChunk
from app.schemas.paper import Paper


def evidence_from_papers(papers: list[Paper], domain: str) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for idx, paper in enumerate(papers, start=1):
        abstract = paper.abstract.strip()
        base_id = f"ev_{idx:03d}"
        claim = _claim_from_paper(paper, domain)
        summary = abstract[:700] if abstract else f"Metadata confirms this work exists: {paper.title}."
        confidence = (
            paper.verification_confidence
            if paper.verification_confidence is not None
            else (0.82 if paper.verification_status == "verified" else 0.62)
        )
        items.append(
            _paper_evidence_item(
                paper=paper,
                evidence_id=base_id,
                claim=claim,
                summary=summary,
                confidence=confidence,
                domain=domain,
                tags=["literature", "paper_summary"],
            )
        )
        items.extend(
            _granular_evidence_items(
                paper=paper,
                base_id=base_id,
                abstract=abstract,
                confidence=confidence,
                domain=domain,
            )
        )
    return items


def evidence_from_pdf_chunks(
    chunks: list[PaperChunk],
    *,
    domain: str,
    start_index: int = 1,
    verified: bool = False,
    verification_method: str | None = None,
    verification_confidence: float | None = None,
    matched_source: str | None = None,
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for offset, chunk in enumerate(chunks, start=start_index):
        items.append(
            EvidenceItem(
                evidence_id=f"ev_{offset:03d}",
                paper_id=chunk.paper_id,
                claim=_claim_from_chunk(chunk, domain),
                evidence_type="pdf_page",
                source_title=chunk.source_title,
                source_url=chunk.source_url,
                source_path=chunk.source_path,
                page=chunk.page,
                section=chunk.section,
                quote_or_summary=chunk.text[:700],
                confidence=verification_confidence if verification_confidence is not None else (0.78 if verified else 0.56),
                verified=verified,
                verification_method=verification_method,
                verification_confidence=verification_confidence,
                matched_source=matched_source,
                eligible_for_report=verified,
                tags=[domain, "pdf", "page_evidence"],
            )
        )
    return items


def _claim_from_paper(paper: Paper, domain: str) -> str:
    title = paper.title.lower()
    if "solid" in title and "electroly" in title:
        return "Solid-state electrolyte literature links structure, transport pathways, and stability constraints."
    if "catalyst" in title or "catalysis" in title:
        return "Catalysis literature connects adsorption energetics, structure features, and screening strategies."
    if domain == "energy_materials":
        return "Energy materials research contains reusable evidence for structure-property-performance hypotheses."
    return "The paper provides domain evidence that can support a verifiable research hypothesis."


def _claim_from_chunk(chunk: PaperChunk, domain: str) -> str:
    section = f" {chunk.section}" if chunk.section else ""
    if domain == "energy_materials":
        return f"PDF page evidence{section} provides traceable material-science context for the research plan."
    return f"PDF page evidence{section} provides traceable context for the research plan."


def _paper_evidence_item(
    *,
    paper: Paper,
    evidence_id: str,
    claim: str,
    summary: str,
    confidence: float,
    domain: str,
    tags: list[str],
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        paper_id=paper.paper_id,
        claim=claim,
        source_title=paper.title,
        source_url=paper.source_url,
        doi=paper.doi,
        quote_or_summary=summary,
        confidence=confidence,
        verified=paper.verification_status == "verified",
        verification_method=paper.verification_method,
        verification_confidence=paper.verification_confidence,
        matched_source=paper.matched_source,
        eligible_for_report=paper.report_eligible,
        tags=[domain, *tags],
    )


def _granular_evidence_items(
    *,
    paper: Paper,
    base_id: str,
    abstract: str,
    confidence: float,
    domain: str,
) -> list[EvidenceItem]:
    if not abstract:
        return []
    selected = _select_evidence_sentences(abstract)
    items: list[EvidenceItem] = []
    for offset, sentence in enumerate(selected, start=1):
        suffix = chr(ord("a") + offset - 1)
        items.append(
            _paper_evidence_item(
                paper=paper,
                evidence_id=f"{base_id}{suffix}",
                claim=sentence[:320],
                summary=sentence[:700],
                confidence=max(0.0, min(1.0, confidence - 0.02)),
                domain=domain,
                tags=["literature", "paper_sentence", "granular_evidence"],
            )
        )
    return items


def _select_evidence_sentences(abstract: str) -> list[str]:
    sentences = [_clean_sentence(item) for item in re.split(r"(?<=[.!?])\s+", abstract)]
    candidates = [item for item in sentences if 60 <= len(item) <= 420]
    if not candidates:
        return []
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(candidates):
        lower = sentence.lower()
        score = sum(1 for keyword in _EVIDENCE_KEYWORDS if keyword in lower)
        if any(value in sentence for value in [" S/cm", "mA cm", "mAh cm", " eV", "%", ">"]):
            score += 2
        if score > 0:
            scored.append((score, -index, sentence))
    scored.sort(reverse=True)
    selected: list[str] = []
    seen: set[str] = set()
    for _, _, sentence in scored:
        key = sentence.lower()
        if key in seen:
            continue
        selected.append(sentence)
        seen.add(key)
        if len(selected) >= 3:
            break
    return selected


def _clean_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_EVIDENCE_KEYWORDS = {
    "activation",
    "barrier",
    "capacity",
    "conductivity",
    "degradation",
    "density",
    "dendrite",
    "electrochemical",
    "energy",
    "interface",
    "interfacial",
    "ionic",
    "li ",
    "lithium",
    "migration",
    "phase",
    "pressure",
    "solid electrolyte",
    "stability",
    "stable",
    "transport",
    "volume",
}
