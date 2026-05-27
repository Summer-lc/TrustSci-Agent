# Reference Repository Notes

## Awesome-Auto-Research-Tools

Local path: `.references/Awesome-Auto-Research-Tools`

The list is useful as a map of the auto-research ecosystem rather than as a codebase to fork. It groups projects into:

- End-to-end autonomous research systems: AI-Scientist, RD-Agent, AutoResearchClaw, Agent Laboratory, AI-Researcher.
- Deep research and literature synthesis: STORM, GPT Researcher, PaperQA2, OpenScholar.
- Automated experiment and code agents: OpenHands, Aider, SWE-agent, AIDE.
- Research skill collections: scientific-agent-skills, AI-Research-SKILLs.

## How We Use It

- Borrow the lifecycle shape: literature review -> idea generation -> novelty check -> experiment design -> result/report writing.
- Keep our own source code and architecture so the contest story remains "self-developed Multi-Agent System + Qwen/Bailian".
- Prioritize citation verification and evidence freezing, because the contest explicitly forbids fabricated references.
- Treat browser automation as a tool layer inspired by Hermes/OpenClaw/AutoResearchClaw, not as the main application framework.

## Codegraph

Local path: `.references/codegraph`

The current Codex session does not expose Codegraph as a callable skill. The repository has been cloned for later local experimentation. For this MVP, repository reading was done with `rg`, `find`, and direct README inspection to keep setup lightweight.

