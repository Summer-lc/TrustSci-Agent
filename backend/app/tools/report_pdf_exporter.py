from html import escape
from pathlib import Path
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


FONT_NAME = "STSong-Light"
LATIN_FONT_NAME = "Helvetica"
CODE_FONT_NAME = "Courier"
ASCII_RUN = re.compile(r"[\x20-\x7e]+")


def export_markdown_pdf(markdown_text: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _register_font()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=output_path.stem,
    )
    styles = _styles()
    flowables = []
    in_code_block = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not line:
            flowables.append(Spacer(1, 4))
            continue
        if in_code_block:
            flowables.append(Paragraph(_rich_text(line, CODE_FONT_NAME), styles["Code"]))
            continue
        if line.startswith("# "):
            flowables.append(Paragraph(_rich_text(line[2:]), styles["Title"]))
            flowables.append(Spacer(1, 8))
        elif line.startswith("## "):
            flowables.append(Paragraph(_rich_text(line[3:]), styles["Heading2"]))
            flowables.append(Spacer(1, 5))
        elif line.startswith("### "):
            flowables.append(Paragraph(_rich_text(line[4:]), styles["Heading3"]))
            flowables.append(Spacer(1, 3))
        elif line.startswith("- "):
            flowables.append(Paragraph(_rich_text(f"- {line[2:]}"), styles["Bullet"]))
        else:
            flowables.append(Paragraph(_rich_text(line), styles["Body"]))

    doc.build(flowables or [Paragraph("Empty report", styles["Body"])])
    return output_path


def _register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "TrustSciTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=16,
            leading=21,
            spaceAfter=8,
        ),
        "Heading2": ParagraphStyle(
            "TrustSciHeading2",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "Heading3": ParagraphStyle(
            "TrustSciHeading3",
            parent=base["Heading3"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=14,
            spaceBefore=5,
            spaceAfter=3,
            textColor="#27364a",
        ),
        "Body": ParagraphStyle(
            "TrustSciBody",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
            spaceAfter=4,
        ),
        "Bullet": ParagraphStyle(
            "TrustSciBullet",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
            leftIndent=8,
            firstLineIndent=0,
            spaceAfter=3,
        ),
        "Code": ParagraphStyle(
            "TrustSciCode",
            parent=base["Code"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            leftIndent=6,
            spaceAfter=2,
        ),
    }


def _safe(text: str) -> str:
    return escape(text).replace("  ", "&nbsp;&nbsp;")


def _rich_text(text: str, latin_font: str = LATIN_FONT_NAME) -> str:
    parts: list[str] = []
    cursor = 0
    for match in ASCII_RUN.finditer(text):
        if match.start() > cursor:
            parts.append(_safe(text[cursor:match.start()]))
        parts.append(f'<font name="{latin_font}">{_safe(match.group())}</font>')
        cursor = match.end()
    if cursor < len(text):
        parts.append(_safe(text[cursor:]))
    return "".join(parts)
