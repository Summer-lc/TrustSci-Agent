from pathlib import Path

from pypdf import PdfReader

from app.schemas.evidence import PaperChunk


def parse_pdf_text(path: Path, max_pages: int = 12) -> list[dict[str, str | int]]:
    reader = PdfReader(str(path))
    pages: list[dict[str, str | int]] = []
    for index, page in enumerate(reader.pages[:max_pages], start=1):
        pages.append({"page": index, "text": page.extract_text() or ""})
    return pages


def parse_pdf_chunks(
    path: Path,
    *,
    paper_id: str | None = None,
    source_title: str = "",
    source_url: str | None = None,
    max_pages: int = 12,
    min_chars: int = 80,
) -> list[PaperChunk]:
    chunks: list[PaperChunk] = []
    for page in parse_pdf_text(path, max_pages=max_pages):
        text = _clean_text(str(page["text"]))
        if len(text) < min_chars:
            continue
        page_number = int(page["page"])
        chunks.append(
            PaperChunk(
                chunk_id=f"{paper_id or path.stem}:p{page_number}",
                paper_id=paper_id,
                source_title=source_title or path.stem,
                source_path=str(path),
                source_url=source_url,
                page=page_number,
                section=_guess_section(text),
                text=text[:2400],
                token_estimate=max(1, len(text) // 4),
            )
        )
    return chunks


def _guess_section(text: str) -> str | None:
    lowered = text[:500].lower()
    for section in ("abstract", "introduction", "methods", "results", "discussion", "conclusion"):
        if section in lowered:
            return section
    return None


def _clean_text(value: str) -> str:
    return " ".join(value.split())
