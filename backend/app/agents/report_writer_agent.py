import json
from typing import Any

from app.evidence.audit import build_citation_audit
from app.evidence.selection import reportable_evidence, reportable_knowledge_cards, reportable_papers
from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.report import (
    FormalResearchReport,
    ReportDatasets,
    ReportExperiments,
    ReportResults,
    ResearchReport,
    SystemProvenance,
)
from app.schemas.run import ResearchRun


SYSTEM_PROMPT = """You are the Report Writer Agent for TrustSci-Agent.
Write a competition-format research plan from verified evidence, selected hypothesis, experiment plan, and data profiles.
Return JSON only. You may organize language and reasoning, but you must not invent references, citations, datasets, or completed experimental results.
Every key paragraph must explicitly separate:
- Evidence-backed: facts directly supported by supplied evidence ids.
- Inference: bounded reasoning from the evidence, not established fact.
- To validate: proposed hypotheses, experiments, expected outcomes, or unsupported audit-sensitive claims.
Write the report bilingually. For every narrative field and list item, write clear English first, then add a faithful Chinese translation prefixed with "中文翻译：".

Required JSON shape:
{
  "report": {
    "problem_statement": "specific limitation, with evidence insufficiency notes where needed",
    "rationale": "reasoning chain grounded in evidence ids and selected hypothesis",
    "technical_details": ["technical stack or method detail"],
    "datasets": ["datasets from experiment plan or to be collected"],
    "source": "source data basis",
    "target": "target data/features",
    "paper_title": "academic title",
    "paper_abstract": "background, method, expected validation",
    "methods": ["implementation step"],
    "experiments": {
      "datasets": [],
      "source": "",
      "target": "",
      "baselines": [],
      "metrics": [],
      "experiment_steps": [],
      "expected_results": "",
      "failure_modes": []
    },
    "results": "bounded feasibility, formula, toy result card, or verification-pending statement"
  }
}
References are not accepted from the model. The backend will attach verified references only.
"""


SYSTEM_PROMPT = """You are the Report Writer Agent for TrustSci-Agent.
Write one formal English scientific report from verified evidence, selected hypothesis, experiment plan, and data profiles.
Return JSON only. You may organize language and reasoning, but you must not invent references, citations, datasets, or completed experimental results.

The English report is the only scientific source of truth. A separate translation step will translate the final audited English report into Chinese after claim verification and revision.
Methods must describe scientific validation methods for the research gap, such as EIS, XRD, SEM/EBSD, DFT/MD, equivalent-circuit fitting, defect analysis, sintering controls, regression, ablation, and uncertainty analysis.
Do not put agent workflow, literature_router, evidence_ledger, critic_review, workflow_plan, or report_export into scientific Methods. Those belong only in system_provenance.
Separate executed results from expected validation outcomes.

Required JSON shape:
{
  "report": {
    "english_report": {
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
}
References are not accepted from the model. The backend will attach verified references only.
"""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)


class ReportWriterAgent:
    """Deterministic report writer for the MVP workflow.

    This mock writer assembles a complete contest-format research plan from
    structured agent outputs. It intentionally does not create new citations.
    """

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        run: ResearchRun,
        hypothesis: Hypothesis | None,
        experiment: ExperimentPlan,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        knowledge_cards: list[KnowledgeCard],
        data_profiles: list[DatasetProfile],
        baseline_result_card: BaselineResultCard | None,
    ) -> ResearchReport:
        fallback = self.run(
            run,
            hypothesis,
            experiment,
            evidence,
            papers,
            knowledge_cards,
            data_profiles,
            baseline_result_card,
        )
        if self.llm is None:
            return fallback
        request_fallback = {"report": _report_payload(fallback)}
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=request_fallback, run_id=run.run_id, agent="report_writer")
            | FallbackParser(
                lambda content: _normalize_qwen_report(
                    content,
                    fallback,
                    run,
                    experiment,
                    evidence,
                    papers,
                    knowledge_cards,
                    data_profiles,
                    baseline_result_card,
                ),
                fallback,
            )
        )
        return await chain.ainvoke(
            {
                "user_prompt": _build_report_prompt(
                    run,
                    hypothesis,
                    experiment,
                    evidence,
                    papers,
                    knowledge_cards,
                    data_profiles,
                    baseline_result_card,
                )
            }
        )

    def run(
        self,
        run: ResearchRun,
        hypothesis: Hypothesis | None,
        experiment: ExperimentPlan,
        evidence: list[EvidenceItem],
        papers: list[Paper],
        knowledge_cards: list[KnowledgeCard],
        data_profiles: list[DatasetProfile],
        baseline_result_card: BaselineResultCard | None,
    ) -> ResearchReport:
        verified_papers = reportable_papers(run, papers, evidence)
        verified_evidence = reportable_evidence(run, evidence)
        evidence_count = len(verified_evidence)
        statement = hypothesis.revised_statement or hypothesis.statement if hypothesis else run.question
        title = _paper_title(run, hypothesis)
        abstract = _paper_abstract(run, evidence_count, verified_papers, baseline_result_card)

        report = ResearchReport(
            problem_statement=_problem_statement(run, verified_papers, verified_evidence),
            rationale=_rationale(statement, hypothesis, verified_evidence),
            technical_details=_technical_details(),
            datasets=experiment.datasets,
            source=experiment.source,
            target=experiment.target,
            paper_title=title,
            paper_abstract=abstract,
            methods=_methods(run, verified_evidence, data_profiles, baseline_result_card),
            experiments=experiment,
            results=_results_text(baseline_result_card, len(verified_papers), evidence_count),
            data_profiles=data_profiles,
            baseline_result_card=baseline_result_card,
            knowledge_cards=reportable_knowledge_cards(run, knowledge_cards),
            references=verified_papers,
            citation_audit_log=build_citation_audit(papers),
        )
        return attach_formal_report_sections(
            _enforce_report_layers(report),
            run,
            hypothesis,
            experiment,
            evidence,
            papers,
            data_profiles,
            baseline_result_card,
        )


