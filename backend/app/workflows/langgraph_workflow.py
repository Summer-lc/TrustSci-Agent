"""LangGraph orchestration layer for TrustSci-Agent.

This module mirrors the linear ``ScientistWorkflow`` as a LangGraph
``StateGraph`` while reusing every existing step method, the ``_step``
bookkeeping, ``QwenClient``, LLM logging, fallbacks, report generation, and
guided pause semantics. It is only engaged when
``Settings.workflow_engine == "langgraph"``; the default (``"classic"``) keeps
the hand-written ``ScientistWorkflow`` untouched.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from app.config import Settings
from app.schemas.common import RunStatus, utc_now
from app.schemas.run import ResearchRun
from app.storage.in_memory import run_store
from app.tools.langchain_literature_tools import (
    build_arxiv_search_tool,
    build_crossref_search_tool,
    build_crossref_verify_tool,
    build_openalex_search_tool,
    search_literature_with_tools,
    verify_citations_with_tools,
)
from app.workflows.scientist_workflow import RunControlSignal, ScientistWorkflow, StepNeedsAction

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt

    _HAS_LANGGRAPH = True
except ImportError:  # pragma: no cover - langgraph optional for the classic engine
    _HAS_LANGGRAPH = False
    MemorySaver = None  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]
    START = None  # type: ignore[assignment]
    END = None  # type: ignore[assignment]
    Command = None  # type: ignore[assignment]
    interrupt = None  # type: ignore[assignment]


def _replace(_old: ResearchRun, new: ResearchRun) -> ResearchRun:
    """Whole-object replace reducer: the run is one channel, not merged fields."""
    return new


class WorkflowState(TypedDict):
    run: Annotated[ResearchRun, _replace]


_CITATION_PAUSE_SUMMARY = (
    "Citation verification is complete. Review papers, accept/reject citations, "
    "then freeze citations before continuing."
)
_EVIDENCE_PAUSE_SUMMARY = (
    "Evidence ledger is ready. Review evidence, accept/reject items, "
    "then freeze evidence before continuing."
)

# Linear step order, matching ScientistWorkflow._run_after_evidence_review and
# the PRD_v3 node chain. Each maps 1:1 to an inherited _step target.
_LINEAR_STEPS: tuple[tuple[str, str], ...] = (
    ("planner", "_plan"),
    ("literature_search", "_search_literature_with_langchain_tools"),
    ("citation_verification", "_verify_citations_with_langchain_tools"),
    ("evidence_ledger", "_build_evidence"),
    ("literature_mining", "_mine_literature"),
    ("scientific_data_profile", "_profile_scientific_data"),
    ("hypothesis_debate", "_generate_and_critique"),
    ("experiment_design", "_design_experiment"),
    ("report_writer", "_write_report"),
    ("claim_verification", "_verify_claims"),
    ("report_revision", "_revise_report_after_audit"),
    ("claim_reverification", "_verify_claims"),
    ("report_translation", "_translate_report"),
)

_LANGGRAPH_WORKFLOW_CACHE: dict[int, "LangGraphWorkflow"] = {}


class LangGraphWorkflow(ScientistWorkflow):
    """LangGraph-backed workflow preserving the ScientistWorkflow contract.

    Public surface (``run`` / ``continue_run``) is identical to
    ``ScientistWorkflow``. The only difference is that the linear
    ``await self._step(...)`` chain is driven by a compiled LangGraph
    ``StateGraph``.
    """

    def __init__(self, settings: Settings) -> None:
        if not _HAS_LANGGRAPH:
            raise RuntimeError(
                "WORKFLOW_ENGINE=langgraph requires the 'langgraph' package. "
                "Install it (pip install langgraph) or set WORKFLOW_ENGINE=classic."
            )
        super().__init__(settings)
        self.openalex_search_tool = build_openalex_search_tool(self.openalex)
        self.arxiv_search_tool = build_arxiv_search_tool(self.arxiv)
        self.crossref_search_tool = build_crossref_search_tool(self.crossref)
        self.crossref_verify_tool = build_crossref_verify_tool(self.crossref)
        self.literature_tool_source_stats: dict[str, int] = {}
        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()

    # -- public contract (mirrors ScientistWorkflow.run / continue_run) --

    async def run(self, run: ResearchRun) -> ResearchRun:
        run.status = RunStatus.running
        run.steps = []
        self._write_workspace(run)
        run_store.save(run)

        try:
            await self._invoke(run)
            # Match classic: a guided pause early-returns without the post-try
            # workspace/updated_at bump (the pause node already wrote them).
            if run.status == RunStatus.paused:
                return run_store.save(run)
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
                await self._resume(run, {"checkpoint": "citation_review", "citation_frozen": True})
                return run_store.save(run)
            if run.current_stage == "awaiting_evidence_review":
                if not run.evidence_frozen:
                    raise ValueError("Freeze evidence before continuing the guided workflow.")
                run.status = RunStatus.running
                await self._resume(run, {"checkpoint": "evidence_review", "evidence_frozen": True})
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

    # -- graph construction --

    def _build_graph(self):
        graph: StateGraph = StateGraph(WorkflowState)
        graph.add_node("entry", self._node_entry)
        for name, _method in _LINEAR_STEPS:
            graph.add_node(name, self._make_step_node(name, _method))
        graph.add_node("pause_citation", self._node_pause_citation)
        graph.add_node("pause_evidence", self._node_pause_evidence)
        graph.add_node("finalize", self._node_finalize)

        graph.add_edge(START, "entry")
        graph.add_conditional_edges(
            "entry",
            self._route_entry,
            {
                "intent_router": "intent_router",
                "evidence_ledger": "evidence_ledger",
                "paper_classification": "paper_classification",
                "scientific_data_profile": "scientific_data_profile",
            },
        )
        # v3 Layer 0: intent router branches to mode-specific placeholder nodes.
        # S3/S4/S6 replace these placeholders with Arena / Code Loop / Assistance.
        graph.add_node("intent_router", self._make_step_node("intent_router", "_route_intent"))
        graph.add_node("branch_discovery", self._node_passthrough)
        graph.add_node("branch_idea_refinement", self._node_passthrough)
        graph.add_node("branch_experiment_assistance", self._node_passthrough)
        graph.add_conditional_edges(
            "intent_router",
            self._route_by_mode,
            {
                "discovery": "branch_discovery",
                "idea_refinement": "branch_idea_refinement",
                "experiment_assistance": "branch_experiment_assistance",
            },
        )
        graph.add_edge("branch_discovery", "planner")
        graph.add_edge("branch_idea_refinement", "planner")
        graph.add_edge("branch_experiment_assistance", "planner")

        graph.add_edge("planner", "literature_search")
        graph.add_edge("literature_search", "citation_verification")
        graph.add_conditional_edges(
            "citation_verification",
            self._route_after_citation,
            {"pause_citation": "pause_citation", "evidence_ledger": "evidence_ledger"},
        )
        graph.add_edge("pause_citation", "evidence_ledger")

        graph.add_edge("evidence_ledger", "literature_mining")
        graph.add_conditional_edges(
            "literature_mining",
            self._route_after_mining,
            {"pause_evidence": "pause_evidence", "paper_classification": "paper_classification"},
        )
        graph.add_node("paper_classification", self._make_step_node("paper_classification", "_classify_papers"))
        graph.add_edge("paper_classification", "scientific_data_profile")
        graph.add_edge("pause_evidence", "paper_classification")

        graph.add_conditional_edges(
            "scientific_data_profile",
            self._route_after_data_profile,
            {"arena": "arena", "hypothesis_debate": "hypothesis_debate", "result_evaluation": "result_evaluation"},
        )
        # Seismic arena + baseline auto chain (S3).
        graph.add_node("arena", self._make_step_node("arena", "_run_arena"))
        graph.add_node("baseline_intake", self._make_step_node("baseline_intake", "_run_baseline_intake"))
        # S5: novelty_check sits between arena and extract_code_urls, with a
        # conditional back-edge to arena for already_done (capped at 2 rounds).
        graph.add_node("novelty_check", self._make_step_node("novelty_check", "_run_novelty_check"))
        graph.add_edge("arena", "novelty_check")
        graph.add_conditional_edges(
            "novelty_check",
            self._route_after_novelty,
            {"arena": "arena", "baseline_intake": "baseline_intake"},
        )
        # S5 Task 7: baseline_quality_gate + re_search_literature cycle between
        # baseline_verify and experiment_design (seismic-only branch).
        graph.add_node("baseline_quality_gate", self._make_step_node("baseline_quality_gate", "_evaluate_baseline_gate"))
        graph.add_node("re_search_literature", self._make_step_node("re_search_literature", "_re_search_literature"))
        graph.add_edge("baseline_intake", "baseline_quality_gate")
        graph.add_conditional_edges(
            "baseline_quality_gate",
            self._route_after_gate,
            {"re_search_literature": "re_search_literature", "experiment_design": "experiment_design"},
        )
        graph.add_conditional_edges(
            "re_search_literature",
            self._route_after_research,
            {"evidence_ledger": "evidence_ledger", "baseline_intake": "baseline_intake"},
        )
        graph.add_edge("hypothesis_debate", "experiment_design")
        # S4: code_experiment sits between experiment_design and report_writer.
        # _run_code_experiment is a no-op for non-seismic domains (first-line
        # domain check), so both seismic and non-seismic runs traverse it —
        # same pattern as paper_classification.
        graph.add_node("code_experiment", self._make_step_node("code_experiment", "_run_code_experiment"))
        graph.add_edge("experiment_design", "code_experiment")
        # S5 Task 8: macro_react sits between code_experiment and report_writer.
        # code_experiment resets code_experiment_mode=None after running; macro_react
        # evaluates the result and sets mode if escalation is warranted; the route
        # honors mode (loop back) or None (accept → report_writer).
        graph.add_node("experiment_result_gate", self._make_step_node("experiment_result_gate", "_evaluate_experiment_result_gate"))
        graph.add_node("experiment_redesign", self._make_step_node("experiment_redesign", "_redesign_experiment"))
        graph.add_edge("code_experiment", "experiment_result_gate")
        graph.add_conditional_edges(
            "experiment_result_gate",
            self._route_after_experiment_result,
            {"experiment_redesign": "experiment_redesign", "result_evaluation": "result_evaluation"},
        )
        graph.add_edge("experiment_redesign", "code_experiment")
        graph.add_node("result_evaluation", self._make_step_node("result_evaluation", "_evaluate_results"))
        graph.add_node("ablation_analysis", self._make_step_node("ablation_analysis", "_analyze_ablations"))
        graph.add_node("result_interpretation", self._make_step_node("result_interpretation", "_interpret_results"))
        graph.add_edge("result_evaluation", "ablation_analysis")
        graph.add_edge("ablation_analysis", "result_interpretation")
        graph.add_edge("result_interpretation", "report_writer")
        graph.add_edge("report_writer", "claim_verification")
        graph.add_edge("claim_verification", "report_revision")
        graph.add_edge("report_revision", "claim_reverification")
        graph.add_edge("claim_reverification", "report_translation")
        graph.add_edge("report_translation", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=self._checkpointer)

    async def _invoke(self, run: ResearchRun) -> None:
        await self._graph.ainvoke({"run": run}, config=self._graph_config(run))

    async def _resume(self, run: ResearchRun, resume_value: dict) -> None:
        await self._graph.ainvoke(
            Command(update={"run": run}, resume=resume_value),
            config=self._graph_config(run),
        )

    @staticmethod
    def _graph_config(run: ResearchRun) -> dict:
        return {"configurable": {"thread_id": run.run_id}}

    # -- nodes --

    async def _node_entry(self, state: WorkflowState) -> WorkflowState:
        return {"run": state["run"]}

    async def _node_passthrough(self, state: WorkflowState) -> WorkflowState:
        """Placeholder for a mode-specific branch; S3/S4/S6 fill these in."""
        return {"run": state["run"]}

    def _route_by_mode(self, state: WorkflowState) -> str:
        return state["run"].mode

    def _make_step_node(self, name: str, method_name: str):
        """Wrap an inherited ``self._step(run, name, self.<method>)`` as a node."""

        async def _node(state: WorkflowState) -> WorkflowState:
            run = state["run"]
            await self._step(run, name, getattr(self, method_name))
            return {"run": run}

        _node.__name__ = f"_node_{name}"
        return _node

    async def _node_pause_citation(self, state: WorkflowState) -> WorkflowState:
        run = state["run"]
        if run.current_stage != "awaiting_citation_review":
            self._pause_for_human(
                run,
                "awaiting_citation_review",
                _CITATION_PAUSE_SUMMARY,
                progress=0.36,
            )
            run_store.save(run)
        interrupt(
            {
                "checkpoint": "citation_review",
                "run_id": run.run_id,
                "current_stage": run.current_stage,
                "message": _CITATION_PAUSE_SUMMARY,
            }
        )
        return {"run": run}

    async def _node_pause_evidence(self, state: WorkflowState) -> WorkflowState:
        run = state["run"]
        if run.current_stage != "awaiting_evidence_review":
            self._pause_for_human(
                run,
                "awaiting_evidence_review",
                _EVIDENCE_PAUSE_SUMMARY,
                progress=0.58,
            )
            run_store.save(run)
        interrupt(
            {
                "checkpoint": "evidence_review",
                "run_id": run.run_id,
                "current_stage": run.current_stage,
                "message": _EVIDENCE_PAUSE_SUMMARY,
            }
        )
        return {"run": run}

    async def _search_literature_with_langchain_tools(self, run: ResearchRun) -> None:
        queries = [str(query) for query in (run.plan.get("search_queries") or [run.question])]
        run.papers, self.literature_tool_source_stats = await search_literature_with_tools(
            queries=queries,
            max_papers=run.constraints.max_papers,
            openalex_search_tool=self.openalex_search_tool,
            arxiv_search_tool=self.arxiv_search_tool,
            crossref_search_tool=self.crossref_search_tool,
            enable_arxiv=run.constraints.enable_arxiv,
            domain=run.domain,
        )
        sources = sorted({paper.source_api for paper in run.papers})
        stats = ", ".join(f"{source}:{count}" for source, count in self.literature_tool_source_stats.items())
        run.steps[-1].summary = (
            f"Collected {len(run.papers)} candidate papers through LangChain Tools from "
            f"{', '.join(sources) or 'OpenAlex/arXiv'}"
            f"{f' ({stats})' if stats else ''}."
        )

    async def _verify_citations_with_langchain_tools(self, run: ResearchRun) -> None:
        run.papers, run.citation_report = await verify_citations_with_tools(
            papers=run.papers,
            openalex_search_tool=self.openalex_search_tool,
            arxiv_search_tool=self.arxiv_search_tool,
            crossref_verify_tool=self.crossref_verify_tool,
        )
        report = run.citation_report
        run.steps[-1].summary = (
            f"Verified {report.verified}/{report.total} papers through LangChain Tool nodes; "
            f"integrity_score={report.integrity_score}."
        )

    async def _node_finalize(self, state: WorkflowState) -> WorkflowState:
        run = state["run"]
        run.status = RunStatus.completed
        run.current_stage = "completed"
        run.progress = 1.0
        run.updated_at = utc_now()
        self._write_workspace(run)
        return {"run": run}

    # -- routing --

    def _route_entry(self, state: WorkflowState) -> str:
        run = state["run"]
        if run.current_stage == "awaiting_citation_review":
            return "evidence_ledger"
        if run.current_stage == "awaiting_evidence_review":
            return "paper_classification"
        return "intent_router"

    def _route_after_citation(self, state: WorkflowState) -> str:
        run = state["run"]
        if run.constraints.workflow_mode == "guided" and not run.citation_frozen:
            return "pause_citation"
        return "evidence_ledger"

    def _route_after_mining(self, state: WorkflowState) -> str:
        run = state["run"]
        if run.constraints.workflow_mode == "guided" and not run.evidence_frozen:
            return "pause_evidence"
        return "paper_classification"

    def _route_after_data_profile(self, state: WorkflowState) -> str:
        run = state["run"]
        if run.mode == "experiment_assistance":
            return "result_evaluation"
        return "arena" if run.domain == "seismic_event_classification" else "hypothesis_debate"


def build_workflow(settings: Settings) -> ScientistWorkflow:
    """Return the configured workflow engine (classic by default)."""
    if str(settings.workflow_engine).lower() == "langgraph":
        # LangGraph interrupt() checkpoints are attached to the compiled graph's
        # checkpointer. FastAPI calls build_workflow() across /start and
        # /continue requests, so keep one workflow per Settings instance in the
        # current backend process.
        key = id(settings)
        workflow = _LANGGRAPH_WORKFLOW_CACHE.get(key)
        if workflow is None:
            workflow = LangGraphWorkflow(settings)
            _LANGGRAPH_WORKFLOW_CACHE[key] = workflow
        return workflow
    return ScientistWorkflow(settings)
