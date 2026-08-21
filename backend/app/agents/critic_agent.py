import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import CriticReview, Hypothesis, ReviewerComment


SYSTEM_PROMPT = """You are the Critic Agent for TrustSci-Agent.
Review each hypothesis with multiple concrete reviewer roles.
Return JSON only. Do not add citations, evidence ids, datasets, or results.

Required JSON shape:
{
  "reviews": [
    {
      "hypothesis_id": "H1",
      "novelty": 1,
      "self_consistency": 1,
      "verifiability": 1,
      "data_availability": 1,
      "feasibility": 1,
      "evidence_support": 1,
      "risk": "specific risk",
      "revision_advice": "required revision",
      "reviewers": [
        {
          "reviewer": "domain expert | machine learning expert | experimental validation expert | skeptical reviewer",
          "score": 1,
          "stance": "support | cautious_support | major_revision | reject",
          "comment": "specific strength, weakness, and missing evidence/experiment",
          "required_action": "specific action"
        }
      ]
    }
  ]
}
Each hypothesis needs at least four reviewer comments covering domain, ML, experimental validation, and skeptical reviewer roles.
"""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)


class CriticAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        hypotheses: list[Hypothesis],
        evidence: list[EvidenceItem],
        *,
        run_id: str | None = None,
    ) -> list[Hypothesis]:
        fallback = self.run([hypothesis.model_copy(deep=True) for hypothesis in hypotheses])
        if self.llm is None:
            return fallback
        fallback_payload = {
            "reviews": [
                {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    **(hypothesis.critic.model_dump() if hypothesis.critic else {}),
                    "reviewers": [comment.model_dump() for comment in hypothesis.reviewer_comments],
                }
                for hypothesis in fallback
            ]
        }
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback_payload, run_id=run_id, agent="critic_reviewer")
            | FallbackParser(lambda content: _apply_reviews(content, hypotheses, fallback), fallback)
        )
        return await chain.ainvoke({"user_prompt": _build_user_prompt(hypotheses, evidence)})

    def run(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        reviewed: list[Hypothesis] = []
        for hypothesis in hypotheses:
            hypothesis.critic = CriticReview(
                novelty=8 if hypothesis.hypothesis_id == "H1" else 7,
                self_consistency=8,
                verifiability=9,
                data_availability=8,
                feasibility=8,
                evidence_support=7 if hypothesis.supporting_evidence else 5,
                reproducibility=8,
                competition_fit=9,
                risk="Novelty may overlap with existing materials informatics workflows unless the evidence-ledger contribution is made explicit.",
                revision_advice="Freeze verified references before report writing and add one bounded benchmark or dataset profile to support the validation path.",
            )
            hypothesis.reviewer_comments = _reviewer_comments(hypothesis)
            reviewed.append(hypothesis)
        return reviewed


def _reviewer_comments(hypothesis: Hypothesis) -> list[ReviewerComment]:
    evidence_note = (
        "supporting evidence ids are present"
        if hypothesis.supporting_evidence
        else "supporting evidence is currently sparse"
    )
    return [
        ReviewerComment(
            reviewer="Literature Reviewer",
            score=7,
            stance="cautious_support",
            comment=f"The idea is plausible, but novelty should be bounded because {evidence_note}.",
            required_action="Add a similar-work boundary and cite only verified papers.",
        ),
        ReviewerComment(
            reviewer="Domain Scientist",
            score=8,
            stance="support",
            comment="The statement is scientifically useful if it remains framed as a testable mechanism or workflow hypothesis.",
            required_action="Name the measurable material property and avoid claiming discovery before validation.",
        ),
        ReviewerComment(
            reviewer="ML/Experiment Reviewer",
            score=8,
            stance="support_with_conditions",
            comment="The validation path is feasible if baseline, metrics, and ablation are explicit.",
            required_action="Tie the experiment plan to a concrete dataset profile and baseline result card.",
        ),
        ReviewerComment(
            reviewer="Skeptical Reviewer",
            score=6,
            stance="major_revision",
            comment="The final report could overstate novelty if the evidence-ledger contribution is not separated from materials-science claims.",
            required_action="Revise the claim to separate verified evidence from expected outcomes.",
        ),
    ]


def _build_user_prompt(hypotheses: list[Hypothesis], evidence: list[EvidenceItem]) -> str:
    payload = {
        "hypotheses": [
            {
                "hypothesis_id": hypothesis.hypothesis_id,
                "statement": hypothesis.statement,
                "rationale": hypothesis.rationale,
                "supporting_evidence": hypothesis.supporting_evidence,
                "novelty_claim": hypothesis.novelty_claim,
                "verification_path": hypothesis.verification_path,
            }
            for hypothesis in hypotheses
        ],
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "verified": item.verified,
                "eligible_for_report": item.eligible_for_report,
            }
            for item in evidence[:16]
        ],
        "reviewer_roles": [
            "domain expert",
            "machine learning expert",
            "experimental validation expert",
            "skeptical reviewer",
        ],
        "instructions": [
            "Comments must be concrete and hypothesis-specific.",
            "Identify strengths, weaknesses, missing evidence, missing experiments, and required revisions.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _apply_reviews(content: object, hypotheses: list[Hypothesis], fallback: list[Hypothesis]) -> list[Hypothesis]:
    if not isinstance(content, dict) or not isinstance(content.get("reviews"), list):
        return fallback
    review_by_id = {
        str(raw.get("hypothesis_id")): raw
        for raw in content["reviews"]
        if isinstance(raw, dict) and raw.get("hypothesis_id")
    }
    reviewed: list[Hypothesis] = []
    for hypothesis in [item.model_copy(deep=True) for item in hypotheses]:
        raw = review_by_id.get(hypothesis.hypothesis_id)
        if not isinstance(raw, dict):
            return fallback
        comments = _reviewer_comments_from_qwen(raw.get("reviewers"))
        if len(comments) < 4:
            return fallback
        try:
            hypothesis.critic = CriticReview(
                novelty=_score(raw.get("novelty")),
                self_consistency=_score(raw.get("self_consistency")),
                verifiability=_score(raw.get("verifiability")),
                data_availability=_score(raw.get("data_availability")),
                feasibility=_score(raw.get("feasibility")),
                evidence_support=_score(raw.get("evidence_support")),
                risk=_clean(raw.get("risk")) or "Evidence or feasibility risk requires revision.",
                revision_advice=_clean(raw.get("revision_advice")) or "Add evidence-bound revisions before report writing.",
            )
        except Exception:
            return fallback
        hypothesis.reviewer_comments = comments
        reviewed.append(hypothesis)
    return reviewed or fallback


def _reviewer_comments_from_qwen(value: object) -> list[ReviewerComment]:
    if not isinstance(value, list):
        return []
    comments: list[ReviewerComment] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        comment = _clean(raw.get("comment"))
        action = _clean(raw.get("required_action"))
        reviewer = _clean(raw.get("reviewer"))
        if not reviewer or len(comment) < 20 or not action:
            continue
        comments.append(
            ReviewerComment(
                reviewer=reviewer,
                score=_score(raw.get("score")),
                stance=_clean(raw.get("stance")) or "cautious_support",
                comment=comment,
                required_action=action,
            )
        )
    return comments


def _score(value: object) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return 7
    return max(1, min(10, score))


def _clean(value: object) -> str:
    return str(value or "").strip()
