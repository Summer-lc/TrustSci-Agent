from pathlib import Path

from pypdf import PdfReader

from app.tools.report_pdf_exporter import export_markdown_pdf


def _extract(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def test_exported_pdf_preserves_chinese_for_text_extraction(tmp_path: Path) -> None:
    output = tmp_path / "unicode-report.pdf"

    export_markdown_pdf(
        "# 中文报告\n\n可信人工智能科学家：真实数据与可验证假设。",
        output,
    )

    extracted = _extract(output)
    assert "中文报告" in extracted
    assert "真实数据与可验证假设" in extracted


def test_exported_pdf_parses_level_three_headings(tmp_path: Path) -> None:
    output = tmp_path / "heading-report.pdf"

    export_markdown_pdf(
        "# Research Report\n\n### 8.1 Baselines\nA reproducible baseline.",
        output,
    )

    extracted = _extract(output)
    assert "8.1 Baselines" in extracted
    assert "###" not in extracted


def test_exported_pdf_uses_latin_font_for_english_runs(tmp_path: Path) -> None:
    output = tmp_path / "mixed-font-report.pdf"

    export_markdown_pdf(
        "# 中文报告\n\n真实数据 accuracy = 0.91，宏平均 F1 = 0.88。",
        output,
    )

    page = PdfReader(str(output)).pages[0]
    fonts = page["/Resources"]["/Font"]
    helvetica_keys = [
        key
        for key, value in fonts.items()
        if str(value.get_object().get("/BaseFont")) == "/Helvetica"
    ]
    assert len(helvetica_keys) == 1
    content = page.get_contents().get_data()
    assert f"{helvetica_keys[0]} 9 Tf".encode("ascii") in content
