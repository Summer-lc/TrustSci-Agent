from app.schemas.experiment_assistance import (
    AblationAnalysis, AblationFinding, MetricDelta, MetricObservation,
    ResultEvaluation, ResultInterpretation,
)
from app.schemas.run import ResearchRun


def _metric_map(items: list[MetricObservation]) -> dict[str, float]:
    return {item.name.strip().lower(): item.value for item in items}


def _source_metrics(run: ResearchRun):
    if run.experiment_assistance:
        item = run.experiment_assistance
        return _metric_map(item.baseline_metrics), _metric_map(item.method_metrics), "user-provided"
    if run.code_experiment:
        item = run.code_experiment.comparison
        return dict(item.baseline_metrics), dict(item.method_metrics), "system-executed"
    return {}, {}, "unavailable"


class ResultEvaluatorAgent:
    def __init__(self, llm) -> None:
        self.llm = llm

    async def arun(self, run: ResearchRun) -> ResultEvaluation:
        baseline, method, source = _source_metrics(run)
        deltas = [MetricDelta(name=n, baseline=baseline[n], method=method[n], delta=method[n] - baseline[n])
                  for n in sorted(set(baseline) & set(method))]
        positive = [d for d in deltas if d.delta is not None and d.delta > 0]
        negative = [d for d in deltas if d.delta is not None and d.delta < 0]
        verdict = "pass" if positive and not negative else "fail" if negative and not positive else "partial"
        return ResultEvaluation(
            verdict=verdict, metric_deltas=deltas,
            supported_claims=[f"{d.name} improved by {d.delta:.4f}." for d in positive],
            unsupported_claims=["The observations do not establish generalization beyond this run."],
            data_quality_warnings=[] if deltas else ["No directly comparable metrics were supplied."],
            reasoning=f"Deterministic comparison over {source} metrics.")


class AblationAgent:
    def __init__(self, llm) -> None:
        self.llm = llm

    async def arun(self, run: ResearchRun) -> AblationAnalysis:
        supplied = run.experiment_assistance
        if not supplied or not supplied.ablations:
            return AblationAnalysis(missing_comparisons=["No controlled component ablation was supplied."],
                                    summary="Ablation evidence is unavailable.")
        method = _metric_map(supplied.method_metrics)
        findings = []
        for item in supplied.ablations:
            ablated = _metric_map(item.metrics)
            deltas = [MetricDelta(name=n, baseline=ablated[n], method=method[n], delta=method[n] - ablated[n])
                      for n in sorted(set(method) & set(ablated))]
            findings.append(AblationFinding(component=item.component, effect="measured", metric_deltas=deltas))
        return AblationAnalysis(coverage="partial", findings=findings,
            missing_comparisons=["Only author-supplied ablations were available."],
            summary="Supplied ablations were compared with the complete method.")


class ResultInterpreterAgent:
    def __init__(self, llm) -> None:
        self.llm = llm

    async def arun(self, run: ResearchRun) -> ResultInterpretation:
        evaluation = run.result_evaluation or ResultEvaluation()
        return ResultInterpretation(
            conclusions=evaluation.supported_claims or ["No improvement is established by comparable metrics."],
            limitations=evaluation.unsupported_claims + evaluation.data_quality_warnings,
            failure_explanation="The comparison gate failed." if evaluation.verdict == "fail" else None,
            next_experiments=["Repeat on an untouched event-level test split.", "Add controlled component ablations."],
            evidence_boundary=("Conclusions are bounded to user-provided results and were not independently reproduced by TrustSci-Agent."
                               if run.experiment_assistance else
                               "Conclusions are bounded to the system-executed local harness result."))
