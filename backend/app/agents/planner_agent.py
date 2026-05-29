from app.schemas.run import ResearchRun
from app.llm.interface import LLMClient, LLMRequest
from app.schemas.planner import PlannerPlan


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
- tools_to_call: tool names selected from openalex_search, crossref_verify, pdf_parser, browser_capture, materials_project_profile, matbench_profile, evidence_ledger, hypothesis_generator, critic_debate, experiment_designer, report_writer
- evidence_requirements: facts that must be supported by verified sources
- workflow_plan: ordered agent workflow steps
- success_criteria: measurable criteria for a good run
- risk_controls: checks that reduce hallucination, weak evidence, or unverifiable experiments
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
        f"- enable_browser_worker: {run.constraints.enable_browser_worker}\n\n"
        "Design a verifiable AI Scientist workflow for this run. Prioritize real papers, "
        "open scientific datasets, explicit evidence requirements, and a bounded experiment plan."
    )


def _fallback_plan(run: ResearchRun) -> PlannerPlan:
    browser_tool = ["browser_capture"] if run.constraints.enable_browser_worker else []
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
            "Crossref",
            "Materials Project",
            "Matbench",
            "local PDF evidence ledger",
        ],
        tools_to_call=[
            "openalex_search",
            *browser_tool,
            "crossref_verify",
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
            "literature_search: retrieve candidate papers from scholarly APIs and browser captures",
            "citation_verification: verify DOI/title/year metadata before using citations",
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

    normalized["research_objective"] = str(
        normalized.get("research_objective") or fallback["research_objective"]
    ).strip()
    normalized["domain"] = str(normalized.get("domain") or fallback["domain"]).strip()
    return PlannerPlan.model_validate(normalized).model_dump()


def _string_list(value: object, fallback: object) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = fallback if isinstance(fallback, list) else []
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return cleaned or [str(item).strip() for item in fallback if str(item).strip()]
