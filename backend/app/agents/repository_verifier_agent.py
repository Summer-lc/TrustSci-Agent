"""RepositoryVerifierAgent — LCEL agent that judges repo–paper match and reproducibility.

Fetches repo metadata, file tree, README, and latest commit via
``GithubBaselineClient``, then runs an LCEL chain
(``PromptTemplate | LLMClientRunnable | RepoVerdictParser``) to score
reproducibility and infer a run command.  When the LLM returns garbage
(or ``None``), the parser falls back to a deterministic heuristic based
on README / requirements / license / commit presence.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable, build_agent_prompt
from app.schemas.baseline import BaselineCandidate
from app.tools.baseline_sources import GithubBaselineClient

SYSTEM_PROMPT = """You are the Repository Verifier for TrustSci-Agent v3.
Given a baseline candidate (paper title + repo URL) and the repo's metadata, README excerpt, file tree, and latest commit, judge whether the repo matches the paper and how reproducible it is.
Return JSON only with keys:
- matches_paper: bool
- reproducibility_score: float in [0,1]
- reproduction_status: one of "verified", "suspicious", "failed"
- run_command: string or null (best-guess run command from README, e.g. "python train.py --config config.yaml")
- risks: list of strings
- reason: one sentence
- repo_type: one of "model_code", "dataset_only", "benchmark_suite", "docs_only", "unknown"
- is_model_baseline: bool (true only if repo_type is model_code AND it implements a trainable/evaluable model)
- matches_paper_method: bool (repo implements the paper's method)
- matches_task_domain: bool (repo and paper are directly relevant to seismic event classification/waveform/phase/event detection tasks)
A dataset-only repo must NOT be is_model_baseline=true.
Generic ML/model repos outside the seismic domain must NOT be verified as baselines.
Do not invent files or commands not suggested by the README/file tree."""

USER_TEMPLATE = """Paper title: {paper_title}
Repo URL: {code_url}
Repo metadata: {metadata}
File tree: {file_tree}
Latest commit: {commit}
README excerpt: {readme}

Judge repo match and reproducibility."""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)
MIN_VERIFIED_REPRO_SCORE = 0.6


class RepoVerdictParser(Runnable):
    """LangChain ``Runnable`` that normalizes LLM content, falling back on error."""

    def __init__(self, fallback: dict) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> dict:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)


class RepositoryVerifierAgent:
    """LLM-backed repo verifier with deterministic heuristic fallback."""

    def __init__(self, llm: LLMClient, github: GithubBaselineClient) -> None:
        self.llm = llm
        self.github = github

    async def arun(self, candidate: BaselineCandidate, *, run_id: str) -> BaselineCandidate:
        metadata = await self.github.repo_metadata(candidate.code_url or "") or {}
        file_tree = await self.github.repo_file_tree(candidate.code_url or "") or []
        readme = (await self.github.repo_readme(candidate.code_url or "") or "")[:1500]
        commit = await self.github.latest_commit(candidate.code_url or "")
        fallback = _heuristic_verdict(candidate, metadata, file_tree, commit, readme)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run_id, agent="repo_verifier")
            | RepoVerdictParser(fallback=fallback)
        )
        verdict = await chain.ainvoke(_prompt_vars(candidate, metadata, file_tree, readme, commit))
        return _apply(candidate, verdict, metadata)


def _prompt_vars(
    candidate: BaselineCandidate,
    metadata: dict[str, Any],
    file_tree: list[str],
    readme: str,
    commit: str | None,
) -> dict[str, str]:
    user_prompt = USER_TEMPLATE.format(
        paper_title=candidate.paper_title,
        code_url=candidate.code_url or "",
        metadata=json.dumps(metadata, ensure_ascii=False),
        file_tree=", ".join(file_tree) if file_tree else "(empty)",
        commit=commit or "unknown",
        readme=readme or "(no README)",
    )
    return {"user_prompt": user_prompt}


def _normalize(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback
    status = str(content.get("reproduction_status", fallback["reproduction_status"]))
    if status not in {"verified", "suspicious", "failed"}:
        status = fallback["reproduction_status"]
    repo_type = str(content.get("repo_type", fallback["repo_type"]))
    if repo_type not in {"model_code", "dataset_only", "benchmark_suite", "docs_only", "unknown"}:
        repo_type = fallback["repo_type"]
    is_model = bool(content.get("is_model_baseline", fallback["is_model_baseline"])) if repo_type != "dataset_only" else False
    return {
        "matches_paper": bool(content.get("matches_paper", fallback["matches_paper"])),
        "matches_paper_method": bool(content.get("matches_paper_method", fallback["matches_paper_method"])),
        "matches_task_domain": bool(content.get("matches_task_domain", fallback["matches_task_domain"])),
        "reproducibility_score": _score(content.get("reproducibility_score", fallback["reproducibility_score"])),
        "reproduction_status": status,
        "run_command": _opt_str(content.get("run_command")),
        "risks": _string_list(content.get("risks")) or fallback["risks"],
        "reason": _opt_str(content.get("reason")) or fallback["reason"],
        "repo_type": repo_type,
        "is_model_baseline": is_model,
    }


def _heuristic_verdict(
    candidate: BaselineCandidate,
    metadata: dict[str, Any],
    file_tree: list[str],
    commit: str | None,
    readme: str = "",
) -> dict[str, Any]:
    tree_lower = {f.lower() for f in file_tree}
    name_lower = (candidate.code_url or "").lower()
    looks_dataset = any(k in name_lower for k in ("dataset", "data")) or any(
        f.startswith("data") or f == "data" for f in tree_lower)
    has_model_files = any("train" in f or "model" in f or "eval" in f for f in tree_lower)
    if looks_dataset and not has_model_files:
        repo_type = "dataset_only"
        is_model = False
    elif has_model_files:
        repo_type = "model_code"
        is_model = True
    else:
        repo_type = "unknown"
        is_model = False
    has_readme = any("readme" in f for f in tree_lower)
    has_reqs = any(
        "requirements" in f or "environment.yml" in f or "setup.py" in f or "pyproject.toml" in f
        for f in tree_lower
    )
    has_license = bool(metadata.get("license"))
    score = (
        0.3
        + (0.2 if has_readme else 0)
        + (0.2 if has_reqs else 0)
        + (0.15 if has_license else 0)
        + (0.15 if commit else 0)
    )
    matches_domain = _matches_seismic_domain(candidate, metadata, file_tree, readme)
    status = (
        "verified" if (has_readme and has_reqs and score >= 0.7 and is_model and matches_domain)
        else ("suspicious" if score >= 0.4 else "failed")
    )
    risks: list[str] = []
    if not has_reqs:
        risks.append("no requirements/environment file — dependency versions unclear")
    if not has_license:
        risks.append("no license — reuse restricted")
    if not has_readme:
        risks.append("no README — run instructions unclear")
    return {
        "matches_paper": True,
        "matches_paper_method": is_model,
        "matches_task_domain": matches_domain,
        "reproducibility_score": round(min(1.0, score), 2),
        "reproduction_status": status,
        "run_command": None,
        "risks": risks,
        "reason": "Heuristic verdict from file tree.",
        "repo_type": repo_type,
        "is_model_baseline": is_model,
    }


def _apply(candidate: BaselineCandidate, verdict: dict[str, Any], metadata: dict[str, Any]) -> BaselineCandidate:
    updated = candidate.model_copy(deep=True)
    updated.repo_type = verdict["repo_type"]
    updated.is_model_baseline = verdict["is_model_baseline"]
    updated.matches_task_domain = verdict["matches_task_domain"]
    effective_status = verdict["reproduction_status"]
    if effective_status == "verified" and verdict["reproducibility_score"] < MIN_VERIFIED_REPRO_SCORE:
        effective_status = "suspicious"
    # dataset-only can never be a verified model baseline
    if verdict["repo_type"] == "dataset_only":
        updated.verified_repo = False
        updated.reproduction_status = "failed"
        updated.is_model_baseline = False
        updated.baseline_rejection_reason = "dataset-only repo, not a model baseline"
    else:
        updated.verified_repo = (
            bool(verdict["matches_paper"])
            and verdict["is_model_baseline"]
            and verdict["matches_task_domain"]
            and effective_status == "verified"
            and verdict["reproducibility_score"] >= MIN_VERIFIED_REPRO_SCORE
        )
        updated.reproduction_status = effective_status
        if not updated.verified_repo and not verdict["is_model_baseline"]:
            updated.baseline_rejection_reason = (
                updated.baseline_rejection_reason
                or f"repo_type={verdict['repo_type']}, not a model baseline"
            )
        elif not updated.verified_repo and not verdict["matches_paper"]:
            updated.baseline_rejection_reason = (
                updated.baseline_rejection_reason
                or "repo does not match the candidate paper"
            )
        elif not updated.verified_repo and not verdict["matches_task_domain"]:
            updated.baseline_rejection_reason = (
                updated.baseline_rejection_reason
                or "repo/paper is not seismic-event-classification relevant"
            )
        elif not updated.verified_repo and verdict["reproducibility_score"] < MIN_VERIFIED_REPRO_SCORE:
            updated.baseline_rejection_reason = (
                updated.baseline_rejection_reason
                or f"reproducibility_score below {MIN_VERIFIED_REPRO_SCORE:.2f}"
            )
        elif not updated.verified_repo and effective_status != "verified":
            updated.baseline_rejection_reason = (
                updated.baseline_rejection_reason
                or f"reproduction_status={effective_status}"
            )
    updated.reproducibility_score = verdict["reproducibility_score"]
    updated.run_command = verdict["run_command"]
    risks = list(candidate.risks)
    for r in verdict["risks"]:
        if r not in risks:
            risks.append(r)
    updated.risks = risks
    if metadata.get("license") and not updated.license:
        updated.license = metadata.get("license")
    if metadata.get("stars"):
        updated.stars = int(metadata.get("stars") or 0)
    updated.baseline_priority_score = _priority_score(updated, verdict)
    return updated


def _priority_score(c: BaselineCandidate, verdict: dict) -> float:
    """Post-verify priority: weighted sum of repo/model signals minus dataset penalty."""
    repo_model = 1.0 if verdict["is_model_baseline"] else 0.0
    match = 1.0 if verdict.get("matches_paper_method") else 0.0
    domain = 1.0 if verdict.get("matches_task_domain") else 0.0
    repro = verdict["reproducibility_score"]
    stars = min(1.0, (c.stars or 0) / 50.0)
    penalty = 0.5 if verdict["repo_type"] == "dataset_only" else 0.0
    score = 0.35 * repo_model + 0.20 * match + 0.25 * domain + 0.15 * repro + 0.05 * stars - penalty
    return round(max(0.0, min(1.0, score)), 3)


_SEISMIC_POSITIVE = (
    "seismic", "earthquake", "quake", "seismology", "seismogram", "waveform",
    "phase picking", "phase-picking", "event detection", "event-detection",
    "earthquake detection", "earthquake classification", "seismic phase",
    "eqtransformer", "eq transformer", "stead", "seisbench", "obspy",
    "microseismic", "aftershock", "explosion", "blast", "seismic signal",
)

_CROSS_DOMAIN_NEGATIVE = (
    "covid", "sentiment", "nlp", "twitter", "stock", "finance", "medical",
    "xray", "x-ray", "remote sensing", "remote-sensing", "image classification",
    "recommender", "recommendation", "malware", "lung", "tumor", "cancer",
    "gaussian radial basis", "active subspace", "polynomial chaos",
)


def _matches_seismic_domain(
    candidate: BaselineCandidate,
    metadata: dict[str, Any],
    file_tree: list[str],
    readme: str,
) -> bool:
    text = " ".join(
        [
            candidate.paper_title or "",
            candidate.code_url or "",
            str(metadata.get("full_name") or ""),
            str(metadata.get("description") or ""),
            " ".join(file_tree or []),
            readme[:800] if readme else "",
        ]
    ).lower()
    if any(k in text for k in _CROSS_DOMAIN_NEGATIVE):
        return False
    return any(k in text for k in _SEISMIC_POSITIVE)


def _score(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []
