from collections.abc import Callable

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.planner import PerspectiveQuestion, PlannerPlan
from app.schemas.run import ResearchRun


SYSTEM_PROMPT = """You are the Research Planner Agent for TrustSci-Agent.
Convert an ambiguous scientific research question into a concrete, evidence-grounded multi-agent plan.
Return JSON only. Do not invent paper titles, DOI values, authors, or measured results.

Required JSON keys:
- research_objective: short objective string
- domain: normalized domain string
- constraints_summary: list of concrete constraints
- sub_questions: 3-5 research sub-questions
- search_queries: 4-8 precise literature/database search queries
- databases: planned evidence/data sources
- tools_to_call: tool names selected from literature_router, openalex_search, semantic_scholar_search, arxiv_search, layered_citation_verifier, pdf_parser, browser_capture, materials_project_profile, matbench_profile, evidence_ledger, hypothesis_generator, critic_debate, experiment_designer, report_writer
- evidence_requirements: facts that must be supported by verified sources
- workflow_plan: ordered agent workflow steps
- success_criteria: measurable criteria for a good run
- risk_controls: checks that reduce hallucination, weak evidence, or unverifiable experiments
- perspectives: 4-6 objects with keys perspective, role, question, search_query, evidence_requirement, risk_control. Cover domain expert, ML/data expert, experimentalist, skeptical reviewer, and translation/application perspectives.

If domain is seismic_event_classification, search queries must be grounded in
seismology terms such as seismic/earthquake waveform, seismic event
classification, phase picking/classification, earthquake detection, and
earthquake-explosion/blast discrimination. Treat natural earthquake, blast,
collapse, induced event, noise, and non-event labels as examples rather than a
fixed taxonomy. Avoid generic machine-learning-only or medical/application-only
queries.
"""


