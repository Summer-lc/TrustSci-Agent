import hashlib
import json
from pathlib import Path

from app.agents.baseline_intake_agent import BaselineIntakeAgent
from app.agents.baseline_discovery_agent import BaselineDiscoveryAgent
from app.agents.challenger_agent import ChallengerAgent
from app.agents.code_writer_agent import CodeWriterAgent
from app.agents.critic_agent import CriticAgent
from app.agents.critic_arena_agent import CriticArenaAgent
from app.agents.experiment_designer_agent import ExperimentDesignerAgent
from app.agents.experiment_redesign_agent import ExperimentRedesignAgent
from app.agents.fair_comparison_planner import FairComparisonPlanner
from app.agents.gap_finder_agent import GapFinderAgent
from app.agents.hypothesis_agent import HypothesisAgent
from app.agents.hypothesis_arena_agent import HypothesisArenaAgent
from app.agents.literature_miner_agent import LiteratureMinerAgent
from app.agents.novelty_checker_agent import NoveltyCheckerAgent
from app.agents.paper_type_classifier_agent import PaperTypeClassifierAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.report_reviser_agent import ReportReviserAgent
from app.agents.report_translator_agent import ReportTranslatorAgent
from app.agents.report_writer_agent import ReportWriterAgent
from app.agents.result_analysis_agents import AblationAgent, ResultEvaluatorAgent, ResultInterpreterAgent
from app.agents.repository_verifier_agent import RepositoryVerifierAgent
from app.agents.revision_agent import RevisionAgent
from app.agents.scientific_data_agent import ScientificDataAgent
from app.agents.idea_intake_agent import IdeaIntakeAgent
from app.agents.intent_router_agent import IntentRouterAgent
from app.schemas.code_experiment import (
    AcceptanceGate, CodeExperimentResult, ComparisonResult, DebugEntry,
    ExperimentSummary, FairComparisonPlan, IterEntry,
)
from app.tools.baseline_sources import GithubBaselineClient, PapersWithCodeClient
from app.tools.code_url_extractor import extract_code_urls_async
from app.tools.sandbox_executor import SandboxExecutor
from app.tools.seismic_data import SeismicDataAdapter
from app.config import Settings
from app.evidence.ledger import evidence_from_papers
from app.evidence.selection import reportable_evidence
from app.llm.registry import build_llm_client
from app.schemas.common import AgentStep, RunStatus, utc_now
from app.schemas.run_control import StepEvent
from app.schemas.hypothesis import Hypothesis
from app.schemas.planner import PerspectiveQuestion
from app.schemas.baseline import BaselineCandidate
from app.schemas.feedback_loop import BaselineGateStatus
from app.schemas.run import ResearchRun
from app.storage.in_memory import run_store
from app.storage.workspace import RunWorkspace
from app.tools.arxiv_client import ArxivClient
from app.tools.claim_verifier import ClaimVerifier
from app.tools.citation_verifier import CitationVerifier
from app.tools.crossref_client import CrossrefClient
from app.tools.literature_router import LiteratureRouter
from app.tools.openalex_client import OpenAlexClient
from app.tools.semantic_scholar_client import SemanticScholarClient
from app.workflows.run_control import SKIPPABLE_STEPS, classify_step_error


class StepNeedsAction(Exception):
    """Pause the workflow until the user retries or skips the current step."""


class RunControlSignal(Exception):
    """Stop pipeline advancement after a persisted user control action."""


