import json

from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable, build_agent_prompt
from app.schemas.feedback_loop import NoveltyVerdict
from app.schemas.hypothesis import Hypothesis
from app.schemas.idea import IdeaBrief
from app.schemas.paper import Paper

SYSTEM_PROMPT = """You are the Novelty / Related Work Checker for TrustSci-Agent v3 (S5 feedback loop).
Given a hypothesis (statement + novelty_claim), the user idea, and the retrieved papers, judge whether the
hypothesis is novel by checking "same task + same core method + same validation goal".

Return JSON only with these keys:
- verdict: one of "novel", "transfer_applicability", "already_done", "dataset_only", "similar_work"
  - "novel": no prior art covers the same task+method+validation
  - "transfer_applicability": the method exists in another domain but the transfer to this domain is new
  - "already_done": a paper in the list already does the same task+method+validation
  - "dataset_only": only the dataset/benchmark is novel, the method is known
  - "similar_work": closely related work exists but does not fully replicate the hypothesis
- claim_revision: a revised (narrowed) hypothesis statement if verdict is not "novel", else null
- prior_art_paper_ids: list of paper_id strings that are prior art
- overlap_points: list of strings where the hypothesis overlaps existing work
- retainable_novelty: list of strings the hypothesis can still claim as novel
- reasoning: a short explanation of the verdict

Verdicts "novel" and "similar_work" may set claim_revision to null or a refinement.
"already_done" and "dataset_only" MUST set claim_revision to a narrowed alternative or null.
"transfer_applicability" MUST set claim_revision to a transfer-applicability restatement.

Do not invent papers. Only reference papers from the provided list."""

USER_TEMPLATE = """User idea: {user_idea}

Hypothesis:
- statement: {hyp_statement}
- novelty_claim: {hyp_novelty_claim}

Retrieved papers:
{papers_json}

Judge novelty: same task + same core method + same validation goal."""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)

_VALID_VERDICTS = {"novel", "transfer_applicability", "already_done", "dataset_only", "similar_work"}


class NoveltyVerdictParser(Runnable):
    """Normalizes LLM output to a NoveltyVerdict, falling back to a safe default."""

    def __init__(self, fallback: NoveltyVerdict) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> NoveltyVerdict:
        try:
            return _normalize_verdict(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> NoveltyVerdict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> NoveltyVerdict:
        return self.parse(input)


class NoveltyReportParser(Runnable):
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


class NoveltyCheckerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @property
    def requests(self) -> list:
        """Proxy to the underlying LLM requests (for testing / audit)."""
        return getattr(self.llm, "requests", [])

    async def arun(
        self,
        papers: list[Paper],
        hypothesis: Hypothesis | None = None,
        idea_brief: IdeaBrief | None = None,
        *,
        run_id: str,
    ) -> NoveltyVerdict:
        fallback = _fallback_verdict(papers, hypothesis, idea_brief)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback.model_dump(), run_id=run_id, agent="novelty_checker")
            | NoveltyVerdictParser(fallback=fallback)
        )
        return await chain.ainvoke(_prompt_vars(papers, hypothesis, idea_brief))


def _prompt_vars(papers: list[Paper], hypothesis: Hypothesis | None, idea_brief: IdeaBrief | None) -> dict:
    user_idea = (idea_brief.user_idea if idea_brief and idea_brief.user_idea else "")
    hyp_statement = hypothesis.statement if hypothesis else ""
    hyp_novelty_claim = hypothesis.novelty_claim if hypothesis else ""
    papers_json = [{"paper_id": p.paper_id, "title": p.title, "code_url": p.code_url, "doi": p.doi,
                     "abstract": (p.abstract or "")[:300]} for p in papers[:10]]
    user_prompt = USER_TEMPLATE.format(
        user_idea=user_idea,
        hyp_statement=hyp_statement,
        hyp_novelty_claim=hyp_novelty_claim,
        papers_json=json.dumps(papers_json, ensure_ascii=False),
    )
    return {"user_prompt": user_prompt}


def _normalize_verdict(content: object, fallback: NoveltyVerdict) -> NoveltyVerdict:
    if not isinstance(content, dict):
        return fallback
    verdict = str(content.get("verdict", "")).strip()
    if verdict not in _VALID_VERDICTS:
        return fallback
    claim_revision = content.get("claim_revision")
    if claim_revision is not None:
        claim_revision = str(claim_revision).strip() or None
    prior_art_paper_ids = _string_list(content.get("prior_art_paper_ids"))
    overlap_points = _string_list(content.get("overlap_points"))
    retainable_novelty = _string_list(content.get("retainable_novelty"))
    reasoning = str(content.get("reasoning", "")).strip()
    # backward-compat fields
    similar_work = _list_of_dicts(content.get("similar_work"))
    has_public_code = bool(content.get("has_public_code", False))
    return NoveltyVerdict(
        verdict=verdict,
        claim_revision=claim_revision,
        prior_art_paper_ids=prior_art_paper_ids,
        overlap_points=overlap_points,
        retainable_novelty=retainable_novelty,
        reasoning=reasoning,
        similar_work=similar_work,
        has_public_code=has_public_code,
    )


def _fallback_verdict(papers: list[Paper], hypothesis: Hypothesis | None, idea_brief: IdeaBrief | None) -> NoveltyVerdict:
    has_code = any(p.code_url for p in papers)
    similar = [{"title": p.title, "code_url": p.code_url} for p in papers if p.code_url]
    retainable = []
    if hypothesis and hypothesis.novelty_claim:
        retainable.append(hypothesis.novelty_claim)
    elif idea_brief and idea_brief.user_idea:
        retainable.append(idea_brief.user_idea)
    return NoveltyVerdict(
        verdict="novel",
        reasoning="LLM unavailable; defaulting to novel",
        similar_work=similar,
        has_public_code=has_code,
        retainable_novelty=retainable,
    )


def _fallback_report(papers: list[Paper], idea_brief: IdeaBrief | None) -> dict:
    """Legacy fallback for backward compatibility (dict format)."""
    has_code = any(p.code_url for p in papers)
    return {
        "similar_work": [{"title": p.title, "code_url": p.code_url} for p in papers if p.code_url],
        "has_public_code": has_code,
        "overlap_points": [],
        "retainable_novelty": [idea_brief.user_idea] if idea_brief and idea_brief.user_idea else [],
        "claims_to_downgrade": [],
        "optimization_directions": [],
    }


def _normalize(content: object, fallback: dict) -> dict:
    """Legacy normalize for backward compatibility (dict format)."""
    if not isinstance(content, dict):
        return fallback
    return {
        "similar_work": _list_of_dicts(content.get("similar_work")),
        "has_public_code": bool(content.get("has_public_code", fallback["has_public_code"])),
        "overlap_points": _string_list(content.get("overlap_points")),
        "retainable_novelty": _string_list(content.get("retainable_novelty")),
        "claims_to_downgrade": _string_list(content.get("claims_to_downgrade")),
        "optimization_directions": _string_list(content.get("optimization_directions")),
    } or fallback


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]
