# Reference Project Analysis

This note records the first pass through `handsome-rich/Awesome-Auto-Research-Tools` and the representative projects cloned under `.references/auto-research-repos`.

`Awesome-Auto-Research-Tools` is mainly a curated index. CodeGraph found only the index/update script in that repository, so code-level analysis was run on selected downstream projects. CodeGraph successfully indexed `SakanaAI/AI-Scientist` with 128 Python files, 6,175 symbols, and 8,851 graph edges. `AutoResearchClaw` is much larger; its CodeGraph run reached the parsing stage but was stopped after it became slow, then inspected by directory structure and key implementation files.

## High-Value References

| Project | Value | What To Reuse In TrustSci-Agent |
| --- | --- | --- |
| AutoResearchClaw | Very high | Multi-agent base classes, domain profiles, sandbox experiment runner, reviewer/scorer rubrics, HITL checks, citation/claim verification concepts. |
| AI-Scientist | Very high | Idea/reflection loop, experiment/writeup/review stage separation, few-shot idea archive, LaTeX report pipeline shape. |
| Agent Laboratory | High | Role model: professor, postdoc, ML engineer, software engineer, PhD student, reviewers; arXiv-backed literature review flow. |
| GPT Researcher | High | FastAPI + Next.js product shape, LangGraph-style workflow, WebSocket progress, report export, retriever/scraper separation. |
| PaperQA2 | High | Scientific RAG with paper search clients, local tantivy index, citation-grounded answer generation, retraction/journal metadata hooks. |
| STORM | High | Persona-guided question generation, expert Q&A loop, outline generation, citation-rich article builder. |
| scientific-agent-skills | High | Skill registry format, reusable scientific procedures, especially `pymatgen`, `deepchem`, `rdkit`, and `citation-management`. |

## Full Awesome List Triage

| Project | Fit | Notes |
| --- | --- | --- |
| autoresearch | Medium | Compact edit-run-evaluate loop; useful as a minimal experiment loop pattern. |
| AI-Scientist | High | Best reference for idea to experiment to paper lifecycle. |
| RD-Agent | Medium | Useful for Dockerized R&D automation and paper-to-code patterns; larger than our MVP needs. |
| AutoResearchClaw | High | Closest to our desired full stack, especially sandbox, review, and domain profile modules. |
| ARIS | Medium | Good Claude Code/MCP workflow ideas; less directly portable to our FastAPI service. |
| AI-Scientist-v2 | Medium | Tree search is valuable later; too heavy for current MVP. |
| Agent Laboratory | High | Simple, readable role decomposition and literature workflow. |
| AI-Researcher | Medium | Strong autonomous research framing; evaluate later for hypothesis and manuscript pipeline. |
| claude-scholar | Low | More personal research workflow than reusable backend architecture. |
| Biomni | Medium | Domain-specific biomedical tool/data integration; useful as a model for future material-science tool packs. |
| EvoScientist | Medium | Persistent memory and messaging channels are future-stage ideas. |
| DeepScientist | Medium | Findings memory and Bayesian experiment search are strong post-MVP ideas. |
| DATAGEN | Medium | LangGraph data-analysis workflow patterns may help our analysis agent. |
| Idea2Paper | Medium | Knowledge graph and proposal refinement are useful for hypothesis management. |
| InternAgent | Medium | Long-horizon cross-science framework; good for future domain adapters. |
| DeerFlow | Medium | LangGraph agent harness ideas; overlaps with GPT Researcher/Open Deep Research. |
| STORM | High | Best reference for citation-backed outline and report construction. |
| GPT Researcher | High | Best full-stack deep research implementation reference. |
| ChatPaper | Low | Paper summarization features overlap with PaperQA2 and are narrower. |
| Tongyi DeepResearch | Medium | Bailian/DashScope relevance and long-horizon search ideas; codebase should be reviewed later if Qwen-native optimization matters. |
| Open Deep Research | Medium | Strong LangGraph/MCP architecture reference; useful if we adopt LangGraph. |
| PaperQA2 | High | Best immediate reference for evidence-grounded scientific document retrieval. |
| local-deep-research | Medium | Local-first search and encrypted storage are useful for privacy later. |
| DeepResearchAgent | Medium | Hierarchical agent design is relevant but not MVP-critical. |
| Auto-Deep-Research | Medium | Good zero-config deep-research UX reference. |
| OpenScholar | Medium | Strong scholarly retrieval benchmark direction; heavy retrieval model stack. |
| ChatReviewer | Medium | Reviewer response and paper critique prompts can inform our critic agent. |
| OpenResearcher | Low | Mainly training/inference pipeline for research model; too large for current application layer. |
| AutoGPT | Low | General-purpose agent builder, less science-specific. |
| OpenHands | Medium | Coding/sandbox agent ideas; useful if we add code-editing experiments. |
| Aider | Medium | Git-based coding loop is useful for experiment branches, but not embedded now. |
| SWE-agent | Low | Software issue fixing rather than scientific research. |
| PaperBanana | Medium | Figure planning/critic loop can inform report visualization later. |
| MLE-agent | Medium | ML experiment and Papers with Code integration ideas. |
| AIDE | Medium | Agentic tree search for ML code is a strong later experiment-planning module. |
| scientific-agent-skills | High | Directly reusable skill-library organization and scientific scripts. |
| AI-Research-SKILLs | Medium | Broad skill taxonomy; useful after our first internal skill schema lands. |
| OpenClaw-Medical-Skills | Low | Medical-heavy; schema ideas are useful, domain fit is lower. |
| awesome-autoresearch | Low | Secondary index. |
| awesome-ai-for-science | Low | Secondary index for discovery, not implementation. |
| Autonomous-Agents | Low | Paper watchlist, not implementation. |
| Awesome-Deep-Research | Low | Secondary index for future tracking. |

## Implementation Takeaways

1. Add a provider-neutral LLM layer first. This is now started with `LLMRequest`, `LLMResponse`, `LLMClient`, and `build_llm_client()`, with Qwen as the first provider.
2. Build an evidence-first retrieval layer rather than a generic web-search wrapper. PaperQA2 suggests separate clients for OpenAlex, Crossref, Semantic Scholar, Unpaywall, and retractions, with a local searchable paper/chunk index.
3. Add a scientific skill registry. Use a small internal schema inspired by `scientific-agent-skills`: name, domain, required packages, inputs, outputs, safety/runtime constraints, and optional scripts/assets.
4. Evolve our agent set toward explicit roles: planner, literature researcher, hypothesis generator, experiment designer, sandbox runner, critic/reviewer, report writer, and human checkpoint.
5. Borrow STORM's "question from perspective -> retrieve -> grounded answer -> outline" loop for report outline construction.
6. Borrow AutoResearchClaw's experiment result model: run id, iteration, code or profile, metrics, primary metric, improved/kept flags, stdout/stderr, and error.
7. Keep full external projects as references, not vendored dependencies. Direct reuse should be limited to small prompt structures, data schemas, and interface ideas unless licenses and integration costs are reviewed.

## Near-Term Backlog For TrustSci-Agent

| Priority | Item | Reference |
| --- | --- | --- |
| P0 | Finish provider-neutral LLM interface and make every agent call it. | AutoResearchClaw base agent, our Qwen client |
| P0 | Evidence ledger backed by PDF/web chunks and source metadata. | PaperQA2, STORM |
| P1 | Retrieval source router for OpenAlex, Crossref, Semantic Scholar, arXiv, browser, and local PDFs. | PaperQA2, Agent Laboratory |
| P1 | Skill registry with first material-science skills: Materials Project profile, Matbench baseline, pymatgen helpers. | scientific-agent-skills |
| P1 | Review/critic rubric with novelty, feasibility, evidence support, reproducibility, and competition-fit scores. | AI-Scientist, AutoResearchClaw, ChatReviewer |
| P2 | Sandbox experiment runner with result cards and keep/discard decision. | AutoResearchClaw, autoresearch, AIDE |
| P2 | Report outline builder with citation freeze before final writing. | STORM, GPT Researcher |
