import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.paper import Paper

SYSTEM_PROMPT = """You are the Paper Type Classifier for TrustSci-Agent v3 baseline quality gate.
Classify each paper into exactly one paper_role:
- method_model: the paper proposes/implements a model or method (potential baseline with code)
- dataset_benchmark: the paper introduces a dataset or benchmark (dataset provenance only, NOT a model baseline)
- survey_review: a survey/review paper (no original method)
- application_only: applies existing methods without a reusable model artifact
- unknown: cannot determine
Also determine whether each paper is directly relevant to seismic event classification, seismic waveform/event detection, seismic phase picking, earthquake/explosion discrimination, or closely related seismology tasks.
Return JSON only: {"papers": [{"paper_id": "...", "paper_role": "...", "seismic_relevant": true/false, "reason": "..."}]}.
Only papers that are BOTH method_model and seismic_relevant are baseline-eligible. Generic machine-learning/math papers are not baseline-eligible even if they propose a model. Do not invent citations."""

USER_TEMPLATE = """Papers:
{papers_json}

Classify each paper's role."""


class PaperTypeClassifierAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, papers: list[Paper], *, run_id: str) -> list[Paper]:
        fallback = {p.paper_id: _fallback_role(p) for p in papers}
        if self.llm is None:
            _apply_roles(papers, fallback)
            return papers
        prompt = build_agent_prompt(SYSTEM_PROMPT)
        chain = (
            prompt
            | LLMClientRunnable(self.llm).bind(fallback={"papers": []}, run_id=run_id, agent="paper_classifier")
            | FallbackParser(lambda content: _normalize(content, papers, fallback), {p.paper_id: _fallback_role(p) for p in papers})
        )
        normalized = await chain.ainvoke({"user_prompt": USER_TEMPLATE.format(papers_json=_payload(papers))})
        _apply_roles(papers, normalized)
        return papers


def _payload(papers: list[Paper]) -> str:
    return json.dumps([{"paper_id": p.paper_id, "title": p.title, "abstract": (p.abstract or "")[:400]} for p in papers], ensure_ascii=False)


def _normalize(content, papers: list[Paper], fallback: dict) -> dict:
    if not isinstance(content, dict) or not isinstance(content.get("papers"), list):
        return fallback
    by_id = {str(r.get("paper_id")): r for r in content["papers"] if isinstance(r, dict) and r.get("paper_id")}
    out: dict = {}
    for p in papers:
        raw = by_id.get(p.paper_id)
        role = str(raw.get("paper_role", "")).strip() if isinstance(raw, dict) else ""
        if role not in {"method_model", "dataset_benchmark", "survey_review", "application_only", "unknown"}:
            out[p.paper_id] = fallback[p.paper_id]
        else:
            reason = str(raw.get("reason") or "").strip() if isinstance(raw, dict) else ""
            seismic_relevant = bool(raw.get("seismic_relevant", fallback[p.paper_id].get("seismic_relevant", False)))
            # Local guardrail: never let a generic model paper become baseline-eligible
            # unless the title/abstract has seismic-domain evidence.
            seismic_relevant = seismic_relevant and _is_seismic_relevant(p)
            out[p.paper_id] = {"paper_role": role, "seismic_relevant": seismic_relevant, "reason": reason}
    return out


def _apply_roles(papers: list[Paper], roles: dict) -> None:
    for p in papers:
        r = roles.get(p.paper_id, {"paper_role": "unknown", "seismic_relevant": False, "reason": ""})
        p.paper_role = r.get("paper_role", "unknown")
        p.seismic_relevant = bool(r.get("seismic_relevant", False))
        p.baseline_eligible = (p.paper_role == "method_model" and p.seismic_relevant)
        if p.baseline_eligible:
            p.baseline_rejection_reason = None
        elif p.paper_role == "method_model" and not p.seismic_relevant:
            p.baseline_rejection_reason = "method/model paper, but not seismic-event-classification relevant"
        else:
            p.baseline_rejection_reason = r.get("reason") or f"role={p.paper_role}"


def _fallback_role(paper: Paper) -> dict:
    text = f"{paper.title or ''} {paper.abstract or ''}".lower()
    seismic_relevant = _is_seismic_relevant(paper)
    if any(k in text for k in ("dataset", "benchmark", "data set")):
        return {"paper_role": "dataset_benchmark", "seismic_relevant": seismic_relevant, "reason": "title/abstract indicates a dataset"}
    if any(k in text for k in ("survey", "review", "a review of")):
        return {"paper_role": "survey_review", "seismic_relevant": seismic_relevant, "reason": "title/abstract indicates a survey/review"}
    if any(k in text for k in ("we propose", "we present", "model", "method", "deep learning", "cnn", "transformer", "network", "classification", "detection")):
        return {"paper_role": "method_model", "seismic_relevant": seismic_relevant, "reason": "title/abstract indicates a method/model"}
    return {"paper_role": "unknown", "seismic_relevant": seismic_relevant, "reason": "could not determine"}


_SEISMIC_POSITIVE = (
    "seismic", "earthquake", "quake", "seismology", "seismogram", "waveform",
    "phase picking", "phase-picking", "event detection", "event-detection",
    "earthquake detection", "earthquake classification", "seismic phase",
    "eqtransformer", "eq transformer", "stead", "seisbench", "obspy",
    "microseismic", "aftershock", "explosion", "blast", "seismic signal",
)

_GENERIC_OR_CROSS_DOMAIN = (
    "gaussian radial basis", "active subspace", "polynomial chaos",
    "mathematics of deep learning", "sentiment", "covid", "recommender",
    "recommendation", "xray", "x-ray", "lung", "tumor", "cancer",
)


def _is_seismic_relevant(paper: Paper) -> bool:
    text = f"{paper.title or ''} {paper.abstract or ''}".lower()
    if any(k in text for k in _GENERIC_OR_CROSS_DOMAIN):
        return False
    return any(k in text for k in _SEISMIC_POSITIVE)
