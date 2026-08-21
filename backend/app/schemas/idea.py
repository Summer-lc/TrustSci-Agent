from pydantic import BaseModel, Field


class IdeaBrief(BaseModel):
    research_problem: str
    user_idea: str | None = None
    target_task: str
    input_data: list[str] = Field(default_factory=list)
    proposed_method: str | None = None
    expected_contribution: str | None = None
    target_labels: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
