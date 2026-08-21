from app.schemas.baseline_intake import BaselineIntake
from app.schemas.run import ResearchRun


class BaselineIntakeAgent:
    async def arun(self, run: ResearchRun) -> BaselineIntake:
        strategy = run.baseline_strategy or "none"
        if strategy == "manual_upload" and run.manual_baseline and run.manual_baseline.manual:
            manual = run.manual_baseline.manual
            return BaselineIntake(
                strategy="manual_upload",
                source_type="manual_upload",
                trust_level="user_provided",
                name=manual.name,
                description=manual.description or "User-provided baseline.",
                metrics=manual.metrics,
                limitations=[
                    "Manual baseline content was recorded but arbitrary user code was not executed by TrustSci-Agent.",
                    "Research-grade trust depends on user-supplied provenance and independent reproducibility evidence.",
                ],
                provenance_notes=[
                    "Baseline was attached before workflow start.",
                    f"repository_url={manual.repository_url or 'not supplied'}",
                    f"run_command={manual.run_command or 'not supplied'}",
                ],
            )
        if strategy == "ai_generated":
            return BaselineIntake(
                strategy="ai_generated",
                source_type="ai_generated",
                trust_level="runnable_demo",
                name="AI-generated local demo baseline",
                description=(
                    "A simple reproducible baseline represented by the fixed local seismic harness "
                    "baseline path. It is intended for demo comparison only."
                ),
                metrics=[],
                limitations=[
                    "This is not an externally verified literature SOTA baseline.",
                    "It supports local demo comparison only and should be reported as degraded research evidence.",
                ],
                provenance_notes=[
                    "Generated from the selected baseline strategy.",
                    "Executable comparison remains bounded to experiments/seismic_event_classification/train.py.",
                ],
            )
        return BaselineIntake(
            strategy="none",
            source_type="unavailable",
            trust_level="insufficient",
            name="No baseline provided",
            description="The run proceeded without a supplied or generated baseline.",
            metrics=[],
            limitations=[
                "No baseline comparison is available.",
                "Report conclusions must avoid comparative performance claims.",
            ],
            provenance_notes=["No baseline strategy payload was supplied, or the user selected no baseline."],
        )
