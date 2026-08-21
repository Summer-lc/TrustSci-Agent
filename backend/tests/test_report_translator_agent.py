import pytest

from app.agents.report_translator_agent import ReportTranslatorAgent
from app.agents.report_writer_agent import ReportWriterAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model")


@pytest.mark.asyncio
async def test_report_translator_translates_final_english_report_field_by_field() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )
    paper = Paper(
        paper_id="p1",
        title="Verified solid electrolyte paper",
        verification_status="verified",
        report_eligible=True,
    )
    hypothesis = Hypothesis(
        hypothesis_id="H1",
        statement="Controlled slow cooling may improve Li7-xPS6-xClx interface stability.",
        rationale="A bounded mechanism hypothesis.",
        supporting_evidence=["ev_001"],
        novelty_claim="A testable cooling-rate hypothesis.",
        verification_path="Run EIS, XRD, and microscopy validation.",
    )
    report = ReportWriterAgent().run(
        run,
        hypothesis,
        ExperimentPlan(
            datasets=["planned characterization data"],
            source="verified literature and planned experiments",
            target="chlorine concentration and stability metrics",
            baselines=["standard cooling"],
            metrics=["ionic conductivity", "interface resistance"],
            experiment_steps=["synthesize samples", "measure EIS"],
            expected_results="Slow cooling may improve interfacial stability.",
            failure_modes=["phase impurity"],
        ),
        [
            EvidenceItem(
                evidence_id="ev_001",
                paper_id="p1",
                claim="Solid electrolyte evidence links structure and stability.",
                source_title="Verified solid electrolyte paper",
                quote_or_summary="Verified evidence summary.",
                verified=True,
                eligible_for_report=True,
            )
        ],
        [paper],
        [],
        [],
        None,
    )
    assert report.english_report is not None
    assert report.chinese_report is None

    llm = FakeLLM(
        {
            "chinese_report": {
                "paper_title": "受控慢冷速率对固态电解质界面稳定性的证据驱动验证",
                "paper_abstract": "本报告忠实翻译最终英文报告，并保留待验证状态。",
                "problem_statement": "研究问题是验证慢冷速率与界面稳定性之间的关系。",
                "rationale": "证据支持结构与稳定性相关，假设仍需验证。",
                "technical_details": "保留 EIS、XRD、显微表征和统计分析。",
                "datasets": {"source": "已核验文献和计划实验。", "target": "氯浓度和稳定性指标。"},
                "methods": "通过 EIS、XRD 和显微表征验证英文报告中的假设。",
                "experiments": {
                    "baselines": "标准冷却基线。",
                    "metrics": "离子电导率和界面电阻。",
                    "design": "合成样品并测量 EIS。",
                },
                "results": {
                    "executed_results": "尚无已完成科学结论。",
                    "expected_validation_outcomes": "慢冷可能改善界面稳定性，但仍需验证。",
                },
                "limitations_and_risk_controls": "不得把预期结果写成已完成发现。",
            }
        }
    )

    translated = await ReportTranslatorAgent(llm).arun(run, report)

    assert translated.english_report == report.english_report
    assert translated.chinese_report is not None
    assert translated.chinese_report.references == report.english_report.references
    assert "慢冷" in translated.chinese_report.paper_title
    assert llm.requests
    assert "english_report" in llm.requests[0].user
    assert llm.requests[0].agent == "report_translator"


def test_report_translator_fallback_marks_chinese_as_pending_translation() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Translate fallback.",
        constraints=ResearchConstraints(max_papers=1),
    )
    report = ReportWriterAgent().run(
        run,
        None,
        ExperimentPlan(
            datasets=["planned data"],
            source="source",
            target="target",
            baselines=["baseline"],
            metrics=["metric"],
            experiment_steps=["step"],
            expected_results="expected",
            failure_modes=["risk"],
        ),
        [],
        [],
        [],
        [],
        None,
    )

    translated = ReportTranslatorAgent().run(run, report)

    assert translated.english_report is not None
    assert translated.chinese_report is not None
    assert "待人工确认的中文翻译来源" in translated.chinese_report.paper_abstract