USER_TEMPLATE = """Domain: {domain}
Question: {question}
Constraints:
- must_verify_citations: {must_verify_citations}
- max_papers: {max_papers}
- require_experiment_plan: {require_experiment_plan}
- enable_browser_worker: {enable_browser_worker}
- enable_semantic_scholar: {enable_semantic_scholar}
- enable_arxiv: {enable_arxiv}

Design a verifiable AI Scientist workflow for this run. Prioritize real papers, open scientific datasets, explicit evidence requirements, and a bounded experiment plan."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])


class PlannerPlanParser(Runnable):
    """Structured output parser for PlannerAgent (LangChain ``Runnable``).

    Validates the LLM content (already JSON-parsed by QwenClient into a dict,
    or a raw string on the fallback path) against the existing PlannerPlan
    normalization. Any parse/validation failure returns the fallback plan, so
    a malformed model output never crashes the run.

    Implemented as a plain ``Runnable`` (not ``BaseOutputParser``) because
    QwenClient already JSON-parses into a dict and records it in the audit log;
    ``BaseOutputParser`` would wrap the dict in a ``Generation(text=...)``
    string slot and reject it. Keeping the dict flowing through preserves the
    audit-log response format unchanged.
    """

    def __init__(self, fallback: dict | None = None) -> None:
        super().__init__()
        self.fallback = fallback if fallback is not None else {}

    def parse(self, content: object) -> dict:
        try:
            return _normalize_plan(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)


class PlannerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun, progress: Callable[[str], None] | None = None) -> dict:
        if progress:
            progress("Preparing planner fallback, prompt context, and structured JSON schema.")
        fallback = _fallback_plan(run).model_dump()
        if progress:
            progress("Calling Qwen/Bailian planner to generate sub-questions, search queries, and perspectives.")
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(
                fallback=fallback, run_id=run.run_id, agent="planner"
            )
            | PlannerPlanParser(fallback=fallback)
        )
        plan = await chain.ainvoke(_prompt_vars(run))
        if progress:
            progress("Normalizing planner output and validating perspectives, evidence requirements, and risk controls.")
        return plan


def _prompt_vars(run: ResearchRun) -> dict:
    constraints = run.constraints
    return {
        "domain": run.domain,
        "question": run.question,
        "must_verify_citations": constraints.must_verify_citations,
        "max_papers": constraints.max_papers,
        "require_experiment_plan": constraints.require_experiment_plan,
        "enable_browser_worker": constraints.enable_browser_worker,
        "enable_semantic_scholar": constraints.enable_semantic_scholar,
        "enable_arxiv": constraints.enable_arxiv,
    }


def _fallback_plan(run: ResearchRun) -> PlannerPlan:
    browser_tool = ["browser_capture"] if run.constraints.enable_browser_worker else []
    arxiv_tool = ["arxiv_search"] if run.constraints.enable_arxiv else []
    semantic_tool = ["semantic_scholar_search"] if run.constraints.enable_semantic_scholar else []
    if run.domain == "seismic_event_classification":
        return _seismic_fallback_plan(run, browser_tool, arxiv_tool, semantic_tool)
    perspectives = _fallback_perspectives(run)
    return PlannerPlan(
        research_objective=run.question,
        domain=run.domain,
        constraints_summary=[
            "Use only real, verifiable literature and database records.",
            f"Collect at most {run.constraints.max_papers} papers before citation verification.",
            "Produce an experiment plan with datasets, baselines, metrics, and failure modes.",
        ],
        sub_questions=[
            "What mechanisms are repeatedly reported in recent literature?",
            "Which structural or compositional features are linked to the target property?",
            "Which open datasets can support a bounded verification experiment?",
            "Where do current methods leave a measurable knowledge gap?",
        ],
        search_queries=[
            f"{run.question} recent review mechanism",
            "solid-state electrolyte ionic conductivity mechanism",
            "structure property relationship solid electrolyte materials project",
            "Matbench materials property prediction benchmark ionic conductivity",
            "machine learning solid electrolyte discovery open dataset",
        ],
        databases=[
            "OpenAlex",
            "Semantic Scholar (optional)",
            "arXiv",
            "Crossref",
            "DataCite",
            "Materials Project",
            "Matbench",
            "local PDF evidence ledger",
        ],
        tools_to_call=[
            "literature_router",
            "openalex_search",
            *semantic_tool,
            *arxiv_tool,
            *browser_tool,
            "layered_citation_verifier",
            "pdf_parser",
            "materials_project_profile",
            "matbench_profile",
            "evidence_ledger",
            "hypothesis_generator",
            "critic_debate",
            "experiment_designer",
            "report_writer",
        ],
        evidence_requirements=[
            "Every literature claim must include title, year, source URL or DOI, and verification status.",
            "Mechanism claims must be linked to quoted or summarized evidence snippets.",
            "Dataset feasibility claims must include source, target variable, task type, and availability.",
            "Experiment claims must separate expected outcomes from verified results.",
        ],
        workflow_plan=[
            "planner: decompose the research question into sub-questions and source plans",
            "literature_search: retrieve candidate papers from OpenAlex, optional Semantic Scholar, arXiv, and browser captures",
            "citation_verification: verify arXiv ID, DOI/title/year, DataCite, and title-search metadata before using citations",
            "evidence_ledger: extract mechanism, dataset, limitation, and method facts",
            "scientific_data_profile: profile Materials Project and Matbench-compatible data",
            "hypothesis_debate: generate, critique, and revise candidate hypotheses",
            "experiment_design: define baseline, metric, dataset split, and failure modes",
            "report_writer: produce the competition-format research plan with citation audit",
        ],
        success_criteria=[
            "At least three research sub-questions are actionable by later agents.",
            "Search queries cover literature mechanisms, datasets, and baseline methods.",
            "The plan names both citation-verification and experiment-design steps.",
            "Risk controls prevent unsupported literature or result claims.",
        ],
        risk_controls=[
            "Reject unverified citations before report writing.",
            "Mark browser/PDF facts as unverified until citation metadata matches.",
            "Do not treat baseline result cards as universal scientific conclusions.",
            "Keep hypotheses bounded to available data and measurable metrics.",
        ],
        perspectives=perspectives,
    )


def _seismic_fallback_plan(
    run: ResearchRun,
    browser_tool: list[str],
    arxiv_tool: list[str],
    semantic_tool: list[str],
) -> PlannerPlan:
    perspectives = _seismic_fallback_perspectives(run)
    return PlannerPlan(
        research_objective=run.question,
        domain=run.domain,
        constraints_summary=[
            "Use only real, verifiable seismology and deep-learning literature records.",
            f"Collect at most {run.constraints.max_papers} papers before citation verification.",
            "Treat event labels such as earthquake, blast, collapse, induced event, noise, and non-event as task examples, not a fixed taxonomy.",
            "Produce an experiment plan with seismic datasets, model baselines, metrics, and failure modes.",
        ],
        sub_questions=[
            "Which deep-learning architectures are used for seismic waveform event detection or classification?",
            "Which label spaces and datasets support earthquake, blast, induced-event, collapse, noise, or non-event discrimination?",
            "Which open code baselines are method/model repositories rather than dataset-only repositories?",
            "Which metrics, splits, and station/region transfer tests make the improvement falsifiable?",
        ],
        search_queries=[
            "seismic event classification deep learning waveform",
            "earthquake explosion discrimination waveform classification deep learning",
            "seismic phase picking phase classification PhaseNet EQTransformer",
            "earthquake detection seismic waveform CNN transformer",
            "microseismic event classification deep learning",
            "SeisBench STEAD INSTANCE seismic waveform classification benchmark",
            "natural earthquake quarry blast noise classification seismic",
        ],
        databases=[
            "OpenAlex",
            "Semantic Scholar (optional)",
            "arXiv",
            "Crossref",
            "DataCite",
            "SeisBench",
            "STEAD",
            "INSTANCE",
            "local PDF evidence ledger",
        ],
        tools_to_call=[
            "literature_router",
            "openalex_search",
            *semantic_tool,
            *arxiv_tool,
            *browser_tool,
            "layered_citation_verifier",
            "pdf_parser",
            "seismic_data_profile",
            "baseline_discovery",
            "repository_verifier",
            "evidence_ledger",
            "hypothesis_generator",
            "critic_debate",
            "experiment_designer",
            "report_writer",
        ],
        evidence_requirements=[
            "Every literature claim must include title, year, source URL or DOI, and verification status.",
            "Dataset claims must name label taxonomy, waveform/source domain, availability, and split assumptions.",
            "Baseline claims must distinguish method/model code from dataset-only repositories.",
            "Experiment claims must separate expected outcomes from verified results.",
        ],
        workflow_plan=[
            "planner: decompose seismic event classification into task, data, baseline, and metric questions",
            "literature_search: retrieve seismology-specific papers from OpenAlex, optional Semantic Scholar, arXiv, and browser captures",
            "citation_verification: verify arXiv ID, DOI/title/year, DataCite, and title-search metadata before using citations",
            "paper_classification: mark papers as method_model, dataset_benchmark, survey_review, application_only, or excluded",
            "baseline_discovery: find code from eligible method papers and per-paper seismic GitHub/PapersWithCode search",
            "repository_verification: reject dataset-only, non-seismic, or unrelated code repositories",
            "hypothesis_debate: generate, critique, and rank candidate model-improvement paths",
            "experiment_design: define dataset, baseline, metric, split, ablation, and failure modes",
            "report_writer: produce the competition-format research plan with citation audit",
        ],
        success_criteria=[
            "At least half of returned papers are directly seismic-relevant when source APIs provide enough candidates.",
            "At least two papers are method/model candidates or the run honestly reports baseline insufficiency.",
            "Search queries cover waveform classification, phase picking/detection, datasets, and executable baselines.",
            "Risk controls prevent generic ML, medical, dataset-only, or unrelated code from becoming baselines.",
        ],
        risk_controls=[
            "Reject or down-rank generic deep-learning papers without seismic waveform/event evidence.",
            "Reject dataset-only repositories as model baselines.",
            "Do not assume a fixed four-class taxonomy; record each paper's actual labels and dataset.",
            "Keep hypotheses bounded to available seismic data and measurable metrics.",
        ],
        perspectives=perspectives,
    )


def _normalize_plan(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback

    normalized = dict(fallback)
    normalized.update(content)
    for key in (
        "constraints_summary",
        "sub_questions",
        "search_queries",
        "databases",
        "tools_to_call",
        "evidence_requirements",
        "workflow_plan",
        "success_criteria",
        "risk_controls",
    ):
        normalized[key] = _string_list(normalized.get(key), fallback.get(key, []))
    normalized["perspectives"] = _perspectives(normalized.get("perspectives"), fallback.get("perspectives", []))

    normalized["research_objective"] = str(
        normalized.get("research_objective") or fallback["research_objective"]
    ).strip()
    normalized["domain"] = str(normalized.get("domain") or fallback["domain"]).strip()
    return PlannerPlan.model_validate(normalized).model_dump()


def _fallback_perspectives(run: ResearchRun) -> list[PerspectiveQuestion]:
    return [
        PerspectiveQuestion(
            perspective="domain_mechanism",
            role="Materials scientist",
            question="Which mechanisms repeatedly connect composition, structure, transport pathways, and stability?",
            search_query=f"{run.question} mechanism structure transport stability",
            evidence_requirement="At least one verified paper must support each mechanism or limitation claim.",
            risk_control="Avoid claiming a mechanism is causal unless the cited paper reports causal or experimental evidence.",
        ),
        PerspectiveQuestion(
            perspective="ml_data",
            role="Machine-learning scientist",
            question="Which open datasets, descriptors, baselines, and metrics can make the hypothesis testable?",
            search_query="solid electrolyte machine learning dataset baseline descriptors metrics",
            evidence_requirement="Dataset feasibility claims must name source, target variable, task type, and metric.",
            risk_control="Separate executable baseline results from expected future outcomes.",
        ),
        PerspectiveQuestion(
            perspective="experimental_validation",
            role="Experimental scientist",
            question="What measurements or validation protocols would make the hypothesis falsifiable?",
            search_query="solid electrolyte ionic conductivity stability experimental validation impedance",
            evidence_requirement="Validation claims must identify measurable properties and plausible experimental protocols.",
            risk_control="Flag plans that require unavailable instruments, labels, or unrealistic synthesis conditions.",
        ),
        PerspectiveQuestion(
            perspective="skeptical_reviewer",
            role="Skeptical reviewer",
            question="Where could the proposed hypothesis be overclaiming novelty, evidence strength, or generality?",
            search_query="solid electrolyte review limitations machine learning discovery reproducibility",
            evidence_requirement="Novelty and limitation claims must cite verified related work or be marked as audit-only.",
            risk_control="Downgrade unsupported novelty claims into risks or future work.",
        ),
        PerspectiveQuestion(
            perspective="application_translation",
            role="Application reviewer",
            question="What practical constraints affect whether the hypothesis is useful for battery materials screening?",
            search_query="solid-state battery electrolyte screening practical constraints stability manufacturability",
            evidence_requirement="Application claims must be grounded in literature or dataset constraints.",
            risk_control="Avoid claiming industrial readiness from proxy benchmark results.",
        ),
    ]


def _seismic_fallback_perspectives(run: ResearchRun) -> list[PerspectiveQuestion]:
    return [
        PerspectiveQuestion(
            perspective="seismology_task",
            role="Seismologist",
            question="Which event types, waveform windows, stations, and label definitions are used in seismic event classification papers?",
            search_query="seismic event classification earthquake blast noise waveform labels",
            evidence_requirement="Task claims must cite papers that describe seismic waveforms, event labels, and data provenance.",
            risk_control="Do not collapse all papers into a fixed four-class taxonomy; preserve each paper's label space.",
        ),
        PerspectiveQuestion(
            perspective="ml_model_baseline",
            role="Machine-learning scientist",
            question="Which neural architectures provide reusable baselines for seismic waveform detection, phase picking, or event classification?",
            search_query="seismic waveform classification deep learning CNN transformer PhaseNet EQTransformer",
            evidence_requirement="Baseline claims must name model architecture, code availability, metric, and dataset when available.",
            risk_control="Reject generic ML/model papers without seismic-domain evidence.",
        ),
        PerspectiveQuestion(
            perspective="data_benchmark",
            role="Data benchmark reviewer",
            question="Which open seismic datasets or benchmarks can support bounded evaluation without confusing dataset papers with model baselines?",
            search_query="STEAD INSTANCE SeisBench seismic waveform dataset benchmark event classification",
            evidence_requirement="Dataset claims must name source, labels, split constraints, and availability.",
            risk_control="Mark dataset-only papers and repos as provenance, not model baselines.",
        ),
        PerspectiveQuestion(
            perspective="experimental_validation",
            role="Experimental ML evaluator",
            question="Which metrics and validation protocols test robustness across station, region, magnitude, noise, and transfer settings?",
            search_query="seismic event classification metrics cross station generalization waveform deep learning",
            evidence_requirement="Experiment plans must include dataset split, baseline, metric, and failure conditions.",
            risk_control="Separate planned experiments from executed results.",
        ),
        PerspectiveQuestion(
            perspective="skeptical_reviewer",
            role="Skeptical reviewer",
            question="Where could the proposed improvement overclaim novelty, baseline strength, or dataset generalization?",
            search_query="seismic deep learning event detection classification limitations reproducibility",
            evidence_requirement="Novelty and limitation claims must cite verified related work or be marked as audit-only.",
            risk_control="Downgrade unsupported novelty or performance claims into risks or future work.",
        ),
    ]


def _perspectives(value: object, fallback: object) -> list[dict]:
    fallback_items = fallback if isinstance(fallback, list) else []
    if not isinstance(value, list):
        return fallback_items
    cleaned = []
    for item in value:
        if not isinstance(item, dict):
            continue
        candidate = {
            "perspective": str(item.get("perspective") or "").strip(),
            "role": str(item.get("role") or "").strip(),
            "question": str(item.get("question") or "").strip(),
            "search_query": str(item.get("search_query") or "").strip(),
            "evidence_requirement": str(item.get("evidence_requirement") or "").strip(),
            "risk_control": str(item.get("risk_control") or "").strip(),
        }
        if all(candidate.values()):
            cleaned.append(candidate)
    return cleaned or fallback_items


def _string_list(value: object, fallback: object) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = fallback if isinstance(fallback, list) else []
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return cleaned or [str(item).strip() for item in fallback if str(item).strip()]