class ScientistWorkflow:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.workspace = RunWorkspace(settings.data_dir)
        self.llm = build_llm_client(settings)
        self.openalex = OpenAlexClient(settings)
        self.crossref = CrossrefClient(settings)
        self.semantic_scholar = SemanticScholarClient(settings)
        self.arxiv = ArxivClient()
        self.literature_router = LiteratureRouter(
            settings,
            openalex=self.openalex,
            crossref=self.crossref,
            semantic_scholar=self.semantic_scholar,
            arxiv=self.arxiv,
        )
        self.citation_verifier = CitationVerifier(
            settings,
            crossref=self.crossref,
            openalex=self.openalex,
            semantic_scholar=self.semantic_scholar,
            arxiv=self.arxiv,
        )
        self.claim_verifier = ClaimVerifier(self.llm)
        self.planner = PlannerAgent(self.llm)
        self.literature_miner = LiteratureMinerAgent(self.llm)
        self.gap_finder = GapFinderAgent(self.llm)
        self.hypothesis_agent = HypothesisAgent(self.llm)
        self.critic = CriticAgent(self.llm)
        self.revision_agent = RevisionAgent()
        self.scientific_data_agent = ScientificDataAgent(settings)
        self.experiment_designer = ExperimentDesignerAgent(self.llm)
        self.experiment_redesigner = ExperimentRedesignAgent()
        self.report_writer = ReportWriterAgent(self.llm)
        self.report_reviser = ReportReviserAgent(self.llm)
        self.report_translator = ReportTranslatorAgent(self.llm)
        self.result_evaluator = ResultEvaluatorAgent(self.llm)
        self.ablation_agent = AblationAgent(self.llm)
        self.result_interpreter = ResultInterpreterAgent(self.llm)
        self.intent_router = IntentRouterAgent(self.llm)
        self.idea_intake = IdeaIntakeAgent(self.llm)
        self.seismic_adapter = SeismicDataAdapter(settings.data_dir)
        self.critic_arena = CriticArenaAgent(self.llm)
        self.challenger = ChallengerAgent(self.llm)
        self.arena_agent = HypothesisArenaAgent(
            hypothesis_agent=self.hypothesis_agent,
            critic_arena=self.critic_arena,
            revision=self.revision_agent,
            challenger=self.challenger,
        )
        self.novelty_checker = NoveltyCheckerAgent(self.llm)
        self.paper_classifier = PaperTypeClassifierAgent(self.llm)
        self._github_baseline = GithubBaselineClient(token=settings.github_token if hasattr(settings, 'github_token') else "")
        self._pwc = PapersWithCodeClient()
        self.baseline_intake_agent = BaselineIntakeAgent()
        self.baseline_discovery = BaselineDiscoveryAgent(self._github_baseline, self._pwc)
        self.repo_verifier = RepositoryVerifierAgent(self.llm, self._github_baseline)
        self.code_writer = CodeWriterAgent(self.llm)
        self.fair_comparison_planner = FairComparisonPlanner()
        self.sandbox_executor = SandboxExecutor(
            self.settings.experiments_dir,
            timeout=self.settings.code_experiment_timeout_seconds,
        )

    async def run(self, run: ResearchRun) -> ResearchRun:
        run.status = RunStatus.running
        run.steps = []
        self._write_workspace(run)
        run_store.save(run)

        try:
            await self._step(run, "intent_router", self._route_intent)
            await self._step(run, "planner", self._plan)
            await self._step(run, "literature_search", self._search_literature)
            await self._step(run, "citation_verification", self._verify_citations)
            if run.constraints.workflow_mode == "guided":
                self._pause_for_human(
                    run,
                    "awaiting_citation_review",
                    "Citation verification is complete. Review papers, accept/reject citations, then freeze citations before continuing.",
                    progress=0.36,
                )
                return run_store.save(run)
            await self._run_after_citation_review(run)
        except RunControlSignal:
            pass
        except StepNeedsAction:
            run.status = RunStatus.paused
            run.pause_reason = "error"
        except Exception as exc:
            run.status = RunStatus.failed
            run.current_stage = "failed"
            run.errors.append(str(exc))
        run.updated_at = utc_now()
        self._write_workspace(run)
        return run_store.save(run)

    async def continue_run(self, run: ResearchRun) -> ResearchRun:
        if run.status == RunStatus.running:
            return run
        try:
            if run.current_stage == "awaiting_citation_review":
                if not run.citation_frozen:
                    raise ValueError("Freeze citations before continuing the guided workflow.")
                run.status = RunStatus.running
                await self._step(run, "evidence_ledger", self._build_evidence)
                await self._step(run, "literature_mining", self._mine_literature)
                self._pause_for_human(
                    run,
                    "awaiting_evidence_review",
                    "Evidence ledger is ready. Review evidence, accept/reject items, then freeze evidence before continuing.",
                    progress=0.58,
                )
                return run_store.save(run)
            if run.current_stage == "awaiting_evidence_review":
                if not run.evidence_frozen:
                    raise ValueError("Freeze evidence before continuing the guided workflow.")
                run.status = RunStatus.running
                await self._run_after_evidence_review(run)
                return run_store.save(run)
            raise ValueError("The run is not waiting for a guided human checkpoint.")
        except RunControlSignal:
            pass
        except StepNeedsAction:
            run.status = RunStatus.paused
            run.pause_reason = "error"
        except Exception as exc:
            run.status = RunStatus.failed
            run.current_stage = "failed"
            run.errors.append(str(exc))
        run.updated_at = utc_now()
        self._write_workspace(run)
        return run_store.save(run)

    async def resume_user_run(self, run: ResearchRun) -> ResearchRun:
        run.status = RunStatus.running
        run.pause_reason = None
        run.control_action = "none"
        try:
            await self._resume_incomplete_pipeline(run)
        except RunControlSignal:
            pass
        except StepNeedsAction:
            run.status = RunStatus.paused
            run.pause_reason = "error"
        except Exception as exc:
            run.status = RunStatus.failed
            run.current_stage = "failed"
            run.errors.append(str(exc))
        run.updated_at = utc_now()
        self._write_workspace(run)
        return run_store.save(run)

    async def resume_waiting_step(self, run: ResearchRun, step: AgentStep, action: str) -> ResearchRun:
        if step.status != "waiting_action" or run.current_stage != step.name:
            raise ValueError("step is not waiting for action")
        now = utc_now()
        run.last_action = {"action": action, "step_name": step.name, "at": now.isoformat()}
        if action == "skip":
            if not step.skippable:
                raise ValueError("critical step cannot be skipped")
            step.status = "skipped"
            step.finished_at = now
            step.events.append(StepEvent(event="skipped", at=now, detail="用户选择跳过此步骤"))
            warning = f"步骤 {step.name} 被用户跳过，相关结论的完整性可能降低。"
            if warning not in run.trust_warnings:
                run.trust_warnings.append(warning)
        else:
            method_name = _STEP_METHODS.get(step.name)
            if method_name is None:
                raise ValueError(f"step {step.name} cannot be retried")
            step.status = "failed"
            step.events.append(StepEvent(event="retried", at=now, detail="用户请求重新执行"))
            run.status = RunStatus.running
            await self._step(run, step.name, getattr(self, method_name))
        run.status = RunStatus.running
        await self._resume_incomplete_pipeline(run)
        return run_store.save(run)

    async def _resume_incomplete_pipeline(self, run: ResearchRun) -> None:
        await self._ensure_step(run, "intent_router", self._route_intent)
        await self._ensure_step(run, "planner", self._plan)
        await self._ensure_step(run, "literature_search", self._search_literature)
        await self._ensure_step(run, "citation_verification", self._verify_citations)
        if run.constraints.workflow_mode == "guided" and not run.citation_frozen:
            self._pause_for_human(
                run,
                "awaiting_citation_review",
                "Citation verification is complete. Review papers, accept/reject citations, then freeze citations before continuing.",
                progress=max(run.progress, 0.36),
            )
            return
        await self._ensure_step(run, "evidence_ledger", self._build_evidence)
        await self._ensure_step(run, "literature_mining", self._mine_literature)
        if run.constraints.workflow_mode == "guided" and not run.evidence_frozen:
            self._pause_for_human(
                run,
                "awaiting_evidence_review",
                "Evidence ledger is ready. Review evidence, accept/reject items, then freeze evidence before continuing.",
                progress=max(run.progress, 0.58),
            )
            return

        if run.mode == "experiment_assistance":
            await self._ensure_step(run, "scientific_data_profile", self._profile_scientific_data)
        else:
            if run.domain == "seismic_event_classification":
                await self._ensure_step(run, "paper_classification", self._classify_papers)
            await self._ensure_step(run, "scientific_data_profile", self._profile_scientific_data)
            if run.domain == "seismic_event_classification":
                await self._ensure_step(run, "arena", self._run_arena)
                await self._ensure_step(run, "novelty_check", self._run_novelty_check)
                await self._ensure_step(run, "baseline_intake", self._run_baseline_intake)
                await self._ensure_step(run, "baseline_quality_gate", self._evaluate_baseline_gate)
            else:
                await self._ensure_step(run, "hypothesis_debate", self._generate_and_critique)
            await self._ensure_step(run, "experiment_design", self._design_experiment)
            if run.domain == "seismic_event_classification":
                await self._ensure_step(run, "code_experiment", self._run_code_experiment)
                await self._ensure_step(run, "experiment_result_gate", self._evaluate_experiment_result_gate)
                if self._route_after_experiment_result({"run": run}) == "experiment_redesign":
                    await self._ensure_step(run, "experiment_redesign", self._redesign_experiment)
                    redesign_index = self._last_done_step_index(run, "experiment_redesign")
                    await self._ensure_step(
                        run,
                        "code_experiment",
                        self._run_code_experiment,
                        after_index=redesign_index,
                    )
                    code_index = self._last_done_step_index(run, "code_experiment")
                    await self._ensure_step(
                        run,
                        "experiment_result_gate",
                        self._evaluate_experiment_result_gate,
                        after_index=code_index,
                    )

        await self._ensure_step(run, "result_evaluation", self._evaluate_results)
        await self._ensure_step(run, "ablation_analysis", self._analyze_ablations)
        await self._ensure_step(run, "result_interpretation", self._interpret_results)
        await self._ensure_step(run, "report_writer", self._write_report)
        await self._ensure_step(run, "claim_verification", self._verify_claims)
        await self._ensure_step(run, "report_revision", self._revise_report_after_audit)
        report_revision_index = self._last_done_step_index(run, "report_revision")
        await self._ensure_step(
            run,
            "claim_reverification",
            self._verify_claims,
            after_index=report_revision_index,
        )
        await self._ensure_step(run, "report_translation", self._translate_report)
        run.status = RunStatus.completed
        run.current_stage = "completed"
        run.progress = 1.0
        run.updated_at = utc_now()
        self._write_workspace(run)
        run_store.save(run)

    async def _ensure_step(self, run: ResearchRun, name: str, fn, *, after_index: int = -1) -> None:
        if any(
            index > after_index and step.name == name and step.status in {"completed", "skipped"}
            for index, step in enumerate(run.steps)
        ):
            return
        await self._step(run, name, fn)

    def _last_done_step_index(self, run: ResearchRun, name: str) -> int:
        return max(
            (
                index
                for index, step in enumerate(run.steps)
                if step.name == name and step.status in {"completed", "skipped"}
            ),
            default=-1,
        )

    async def _run_after_citation_review(self, run: ResearchRun) -> None:
        await self._step(run, "evidence_ledger", self._build_evidence)
        await self._step(run, "literature_mining", self._mine_literature)
        await self._run_after_evidence_review(run)

    async def _run_after_evidence_review(self, run: ResearchRun) -> None:
        if run.mode == "experiment_assistance":
            await self._step(run, "scientific_data_profile", self._profile_scientific_data)
            await self._run_result_analysis(run)
            await self._step(run, "report_writer", self._write_report)
            await self._step(run, "claim_verification", self._verify_claims)
            await self._step(run, "report_revision", self._revise_report_after_audit)
            await self._step(run, "claim_reverification", self._verify_claims)
            await self._step(run, "report_translation", self._translate_report)
            run.status = RunStatus.completed
            run.current_stage = "completed"
            run.progress = 1.0
            return
        if run.domain == "seismic_event_classification":
            await self._step(run, "paper_classification", self._classify_papers)
        await self._step(run, "scientific_data_profile", self._profile_scientific_data)
        if run.domain == "seismic_event_classification":
            await self._step(run, "arena", self._run_arena)
            await self._step(run, "novelty_check", self._run_novelty_check)
            await self._step(run, "baseline_intake", self._run_baseline_intake)
            await self._step(run, "baseline_quality_gate", self._evaluate_baseline_gate)
        else:
            await self._step(run, "hypothesis_debate", self._generate_and_critique)
        await self._step(run, "experiment_design", self._design_experiment)
        if run.domain == "seismic_event_classification":
            await self._step(run, "code_experiment", self._run_code_experiment)
            await self._step(run, "experiment_result_gate", self._evaluate_experiment_result_gate)
            if self._route_after_experiment_result({"run": run}) == "experiment_redesign":
                await self._step(run, "experiment_redesign", self._redesign_experiment)
                await self._step(run, "code_experiment", self._run_code_experiment)
                await self._step(run, "experiment_result_gate", self._evaluate_experiment_result_gate)
        await self._run_result_analysis(run)
        await self._step(run, "report_writer", self._write_report)
        await self._step(run, "claim_verification", self._verify_claims)
        await self._step(run, "report_revision", self._revise_report_after_audit)
        await self._step(run, "claim_reverification", self._verify_claims)
        await self._step(run, "report_translation", self._translate_report)
        run.status = RunStatus.completed
        run.current_stage = "completed"
        run.progress = 1.0
        run.updated_at = utc_now()
        self._write_workspace(run)

    def _pause_for_human(self, run: ResearchRun, stage: str, summary: str, *, progress: float) -> None:
        run.status = RunStatus.paused
        run.pause_reason = "review"
        run.current_stage = stage
        run.progress = progress
        run.updated_at = utc_now()
        run.steps.append(AgentStep(name=stage, status="paused", started_at=utc_now(), summary=summary))
        self._write_workspace(run)

    async def _step(self, run: ResearchRun, name: str, fn) -> None:
        self._stop_if_requested(run)
        started_at = utc_now()
        step = AgentStep(
            name=name,
            status="running",
            started_at=started_at,
            summary=_stage_start_summary(name),
            skippable=name in SKIPPABLE_STEPS,
            events=[StepEvent(event="started", at=started_at, detail="step started")],
        )
        run.steps.append(step)
        run.current_stage = name
        run.updated_at = utc_now()
        self._write_workspace(run)
        run_store.save(run)
        while step.attempts < 2:
            step.attempts += 1
            try:
                await fn(run)
            except Exception as exc:
                decision = classify_step_error(exc, name)
                step.error_code = decision.code
                step.error_summary = decision.summary
                step.retryable = decision.retryable
                if decision.retryable and step.attempts < 2:
                    step.status = "retrying"
                    step.summary = f"{decision.summary}，正在自动重试一次。"
                    step.events.append(
                        StepEvent(event="retrying", at=utc_now(), detail=decision.summary)
                    )
                    run.updated_at = utc_now()
                    self._write_workspace(run)
                    run_store.save(run)
                    continue
                step.status = "waiting_action"
                step.summary = decision.summary
                step.finished_at = utc_now()
                step.events.append(
                    StepEvent(event="failed", at=step.finished_at, detail=decision.summary)
                )
                run.status = RunStatus.paused
                run.pause_reason = "error"
                run.current_stage = name
                run.updated_at = utc_now()
                self._write_workspace(run)
                run_store.save(run)
                raise StepNeedsAction(decision.summary) from exc
            step.status = "completed"
            step.error_code = None
            step.error_summary = None
            step.retryable = False
            step.finished_at = utc_now()
            step.events.append(
                StepEvent(event="completed", at=step.finished_at, detail=step.summary)
            )
            run.progress = min(0.98, run.progress + 0.14)
            run.updated_at = utc_now()
            self._write_workspace(run)
            run_store.save(run)
            self._stop_if_requested(run)
            return

    def _stop_if_requested(self, run: ResearchRun) -> None:
        if run.control_action == "none":
            return
        now = utc_now()
        if run.control_action == "pause":
            run.status = RunStatus.paused
            run.pause_reason = "user"
            run.control_action = "none"
        else:
            run.status = RunStatus.abandoned
            run.pause_reason = None
        run.updated_at = now
        self._write_workspace(run)
        run_store.save(run)
        raise RunControlSignal(str(run.status))

    async def _plan(self, run: ResearchRun) -> None:
        def progress(summary: str) -> None:
            run.steps[-1].summary = summary
            run.updated_at = utc_now()
            self._write_workspace(run)
            run_store.save(run)

        run.plan = await self.planner.run(run, progress=progress)
        run.perspectives = [
            PerspectiveQuestion.model_validate(item)
            for item in run.plan.get("perspectives", [])
            if isinstance(item, dict)
        ]
        run.steps[-1].summary = (
            f"Generated {len(run.plan.get('search_queries', []))} search queries "
            f"and {len(run.perspectives)} perspectives."
        )

    async def _route_intent(self, run: ResearchRun) -> None:
        run.intent = await self.intent_router.run(run)
        if run.mode == "idea_refinement":
            run.idea_brief = await self.idea_intake.run(run)
            if run.steps:
                run.steps[-1].summary = (
                    f"Intent routed to idea_refinement (inferred={run.intent['mode']}, "
                    f"confidence={run.intent['confidence']}); structured IdeaBrief ready."
                )
        else:
            if run.steps:
                run.steps[-1].summary = (
                    f"Intent routed to {run.mode} (inferred={run.intent['mode']}, "
                    f"confidence={run.intent['confidence']}); required_inputs={run.intent['required_inputs']}."
                )

    async def _search_literature(self, run: ResearchRun) -> None:
        queries = run.plan.get("search_queries") or [run.question]
        run.papers = await self.literature_router.search(
            [str(query) for query in queries],
            max_papers=run.constraints.max_papers,
            enable_semantic_scholar=run.constraints.enable_semantic_scholar,
            enable_arxiv=run.constraints.enable_arxiv,
            domain=run.domain,
        )
        sources = sorted({paper.source_api for paper in run.papers})
        stats = ", ".join(f"{source}:{count}" for source, count in self.literature_router.last_source_stats.items())
        run.steps[-1].summary = (
            f"Collected {len(run.papers)} candidate papers from "
            f"{', '.join(sources) or 'literature APIs'}"
            f"{f' ({stats})' if stats else ''}."
        )

    async def _verify_citations(self, run: ResearchRun) -> None:
        run.papers, run.citation_report = await self.citation_verifier.verify_many(
            run.papers,
            enable_semantic_scholar=run.constraints.enable_semantic_scholar,
        )
        report = run.citation_report
        run.steps[-1].summary = (
            f"Verified {report.verified}/{report.total} papers across layered checks; "
            f"integrity_score={report.integrity_score}."
        )

    async def _build_evidence(self, run: ResearchRun) -> None:
        run.evidence = evidence_from_papers(run.papers, run.domain)
        run.evidence_frozen = False
        run.frozen_evidence_ids = []
        verified = len([item for item in run.evidence if item.verified])
        run.steps[-1].summary = f"Built {len(run.evidence)} evidence items; {verified} verified."

    async def _mine_literature(self, run: ResearchRun) -> None:
        evidence = _workflow_evidence(run)
        run.knowledge_cards = await self.literature_miner.arun(evidence, run.papers, run.perspectives, run_id=run.run_id)
        eligible = len([card for card in run.knowledge_cards if card.report_eligible])
        run.steps[-1].summary = f"Generated {len(run.knowledge_cards)} knowledge cards; {eligible} report-ready."

    async def _generate_and_critique(self, run: ResearchRun) -> None:
        evidence = _workflow_evidence(run)
        gaps = await self.gap_finder.arun(run.knowledge_cards, evidence, run.data_profiles, run_id=run.run_id)
        hypotheses = await self.hypothesis_agent.arun(gaps, evidence, run.data_profiles, run_id=run.run_id)
        reviewed = await self.critic.arun(hypotheses, evidence, run_id=run.run_id)
        run.hypotheses = self.revision_agent.run(reviewed)
        if run.hypotheses:
            run.hypotheses[0].selected = True
            run.hypotheses[0].selection_rationale = _selection_rationale(run.hypotheses[0])
        reviewer_comments = sum(len(hypothesis.reviewer_comments) for hypothesis in run.hypotheses)
        revisions = sum(len(hypothesis.revision_history) for hypothesis in run.hypotheses)
        run.steps[-1].summary = (
            f"Generated {len(run.hypotheses)} hypotheses, "
            f"{reviewer_comments} reviewer comments, and {revisions} revisions."
        )

    async def _run_arena(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped arena (non-seismic domain)."
            return
        evidence = _workflow_evidence(run)
        gaps = await self.gap_finder.arun(run.knowledge_cards, evidence, run.data_profiles, run_id=run.run_id)
        avoid_prior_art = None
        if run.novelty_verdict and run.novelty_verdict.prior_art_paper_ids:
            paper_titles = {p.paper_id: p.title for p in run.papers}
            avoid_prior_art = [paper_titles[pid] for pid in run.novelty_verdict.prior_art_paper_ids if pid in paper_titles]
        result, hypotheses = await self.arena_agent.arun(
            run.mode, gaps, evidence, run.data_profiles, run.idea_brief, run.papers, run_id=run.run_id,
            avoid_prior_art=avoid_prior_art,
        )
        run.arena_result = result
        run.hypotheses = hypotheses
        selected = _selected_hypothesis(run.hypotheses)
        if run.steps:
            run.steps[-1].summary = (
                f"Arena ({result.mode}) ranked {len(result.ranking)} hypotheses; "
                f"selected={result.selected_for_experiment}, switchback={result.switchback_candidate}."
            ) + (f" Selected: {selected.statement[:80]}." if selected else "")

    async def _run_novelty_check(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped novelty check (non-seismic)."
            return
        selected = _selected_hypothesis(run.hypotheses)
        verdict = await self.novelty_checker.arun(
            run.papers, selected, run.idea_brief, run_id=run.run_id)
        run.novelty_verdict = verdict
        if verdict.verdict in ("transfer_applicability", "similar_work") and verdict.claim_revision:
            self.revision_agent.run(run.hypotheses, novelty_verdict=verdict)
        if verdict.verdict == "already_done":
            # dual effect: prior-art papers become baseline candidates
            for pid in verdict.prior_art_paper_ids:
                if not any(c.paper_id == pid for c in run.baseline_candidates):
                    run.baseline_candidates.append(_prior_art_as_candidate(pid, run.papers))
            run.novelty_round += 1
            if run.novelty_round >= 2:
                run.novelty_status = "low_novelty"
        else:
            run.novelty_status = "ok"
        if run.steps:
            run.steps[-1].summary = (
                f"Novelty: {verdict.verdict} (round {run.novelty_round}, status={run.novelty_status}).")

    def _route_after_novelty(self, state) -> str:
        run = state["run"]
        if run.domain != "seismic_event_classification":
            return "baseline_intake"  # shouldn't be reached (non-seismic skips this node)
        v = run.novelty_verdict
        if v and v.verdict == "already_done" and run.novelty_round < 2:
            return "arena"
        return "baseline_intake"

    def _route_after_gate(self, state) -> str:
        run = state["run"]
        if run.domain != "seismic_event_classification":
            return "experiment_design"
        g = run.baseline_gate_status
        if g and not g.research_gate_passed and run.re_search_round < 2:
            return "re_search_literature"
        return "experiment_design"

    def _route_after_research(self, state) -> str:
        run = state["run"]
        return "evidence_ledger" if run.evidence_changed else "baseline_intake"

    async def _extract_code_urls(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.papers:
            if run.steps:
                run.steps[-1].summary = "Skipped code-url extraction."
            return
        await extract_code_urls_async(run.papers, max_pdf=5)
        with_code = sum(1 for p in run.papers if p.code_url)
        if run.steps:
            run.steps[-1].summary = f"Mined code URLs from abstracts/PDFs; {with_code}/{len(run.papers)} papers have a code link."

    async def _discover_baselines_auto(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped baseline discovery (non-seismic)."
            return
        task = "seismic event classification"
        prior_art = [c for c in run.baseline_candidates if c.code_source == "prior_art"]
        discovered = await self.baseline_discovery.arun(run.papers, task, run_id=run.run_id)
        run.baseline_candidates = prior_art + discovered
        if run.steps:
            run.steps[-1].summary = f"Discovered {len(run.baseline_candidates)} baseline candidates (auto)."

    async def _verify_baselines_auto(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.baseline_candidates:
            if run.steps:
                run.steps[-1].summary = "Skipped repo verification (no candidates)."
            return
        to_verify = sorted(
            [c for c in run.baseline_candidates if not c.verified_repo and (c.is_model_baseline or c.repo_type == "unknown")],
            key=lambda c: c.baseline_priority_score,
            reverse=True,
        )[:3]
        for candidate in to_verify:
            try:
                updated = await self.repo_verifier.arun(candidate, run_id=run.run_id)
                idx = run.baseline_candidates.index(candidate)
                run.baseline_candidates[idx] = updated
            except Exception:
                continue
        model_baselines = sum(1 for c in run.baseline_candidates if c.is_model_baseline and c.verified_repo)
        if run.steps:
            run.steps[-1].summary = f"Verified {len(to_verify)} by priority; {model_baselines} verified model baselines."

    async def _run_baseline_intake(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped baseline intake (non-seismic)."
            return
        run.baseline_intake = await self.baseline_intake_agent.arun(run)
        if run.steps:
            run.steps[-1].summary = (
                f"Baseline intake: {run.baseline_intake.source_type} "
                f"({run.baseline_intake.trust_level})."
            )

    async def _evaluate_baseline_gate(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped baseline gate (non-seismic)."
            return
        if run.baseline_intake is not None:
            intake = run.baseline_intake
            if intake.source_type == "manual_upload":
                comparable = 1 if intake.metrics or intake.provenance_notes else 0
                run.baseline_gate_status = BaselineGateStatus(
                    external_verified_model_baselines=0,
                    comparable_count=comparable,
                    run_gate_passed=bool(comparable),
                    research_gate_passed=False,
                    insufficient_reasons=intake.limitations,
                    comparison_grade="degraded",
                )
            elif intake.source_type == "ai_generated":
                run.baseline_gate_status = BaselineGateStatus(
                    external_verified_model_baselines=0,
                    comparable_count=1,
                    run_gate_passed=True,
                    research_gate_passed=False,
                    insufficient_reasons=intake.limitations,
                    comparison_grade="degraded",
                )
            else:
                run.baseline_gate_status = BaselineGateStatus(
                    external_verified_model_baselines=0,
                    comparable_count=0,
                    run_gate_passed=False,
                    research_gate_passed=False,
                    insufficient_reasons=intake.limitations,
                    comparison_grade="degraded",
                )
            if run.steps:
                g = run.baseline_gate_status
                run.steps[-1].summary = (
                    f"Baseline gate from intake: {g.comparison_grade} "
                    f"(run_gate={g.run_gate_passed}, research_gate={g.research_gate_passed})."
                )
            return
        run.baseline_gate_status = _baseline_gate_status(run.baseline_candidates)
        g = run.baseline_gate_status
        if run.steps:
            run.steps[-1].summary = (
                f"Baseline gate: {g.comparison_grade} "
                f"(verified={g.external_verified_model_baselines}, "
                f"comparable={g.comparable_count}).")

    async def _re_search_literature(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped re-search (non-seismic)."
            return
        # Focused queries (escalate specificity by round).
        queries = [
            "seismic event classification deep learning github",
            "earthquake explosion CNN waveform code reproduction",
            "EQTransformer PhaseNet seismic waveform reproduction",
        ]
        round_idx = min(run.re_search_round, len(queries) - 1)
        new_papers = await self.literature_router.search(
            [queries[round_idx]], max_papers=run.constraints.max_papers,
            enable_semantic_scholar=run.constraints.enable_semantic_scholar,
            enable_arxiv=run.constraints.enable_arxiv, domain=run.domain,
        )
        # Replace dataset/no-code/non-eligible papers; keep method_model.
        keep = [p for p in run.papers if p.baseline_eligible]
        replaced = len(run.papers) - len(keep)
        run.papers = keep + new_papers
        run.evidence_changed = replaced > 0 or len(new_papers) > 0
        run.re_search_round += 1
        if run.steps:
            run.steps[-1].summary = (
                f"Re-search round {run.re_search_round}: replaced {replaced} non-eligible papers, "
                f"added {len(new_papers)} new; evidence_changed={run.evidence_changed}.")

    async def _run_code_experiment(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped code experiment (non-seismic)."
            return
        try:
            selected = _selected_hypothesis(run.hypotheses)
            mode = run.code_experiment_mode  # None / "initial" / "macro" / "switchback" / "redesign"
            if mode == "macro":
                prev_ce = run.code_experiment
                last_metrics = prev_ce.comparison.method_metrics if prev_ce else {}
                last_comparison = (
                    prev_ce.comparison.model_dump() if prev_ce else {})
                notes = prev_ce.comparison.notes if prev_ce else []
                source = await self.code_writer.arun(
                    "macro", selected, run.experiment_plan,
                    current_source=prev_ce.model_py_source if prev_ce else "",
                    last_metrics=last_metrics,
                    last_comparison=last_comparison,
                    notes=notes,
                    run_id=run.run_id,
                )
                trigger = "macro"
            elif mode == "switchback":
                top2_id = (
                    run.arena_result.switchback_candidate
                    if run.arena_result else None)
                top2 = None
                for h in run.hypotheses:
                    if h.hypothesis_id == top2_id:
                        top2 = h
                        break
                for h in run.hypotheses:
                    h.selected = False
                if top2 is not None:
                    top2.selected = True
                selected = top2
                source = await self.code_writer.arun(
                    "initial", selected, run.experiment_plan, run_id=run.run_id)
                trigger = "switchback"
            elif mode == "redesign":
                source = await self.code_writer.arun(
                    "initial", selected, run.experiment_plan, run_id=run.run_id)
                trigger = "redesign"
            else:
                source = await self.code_writer.arun(
                    "initial", selected, run.experiment_plan, run_id=run.run_id)
                trigger = "initial"
            run.code_experiment = await self._execute_micro_loop(
                run, source, selected, trigger)
            run.code_experiment_mode = None
            if run.steps:
                ce = run.code_experiment
                run.steps[-1].summary = (
                    f"Code experiment: {ce.comparison.outcome} "
                    f"(tests_pass={ce.acceptance_gate.tests_pass}, "
                    f"beats_baseline={ce.comparison.method_beats_baseline}, "
                    f"best_metric={ce.summary.best_metric}).")
        except Exception as exc:
            run.code_experiment = CodeExperimentResult(
                summary=ExperimentSummary(
                    outcome="failed",
                    tests_pass=False,
                    method_beats_baseline=False,
                    best_metric=None,
                    failure_reason=f"code experiment crashed: {exc!r}",
                ),
            )
            run.code_experiment_mode = None
            if run.steps:
                run.steps[-1].summary = f"Code experiment crashed: {exc!r}"

    async def _execute_micro_loop(
        self,
        run: ResearchRun,
        starting_source: str,
        hypothesis: Hypothesis | None,
        trigger: str,
    ) -> CodeExperimentResult:
        """S4 micro loop body: prepare sandbox -> tests max N -> train -> result."""
        sandbox_dir = self.settings.data_dir / "outputs" / run.run_id / "sandbox"
        fcp = self.fair_comparison_planner.plan()
        manifest = self._load_harness_manifest()
        max_rounds = int(manifest.get("max_repair_rounds", 3))
        iteration_log: list[IterEntry] = []
        debug_log: list[DebugEntry] = []
        source = starting_source
        tests_pass = False
        last_stderr = None
        try:
            for rnd in range(1, max_rounds + 1):
                self.sandbox_executor.prepare(sandbox_dir, source)
                res = self.sandbox_executor.run(sandbox_dir, "tests.py")
                tests_pass = res.exit_code == 0
                last_stderr = None if tests_pass else res.stderr
                iteration_log.append(IterEntry(
                    round=rnd,
                    phase="initial" if rnd == 1 else "repair",
                    model_py_hash=hashlib.md5(source.encode("utf-8")).hexdigest()[:8],
                    tests_passed=tests_pass,
                    traceback_summary=(last_stderr or "")[:300] or None,
                ))
                debug_log.append(DebugEntry(round=rnd, traceback_full=last_stderr, patch_diff=None))
                if tests_pass:
                    break
                if rnd < max_rounds:
                    source = await self.code_writer.arun(
                        "repair", hypothesis, run.experiment_plan,
                        current_source=source, traceback=last_stderr, run_id=run.run_id)
            gate = AcceptanceGate(tests_pass=tests_pass)
            comparison = ComparisonResult()
            if not tests_pass:
                comparison.outcome = "failed"
                comparison.notes.append("micro repair exhausted; tests.py never passed")
            else:
                self.sandbox_executor.clear_artifacts(sandbox_dir)
                tres = self.sandbox_executor.run(sandbox_dir, "train.py")
                metrics_p = sandbox_dir / "metrics.json"
                comp_p = sandbox_dir / "comparison.json"
                train_ok = tres.exit_code == 0 and not tres.timed_out
                gate.metrics_generated = train_ok and metrics_p.exists()
                gate.baseline_comparison_written = train_ok and comp_p.exists()
                if not train_ok or not (gate.metrics_generated and gate.baseline_comparison_written):
                    debug_log.append(DebugEntry(
                        round=len(iteration_log) + 1,
                        traceback_full=(tres.stderr or "") + (f"\n[timed_out={tres.timed_out}]" if tres.timed_out else ""),
                        patch_diff=None,
                    ))
                if train_ok and gate.metrics_generated and gate.baseline_comparison_written:
                    try:
                        comparison = ComparisonResult(**json.loads(comp_p.read_text(encoding="utf-8")))
                    except Exception:
                        comparison.outcome = "failed"
                        comparison.notes.append("comparison.json malformed")
                elif not train_ok:
                    comparison.outcome = "failed"
                    comparison.notes.append(
                        f"train.py failed (exit_code={tres.exit_code}, timed_out={tres.timed_out}); "
                        "metrics/comparison ignored"
                    )
                else:
                    comparison.outcome = "failed"
                    comparison.notes.append("train.py failed; metrics/comparison not written")
            best = _best_metric(comparison)
            failure_reason = (comparison.notes[0] if comparison.outcome == "failed" and comparison.notes else None)
            return CodeExperimentResult(
                model_py_source=source,
                fair_comparison_plan=fcp,
                acceptance_gate=gate,
                comparison=comparison,
                iteration_log=iteration_log,
                debug_log=debug_log,
                summary=ExperimentSummary(
                    outcome=comparison.outcome,
                    tests_pass=tests_pass,
                    method_beats_baseline=comparison.method_beats_baseline,
                    baseline_source=fcp.baseline_source,
                    best_metric=best,
                    failure_reason=failure_reason,
                ),
                trigger=trigger,
            )
        except Exception as exc:
            # S4 defensive catch (I1 fix) — never let the micro loop crash the workflow.
            return CodeExperimentResult(
                model_py_source=source,
                fair_comparison_plan=fcp,
                acceptance_gate=AcceptanceGate(tests_pass=tests_pass),
                comparison=ComparisonResult(outcome="failed", notes=[f"micro loop crashed: {exc!r}"]),
                iteration_log=iteration_log,
                debug_log=debug_log,
                summary=ExperimentSummary(
                    outcome="failed",
                    tests_pass=tests_pass,
                    method_beats_baseline=False,
                    baseline_source=fcp.baseline_source,
                    best_metric=None,
                    failure_reason=f"micro loop crashed: {exc!r}",
                ),
                trigger=trigger,
            )

    async def _run_macro_react(self, run: ResearchRun) -> None:
        """Decision step: evaluate code_experiment outcome, set code_experiment_mode."""
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped macro-react (non-seismic)."
            return
        run.code_experiment_mode = None  # default: accept
        ce = run.code_experiment
        if ce is None:
            if run.steps:
                run.steps[-1].summary = "Macro-react: no code experiment to evaluate."
            return
        outcome = ce.summary.outcome
        method = ce.summary.best_metric
        baseline = _baseline_metric(ce.comparison)
        margin = (baseline - method) if (method is not None and baseline is not None) else None
        bad = (outcome == "failed") or (
            outcome == "completed_negative" and margin is not None and margin >= 0.05)
        if not bad:
            if run.steps:
                run.steps[-1].summary = f"Macro-react: accept ({outcome})."
            return
        # escalate
        if run.macro_round < 1:
            run.macro_round += 1
            run.code_experiment_mode = "macro"
            if run.steps:
                run.steps[-1].summary = "Macro-react: macro repair (round 1)."
            return
        if not run.switchback_used and run.arena_result and run.arena_result.switchback_candidate:
            top2_id = run.arena_result.switchback_candidate
            if any(h.hypothesis_id == top2_id for h in run.hypotheses):
                run.switchback_used = True
                run.code_experiment_mode = "switchback"
                if run.steps:
                    run.steps[-1].summary = "Macro-react: switchback to Top2."
                return
        if run.steps:
            run.steps[-1].summary = "Macro-react: accept negative result (no further escalation)."

    async def _evaluate_experiment_result_gate(self, run: ResearchRun) -> None:
        ce = run.code_experiment
        if ce is None:
            if run.steps:
                run.steps[-1].summary = "Experiment result gate: no code experiment result."
            return
        if run.steps:
            run.steps[-1].summary = (
                f"Experiment result gate: {ce.summary.outcome}, "
                f"redesign_round={getattr(run, 'experiment_redesign_round', 0)}."
            )

    def _route_after_experiment_result(self, state) -> str:
        run = state["run"] if isinstance(state, dict) else state
        ce = run.code_experiment
        if run.domain != "seismic_event_classification" or ce is None:
            return "result_evaluation"
        if run.experiment_redesign_round >= 1:
            return "result_evaluation"
        if ce.summary.outcome == "completed_negative":
            baseline = _baseline_metric(ce.comparison)
            method = ce.summary.best_metric
            margin = (baseline - method) if baseline is not None and method is not None else None
            if margin is None or margin >= 0.05:
                return "experiment_redesign"
        return "result_evaluation"

    async def _redesign_experiment(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped experiment redesign (non-seismic)."
            return
        run.experiment_plan = await self.experiment_redesigner.arun(run)
        run.experiment_redesign_round += 1
        run.code_experiment_mode = "redesign"
        if run.steps:
            run.steps[-1].summary = f"Redesigned experiment plan (round {run.experiment_redesign_round})."

    def _route_after_macro(self, state) -> str:
        """Route after macro_react: honor code_experiment_mode set by the decision step."""
        run = state["run"]
        if run.domain != "seismic_event_classification":
            return "report_writer"
        return "code_experiment" if run.code_experiment_mode is not None else "report_writer"

    def _load_harness_manifest(self) -> dict:
        path = self.settings.experiments_dir / "harness_manifest.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"max_repair_rounds": 3}

    async def _classify_papers(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.papers:
            if run.steps:
                run.steps[-1].summary = "Skipped paper classification."
            return
        await self.paper_classifier.arun(run.papers, run_id=run.run_id)
        eligible = sum(1 for p in run.papers if p.baseline_eligible)
        if run.steps:
            run.steps[-1].summary = f"Classified {len(run.papers)} papers; {eligible} method-model (baseline-eligible)."

    async def _design_experiment(self, run: ResearchRun) -> None:
        run.experiment_plan = await self.experiment_designer.arun(
            _selected_hypothesis(run.hypotheses),
            run.data_profiles,
            _workflow_evidence(run),
            run_id=run.run_id,
        )
        run.steps[-1].summary = "Created baselines, metrics, experiment steps, and failure modes."

    async def _profile_scientific_data(self, run: ResearchRun) -> None:
        if run.domain == "seismic_event_classification":
            run.seismic_data_profile = self.seismic_adapter.profile()
            run.data_profiles = []
            run.baseline_result_card = None
            if run.steps:
                run.steps[-1].summary = (
                    f"Profiled seismic demo subset: {run.seismic_data_profile.num_events} events, "
                    f"labels={run.seismic_data_profile.labels}; risks={len(run.seismic_data_profile.risks)}."
                )
            return
        run.data_profiles, run.baseline_result_card = self.scientific_data_agent.run()
        if run.steps:
            run.steps[-1].summary = (
                f"Profiled {len(run.data_profiles)} data sources and generated result card "
                f"{run.baseline_result_card.name if run.baseline_result_card else 'none'}."
            )

    async def _write_report(self, run: ResearchRun) -> None:
        if run.experiment_plan is None:
            run.experiment_plan = await self.experiment_designer.arun(
                _selected_hypothesis(run.hypotheses),
                run.data_profiles,
                _workflow_evidence(run),
                run_id=run.run_id,
            )
        run.report = await self.report_writer.arun(
            run,
            _selected_hypothesis(run.hypotheses),
            run.experiment_plan,
            run.evidence,
            run.papers,
            run.knowledge_cards,
            run.data_profiles,
            run.baseline_result_card,
        )
        _write_markdown_report(run, self.settings.data_dir)
        run.steps[-1].summary = "Exported contest-format report with citation audit log."

    async def _evaluate_results(self, run: ResearchRun) -> None:
        run.result_evaluation = await self.result_evaluator.arun(run)

    async def _analyze_ablations(self, run: ResearchRun) -> None:
        run.ablation_analysis = await self.ablation_agent.arun(run)

    async def _interpret_results(self, run: ResearchRun) -> None:
        run.result_interpretation = await self.result_interpreter.arun(run)

    async def _run_result_analysis(self, run: ResearchRun) -> None:
        await self._step(run, "result_evaluation", self._evaluate_results)
        await self._step(run, "ablation_analysis", self._analyze_ablations)
        await self._step(run, "result_interpretation", self._interpret_results)

    async def _verify_claims(self, run: ResearchRun) -> None:
        if run.report is None:
            run.steps[-1].summary = "Skipped claim verification because no report was generated."
            return
        run.claim_audit = await self.claim_verifier.arun(
            run,
            run.report,
            reportable_evidence(run),
            _selected_hypothesis(run.hypotheses),
        )
        _write_markdown_report(run, self.settings.data_dir)
        run.steps[-1].summary = (
            f"Audited {run.claim_audit.total} report claims; "
            f"support_score={run.claim_audit.support_score}."
        )

    async def _revise_report_after_audit(self, run: ResearchRun) -> None:
        if run.report is None or run.claim_audit is None:
            run.steps[-1].summary = "Skipped report revision because report or claim audit is missing."
            return
        before = run.claim_audit.support_score
        flagged = run.claim_audit.weakly_supported + run.claim_audit.unsupported
        if flagged == 0 and before >= 0.8:
            run.report = self.report_reviser.run(
                run,
                run.report,
                run.claim_audit,
                reportable_evidence(run),
                run.papers,
                run.knowledge_cards,
            )
            _write_markdown_report(run, self.settings.data_dir)
            run.steps[-1].summary = (
                f"Report already passed audit gates; enforced evidence/inference/validation labels "
                f"without Qwen revision. support_score={before}."
            )
            return
        run.report = await self.report_reviser.arun(
            run,
            run.report,
            run.claim_audit,
            reportable_evidence(run),
            run.papers,
            run.knowledge_cards,
            _selected_hypothesis(run.hypotheses),
        )
        _write_markdown_report(run, self.settings.data_dir)
        run.steps[-1].summary = (
            f"Revised report after audit; prior support_score={before}, "
            f"flagged_claims={flagged}. Re-running claim verifier next."
        )

    async def _translate_report(self, run: ResearchRun) -> None:
        if run.report is None or run.report.english_report is None:
            run.steps[-1].summary = "Skipped report translation because no final English report was generated."
            return
        run.report = await self.report_translator.arun(run, run.report)
        _write_markdown_report(run, self.settings.data_dir)
        run.steps[-1].summary = "Translated final audited English report into Chinese for human review."

    def _write_workspace(self, run: ResearchRun) -> None:
        run.workspace_path = str(self.workspace.ensure(run))
        run.workspace_artifacts = self.workspace.write_snapshot(run)


def _baseline_gate_status(candidates: list[BaselineCandidate]) -> BaselineGateStatus:
    verified = [
        c for c in candidates
        if c.verified_repo
        and c.is_model_baseline
        and c.matches_task_domain
        and c.repo_type == "model_code"
        and c.reproducibility_score >= 0.6
        and c.reproduction_status == "verified"
    ]
    ext_verified = len(verified)
    comparable = ext_verified + 1  # harness_trivial always available
    reasons: list[str] = []
    if ext_verified == 0:
        reasons.append("no verified external model baseline")
    if candidates and all(
        (c.repo_type in ("dataset_only", "docs_only", "unknown") and not c.is_model_baseline)
        for c in candidates):
        reasons.append("all candidates are dataset/docs/empty repos")
    if comparable < 2:
        reasons.append(f"only {comparable} comparable model(s) (need >=2)")
    if any(c.is_model_baseline and not c.matches_task_domain for c in candidates):
        reasons.append("baseline does not match seismic task domain")
    if any(c.is_model_baseline and c.reproducibility_score < 0.6 for c in candidates):
        reasons.append("repo reproducibility score below 0.6")
    return BaselineGateStatus(
        external_verified_model_baselines=ext_verified,
        comparable_count=comparable,
        run_gate_passed=comparable >= 1,
        research_gate_passed=ext_verified >= 1,
        insufficient_reasons=reasons,
        comparison_grade="research" if ext_verified >= 1 else "degraded",
    )


def _selected_hypothesis(hypotheses: list[Hypothesis]) -> Hypothesis | None:
    return next((hypothesis for hypothesis in hypotheses if hypothesis.selected), hypotheses[0] if hypotheses else None)


def _prior_art_as_candidate(pid: str, papers: list) -> BaselineCandidate:
    """Build a minimal baseline candidate from a prior-art paper id."""
    paper = next((p for p in papers if p.paper_id == pid), None)
    return BaselineCandidate(
        baseline_id=f"prior_art_{pid}",
        paper_id=pid,
        paper_title=paper.title if paper else pid,
        code_url=paper.code_url if paper else None,
        code_source="prior_art",
        task_match="seismic",
        input_type="unknown",
        is_model_baseline=False,
        repo_type="unknown",
        reproduction_status="pending",
    )


def _best_metric(comparison: ComparisonResult) -> float | None:
    m = comparison.method_metrics or {}
    for key in ("accuracy", "macro_f1"):
        v = m.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _baseline_metric(comparison: ComparisonResult) -> float | None:
    m = comparison.baseline_metrics or {}
    for key in ("accuracy", "macro_f1"):
        v = m.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _workflow_evidence(run: ResearchRun):
    selected = reportable_evidence(run)
    if run.citation_frozen or run.evidence_frozen:
        return selected
    return selected or run.evidence


def _selection_rationale(hypothesis: Hypothesis) -> str:
    if hypothesis.critic is None:
        return "Selected as the default candidate for downstream experiment design."
    return (
        "Selected because it has the strongest MVP balance of "
        f"verifiability={hypothesis.critic.verifiability}, "
        f"data_availability={hypothesis.critic.data_availability}, "
        f"evidence_support={hypothesis.critic.evidence_support}, and "
        f"competition_fit={hypothesis.critic.competition_fit}."
    )


def _write_markdown_report(run: ResearchRun, data_dir: Path) -> None:
    if run.report is None:
        return
    out_dir = data_dir / "outputs" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run.run_id}.md"
    report = run.report
    if report.english_report and report.chinese_report:
        path.write_text(_bilingual_markdown_report(run), encoding="utf-8")
        return

    references = _reference_markdown(report.references)
    audit = "\n".join(f"- {line}" for line in report.citation_audit_log)
    path.write_text(
        f"# English Report\n\n"
        f"## 1. Paper Title\n{report.paper_title}\n\n"
        f"## 2. Paper Abstract\n{report.paper_abstract}\n\n"
        f"## 3. Problem Statement\n{report.problem_statement}\n\n"
        f"## 4. Rationale\n{report.rationale}\n\n"
        f"## 5. Technical Details\n{_markdown_list(report.technical_details)}\n\n"
        f"## 6. Datasets\n\n### 6.1 Source\n{report.source}\n\n### 6.2 Target\n{report.target}\n\n"
        f"## 7. Methods\n{_markdown_list(report.methods)}\n\n"
        f"## 8. Experiments\n\n### 8.1 Baselines\n{_markdown_list(report.experiments.baselines)}\n\n"
        f"### 8.2 Metrics\n{_markdown_list(report.experiments.metrics)}\n\n"
        f"### 8.3 Experimental Design\n{_markdown_list(report.experiments.experiment_steps)}\n\n"
        f"## 9. Results\n\n### 9.1 Executed Results\n{report.results}\n\n"
        f"### 9.2 Expected Validation Outcomes\n{report.experiments.expected_results}\n\n"
        f"## 10. Limitations and Risk Controls\nSee audit appendix.\n\n"
        f"## 11. References\n{references}\n\n"
        f"# System Provenance and Audit Appendix\n\n"
        f"## Citation Audit Log\n{audit}\n",
        encoding="utf-8",
    )


def _bilingual_markdown_report(run: ResearchRun) -> str:
    report = run.report
    assert report is not None and report.english_report is not None and report.chinese_report is not None
    english = report.english_report
    chinese = report.chinese_report
    provenance = report.system_provenance
    return (
        "# English Report\n\n"
        f"## 1. Paper Title\n{english.paper_title}\n\n"
        f"## 2. Paper Abstract\n{english.paper_abstract}\n\n"
        f"## 3. Problem Statement\n{english.problem_statement}\n\n"
        f"## 4. Rationale\n{english.rationale}\n\n"
        f"## 5. Technical Details\n{english.technical_details}\n\n"
        f"## 6. Datasets\n\n### 6.1 Source\n{english.datasets.source}\n\n### 6.2 Target\n{english.datasets.target}\n\n"
        f"## 7. Methods\n{english.methods}\n\n"
        f"## 8. Experiments\n\n### 8.1 Baselines\n{english.experiments.baselines}\n\n"
        f"### 8.2 Metrics\n{english.experiments.metrics}\n\n"
        f"### 8.3 Experimental Design\n{english.experiments.design}\n\n"
        f"## 9. Results\n\n### 9.1 Executed Results\n{english.results.executed_results}\n\n"
        f"### 9.2 Expected Validation Outcomes\n{english.results.expected_validation_outcomes}\n\n"
        f"## 10. Limitations and Risk Controls\n{english.limitations_and_risk_controls}\n\n"
        f"## 11. References\n{_reference_markdown(english.references)}\n\n"
        "# 中文报告\n\n"
        f"## 1. 标题\n{chinese.paper_title}\n\n"
        f"## 2. 摘要\n{chinese.paper_abstract}\n\n"
        f"## 3. 待研究问题\n{chinese.problem_statement}\n\n"
        f"## 4. 解决思路\n{chinese.rationale}\n\n"
        f"## 5. 必要的技术手段\n{chinese.technical_details}\n\n"
        f"## 6. 数据集\n\n### 6.1 Source: 假设推演依据的历史数据\n{chinese.datasets.source}\n\n"
        f"### 6.2 Target: 验证实验所需的拟采集数据特征\n{chinese.datasets.target}\n\n"
        f"## 7. 方法论\n{chinese.methods}\n\n"
        f"## 8. 实验设计\n\n### 8.1 基线对比\n{chinese.experiments.baselines}\n\n"
        f"### 8.2 评估指标\n{chinese.experiments.metrics}\n\n"
        f"### 8.3 实验流程\n{chinese.experiments.design}\n\n"
        f"## 9. 实验结果\n\n### 9.1 已执行结果\n{chinese.results.executed_results}\n\n"
        f"### 9.2 预期验证结果\n{chinese.results.expected_validation_outcomes}\n\n"
        f"## 10. 局限性与风险控制\n{chinese.limitations_and_risk_controls}\n\n"
        f"## 11. 参考论文\n{_reference_markdown(chinese.references)}\n\n"
        "# System Provenance and Audit Appendix\n\n"
        f"## Agent Workflow\n{_workflow_markdown(provenance.agent_workflow if provenance else [])}\n\n"
        f"## Evidence Ledger\n{_evidence_markdown(provenance.evidence_ledger if provenance else [])}\n\n"
        f"## Citation Audit Log\n{_markdown_list(provenance.citation_audit_log if provenance else [])}\n\n"
        f"## Claim Audit Summary\n```json\n{run.claim_audit.model_dump_json(indent=2) if run.claim_audit else '{}'}\n```\n\n"
        f"## Run Metadata\n```json\n{provenance.model_dump_json(indent=2) if provenance else '{}'}\n```\n"
    )


def _reference_markdown(references) -> str:
    if not references:
        return "- No verified report-eligible references are available."
    lines = []
    for paper in references:
        identifier = paper.doi or paper.arxiv_id or paper.openalex_id or paper.source_url or "N/A"
        lines.append(
            f"- {paper.title} ({paper.year or 'n.d.'}). ID: {identifier}. "
            f"Verification: {paper.verification_method or paper.verification_status}; "
            f"confidence={paper.verification_confidence if paper.verification_confidence is not None else 'n/a'}."
        )
    return "\n".join(lines)


def _workflow_markdown(items: list[dict]) -> str:
    if not items:
        return "- No agent workflow steps recorded."
    return "\n".join(
        f"- {item.get('name', 'unknown')}: {item.get('status', 'unknown')} - {item.get('summary', '')}"
        for item in items
    )


def _evidence_markdown(items: list[dict]) -> str:
    if not items:
        return "- No evidence ledger items recorded."
    return "\n".join(
        f"- {item.get('evidence_id')}: {item.get('claim')} "
        f"(verified={item.get('verified')}, eligible={item.get('eligible_for_report')}, "
        f"method={item.get('verification_method')}, confidence={item.get('confidence')})"
        for item in items
    )


def _markdown_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None"


def _stage_start_summary(name: str) -> str:
    summaries = {
        "intent_router": "Classifying the research entry mode and structuring the user idea if present.",
        "planner": "Planning sub-questions, search queries, perspectives, evidence requirements, and risk controls.",
        "literature_search": "Searching scholarly sources and deduplicating candidate papers across enabled literature APIs.",
        "citation_verification": "Verifying candidate papers with DOI, arXiv ID, title, and source metadata checks.",
        "evidence_ledger": "Converting verified papers into traceable evidence items for downstream claims.",
        "literature_mining": "Mining evidence into knowledge cards tied to perspectives and report eligibility.",
        "paper_classification": "Classifying papers by role (method_model, dataset_benchmark, survey, application) for baseline eligibility.",
        "scientific_data_profile": "Profiling scientific datasets and generating a bounded baseline result card.",
        "hypothesis_debate": "Generating hypotheses, collecting reviewer-style critiques, and revising candidates.",
        "arena": "Running multi-perspective hypothesis arena with weighted ranking and auto-selection.",
        "baseline_intake": "Recording user-selected baseline strategy and provenance.",
        "extract_code_urls": "Mining code URLs from paper abstracts and PDF full text.",
        "baseline_discover": "Discovering baseline candidates from GitHub and Papers with Code.",
        "baseline_verify": "Auto-verifying baseline repository reproducibility.",
        "experiment_design": "Building datasets, baselines, metrics, experiment steps, expected results, and failure modes.",
        "report_writer": "Assembling the contest-format report from verified references and eligible evidence.",
        "claim_verification": "Auditing report claims against reportable evidence and selected hypothesis support.",
        "report_revision": "Rewriting weak or unsupported report claims into evidence-backed, inference, and to-validate layers.",
        "claim_reverification": "Re-auditing the revised report after post-audit report revision.",
        "report_translation": "Translating the final audited English report into Chinese.",
    }
    return summaries.get(name, "Running workflow step.")


_STEP_METHODS = {
    "intent_router": "_route_intent",
    "planner": "_plan",
    "literature_search": "_search_literature",
    "citation_verification": "_verify_citations",
    "evidence_ledger": "_build_evidence",
    "literature_mining": "_mine_literature",
    "paper_classification": "_classify_papers",
    "scientific_data_profile": "_profile_scientific_data",
    "hypothesis_debate": "_generate_and_critique",
    "arena": "_run_arena",
    "novelty_check": "_run_novelty_check",
    "baseline_intake": "_run_baseline_intake",
    "baseline_quality_gate": "_evaluate_baseline_gate",
    "experiment_design": "_design_experiment",
    "code_experiment": "_run_code_experiment",
    "experiment_result_gate": "_evaluate_experiment_result_gate",
    "experiment_redesign": "_redesign_experiment",
    "result_evaluation": "_evaluate_results",
    "ablation_analysis": "_analyze_ablations",
    "result_interpretation": "_interpret_results",
    "report_writer": "_write_report",
    "claim_verification": "_verify_claims",
    "report_revision": "_revise_report_after_audit",
    "claim_reverification": "_verify_claims",
    "report_translation": "_translate_report",
}
