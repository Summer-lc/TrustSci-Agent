from pathlib import Path

from app.agents.critic_agent import CriticAgent
from app.agents.experiment_designer_agent import ExperimentDesignerAgent
from app.agents.gap_finder_agent import GapFinderAgent
from app.agents.hypothesis_agent import HypothesisAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.report_writer_agent import ReportWriterAgent
from app.agents.scientific_data_agent import ScientificDataAgent
from app.config import Settings
from app.evidence.ledger import evidence_from_papers
from app.schemas.common import AgentStep, RunStatus, utc_now
from app.schemas.hypothesis import Hypothesis
from app.schemas.run import ResearchRun
from app.storage.in_memory import run_store
from app.tools.crossref_client import CrossrefClient
from app.tools.openalex_client import OpenAlexClient
from app.tools.qwen_client import QwenClient


class ScientistWorkflow:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = QwenClient(settings)
        self.openalex = OpenAlexClient(settings)
        self.crossref = CrossrefClient()
        self.planner = PlannerAgent(self.llm)
        self.gap_finder = GapFinderAgent()
        self.hypothesis_agent = HypothesisAgent()
        self.critic = CriticAgent()
        self.scientific_data_agent = ScientificDataAgent(settings)
        self.experiment_designer = ExperimentDesignerAgent()
        self.report_writer = ReportWriterAgent()

    async def run(self, run: ResearchRun) -> ResearchRun:
        run.status = RunStatus.running
        run.steps = []
        run_store.save(run)

        try:
            await self._step(run, "planner", self._plan)
            await self._step(run, "literature_search", self._search_literature)
            await self._step(run, "citation_verification", self._verify_citations)
            await self._step(run, "evidence_ledger", self._build_evidence)
            await self._step(run, "scientific_data_profile", self._profile_scientific_data)
            await self._step(run, "hypothesis_debate", self._generate_and_critique)
            await self._step(run, "experiment_design", self._design_experiment)
            await self._step(run, "report_writer", self._write_report)
            run.status = RunStatus.completed
            run.current_stage = "completed"
            run.progress = 1.0
        except Exception as exc:
            run.status = RunStatus.failed
            run.current_stage = "failed"
            run.errors.append(str(exc))
        run.updated_at = utc_now()
        return run_store.save(run)

    async def _step(self, run: ResearchRun, name: str, fn) -> None:
        step = AgentStep(name=name, status="running", started_at=utc_now())
        run.steps.append(step)
        run.current_stage = name
        run.updated_at = utc_now()
        run_store.save(run)
        await fn(run)
        step.status = "completed"
        step.finished_at = utc_now()
        run.progress = min(0.98, run.progress + 0.14)
        run.updated_at = utc_now()
        run_store.save(run)

    async def _plan(self, run: ResearchRun) -> None:
        run.plan = await self.planner.run(run)
        run.steps[-1].summary = f"Generated {len(run.plan.get('search_queries', []))} search queries."

    async def _search_literature(self, run: ResearchRun) -> None:
        queries = run.plan.get("search_queries") or [run.question]
        seen: set[str] = set()
        papers = []
        for query in queries[:2]:
            for paper in await self.openalex.search(query, run.constraints.max_papers):
                key = paper.doi or paper.title.lower()
                if key not in seen:
                    seen.add(key)
                    papers.append(paper)
                if len(papers) >= run.constraints.max_papers:
                    break
            if len(papers) >= run.constraints.max_papers:
                break
        run.papers = papers
        run.steps[-1].summary = f"Collected {len(papers)} candidate papers from OpenAlex."

    async def _verify_citations(self, run: ResearchRun) -> None:
        run.papers = [await self.crossref.verify(paper) for paper in run.papers]
        verified = len([paper for paper in run.papers if paper.verification_status == "verified"])
        run.steps[-1].summary = f"Verified {verified}/{len(run.papers)} papers through Crossref."

    async def _build_evidence(self, run: ResearchRun) -> None:
        run.evidence = evidence_from_papers(run.papers, run.domain)
        verified = len([item for item in run.evidence if item.verified])
        run.steps[-1].summary = f"Built {len(run.evidence)} evidence items; {verified} verified."

    async def _generate_and_critique(self, run: ResearchRun) -> None:
        gaps = self.gap_finder.run(run.evidence)
        run.hypotheses = self.critic.run(self.hypothesis_agent.run(gaps))
        if run.hypotheses:
            run.hypotheses[0].selected = True
        run.steps[-1].summary = f"Generated and reviewed {len(run.hypotheses)} hypotheses."

    async def _design_experiment(self, run: ResearchRun) -> None:
        run.experiment_plan = self.experiment_designer.run(_selected_hypothesis(run.hypotheses), run.data_profiles)
        run.steps[-1].summary = "Created baselines, metrics, experiment steps, and failure modes."

    async def _profile_scientific_data(self, run: ResearchRun) -> None:
        run.data_profiles, run.baseline_result_card = self.scientific_data_agent.run()
        run.steps[-1].summary = (
            f"Profiled {len(run.data_profiles)} data sources and generated result card "
            f"{run.baseline_result_card.name if run.baseline_result_card else 'none'}."
        )

    async def _write_report(self, run: ResearchRun) -> None:
        if run.experiment_plan is None:
            run.experiment_plan = self.experiment_designer.run(_selected_hypothesis(run.hypotheses), run.data_profiles)
        run.report = self.report_writer.run(
            run,
            _selected_hypothesis(run.hypotheses),
            run.experiment_plan,
            run.evidence,
            run.papers,
            run.data_profiles,
            run.baseline_result_card,
        )
        _write_markdown_report(run, self.settings.data_dir)
        run.steps[-1].summary = "Exported contest-format report with citation audit log."


def _selected_hypothesis(hypotheses: list[Hypothesis]) -> Hypothesis | None:
    return next((hypothesis for hypothesis in hypotheses if hypothesis.selected), hypotheses[0] if hypotheses else None)


def _write_markdown_report(run: ResearchRun, data_dir: Path) -> None:
    if run.report is None:
        return
    out_dir = data_dir / "outputs" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run.run_id}.md"
    report = run.report
    references = "\n".join(
        f"- {paper.title} ({paper.year or 'n.d.'}). DOI: {paper.doi or 'N/A'}" for paper in report.references
    )
    audit = "\n".join(f"- {line}" for line in report.citation_audit_log)
    methods = "\n".join(f"- {item}" for item in report.methods)
    data_profiles = "\n".join(
        f"- {profile.name}: {profile.rows or 'n/a'} rows, target={profile.target}, availability={profile.availability}"
        for profile in report.data_profiles
    )
    result_card = report.baseline_result_card.model_dump_json(indent=2) if report.baseline_result_card else "None"
    path.write_text(
        f"# {report.paper_title}\n\n"
        f"## Problem Statement\n{report.problem_statement}\n\n"
        f"## Rationale\n{report.rationale}\n\n"
        f"## Methods\n{methods}\n\n"
        f"## Data Profiles\n{data_profiles}\n\n"
        f"## Experiments\n{report.experiments.model_dump_json(indent=2)}\n\n"
        f"## Baseline Result Card\n{result_card}\n\n"
        f"## Results\n{report.results}\n\n"
        f"## References\n{references}\n\n"
        f"## Citation Audit Log\n{audit}\n",
        encoding="utf-8",
    )
