from app.schemas.run import ResearchRun
from app.tools.qwen_client import QwenClient


class PlannerAgent:
    def __init__(self, llm: QwenClient) -> None:
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
        return await self.llm.chat_json(
            "You are a scientific research planner. Return compact JSON only.",
            f"Domain: {run.domain}\nQuestion: {run.question}\nDesign a verifiable AI Scientist workflow.",
            fallback,
            run_id=run.run_id,
            agent="planner",
        )
