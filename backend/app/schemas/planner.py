from pydantic import BaseModel, Field


class PerspectiveQuestion(BaseModel):
    perspective: str
    role: str
    question: str
    search_query: str
    evidence_requirement: str
    risk_control: str


class PlannerPlan(BaseModel):
    research_objective: str
    domain: str
    constraints_summary: list[str] = Field(default_factory=list)
    sub_questions: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools_to_call: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    workflow_plan: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    risk_controls: list[str] = Field(default_factory=list)
    perspectives: list[PerspectiveQuestion] = Field(default_factory=list)
