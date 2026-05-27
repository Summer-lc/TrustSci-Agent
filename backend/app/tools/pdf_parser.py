from pathlib import Path

from pypdf import PdfReader


def parse_pdf_text(path: Path, max_pages: int = 12) -> list[dict[str, str | int]]:
    reader = PdfReader(str(path))
    pages: list[dict[str, str | int]] = []
    for index, page in enumerate(reader.pages[:max_pages], start=1):
        pages.append({"page": index, "text": page.extract_text() or ""})
    return pages

