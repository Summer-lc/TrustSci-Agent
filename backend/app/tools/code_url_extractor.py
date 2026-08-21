"""Mine github.com/owner/repo URLs from paper abstracts and PDF full text.

Two entry points:
- ``extract_code_urls`` (sync): abstract-only regex pass over every paper.
- ``extract_code_urls_async``: abstract pass + async PDF download/parse for
  the top-N papers that still lack a code_url and have a pdf_url.

Both set ``paper.code_url`` in place and return the same list.
No exception escapes — PDF download/parse failures are silently skipped.
"""
import re
from pathlib import Path

import httpx

from app.schemas.paper import Paper
from app.tools.pdf_parser import parse_pdf_text

# Matches github.com/owner/repo in running text, stopping at common
# delimiters (paren, slash, quote, angle bracket, whitespace, .git suffix).
GITHUB_RE = re.compile(
    r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:[)/\s'\"<>,;:!?\.]|$)"
)
_MAX_PDF_DOWNLOADS = 5


def extract_code_urls(
    papers: list[Paper],
    *,
    max_pdf: int = _MAX_PDF_DOWNLOADS,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[Paper]:
    """Sync abstract-only mining. Sets paper.code_url in place.

    PDF mining requires the async variant (``extract_code_urls_async``).
    """
    for paper in papers:
        if paper.code_url:
            continue
        url = _mine_text(paper.abstract or "")
        if url:
            paper.code_url = url
            paper.code_url_source = "abstract"
    return papers


async def extract_code_urls_async(
    papers: list[Paper],
    *,
    max_pdf: int = _MAX_PDF_DOWNLOADS,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[Paper]:
    """Abstract mining (sync) + PDF full-text mining (async, top-N with pdf_url)."""
    extract_code_urls(papers)  # abstract pass
    pdf_candidates = [p for p in papers if not p.code_url and p.pdf_url][:max_pdf]
    for paper in pdf_candidates:
        try:
            text = await _download_pdf_text(paper.pdf_url, transport=transport)
            url = _mine_text(text)
            if url:
                paper.code_url = url
                paper.code_url_source = "pdf"
        except Exception:
            continue
    return papers


def _mine_text(text: str) -> str | None:
    """Return the first github.com/owner/repo URL found in *text*, or None."""
    if not text:
        return None
    match = GITHUB_RE.search(text)
    if not match:
        return None
    return f"https://github.com/{match.group(1)}"


async def _download_pdf_text(
    pdf_url: str | None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    """Download a PDF, parse its pages, and return concatenated text."""
    if not pdf_url:
        return ""
    async with httpx.AsyncClient(
        timeout=30, transport=transport, follow_redirects=True
    ) as client:
        resp = await client.get(pdf_url, headers={"User-Agent": "TrustSci-Agent/0.1"})
        resp.raise_for_status()
        content = resp.content
    # Write to a temp path and parse with pypdf.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        pages = parse_pdf_text(tmp_path, max_pages=12)
        return "\n".join(str(p.get("text") or "") for p in pages)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