def _build_report_prompt(
    run: ResearchRun,
    hypothesis: Hypothesis | None,
    experiment: ExperimentPlan,
    evidence: list[EvidenceItem],
    papers: list[Paper],
    knowledge_cards: list[KnowledgeCard],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> str:
    verified_papers = reportable_papers(run, papers, evidence)
    verified_evidence = reportable_evidence(run, evidence)
    payload = {
        "run": {
            "run_id": run.run_id,
            "domain": run.domain,
            "question": run.question,
            "evidence_frozen": run.evidence_frozen,
            "citation_frozen": run.citation_frozen,
            "frozen_evidence_ids": run.frozen_evidence_ids,
            "frozen_paper_ids": run.frozen_paper_ids,
        },
        "verified_references": [
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "year": paper.year,
                "doi": paper.doi,
                "source_url": paper.source_url,
            }
            for paper in verified_papers
        ],
        "verified_evidence": [
            {
                "evidence_id": item.evidence_id,
                "paper_id": item.paper_id,
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "source_title": item.source_title,
            }
            for item in verified_evidence
        ],
        "selected_hypothesis": hypothesis.model_dump(mode="json") if hypothesis else None,
        "experiment_plan": experiment.model_dump(mode="json"),
        "knowledge_cards": [card.model_dump(mode="json") for card in reportable_knowledge_cards(run, knowledge_cards)],
        "data_profiles": [profile.model_dump(mode="json") for profile in data_profiles],
        "baseline_result_card": baseline_result_card.model_dump(mode="json") if baseline_result_card else None,
        "instructions": [
            "Return only english_report. Do not return chinese_report.",
            "Do not include Chinese translation labels or Chinese paragraphs.",
            "Make Methods scientific validation methods, not agent workflow.",
            "Put agent workflow, citation audit, and evidence ledger only in system_provenance.",
            "If evidence is insufficient, lower confidence and write verification pending.",
            "Do not output references; they are attached by backend from verified_references only.",
            "Do not describe expected results as completed experiments.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_qwen_report(
    content: object,
    fallback: ResearchReport,
    run: ResearchRun,
    experiment: ExperimentPlan,
    evidence: list[EvidenceItem],
    papers: list[Paper],
    knowledge_cards: list[KnowledgeCard],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> ResearchReport:
    if not isinstance(content, dict) or not isinstance(content.get("report"), dict):
        return fallback
    raw = content["report"]
    try:
        raw_experiment = raw.get("experiments")
        qwen_experiment = experiment
        if isinstance(raw_experiment, dict):
            qwen_experiment = ExperimentPlan(
                datasets=_string_list(raw_experiment.get("datasets")) or experiment.datasets,
                source=_clean(raw_experiment.get("source")) or experiment.source,
                target=_clean(raw_experiment.get("target")) or experiment.target,
                baselines=_string_list(raw_experiment.get("baselines")) or experiment.baselines,
                metrics=_string_list(raw_experiment.get("metrics")) or experiment.metrics,
                experiment_steps=_string_list(raw_experiment.get("experiment_steps")) or experiment.experiment_steps,
                expected_results=_clean(raw_experiment.get("expected_results")) or experiment.expected_results,
                failure_modes=_string_list(raw_experiment.get("failure_modes")) or experiment.failure_modes,
            )
        report = ResearchReport(
            problem_statement=_clean(raw.get("problem_statement")) or fallback.problem_statement,
            rationale=_clean(raw.get("rationale")) or fallback.rationale,
            technical_details=_string_list(raw.get("technical_details")) or fallback.technical_details,
            datasets=experiment.datasets,
            source=_clean(raw.get("source")) or experiment.source,
            target=_clean(raw.get("target")) or experiment.target,
            paper_title=_clean(raw.get("paper_title")) or fallback.paper_title,
            paper_abstract=_clean(raw.get("paper_abstract")) or fallback.paper_abstract,
            methods=_string_list(raw.get("methods")) or fallback.methods,
            experiments=qwen_experiment,
            results=_clean(raw.get("results")) or fallback.results,
            data_profiles=data_profiles,
            baseline_result_card=baseline_result_card,
            knowledge_cards=reportable_knowledge_cards(run, knowledge_cards),
            references=reportable_papers(run, papers, evidence),
            citation_audit_log=build_citation_audit(papers),
        )
        return attach_formal_report_sections(
            _enforce_report_layers(report),
            run,
            _selected_hypothesis_from_run(run),
            qwen_experiment,
            evidence,
            papers,
            data_profiles,
            baseline_result_card,
            raw=raw,
        )
    except Exception:
        return fallback


def _report_payload(report: ResearchReport) -> dict:
    payload = report.model_dump()
    payload.pop("chinese_report", None)
    payload.pop("system_provenance", None)
    payload.pop("references", None)
    payload.pop("citation_audit_log", None)
    payload.pop("knowledge_cards", None)
    payload.pop("data_profiles", None)
    payload.pop("baseline_result_card", None)
    return payload


def attach_formal_report_sections(
    report: ResearchReport,
    run: ResearchRun,
    hypothesis: Hypothesis | None,
    experiment: ExperimentPlan,
    evidence: list[EvidenceItem],
    papers: list[Paper],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
    *,
    raw: dict | None = None,
) -> ResearchReport:
    report = report.model_copy(deep=True)
    verified_papers = reportable_papers(run, papers, evidence)
    verified_evidence = reportable_evidence(run, evidence)
    report.references = verified_papers
    report.citation_audit_log = build_citation_audit(papers)

    english_from_model = _formal_from_raw(raw, "english_report", verified_papers) if raw else None
    existing_english = _formal_with_references(report.english_report, verified_papers)
    existing_chinese = _formal_with_references(report.chinese_report, verified_papers)
    if existing_chinese and _looks_like_mixed_chinese_report(existing_chinese):
        existing_chinese = None

    if english_from_model:
        english_report = english_from_model
    elif existing_english:
        english_report = existing_english
    else:
        english_report = _english_formal_report(
            run,
            hypothesis,
            experiment,
            verified_evidence,
            verified_papers,
            data_profiles,
            baseline_result_card,
        )

    report.english_report = _append_formal_claim_audit_note(english_report, run, language="en")
    report.chinese_report = _append_formal_claim_audit_note(existing_chinese, run, language="zh") if existing_chinese else None
    report.system_provenance = _system_provenance(run, evidence, papers, report.citation_audit_log)
    return report


def _enforce_report_layers(report: ResearchReport) -> ResearchReport:
    report = report.model_copy(deep=True)
    report.problem_statement = _layered_text(
        report.problem_statement,
        inference="The limitation is treated as a bounded synthesis across the verified evidence, not a completed discovery.",
        to_validate="Any mechanism not directly quoted from evidence remains a validation target.",
    )
    report.rationale = _layered_text(
        report.rationale,
        inference="The novelty claim is a hypothesis derived from the evidence chain and reviewer critique.",
        to_validate="The selected hypothesis must be tested by the experiment plan before being stated as a finding.",
    )
    report.paper_abstract = _layered_text(
        report.paper_abstract,
        inference="The abstract frames the proposed contribution as an evidence-grounded research plan.",
        to_validate="Expected results and experimental outcomes remain verification pending.",
    )
    report.results = _layered_text(
        report.results,
        inference="Feasibility is bounded by the available result card, data profiles, and verified evidence coverage.",
        to_validate="Full scientific claims require the proposed experiments or benchmark runs.",
    )
    report.technical_details = _label_items(report.technical_details, "Evidence-backed")
    report.methods = _label_items(report.methods, "To validate")
    report.experiments.experiment_steps = _label_items(report.experiments.experiment_steps, "To validate")
    report.experiments.expected_results = _prefix_label(report.experiments.expected_results, "To validate")
    return report


def _layered_text(text: str, *, inference: str, to_validate: str) -> str:
    text = _clean(text)
    if _has_layer_labels(text):
        return text
    return (
        f"Evidence-backed: {text}\n"
        f"Inference: {inference}\n"
        f"To validate: {to_validate}"
    )


def _label_items(items: list[str], label: str) -> list[str]:
    return [_prefix_label(item, label) for item in items]


def _prefix_label(text: str, label: str) -> str:
    text = _clean(text)
    if not text or _has_any_layer_label(text):
        return text
    return f"{label}: {text}"


def _has_layer_labels(text: str) -> bool:
    lowered = text.lower()
    return all(label in lowered for label in ["evidence-backed:", "inference:", "to validate:"])


def _has_any_layer_label(text: str) -> bool:
    lowered = text.lower()
    return any(label in lowered for label in ["evidence-backed:", "inference:", "to validate:"])


def _formal_from_raw(raw: dict | None, key: str, references: list[Paper]) -> FormalResearchReport | None:
    if not isinstance(raw, dict):
        return None
    payload = raw.get(key)
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
            datasets=ReportDatasets(
                source=_clean(datasets.get("source")),
                target=_clean(datasets.get("target")),
            ),
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
    if not all(required):
        return None
    if _looks_like_agent_workflow(report.methods):
        return None
    if key == "chinese_report" and _looks_like_mixed_chinese_report(report):
        return None
    return report


def _formal_with_references(
    report: FormalResearchReport | None,
    references: list[Paper],
) -> FormalResearchReport | None:
    if report is None:
        return None
    copied = report.model_copy(deep=True)
    copied.references = references
    return copied


def _append_formal_claim_audit_note(
    report: FormalResearchReport,
    run: ResearchRun,
    *,
    language: str,
) -> FormalResearchReport:
    if not run.claim_audit:
        return report
    unsupported = run.claim_audit.unsupported
    weak = run.claim_audit.weakly_supported
    if not unsupported and not weak:
        return report

    copied = report.model_copy(deep=True)
    if language == "zh":
        note = f"论断审计提示：{unsupported} 条缺少支持、{weak} 条弱支持的论断只能作为局限性、推断或待验证目标。"
        marker = "论断审计提示"
    else:
        note = (
            f"Claim audit note: {unsupported} unsupported claims and {weak} weakly supported claims "
            "must remain limitations, bounded inferences, or validation targets."
        )
        marker = "Claim audit note"
    if marker not in copied.limitations_and_risk_controls:
        copied.limitations_and_risk_controls = f"{copied.limitations_and_risk_controls} {note}".strip()
    return copied


def _english_formal_report(
    run: ResearchRun,
    hypothesis: Hypothesis | None,
    experiment: ExperimentPlan,
    evidence: list[EvidenceItem],
    references: list[Paper],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> FormalResearchReport:
    statement = _hypothesis_statement(run, hypothesis)
    evidence_summary = _evidence_summary_clean(evidence)
    materials_note = _materials_project_note(data_profiles)
    return FormalResearchReport(
        paper_title=_english_title(run, hypothesis),
        paper_abstract=(
            f"This report proposes a verifiable scientific study around the selected hypothesis: {statement}. "
            f"The proposal is grounded in {len(references)} verified references and {len(evidence)} report-eligible evidence items. "
            "It separates preliminary executed feasibility results from validation outcomes that still require laboratory or computational experiments. "
            f"{_executed_result_sentence(baseline_result_card)} "
            "The planned validation combines impedance spectroscopy, structural and microstructural characterization, defect analysis, and computational or statistical tests."
        ),
        problem_statement=(
            f"The current research gap is not simply that {run.domain} is important; it is that the verified evidence supports a bounded hypothesis but does not yet quantify the relative contribution of transport bottlenecks, microstructure, and defect descriptors. "
            f"Evidence basis: {evidence_summary}. The mechanism remains a hypothesis until the proposed measurements and calculations are completed."
        ),
        rationale=(
            f"Evidence-backed facts: {evidence_summary}. "
            f"Inference: these facts make the selected hypothesis plausible because they connect source-grounded material behavior with measurable validation targets. "
            f"Hypothesis to validate: {statement}. The novelty is the explicit decomposition of the scientific gap into measurable structural, electrochemical, and computational factors instead of presenting an unverified mechanism as a conclusion."
        ),
        technical_details=(
            "The required scientific toolkit includes electrochemical impedance spectroscopy (EIS) with equivalent-circuit fitting, XRD phase analysis, SEM/EBSD grain-size and grain-boundary characterization, XPS/EPR/ICP-OES defect or stoichiometry descriptors, and DFT, molecular dynamics, or machine-learning interatomic potentials for migration-barrier comparison. Statistical regression, ablation analysis, and uncertainty analysis should be used to quantify which measured descriptors explain the target property."
        ),
        datasets=ReportDatasets(
            source=(
                f"Source evidence consists of verified papers, verified evidence items, citation metadata, the bundled local solid-electrolyte candidate table, Matbench metadata, and Materials Project availability status. {materials_note}"
            ),
            target=(
                "Target validation data are planned collection data, not already completed results: controlled samples across synthesis or sintering conditions, XRD phase purity, SEM/EBSD grain size and grain-boundary density, EIS bulk and grain-boundary resistance, total ionic conductivity, activation energy from temperature-dependent EIS, defect descriptors from XPS/EPR/ICP-OES, and electrochemical stability-window measurements."
            ),
        ),
        methods=_scientific_methods_en(),
        experiments=ReportExperiments(
            baselines=_join_or_default(
                experiment.baselines,
                "literature-reported conductivity, unoptimized synthesis condition, mean baseline, and simple regression baseline",
            ),
            metrics=_join_or_default(
                experiment.metrics,
                "ionic conductivity, activation energy, bulk resistance, grain-boundary resistance, phase purity, grain size, defect descriptors, stability window, MAE, and R2",
            ),
            design=(
                f"{_join_or_default(experiment.experiment_steps, 'Prepare controlled material groups, characterize structure and defects, run EIS, then compare descriptors against conductivity and resistance components.')} "
                "The hypothesis is supported only if changes in the proposed descriptors consistently explain the measured conductivity gap relative to baselines; otherwise the hypothesis should be rejected or revised."
            ),
        ),
        results=ReportResults(
            executed_results=_executed_results_text(baseline_result_card),
            expected_validation_outcomes=(
                f"{experiment.expected_results} If grain-boundary effects dominate, larger grains or lower grain-boundary density should reduce fitted grain-boundary resistance and improve total conductivity. If defect chemistry dominates, defect descriptors should correlate with EIS-derived resistance or activation-energy changes. These outcomes are expected validation targets, not completed results."
            ),
        ),
        limitations_and_risk_controls=_limitations_en(run, evidence, data_profiles),
        references=references,
    )


def _chinese_formal_report(
    run: ResearchRun,
    hypothesis: Hypothesis | None,
    experiment: ExperimentPlan,
    evidence: list[EvidenceItem],
    references: list[Paper],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> FormalResearchReport:
    statement = _hypothesis_statement_zh(run, hypothesis)
    evidence_summary = _evidence_summary_clean_zh(evidence)
    materials_note = _materials_project_note_zh(data_profiles)
    return FormalResearchReport(
        paper_title=_chinese_title(run, hypothesis),
        paper_abstract=(
            f"本报告围绕最终选定的待验证假设展开：{statement}。报告依据 {len(references)} 篇已核验参考文献和 {len(evidence)} 条可进入报告的证据项，形成一个可复核的科研验证方案。"
            "报告明确区分已经执行的初步可行性结果和仍需实验或计算验证的预期结果。"
            f"{_executed_result_sentence_zh(baseline_result_card)} "
            "后续验证将结合电化学阻抗谱、结构与微观形貌表征、缺陷分析，以及计算或统计建模。"
        ),
        problem_statement=(
            f"当前待研究问题不是笼统地说明 {run.domain} 具有重要性，而是要在已核验证据基础上，定量拆分传输瓶颈、微观结构和缺陷描述符对目标性能差距的贡献。"
            f"证据基础包括：{evidence_summary}。相关机制目前仍是待验证假设，不能被写成已经证明的结论。"
        ),
        rationale=(
            f"证据支持的事实：{evidence_summary}。"
            f"基于逻辑的推断：这些事实把材料行为、可测量变量和验证目标连接起来，因此使选定假设具备验证价值。"
            f"待验证假设：{statement}。本方案的创新点在于把科学 gap 拆解为可测量的结构、电化学和计算因素，而不是直接宣称某一机制已经成立。"
        ),
        technical_details=(
            "验证该假设需要的科研技术包括：电化学阻抗谱 EIS 及等效电路拟合、XRD 物相分析、SEM/EBSD 晶粒尺寸和晶界密度表征、XPS/EPR/ICP-OES 缺陷或化学计量描述符分析，以及 DFT、分子动力学或机器学习原子间势对迁移势垒进行比较。还需要使用统计回归、消融分析和不确定性分析，量化不同测量描述符对目标性能的解释能力。"
        ),
        datasets=ReportDatasets(
            source=(
                f"来源数据包括已核验论文、已核验证据项、引用元数据、本地固态电解质候选材料示例表、Matbench 元数据，以及 Materials Project 的可用性状态。{materials_note}"
            ),
            target=(
                "目标数据属于计划采集数据，而不是已经完成的数据：不同合成或烧结条件下的样品、XRD 物相纯度、SEM/EBSD 晶粒尺寸和晶界密度、EIS 拟合得到的体相电阻与晶界电阻、总离子电导率、变温 EIS 得到的活化能、XPS/EPR/ICP-OES 得到的缺陷描述符，以及电化学稳定窗口。"
            ),
        ),
        methods=_scientific_methods_zh(),
        experiments=ReportExperiments(
            baselines=_join_or_default_zh(
                experiment.baselines,
                "文献报道电导率、未优化合成条件、均值基线和简单回归基线",
                kind="baseline",
            ),
            metrics=_join_or_default_zh(
                experiment.metrics,
                "离子电导率、活化能、体相电阻、晶界电阻、物相纯度、晶粒尺寸、缺陷描述符、稳定窗口、MAE 和 R2",
                kind="metric",
            ),
            design=(
                f"{_experiment_design_zh(experiment)} "
                "只有当目标描述符能够稳定解释相对基线的电导率差距时，假设才得到支持；否则应拒绝或修订该假设。"
            ),
        ),
        results=ReportResults(
            executed_results=_executed_results_text_zh(baseline_result_card),
            expected_validation_outcomes=(
                f"{_expected_results_zh(experiment.expected_results)} 如果晶界效应占主导，较大晶粒或较低晶界密度应降低等效电路拟合得到的晶界电阻，并提高总电导率。"
                "如果缺陷化学占主导，缺陷描述符应与 EIS 拟合电阻或活化能变化显著相关。这些内容均属于预期验证结果，不是已经完成的实验结论。"
            ),
        ),
        limitations_and_risk_controls=_limitations_zh(run, evidence, data_profiles),
        references=references,
    )


def _system_provenance(
    run: ResearchRun,
    evidence: list[EvidenceItem],
    papers: list[Paper],
    citation_audit_log: list[str],
) -> SystemProvenance:
    claim_summary = (
        run.claim_audit.model_dump(mode="json", exclude={"items"})
        if run.claim_audit
        else {"status": "claim audit not generated yet"}
    )
    return SystemProvenance(
        agent_workflow=[
            {
                "name": step.name,
                "status": step.status,
                "summary": step.summary,
            }
            for step in run.steps
        ],
        evidence_ledger=[
            {
                "evidence_id": item.evidence_id,
                "paper_id": item.paper_id,
                "claim": item.claim,
                "verified": item.verified,
                "eligible_for_report": item.eligible_for_report,
                "verification_method": item.verification_method,
                "confidence": item.verification_confidence or item.confidence,
            }
            for item in evidence[:50]
        ],
        citation_audit_log=citation_audit_log,
        claim_audit_summary=claim_summary,
        arena_report=run.arena_result.model_dump(mode="json") if run.arena_result else {},
        baseline_provenance=_baseline_provenance(run),
        experiment_iteration_log=(
            [item.model_dump(mode="json") for item in run.code_experiment.iteration_log]
            if run.code_experiment else []
        ),
        code_debug_log=(
            [{"round": item.round, "traceback_summary": (item.traceback_full or "")[:500],
              "has_patch": bool(item.patch_diff)} for item in run.code_experiment.debug_log]
            if run.code_experiment else []
        ),
        ablation_report=run.ablation_analysis.model_dump(mode="json") if run.ablation_analysis else {},
        result_support_judgment=run.result_evaluation.model_dump(mode="json") if run.result_evaluation else {},
        run_metadata={
            "run_id": run.run_id,
            "domain": run.domain,
            "question": run.question,
            "status": str(run.status.value if hasattr(run.status, "value") else run.status),
            "current_stage": run.current_stage,
            "papers": len(papers),
            "report_references": len(reportable_papers(run, papers, evidence)),
            "evidence_items": len(evidence),
            "citation_frozen": run.citation_frozen,
            "evidence_frozen": run.evidence_frozen,
            "frozen_paper_ids": run.frozen_paper_ids,
            "frozen_evidence_ids": run.frozen_evidence_ids,
        },
    )


def _baseline_provenance(run: ResearchRun) -> dict[str, Any]:
    if run.baseline_intake:
        return {
            "strategy": run.baseline_intake.strategy,
            "source_type": run.baseline_intake.source_type,
            "trust_level": run.baseline_intake.trust_level,
            "name": run.baseline_intake.name,
            "description": run.baseline_intake.description,
            "metrics": [item.model_dump(mode="json") for item in run.baseline_intake.metrics],
            "limitations": run.baseline_intake.limitations,
            "provenance_notes": run.baseline_intake.provenance_notes,
        }
    if run.experiment_assistance:
        return {
            "source": "user-provided",
            "name": run.experiment_assistance.baseline_name,
            "metrics": [item.model_dump(mode="json") for item in run.experiment_assistance.baseline_metrics],
        }
    if run.code_experiment:
        return {
            "source": "system-executed",
            "baseline": run.code_experiment.baseline_source,
            "comparison": run.code_experiment.comparison.model_dump(mode="json"),
        }
    return {}


def _selected_hypothesis_from_run(run: ResearchRun) -> Hypothesis | None:
    return next((item for item in run.hypotheses if item.selected), run.hypotheses[0] if run.hypotheses else None)


def _hypothesis_statement(run: ResearchRun, hypothesis: Hypothesis | None) -> str:
    if hypothesis is None:
        return run.question
    return hypothesis.revised_statement or hypothesis.statement


def _hypothesis_statement_zh(run: ResearchRun, hypothesis: Hypothesis | None) -> str:
    statement = _hypothesis_statement(run, hypothesis)
    if _has_cjk(statement) and not _has_long_latin_phrase(statement):
        return statement
    domain = run.domain.replace("_", " ")
    if "solid" in statement.lower() or "electrolyte" in statement.lower() or "battery" in statement.lower():
        return "围绕固态电解质结构、晶界传输、缺陷化学与稳定性关系形成的待验证机制假设"
    if "seismic" in statement.lower() or "earthquake" in statement.lower():
        return "围绕地震事件数据特征、模型判别能力与可验证误差来源形成的待验证机制假设"
    return f"围绕 {domain} 研究问题形成的待验证机制假设"


def _english_title(run: ResearchRun, hypothesis: Hypothesis | None) -> str:
    statement = _hypothesis_statement(run, hypothesis).strip().rstrip(".")
    if statement and statement != run.question:
        return f"Evidence-Grounded Validation of {statement[:110]}"
    return f"Evidence-Grounded Validation Plan for {run.domain.replace('_', ' ').title()}"


def _chinese_title(run: ResearchRun, hypothesis: Hypothesis | None) -> str:
    statement = _hypothesis_statement_zh(run, hypothesis).strip().rstrip("。")
    if statement and statement != run.question:
        return f"基于证据链的科研假设验证方案：{statement[:80]}"
    return f"{run.domain} 方向的证据驱动科研验证方案"


def _evidence_summary_clean(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "no verified report-eligible evidence is currently available, so literature claims remain verification pending"
    snippets = []
    for item in evidence[:3]:
        source = item.source_title or item.paper_id or "unknown source"
        snippets.append(f"{item.claim} [{item.evidence_id}, {source}]")
    return "; ".join(snippets)


def _evidence_summary_clean_zh(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "当前尚无可进入报告的已核验证据，因此文献相关结论仍需后续验证"
    snippets = []
    for item in evidence[:3]:
        source = item.source_title or item.paper_id or "已核验来源"
        snippets.append(
            f"{item.evidence_id} 来自已核验来源《{source}》，用于支持结构、传输、稳定性、数据或方法边界相关事实"
        )
    return "；".join(snippets)


def _scientific_methods_en() -> str:
    return (
        "Prepare controlled solid-electrolyte sample groups under defined synthesis or sintering conditions. "
        "Use XRD to confirm phase purity, SEM/EBSD to quantify grain size and grain-boundary density, and EIS with equivalent-circuit fitting to separate bulk resistance, grain-boundary resistance, and total ionic conductivity. "
        "Use temperature-dependent EIS to estimate activation energy, XPS/EPR/ICP-OES to quantify defect or stoichiometry descriptors, and DFT, MD, or machine-learning interatomic potentials to compare Li-ion migration barriers in bulk and boundary environments. "
        "Finally, use regression, ablation analysis, and uncertainty analysis to test whether grain-boundary and defect descriptors explain the conductivity gap."
    )


def _scientific_methods_zh() -> str:
    return (
        "在受控合成或烧结条件下制备固态电解质样品组。"
        "使用 XRD 确认物相纯度，使用 SEM/EBSD 量化晶粒尺寸和晶界密度，使用 EIS 及等效电路拟合分离体相电阻、晶界电阻和总离子电导率。"
        "通过变温 EIS 估计活化能，通过 XPS/EPR/ICP-OES 量化缺陷或化学计量描述符，并使用 DFT、分子动力学或机器学习原子间势比较体相与晶界环境中的锂离子迁移势垒。"
        "最后通过回归、消融分析和不确定性分析，检验晶界与缺陷描述符是否能够解释电导率差距。"
    )


def _executed_result_sentence(card: BaselineResultCard | None) -> str:
    if card is None:
        return "No executable baseline result card has been attached yet."
    return f"An executable preliminary feasibility result is available from {card.name}."


def _executed_result_sentence_zh(card: BaselineResultCard | None) -> str:
    if card is None:
        return "当前尚未附加可执行的基线结果卡。"
    return f"当前已有来自 {card.name} 的初步可执行可行性结果。"


def _executed_results_text(card: BaselineResultCard | None) -> str:
    if card is None:
        return "No executed scientific experiment is reported. Quantitative performance remains verification pending until a baseline result card or laboratory/computational validation is attached."
    metrics = ", ".join(f"{key}={value}" for key, value in card.metrics.items())
    return (
        f"Executed preliminary result: {card.name}; dataset={card.dataset}; target={card.target}; "
        f"model={card.model}; train_rows={card.train_rows}; test_rows={card.test_rows}; metrics=({metrics}). "
        "This is an executable feasibility and result-card contract, not a completed materials-discovery conclusion."
    )


def _executed_results_text_zh(card: BaselineResultCard | None) -> str:
    if card is None:
        return "尚未报告已经执行的科学实验。定量性能需要等待基线结果卡、实验验证或计算验证后才能确认。"
    metrics = ", ".join(f"{key}={value}" for key, value in card.metrics.items())
    return (
        f"已执行的初步结果：{card.name}；数据集={card.dataset}；目标变量={card.target}；"
        f"模型={card.model}；训练样本数={card.train_rows}；测试样本数={card.test_rows}；指标=({metrics})。"
        "该结果用于证明流程和结果卡契约可执行，不代表已经完成材料发现结论。"
    )


def _limitations_en(run: ResearchRun, evidence: list[EvidenceItem], data_profiles: list[DatasetProfile]) -> str:
    unsupported = run.claim_audit.unsupported if run.claim_audit else None
    audit_note = (
        f"Claim audit currently flags {unsupported} unsupported claims; those claims must remain limitations or validation targets."
        if unsupported
        else "Claim audit has no unsupported claims or has not yet found unsupported claims."
    )
    return (
        f"Evidence remains limited to {len(evidence)} report-eligible items, so mechanism-level conclusions must stay provisional. "
        f"{audit_note} {_materials_project_note(data_profiles)} "
        "If the experimental target data have not been collected, the hypothesis remains pending validation. Suspicious, skipped, rejected, or hallucinated citations are excluded from formal references and retained only in the audit appendix."
    )


def _limitations_zh(run: ResearchRun, evidence: list[EvidenceItem], data_profiles: list[DatasetProfile]) -> str:
    unsupported = run.claim_audit.unsupported if run.claim_audit else None
    audit_note = (
        f"论断审计当前仍有 {unsupported} 条缺少支持的论断，这些内容只能作为局限性或待验证目标。"
        if unsupported
        else "论断审计当前没有发现缺少支持的论断，或尚未生成完整审计。"
    )
    return (
        f"当前正式报告只依据 {len(evidence)} 条可进入报告的证据项，因此机制层面的结论必须保持审慎。"
        f"{audit_note}{_materials_project_note_zh(data_profiles)}"
        "如果目标实验数据尚未采集，假设仍处于待验证状态。suspicious、skipped、rejected 或 hallucinated 文献不会进入正式参考文献，只保留在审计附录中。"
    )


def _materials_project_note(data_profiles: list[DatasetProfile]) -> str:
    profile = next((item for item in data_profiles if item.name == "materials_project_summary_adapter"), None)
    if profile is None:
        return "Materials Project validation is planned or unavailable in the current run."
    if profile.availability == "configured":
        return "Materials Project access is configured, but any generated candidate data must still be treated as validation input rather than completed experimental proof."
    return "Materials Project validation is planned or unavailable because MATERIALS_PROJECT_API_KEY is not configured."


def _materials_project_note_zh(data_profiles: list[DatasetProfile]) -> str:
    profile = next((item for item in data_profiles if item.name == "materials_project_summary_adapter"), None)
    if profile is None:
        return "Materials Project 验证在当前运行中属于计划或不可用状态。"
    if profile.availability == "configured":
        return "Materials Project 访问已配置，但相关候选数据仍应作为验证输入，而不是已完成实验证明。"
    return "由于未配置 MATERIALS_PROJECT_API_KEY，Materials Project 验证目前属于计划或不可用状态。"


def _join_or_default(items: list[str], default: str) -> str:
    cleaned = [item for item in items if str(item).strip()]
    return "; ".join(cleaned) if cleaned else default


def _join_or_default_zh(items: list[str], default: str, *, kind: str) -> str:
    cleaned = [_translate_short_scientific_item(item) for item in items if str(item).strip()]
    cleaned = [item for item in cleaned if item]
    if not cleaned:
        return default
    joined = "；".join(cleaned)
    if _has_long_latin_phrase(joined):
        count = len(cleaned)
        if kind == "baseline":
            return f"实验计划中定义了 {count} 类对照基线，包括未改性样品、单因素改性样品或简单预测基线；具体英文标识保留在系统审计附录中。"
        if kind == "metric":
            return f"实验计划中定义了 {count} 类评估指标，覆盖电导率、迁移势垒、晶界阻抗、结构表征指标以及必要的统计误差指标；具体英文标识保留在系统审计附录中。"
        return f"实验计划中定义了 {count} 个步骤，正式中文报告仅保留其科研含义，具体英文标识保留在系统审计附录中。"
    return joined


def _experiment_design_zh(experiment: ExperimentPlan) -> str:
    steps = [_translate_short_scientific_item(item) for item in experiment.experiment_steps if str(item).strip()]
    joined = "；".join(item for item in steps if item)
    if not joined or _has_long_latin_phrase(joined):
        return (
            "制备受控材料组，表征物相、晶粒、晶界和缺陷特征，进行 EIS 及等效电路拟合，"
            "并结合 DFT、分子动力学或统计建模比较关键描述符与电导率、阻抗和迁移势垒之间的关系。"
        )
    return joined


def _expected_results_zh(expected_results: str) -> str:
    text = _translate_short_scientific_item(expected_results)
    if not text or _has_long_latin_phrase(text):
        return "预期验证结果是：目标结构、晶界或缺陷描述符能够解释相对基线的电导率、阻抗或迁移势垒差异。"
    return text


def _translate_short_scientific_item(value: object) -> str:
    text = _clean(value)
    if not text:
        return ""
    replacements = {
        "mean_baseline": "均值基线",
        "solid_electrolyte_mean_baseline": "固态电解质均值基线",
        "baseline": "基线",
        "Undoped": "未掺杂",
        "single-doped": "单掺杂",
        "bulk and grain boundary": "体相与晶界",
        "grain boundary": "晶界",
        "Activation energy": "活化能",
        "activation energy": "活化能",
        "Ionic conductivity": "离子电导率",
        "ionic conductivity": "离子电导率",
        "Grain boundary resistance": "晶界电阻",
        "grain boundary resistance": "晶界电阻",
        "Segregation energy": "偏聚能",
        "segregation energy": "偏聚能",
        "Load profile": "加载数据画像",
        "Run baseline": "运行基线实验",
        "Create result card": "生成结果卡",
        "Expected improvement must be validated by a real benchmark run.": "预期提升必须通过真实基准实验验证。",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _looks_like_agent_workflow(text: str) -> bool:
    lowered = text.lower()
    bad_terms = ["literature_router", "evidence_ledger", "critic_review", "workflow_plan", "report_export"]
    scientific_terms = ["eis", "xrd", "sem", "ebsd", "dft", "md", "equivalent circuit", "grain boundary", "defect", "sintering"]
    return any(term in lowered for term in bad_terms) and not any(term in lowered for term in scientific_terms)


def _looks_like_mixed_chinese_report(report: FormalResearchReport) -> bool:
    fields = [
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
    long_latin_fields = sum(1 for field in fields if _has_long_latin_phrase(field))
    return long_latin_fields >= 3


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _has_long_latin_phrase(text: str) -> bool:
    latin_words = [word for word in text.replace("_", " ").split() if any("A" <= char <= "z" for char in word)]
    long_words = [word for word in latin_words if sum(char.isalpha() for char in word) >= 4]
    return len(long_words) >= 8


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in [_clean(raw) for raw in value] if item]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _problem_statement(
    run: ResearchRun,
    verified_papers: list[Paper],
    verified_evidence: list[EvidenceItem],
) -> str:
    if not verified_papers:
        citation_note = (
            "目前还没有可用的已核验参考文献，所有文献相关结论都应标记为待验证。 "
            "No verified reference is available yet; literature claims must remain verification pending."
        )
    else:
        citation_note = (
            f"当前运行已有 {len(verified_papers)} 篇已核验参考文献和 {len(verified_evidence)} 条已核验证据。 "
            f"The current run has {len(verified_papers)} verified references and "
            f"{len(verified_evidence)} verified evidence items."
        )
    return (
        "早期科研构思很容易把真实文献、合理猜想和缺证据结论混在一起。 "
        f"对于当前领域（{run.domain}），本报告要回答的问题是：{run.question} "
        "系统要求每个关键科学结论都能够追溯到已核验证据，并落到可执行的验证路径上。 "
        f"{citation_note}\n\n"
        "Early-stage scientific ideation often mixes real literature with unsupported claims. "
        f"For the selected domain ({run.domain}), the concrete task is to answer: {run.question} "
        "The report must keep every scientific claim traceable to verified evidence and an executable validation path. "
        f"{citation_note}"
    )


def _rationale(
    statement: str,
    hypothesis: Hypothesis | None,
    verified_evidence: list[EvidenceItem],
) -> str:
    evidence_summary = _evidence_summary(verified_evidence)
    critic_note = ""
    if hypothesis and hypothesis.critic:
        critic_note = (
            " 审稿式评价分数："
            f"novelty={hypothesis.critic.novelty}, "
            f"verifiability={hypothesis.critic.verifiability}, "
            f"data_availability={hypothesis.critic.data_availability}。"
            f"修订建议：{hypothesis.critic.revision_advice} "
            " Critic review scores: "
            f"novelty={hypothesis.critic.novelty}, "
            f"verifiability={hypothesis.critic.verifiability}, "
            f"data_availability={hypothesis.critic.data_availability}. "
            f"Revision advice: {hypothesis.critic.revision_advice}"
        )
    return (
        f"选定假设：{statement}。证据基础：{evidence_summary}.{critic_note}\n\n"
        f"Selected hypothesis: {statement}. Evidence basis: {evidence_summary}.{critic_note}"
    )


def _technical_details() -> list[str]:
    return [
        "使用兼容 Qwen/百炼的 LLM 客户端，并通过 provider-neutral LLM interface 封装模型调用。",
        "Planner 输出子问题、检索词、工具、证据要求和风险控制 / sub-questions, search queries, tools, evidence requirements, and risk controls.",
        "统一 Literature Router 接入 OpenAlex、Semantic Scholar 和 arXiv，并基于 DOI/arXiv/title 去重。",
        "引用进入 References 前必须经过 arXiv ID、Crossref DOI、DataCite DOI、OpenAlex title、Semantic Scholar title 和 arXiv title search 等分层核验。",
        "Evidence ledger 记录 verification method、confidence、matched source、report eligibility，并支持 citation/evidence freeze 后再生成最终报告。",
        "PDF page chunks 可通过浏览器或本地 PDF 捕获后入账到 evidence ledger，作为 page-level support。",
        "Claim audit 会把最终报告结论与 eligible evidence 对齐，标记 unsupported claims 供用户审核。",
        "Scientific data profiling 生成 Materials Project / Matbench-compatible result cards。",
        "Deterministic Report Writer mock assembles structured outputs without inventing citations，并避免新增未验证引用。",
    ]


def _methods(
    run: ResearchRun,
    verified_evidence: list[EvidenceItem],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> list[str]:
    browser_step = (
        "浏览器采集和 PDF 解析结果仅作为补充证据，直到 citation metadata 被核验。 "
        "Use browser captures and PDF parsing only as supporting evidence until citation metadata is verified."
        if run.constraints.enable_browser_worker
        else "优先使用 scholarly API retrieval；browser/PDF evidence 可在后续运行中启用。 Use scholarly API retrieval first; browser/PDF evidence can be enabled in later runs."
    )
    result_card_step = (
        f"附加 baseline result card {baseline_result_card.name}，用于区分可执行 MVP 结果和预期结果。 Attach baseline result card {baseline_result_card.name} to separate executable mock results from expected outcomes."
        if baseline_result_card
        else "在 baseline result card 生成前，所有定量结果都标记为待验证。 Mark quantitative results as verification pending until a baseline result card is generated."
    )
    return [
        "将科研问题拆解为检索、抽取、核验、假设和实验设计子任务 / Plan the research question into search, extraction, verification, hypothesis, and experiment subtasks.",
        "从 Literature Router 获取候选论文，并在进入 References 前核验 arXiv ID、DOI、title 和 source metadata。",
        f"将 {len(verified_evidence)} 条已核验证据用于假设支撑和 gap analysis / Convert verified evidence items into hypothesis support and gap analysis.",
        f"分析 {len(data_profiles)} 个科学数据源的 availability、target variable 和 task type。",
        "在实验设计前进行 critic review，并选择或修订假设 / Run critic review and select or revise the hypothesis before experiment design.",
        result_card_step,
        browser_step,
        "导出比赛格式报告，并附 citation audit log，覆盖 accepted、suspicious、hallucinated、skipped 和 audit-only papers。",
    ]


def _paper_title(run: ResearchRun, hypothesis: Hypothesis | None) -> str:
    if hypothesis:
        short = hypothesis.statement.strip().rstrip(".")
        return f"Evidence-Grounded Research Plan: {short[:90]}"
    return f"Evidence-Grounded Research Plan for {run.domain}"


def _paper_abstract(
    run: ResearchRun,
    evidence_count: int,
    verified_papers: list[Paper],
    card: BaselineResultCard | None,
) -> str:
    result_card_note = (
        f" It includes an executable baseline result card ({card.name}) as a bounded MVP validation artifact."
        if card
        else " Quantitative results are marked verification pending until a baseline run is attached."
    )
    return (
        "本报告由 TrustSci-Agent 的 Report Writer Agent 自动生成。 "
        f"它面向 '{run.domain}' 领域，融合 planner output、citation verification、"
        f"{evidence_count} 条 verified evidence items 和明确的 experiment design。"
        f"References 被限制为 {len(verified_papers)} 篇 verified papers；未核验或被拒绝论文只进入 audit log。"
        f"{result_card_note}\n\n"
        "This mock report is generated by TrustSci-Agent's Report Writer Agent. "
        f"It addresses the domain '{run.domain}' by combining planner output, citation verification, "
        f"{evidence_count} verified evidence items, and an explicit experiment design. "
        f"References are restricted to {len(verified_papers)} verified papers; unverified or rejected papers only appear in the audit log."
        f"{result_card_note}"
    )


def _evidence_summary(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "verification pending; no verified evidence item is available yet"
    snippets = []
    for item in evidence[:3]:
        source = item.source_title or item.paper_id or "unknown source"
        snippets.append(f"{item.claim} ({source})")
    return "; ".join(snippets)


def _results_text(card: BaselineResultCard | None, verified_reference_count: int, verified_evidence_count: int) -> str:
    if card is None:
        return (
            "MVP 可行性由可执行规划、引用核验、证据绑定和报告生成共同证明。 "
            f"本次运行包含 {verified_reference_count} 篇已核验参考文献和 {verified_evidence_count} 条已核验证据。 "
            "在接入 Matbench 或 Materials Project baseline card 前，定量模型性能仍标记为待验证。\n\n"
            "MVP feasibility is demonstrated by executable planning, citation verification, evidence binding, and report generation. "
            f"This run has {verified_reference_count} verified references and {verified_evidence_count} verified evidence items. "
            "Quantitative model performance is verification pending until a Matbench or Materials Project baseline card is attached."
        )
    metrics = ", ".join(f"{key}={value}" for key, value in card.metrics.items())
    return (
        f"系统生成了一个小型可执行 baseline result card：{card.name}，dataset={card.dataset}，"
        f"train_rows={card.train_rows}，test_rows={card.test_rows}，metrics=({metrics})。"
        f"报告引用 {verified_reference_count} 篇已核验论文和 {verified_evidence_count} 条已核验证据。"
        "这一步先验证 result-card contract，后续可扩展到完整 Matbench 或 Materials Project 数据。\n\n"
        f"A small executable baseline result card was generated: {card.name}, dataset={card.dataset}, "
        f"train_rows={card.train_rows}, test_rows={card.test_rows}, metrics=({metrics}). "
        f"The report references {verified_reference_count} verified papers and {verified_evidence_count} verified evidence items. "
        "This verifies the result-card contract before scaling to full Matbench or Materials Project data."
    )


# Clean UTF-8 reporter templates. These definitions intentionally override the
# earlier deterministic fallback templates so generated reports are bilingual.
def _problem_statement(
    run: ResearchRun,
    verified_papers: list[Paper],
    verified_evidence: list[EvidenceItem],
) -> str:
    if not verified_papers:
        citation_note = (
            "No verified reference is available yet; literature-related claims must remain verification pending.\n"
            "中文翻译：目前还没有可用的已核验参考文献，所有文献相关结论都必须标记为待验证。"
        )
    else:
        citation_note = (
            f"The current run has {len(verified_papers)} verified references and "
            f"{len(verified_evidence)} verified evidence items.\n"
            f"中文翻译：当前运行已有 {len(verified_papers)} 篇已核验参考文献和 "
            f"{len(verified_evidence)} 条已核验证据。"
        )
    return (
        "Early-stage scientific ideation often mixes real literature, plausible inference, and unsupported conclusions. "
        f"For the selected domain ({run.domain}), the concrete task is to answer: {run.question}. "
        "Every key scientific claim in this report must be traceable to verified evidence and an executable validation path. "
        f"{citation_note}\n"
        "中文翻译：早期科研构思很容易把真实文献、合理推断和缺少证据的结论混在一起。"
        f"对于当前领域（{run.domain}），本报告要回答的问题是：{run.question}。"
        "报告中的每一个关键科学结论都必须能够追溯到已核验证据，并落到可执行的验证路径上。"
    )


def _rationale(
    statement: str,
    hypothesis: Hypothesis | None,
    verified_evidence: list[EvidenceItem],
) -> str:
    evidence_summary = _evidence_summary(verified_evidence)
    critic_note = ""
    if hypothesis and hypothesis.critic:
        critic_note = (
            " Critic review scores: "
            f"novelty={hypothesis.critic.novelty}, "
            f"verifiability={hypothesis.critic.verifiability}, "
            f"data_availability={hypothesis.critic.data_availability}. "
            f"Revision advice: {hypothesis.critic.revision_advice} "
            "中文翻译：审稿式评价分数："
            f"novelty={hypothesis.critic.novelty}, "
            f"verifiability={hypothesis.critic.verifiability}, "
            f"data_availability={hypothesis.critic.data_availability}。"
            f"修订建议：{hypothesis.critic.revision_advice}"
        )
    return (
        f"Selected hypothesis: {statement}. Evidence basis: {evidence_summary}.{critic_note}\n"
        f"中文翻译：选定假设：{statement}。证据基础：{evidence_summary}。{critic_note}"
    )


def _technical_details() -> list[str]:
    return [
        "Use a Qwen/Bailian-compatible LLM client behind a provider-neutral LLM interface. 中文翻译：通过兼容 Qwen/百炼的 LLM 客户端和统一的模型接口封装模型调用。",
        "Planner produces sub-questions, search queries, tool choices, evidence requirements, and risk controls. 中文翻译：Planner 输出子问题、检索词、工具选择、证据要求和风险控制。",
        "Literature Router unifies OpenAlex, Semantic Scholar, and arXiv retrieval with DOI/arXiv/title deduplication. 中文翻译：Literature Router 统一接入 OpenAlex、Semantic Scholar 和 arXiv，并基于 DOI、arXiv ID 和标题去重。",
        "References must pass layered verification before entering the final report. 中文翻译：参考文献进入最终报告前必须经过分层引用核验。",
        "Evidence ledger records verification method, confidence, matched source, and report eligibility. 中文翻译：Evidence Ledger 记录核验方法、置信度、匹配来源和报告可用性。",
        "PDF page chunks can be ingested as page-level evidence after citation metadata is verified. 中文翻译：PDF 页面片段可在引用元数据核验后作为页面级证据入账。",
        "Claim audit aligns final report claims with eligible evidence and flags unsupported claims. 中文翻译：Claim Audit 将最终报告中的论断与可用证据对齐，并标记缺少支持的论断。",
        "Scientific data profiling creates Materials Project / Matbench-compatible result cards. 中文翻译：Scientific Data Profiling 生成兼容 Materials Project / Matbench 风格的结果卡。",
        "Report Writer assembles structured outputs without inventing citations. 中文翻译：Report Writer 组装结构化报告，但不会虚构引用。",
    ]


def _methods(
    run: ResearchRun,
    verified_evidence: list[EvidenceItem],
    data_profiles: list[DatasetProfile],
    baseline_result_card: BaselineResultCard | None,
) -> list[str]:
    browser_step = (
        "Use browser captures and PDF parsing only as supporting evidence until citation metadata is verified. 中文翻译：浏览器采集和 PDF 解析结果仅作为补充证据，直到引用元数据通过核验。"
        if run.constraints.enable_browser_worker
        else "Use scholarly API retrieval first; browser/PDF evidence can be enabled in later runs. 中文翻译：优先使用学术 API 检索；浏览器和 PDF 证据可在后续运行中启用。"
    )
    result_card_step = (
        f"Attach baseline result card {baseline_result_card.name} to separate executable MVP results from expected outcomes. 中文翻译：附加 baseline result card {baseline_result_card.name}，用于区分已执行的 MVP 结果和预期结果。"
        if baseline_result_card
        else "Mark quantitative results as verification pending until a baseline result card is generated. 中文翻译：在 baseline result card 生成前，所有定量结果都应标记为待验证。"
    )
    return [
        "Plan the research question into search, extraction, verification, hypothesis, and experiment-design subtasks. 中文翻译：将科研问题拆解为检索、抽取、核验、假设生成和实验设计子任务。",
        "Retrieve candidate papers through Literature Router and verify arXiv ID, DOI, title, and source metadata before references are used. 中文翻译：通过 Literature Router 获取候选论文，并在引用进入 References 前核验 arXiv ID、DOI、标题和来源元数据。",
        f"Convert {len(verified_evidence)} verified evidence items into hypothesis support and gap analysis. 中文翻译：将 {len(verified_evidence)} 条已核验证据用于假设支撑和 gap analysis。",
        f"Profile {len(data_profiles)} scientific data sources for availability, target variable, and task type. 中文翻译：分析 {len(data_profiles)} 个科学数据源的可用性、目标变量和任务类型。",
        "Run critic review before experiment design, then select or revise the hypothesis. 中文翻译：在实验设计前进行 critic review，并选择或修订假设。",
        result_card_step,
        browser_step,
        "Export a competition-format report with citation audit log covering accepted, suspicious, hallucinated, skipped, and audit-only papers. 中文翻译：导出比赛格式报告，并附带 citation audit log，覆盖 accepted、suspicious、hallucinated、skipped 和 audit-only papers。",
    ]


def _paper_abstract(
    run: ResearchRun,
    evidence_count: int,
    verified_papers: list[Paper],
    card: BaselineResultCard | None,
) -> str:
    result_card_note = (
        f" It includes an executable baseline result card ({card.name}) as a bounded MVP validation artifact."
        if card
        else " Quantitative results are marked verification pending until a baseline run is attached."
    )
    chinese_card_note = (
        f"它包含一个可执行的 baseline result card（{card.name}），作为有边界的 MVP 验证产物。"
        if card
        else "在附加 baseline run 之前，定量结果均标记为待验证。"
    )
    return (
        "This report is generated by TrustSci-Agent's Report Writer Agent. "
        f"It addresses the domain '{run.domain}' by combining planner output, citation verification, "
        f"{evidence_count} verified evidence items, and an explicit experiment design. "
        f"References are restricted to {len(verified_papers)} verified papers; unverified or rejected papers only appear in the audit log."
        f"{result_card_note}\n"
        "中文翻译：本报告由 TrustSci-Agent 的 Report Writer Agent 自动生成。"
        f"它面向“{run.domain}”领域，融合 planner output、citation verification、"
        f"{evidence_count} 条已核验证据和明确的 experiment design。"
        f"References 被限制为 {len(verified_papers)} 篇 verified papers；未核验或被拒绝的论文只进入 audit log。"
        f"{chinese_card_note}"
    )


def _results_text(card: BaselineResultCard | None, verified_reference_count: int, verified_evidence_count: int) -> str:
    if card is None:
        return (
            "MVP feasibility is demonstrated by executable planning, citation verification, evidence binding, and report generation. "
            f"This run has {verified_reference_count} verified references and {verified_evidence_count} verified evidence items. "
            "Quantitative model performance is verification pending until a Matbench or Materials Project baseline card is attached.\n"
            "中文翻译：MVP 可行性由可执行规划、引用核验、证据绑定和报告生成共同证明。"
            f"本次运行包含 {verified_reference_count} 篇已核验参考文献和 {verified_evidence_count} 条已核验证据。"
            "在接入 Matbench 或 Materials Project baseline card 前，定量模型性能仍标记为待验证。"
        )
    metrics = ", ".join(f"{key}={value}" for key, value in card.metrics.items())
    return (
        f"A small executable baseline result card was generated: {card.name}, dataset={card.dataset}, "
        f"train_rows={card.train_rows}, test_rows={card.test_rows}, metrics=({metrics}). "
        f"The report references {verified_reference_count} verified papers and {verified_evidence_count} verified evidence items. "
        "This verifies the result-card contract before scaling to full Matbench or Materials Project data.\n"
        f"中文翻译：系统生成了一个小型可执行 baseline result card：{card.name}，dataset={card.dataset}，"
        f"train_rows={card.train_rows}，test_rows={card.test_rows}，metrics=({metrics})。"
        f"报告引用 {verified_reference_count} 篇已核验论文和 {verified_evidence_count} 条已核验证据。"
        "这一步先验证 result-card contract，后续可扩展到完整 Matbench 或 Materials Project 数据。"
    )
