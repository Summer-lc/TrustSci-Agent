import json
from typing import Any

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.report import FormalResearchReport, ReportDatasets, ReportExperiments, ReportResults, ResearchReport
from app.schemas.run import ResearchRun


SYSTEM_PROMPT = """You are the Report Translator Agent for TrustSci-Agent.
Translate the final audited English formal scientific report into Chinese.
Return JSON only. Do not add, remove, weaken, strengthen, or reinterpret any scientific claim.

Rules:
- Translate field by field from english_report into chinese_report.
- Preserve all evidence IDs, citation markers, chemical formulas, units, dataset names, model names, metrics, and section structure.
- Keep executed results separate from expected validation outcomes.
- Keep uncertainty, limitations, and "to validate" status unchanged in meaning.
- Do not introduce new references, datasets, methods, claims, or results.

Required JSON shape:
{
  "chinese_report": {
    "paper_title": "",
    "paper_abstract": "",
    "problem_statement": "",
    "rationale": "",
    "technical_details": "",
    "datasets": {"source": "", "target": ""},
    "methods": "",
    "experiments": {"baselines": "", "metrics": "", "design": ""},
    "results": {"executed_results": "", "expected_validation_outcomes": ""},
    "limitations_and_risk_controls": ""
  }
}
"""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)


class ReportTranslatorAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, run: ResearchRun, report: ResearchReport) -> ResearchReport:
        fallback = self.run(run, report)
        if self.llm is None or report.english_report is None:
            return fallback
        request_fallback = {"chinese_report": _formal_payload(fallback.chinese_report)}
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=request_fallback, run_id=run.run_id, agent="report_translator")
            | FallbackParser(lambda content: _normalize_translation(content, fallback), fallback)
        )
        return await chain.ainvoke({"user_prompt": _build_translation_prompt(run, report.english_report)})

    def run(self, run: ResearchRun, report: ResearchReport) -> ResearchReport:
        translated = report.model_copy(deep=True)
        if translated.english_report is None:
            return translated
        translated.chinese_report = _fallback_translation(translated.english_report)
        return translated


def _build_translation_prompt(run: ResearchRun, english_report: FormalResearchReport) -> str:
    payload = {
        "run": {
            "run_id": run.run_id,
            "domain": run.domain,
            "question": run.question,
        },
        "english_report": _formal_payload(english_report),
        "instructions": [
            "Translate, do not rewrite.",
            "Preserve section-level meaning and all technical identifiers.",
            "Do not add unsupported novelty, completed results, or extra citations.",
            "Return only chinese_report.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_translation(content: object, fallback: ResearchReport) -> ResearchReport:
    if not isinstance(content, dict):
        return fallback
    report = _formal_from_payload(content.get("chinese_report"), fallback.english_report.references if fallback.english_report else [])
    if report is None:
        return fallback
    translated = fallback.model_copy(deep=True)
    translated.chinese_report = report
    return translated


def _formal_from_payload(payload: object, references: list) -> FormalResearchReport | None:
    if not isinstance(payload, dict):
        return None
    try:
        datasets = payload.get("datasets") if isinstance(payload.get("datasets"), dict) else {}
        experiments = payload.get("experiments") if isinstance(payload.get("experiments"), dict) else {}
        results = payload.get("results") if isinstance(payload.get("results"), dict) else {}
        report = FormalResearchReport(
            paper_title=_clean(payload.get("paper_title")),
            paper_abstract=_clean(payload.get("paper_abstract")),
            problem_statement=_clean(payload.get("problem_statement")),
            rationale=_clean(payload.get("rationale")),
            technical_details=_clean(payload.get("technical_details")),
            datasets=ReportDatasets(source=_clean(datasets.get("source")), target=_clean(datasets.get("target"))),
            methods=_clean(payload.get("methods")),
            experiments=ReportExperiments(
                baselines=_clean(experiments.get("baselines")),
                metrics=_clean(experiments.get("metrics")),
                design=_clean(experiments.get("design")),
            ),
            results=ReportResults(
                executed_results=_clean(results.get("executed_results")),
                expected_validation_outcomes=_clean(results.get("expected_validation_outcomes")),
            ),
            limitations_and_risk_controls=_clean(payload.get("limitations_and_risk_controls")),
            references=references,
        )
    except Exception:
        return None
    required = [
        report.paper_title,
        report.paper_abstract,
        report.problem_statement,
        report.rationale,
        report.technical_details,
        report.datasets.source,
        report.datasets.target,
        report.methods,
        report.experiments.baselines,
        report.experiments.metrics,
        report.experiments.design,
        report.results.executed_results,
        report.results.expected_validation_outcomes,
        report.limitations_and_risk_controls,
    ]
    return report if all(required) else None


def _fallback_translation(english: FormalResearchReport) -> FormalResearchReport:
    return FormalResearchReport(
        paper_title=f"待翻译标题：{english.paper_title}",
        paper_abstract=f"待人工确认的中文翻译来源：{english.paper_abstract}",
        problem_statement=f"待人工确认的中文翻译来源：{english.problem_statement}",
        rationale=f"待人工确认的中文翻译来源：{english.rationale}",
        technical_details=f"待人工确认的中文翻译来源：{english.technical_details}",
        datasets=ReportDatasets(
            source=f"待人工确认的中文翻译来源：{english.datasets.source}",
            target=f"待人工确认的中文翻译来源：{english.datasets.target}",
        ),
        methods=f"待人工确认的中文翻译来源：{english.methods}",
        experiments=ReportExperiments(
            baselines=f"待人工确认的中文翻译来源：{english.experiments.baselines}",
            metrics=f"待人工确认的中文翻译来源：{english.experiments.metrics}",
            design=f"待人工确认的中文翻译来源：{english.experiments.design}",
        ),
        results=ReportResults(
            executed_results=f"待人工确认的中文翻译来源：{english.results.executed_results}",
            expected_validation_outcomes=f"待人工确认的中文翻译来源：{english.results.expected_validation_outcomes}",
        ),
        limitations_and_risk_controls=f"待人工确认的中文翻译来源：{english.limitations_and_risk_controls}",
        references=english.references,
    )


def _formal_payload(report: FormalResearchReport | None) -> dict[str, Any]:
    if report is None:
        return {}
    payload = report.model_dump()
    payload.pop("references", None)
    return payload


def _clean(value: object) -> str:
    return str(value or "").strip()
