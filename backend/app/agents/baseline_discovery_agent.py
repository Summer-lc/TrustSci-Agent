"""BaselineDiscoveryAgent — deterministic tool orchestrator (no LLM).

Searches GitHub + Papers with Code using paper titles and the user-supplied
task description, assembles a deduplicated list of BaselineCandidate records,
and degrades gracefully to an empty list when no sources return results.

This agent only provides initial heuristics. Deep reproducibility scoring and
risk analysis are the job of RepositoryVerifier (Task 5).
"""
from __future__ import annotations

import re
from typing import Any

from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.tools.baseline_sources import GithubBaselineClient, PapersWithCodeClient


# Defensive caps — keep discovery bounded even if callers pass long lists.
MAX_PAPERS = 5
MAX_GITHUB_PER_PAPER = 3
MAX_PWC_RESULTS = 5
MAX_CANDIDATES = 15

# Words that carry little signal for a code search; stripped from queries.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with",
    "by", "from", "as", "at", "is", "are", "was", "were", "be", "been",
    "using", "based", "via", "towards", "toward", "its", "their", "our",
    "we", "new", "novel", "approach", "method", "model", "framework",
}
_PUNCT_RE = re.compile(r"[^\w\s]+")


# Cheap relevance pre-filter for GitHub search results (NOT a recall mechanism;
# the S5 feedback loop handles "no baselines found -> re-search literature").
# A repo is kept only if it hits a seismic positive keyword and no cross-domain
# negative keyword in its name/description. Paper-self-declared code_url
# candidates bypass this filter (the RepositoryVerifier judges those).
_SEISMIC_POSITIVE = {
    "seismic", "earthquake", "quake", "seismology", "seismogram", "waveform",
    "phase picking", "phase-picking", "event detection", "event-detection",
    "seisbench", "obspy", "stead", "instance", "eqtransformer", "eq transformer",
    "microseismic", "aftershock", "explosion", "blast", "discrimination",
}
_CROSS_DOMAIN_NEGATIVE = {
    "covid", "sentiment", "nlp", "twitter", "stock", "finance", "medical",
    "xray", "x-ray", "remote sensing", "remote-sensing", "image classification",
    "recommender", "recommendation", "malware", "lung", "tumor", "cancer",
}


def _is_relevant_repo(repo: dict[str, Any]) -> bool:
    """Keep a GitHub repo only if it looks seismic-relevant (positive keyword hit,
    no cross-domain negative hit). Conservative pre-filter, not full recall."""
    text = f"{repo.get('full_name', '')} {repo.get('description', '')}".lower()
    if not any(kw in text for kw in _SEISMIC_POSITIVE):
        return False
    if any(kw in text for kw in _CROSS_DOMAIN_NEGATIVE):
        return False
    return True


