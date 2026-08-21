import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.experiment import ExperimentPlan
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis
from app.schemas.data import DatasetProfile


SYSTEM_PROMPT = """You are the Experiment Designer Agent for TrustSci-Agent.
Convert the selected hypothesis into a bounded, verifiable experiment plan.
Return JSON only. Do not invent completed large-scale results. Do not invent existing datasets; use profile names or mark data as to be collected.

Required JSON shape:
{
  "experiment_plan": {
    "datasets": ["existing profile name or to be collected: ..."],
    "source": "historical/source data used for the hypothesis",
    "target": "target variable or data to predict/collect",
    "baselines": ["reasonable baseline"],
    "metrics": ["reasonable metric"],
    "methods": ["method or model architecture"],
    "experiment_steps": ["step"],
    "expected_results": "bounded expected result, formula, toy validation, or feasibility statement",
    "failure_modes": ["risk"],
    "possible_ablation": ["ablation"]
  }
}
Datasets must come from data_profiles unless clearly marked to be collected.
"""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)


class ExperimentDesignerAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        selected: Hypothesis | None,
        data_profiles: list[DatasetProfile] | None = None,
        evidence: list[EvidenceItem] | None = None,
        *,
        run_id: str | None = None,
    ) -> ExperimentPlan:
        fallback = self.run(selected, data_profiles)
        if self.llm is None:
            return fallback
        request_fallback = {"experiment_plan": fallback.model_dump()}
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=request_fallback, run_id=run_id, agent="experiment_designer")
            | FallbackParser(lambda content: _normalize_plan(content, fallback, data_profiles or []), fallback)
        )
        return await chain.ainvoke({"user_prompt": _build_user_prompt(selected, data_profiles or [], evidence or [])})

    def run(self, selected: Hypothesis | None, data_profiles: list[DatasetProfile] | None = None) -> ExperimentPlan:
        target = selected.statement if selected else "Validate the selected AI-generated materials hypothesis."
        datasets = [profile.name for profile in data_profiles or []] or [
            "Matbench-like open materials property table",
            "Materials Project-derived candidate metadata",
            "User-uploaded CSV for sample profiling",
        ]
        return ExperimentPlan(
            datasets=datasets,
            source="Verified literature metadata, paper abstracts/full text where available, and public materials datasets.",
            target="A bounded candidate set with composition, structure descriptors, stability indicators, and target property labels.",
            baselines=[
                "composition-only regression/ranking baseline",
                "structure-descriptor baseline",
                "literature-augmented feature baseline",
            ],
            metrics=["MAE", "R2", "top-k hit rate", "evidence coverage", "unsupported-claim count"],
            experiment_steps=[
                "Create a clean candidate table and profile missing values.",
                "Train or simulate the composition-only baseline.",
                "Add structure descriptors and compare predictive metrics.",
                "Add literature-derived mechanism tags linked to evidence IDs.",
                "Run ablation and generate a result card for the final report.",
            ],
            expected_results=f"The plan should show whether this hypothesis is feasible to test: {target}",
            failure_modes=["Insufficient labels", "feature leakage", "weak novelty against prior structure-aware models"],
        )


def _build_user_prompt(
    selected: Hypothesis | None,
    data_profiles: list[DatasetProfile],
    evidence: list[EvidenceItem],
) -> str:
    payload = {
        "selected_hypothesis": selected.model_dump() if selected else None,
        "data_profiles": [
            {
                "name": profile.name,
                "source": profile.source,
                "rows": profile.rows,
                "fields": profile.fields,
                "target": profile.target,
                "task_type": profile.task_type,
                "availability": profile.availability,
            }
            for profile in data_profiles
        ],
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "verified": item.verified,
                "eligible_for_report": item.eligible_for_report,
            }
            for item in evidence[:12]
        ],
        "instructions": [
            "Use profile names exactly when datasets already exist.",
            "Mark new datasets as 'to be collected: ...'.",
            "Expected results must be bounded or verification-pending, not completed discoveries.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_plan(
    content: object,
    fallback: ExperimentPlan,
    data_profiles: list[DatasetProfile],
) -> ExperimentPlan:
    if not isinstance(content, dict):
        return fallback
    raw = content.get("experiment_plan")
    if not isinstance(raw, dict):
        return fallback
    profile_names = {profile.name for profile in data_profiles}
    datasets = _string_list(raw.get("datasets"))
    if profile_names:
        datasets = [
            item
            for item in datasets
            if item in profile_names or item.lower().startswith("to be collected")
        ]
    if not datasets:
        datasets = fallback.datasets
    methods = _string_list(raw.get("methods"))
    steps = _string_list(raw.get("experiment_steps"))
    ablations = _string_list(raw.get("possible_ablation"))
    if methods:
        steps = [f"Method: {item}" for item in methods] + steps
    if ablations:
        steps = steps + [f"Ablation: {item}" for item in ablations]
    try:
        return ExperimentPlan(
            datasets=datasets,
            source=_clean(raw.get("source")) or fallback.source,
            target=_clean(raw.get("target")) or fallback.target,
            baselines=_string_list(raw.get("baselines")) or fallback.baselines,
            metrics=_string_list(raw.get("metrics")) or fallback.metrics,
            experiment_steps=steps or fallback.experiment_steps,
            expected_results=_clean(raw.get("expected_results")) or fallback.expected_results,
            failure_modes=_string_list(raw.get("failure_modes")) or fallback.failure_modes,
        )
    except Exception:
        return fallback


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in [_clean(raw) for raw in value] if item]


def _clean(value: object) -> str:
    return str(value or "").strip()
