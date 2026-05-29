from app.schemas.run import ResearchRun
from app.llm.interface import LLMClient, LLMRequest


class PlannerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun) -> dict:
        fallback = {
            "sub_questions": [
                "What mechanisms are repeatedly reported in recent literature?",
                "Which open datasets can support a bounded verification experiment?",
                "Where do current methods leave a measurable knowledge gap?",
            ],
            "search_queries": [
                "solid-state electrolyte ionic conductivity stability machine learning",
                "energy materials structure property prediction benchmark",
                "materials project matbench solid electrolyte discovery",
            ],
            "workflow_plan": [
                "retrieve verified papers",
                "extract evidence ledger",
                "generate hypotheses",
                "critic review",
                "design experiment",
                "write competition report",
            ],
        }
        response = await self.llm.complete(
            LLMRequest(
                system="You are a scientific research planner. Return compact JSON only.",
                user=f"Domain: {run.domain}\nQuestion: {run.question}\nDesign a verifiable AI Scientist workflow.",
                fallback=fallback,
                run_id=run.run_id,
                agent="planner",
            )
        )
        return response.content if isinstance(response.content, dict) else fallback