class BaselineDiscoveryAgent:
    """Deterministic baseline discovery: search GitHub + Papers with Code by
    paper titles/task, build BaselineCandidate list with initial heuristics.

    No LLM call here — pure tool orchestration. RepositoryVerifier (Task 5)
    deepens reproducibility_score/risks per candidate.
    """

    def __init__(
        self,
        github: GithubBaselineClient,
        pwc: PapersWithCodeClient,
    ) -> None:
        self.github = github
        self.pwc = pwc

    async def arun(
        self,
        papers: list[Paper],
        task: str,
        *,
        run_id: str,
    ) -> list[BaselineCandidate]:
        candidates: list[BaselineCandidate] = []
        seen_urls: set[str] = set()

        # Only consider baseline-eligible papers for all paper-based passes.
        eligible = [p for p in (papers or [])[:MAX_PAPERS] if p.baseline_eligible]

        # 0) Papers that self-declare a code link (abstract/PDF mining) — highest confidence.
        for paper in eligible:
            url = (paper.code_url or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(_candidate_from_paper_code_url(paper, task))

        # 1) GitHub: one query per eligible paper (capped).
        for paper in eligible:
            query = _search_query(paper, task)
            if not query:
                continue
            try:
                repos = await self.github.search_repos(query, limit=MAX_GITHUB_PER_PAPER)
            except Exception:
                repos = []
            for repo in repos or []:
                if not _is_relevant_repo(repo):
                    continue
                url = (repo.get("html_url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(_candidate_from_github(paper, repo, task))

        # 2) Papers with Code: one task-scoped query.
        try:
            pwc_items = await self.pwc.search(task or "", limit=MAX_PWC_RESULTS)
        except Exception:
            pwc_items = []
        for item in pwc_items or []:
            url = (item.get("code_url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(_candidate_from_pwc(item, task))

        return candidates[:MAX_CANDIDATES]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_query(paper: Paper, task: str = "") -> str:
    """Build a compact GitHub search query from paper title only.

    Returns only the top 4 distinctive title tokens (drops stopwords/punctuation,
    takes first 4). Does NOT append task tokens — keeps per-paper queries short
    because GitHub ANDs all terms and long queries return 0 results.
    Capped at 60 chars.
    """
    base = paper.title or paper.arxiv_id or ""
    tokens = _tokenize(base)
    # Preserve order, drop dupes and stopwords; take only top 4.
    seen: set[str] = set()
    kept: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if not low or low in _STOPWORDS or low in seen:
            continue
        seen.add(low)
        kept.append(tok)
        if len(kept) >= 4:
            break
    query = " ".join(kept)
    return query[:60].strip()


def _task_query(task: str) -> str:
    """Build a short GitHub search query from the task description.

    Drops stopwords and duplicates, capped at 60 chars. Used for a broad
    task-level search that complements the narrower per-paper queries.
    """
    tokens = _tokenize(task)
    seen: set[str] = set()
    kept: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if not low or low in _STOPWORDS or low in seen:
            continue
        seen.add(low)
        kept.append(tok)
    query = " ".join(kept)
    return query[:60].strip()


def _tokenize(text: str) -> list[str]:
    cleaned = _PUNCT_RE.sub(" ", text or "")
    return cleaned.split()


def _stable_id(seed: tuple[Any, ...]) -> str:
    return f"baseline_{abs(hash(seed)) % 10**8:08d}"


def _initial_priority_score(candidate: BaselineCandidate, *, paper_role: str = "unknown") -> float:
    """Compute an initial priority score (pre-verify) from paper_role, stars,
    and a repo-name dataset heuristic. Returns 0.0–1.0.
    """
    url = (candidate.code_url or "").lower()
    name_looks_dataset = any(k in url for k in ("dataset", "data"))
    paper_method = 1.0 if paper_role == "method_model" else 0.4
    repo_model_signal = 0.0 if name_looks_dataset else 0.5
    stars = min(1.0, (candidate.stars or 0) / 50.0)
    penalty = 0.5 if name_looks_dataset else 0.0
    score = 0.30 * paper_method + 0.30 * repo_model_signal + 0.05 * stars - penalty
    return round(max(0.0, min(1.0, score)), 3)


def _candidate_from_paper_code_url(paper: Paper, task: str) -> BaselineCandidate:
    """Build a high-confidence candidate from a paper's self-declared code URL."""
    url = paper.code_url or ""
    name_looks_dataset = any(k in url.lower() for k in ("dataset", "data"))
    repo_type = "dataset_only" if name_looks_dataset else "model_code"
    is_model = not name_looks_dataset
    source = paper.code_url_source or "paper_abstract"
    cand = BaselineCandidate(
        baseline_id=_stable_id(("paper", paper.paper_id, url)),
        paper_id=paper.paper_id,
        paper_title=paper.title,
        paper_doi=paper.doi,
        paper_url=paper.source_url,
        code_url=url,
        code_source=source,
        task_match=task,
        input_type="unknown",
        license=None,
        verified_repo=False,
        reproduction_status="pending" if is_model else "failed",
        repo_type=repo_type,
        is_model_baseline=is_model,
        matches_task_domain=True,
        baseline_rejection_reason=None if is_model else "dataset-only repo (paper-declared)",
        stars=0,
    )
    cand.baseline_priority_score = _initial_priority_score(cand, paper_role=paper.paper_role)
    return cand


def _candidate_from_github(paper: Paper, repo: dict[str, Any], task: str) -> BaselineCandidate:
    cand = BaselineCandidate(
        baseline_id=_stable_id((paper.paper_id, repo.get("full_name", ""))),
        paper_id=paper.paper_id,
        paper_title=paper.title,
        paper_doi=paper.doi,
        paper_url=paper.source_url,
        code_url=repo.get("html_url"),
        code_source="github_search",
        task_match=task,
        input_type="unknown",
        license=repo.get("license"),
        risks=_github_risks(repo),
        stars=int(repo.get("stars") or 0),
        matches_task_domain=True,
    )
    cand.baseline_priority_score = _initial_priority_score(cand, paper_role=paper.paper_role)
    return cand




def _candidate_from_pwc(item: dict[str, Any], task: str) -> BaselineCandidate:
    return BaselineCandidate(
        baseline_id=_stable_id(("pwc", item.get("code_url", ""))),
        paper_id="",
        paper_title=item.get("paper_title") or "",
        code_url=item.get("code_url"),
        code_source="paperswithcode",
        task_match=task,
        input_type="unknown",
        risks=[],
        matches_task_domain="seismic" in (task or "").lower() or "earthquake" in (task or "").lower(),
    )


def _github_risks(repo: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    if not repo.get("license"):
        risks.append("no license detected — reuse may be restricted")
    open_issues = repo.get("open_issues", 0) or 0
    if open_issues > 20:
        risks.append(f"high open issue count ({open_issues}) may indicate instability")
    stars = repo.get("stars", 0) or 0
    if stars < 3:
        risks.append("low star count — maturity/reproducibility uncertain")
    return risks
