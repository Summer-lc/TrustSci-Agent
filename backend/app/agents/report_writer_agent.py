import json

from app.evidence.audit import build_citation_audit
from app.evidence.selection import reportable_evidence, reportable_knowledge_cards, reportable_papers
from app.llm.interface import LLMClient, LLMRequest
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.report import ResearchReport
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
        response = await self.llm.complete(
            LLMRequest(
                system=SYSTEM_PROMPT,
                user=_build_report_prompt(
                    run,
                    hypothesis,
                    experiment,
                    evidence,
                    papers,
                    knowledge_cards,
                    data_profiles,
                    baseline_result_card,
                ),
                fallback={"report": _report_payload(fallback)},
                run_id=run.run_id,
                agent="report_writer",
            )
        )
        return _normalize_qwen_report(
            response.content,
            fallback,
            run,
            experiment,
            evidence,
            papers,
            knowledge_cards,
            data_profiles,
            baseline_result_card,
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
        return _enforce_report_layers(report)


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
            "Mention evidence ids in rationale or methods when making key claims.",
            "Use explicit Evidence-backed:, Inference:, and To validate: labels in problem_statement, rationale, paper_abstract, results, and major method/technical detail bullets.",
            "Write each required report field bilingually: English first, then a faithful Chinese translation prefixed with 中文翻译：.",
            "For list items, use English first and add 中文翻译： in the same item.",
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
        return _enforce_report_layers(report)
    except Exception:
        return fallback


def _report_payload(report: ResearchReport) -> dict:
    payload = report.model_dump()
    payload.pop("references", None)
    payload.pop("citation_audit_log", None)
    payload.pop("knowledge_cards", None)
    payload.pop("data_profiles", None)
    payload.pop("baseline_result_card", None)
    return payload


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
