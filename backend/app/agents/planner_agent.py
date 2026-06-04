from app.schemas.run import ResearchRun
from app.llm.interface import LLMClient, LLMRequest
from app.schemas.planner import PerspectiveQuestion, PlannerPlan


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
"""


class PlannerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun) -> dict:
        fallback = _fallback_plan(run).model_dump()
        response = await self.llm.complete(
            LLMRequest(
                system=SYSTEM_PROMPT,
                user=_build_user_prompt(run),
                fallback=fallback,
                run_id=run.run_id,
                agent="planner",
            )
        )
        return _normalize_plan(response.content, fallback)


def _build_user_prompt(run: ResearchRun) -> str:
    return (
        f"Domain: {run.domain}\n"
        f"Question: {run.question}\n"
        "Constraints:\n"
        f"- must_verify_citations: {run.constraints.must_verify_citations}\n"
        f"- max_papers: {run.constraints.max_papers}\n"
        f"- require_experiment_plan: {run.constraints.require_experiment_plan}\n"
        f"- enable_browser_worker: {run.constraints.enable_browser_worker}\n"
        f"- enable_semantic_scholar: {run.constraints.enable_semantic_scholar}\n"
        f"- enable_arxiv: {run.constraints.enable_arxiv}\n\n"
        "Design a verifiable AI Scientist workflow for this run. Prioritize real papers, "
        "open scientific datasets, explicit evidence requirements, and a bounded experiment plan."
    )


def _fallback_plan(run: ResearchRun) -> PlannerPlan:
    browser_tool = ["browser_capture"] if run.constraints.enable_browser_worker else []
    arxiv_tool = ["arxiv_search"] if run.constraints.enable_arxiv else []
    semantic_tool = ["semantic_scholar_search"] if run.constraints.enable_semantic_scholar else []
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
