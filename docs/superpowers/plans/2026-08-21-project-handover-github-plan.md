# TrustSci-Agent Project Handover and GitHub Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a verified Chinese onboarding package, commit a safe current-project snapshot, reader-test the documentation, and push `codex/project-handover-docs` without changing `main`.

**Architecture:** Keep the root README as the single entry point and place focused onboarding documents under `docs/onboarding/`. Derive every status, workflow, model, result, and setup claim from current code, fresh verification output, or identified representative artifacts. Stage the dirty worktree in controlled groups, exclude secrets and generated data, and push only the dedicated branch.

**Tech Stack:** Markdown, Git, PowerShell, Python/FastAPI/pytest, Next.js/TypeScript/Vitest, Docker Compose, LangChain, LangGraph, Qwen/Bailian, NumPy, scikit-learn.

---

## File Map

**Create**

- `docs/onboarding/README.md`: reading order and quick navigation.
- `docs/onboarding/01_PROJECT_STATUS.md`: evidence-backed completion matrix and limitations.
- `docs/onboarding/02_ARCHITECTURE.md`: service, workflow, agent, tool, storage, and experiment architecture.
- `docs/onboarding/03_RUNTIME_FLOW.md`: API-to-workflow execution sequence, branches, retries, and persistence.
- `docs/onboarding/04_INPUT_OUTPUT.md`: run inputs, datasets, intermediate artifacts, APIs, and final outputs.
- `docs/onboarding/05_MODELS_ALGORITHMS.md`: Qwen, LCEL, LangGraph, baseline, generated model, metrics, and sandbox.
- `docs/onboarding/06_RESULTS_EVIDENCE.md`: fresh verification results and sanitized representative experiment evidence.
- `docs/onboarding/07_SETUP_GUIDE.md`: prerequisites, Docker/local startup, environment variables, and troubleshooting.
- `docs/onboarding/08_CODEBASE_MAP.md`: directory/file responsibilities and recommended code-reading path.
- `docs/onboarding/09_NEXT_WORK.md`: prioritized backlog and two-member ownership proposal.
- `docs/onboarding/10_PPT_SOURCE_OUTLINE.md`: slide-by-slide source outline for a later presentation.
- `docs/onboarding/11_GITHUB_CONTENTS.md`: included/excluded files, data boundaries, and branch information.

**Modify**

- `README.md`: Chinese project overview, verified status summary, quick start, and onboarding index.
- `.gitignore`: exclude current generated, local, trace, PowerPoint-build, and TypeScript build artifacts.
- `.env.example`: keep only documented variable names with safe empty or public defaults.
- `docs/ARCHITECTURE.md`: add a current-status note and link to the detailed Chinese architecture guide where needed.
- `docs/API.md`: add a current-status note and link to the onboarding runtime/input-output guides where needed.

**Preserve and reference**

- `PRD_v1.md`, `PRD_v2.md`, `PRD_v3.md`, and `prd_v3_s*.md`: historical requirements and sprint rationale.
- `项目展示/项目展示_TrustSci-Agent甲方功能展示_完整16页版.pptx`: formal presentation asset, subject to size and sensitive-content checks.
- `data/seismic_demo/events.csv` and `data/sample_datasets/solid_electrolyte_candidates.csv`: small bundled demo/sample datasets.
- `experiments/seismic_event_classification/`: controlled experiment harness.

## Task 1: Establish the Evidence Baseline

**Files:**
- Read: `README.md`
- Read: `SESSION_HANDOFF.md`
- Read: `docs/superpowers/specs/2026-08-21-project-handover-github-design.md`
- Read: `backend/app/main.py`
- Read: `backend/app/api/routes_runs.py`
- Read: `backend/app/workflows/scientist_workflow.py`
- Read: `backend/app/workflows/langgraph_workflow.py`
- Read: `frontend/lib/api.ts`
- Read: `experiments/seismic_event_classification/`

- [ ] **Step 1: Confirm branch and preserve the dirty-worktree baseline**

Run:

```powershell
git branch --show-current
git status --short --branch
git log -3 --oneline
```

Expected: current branch is `codex/project-handover-docs`; the design commit `ee28a6c` is visible; existing modified and untracked files remain present.

- [ ] **Step 2: Capture source inventory counts without staging anything**

Run:

```powershell
$tracked = git ls-files
$untracked = git ls-files --others --exclude-standard
"tracked=$($tracked.Count)"
"untracked=$($untracked.Count)"
"backend_tests=$((Get-ChildItem backend/tests -File -Filter 'test_*.py').Count)"
"agents=$((Get-ChildItem backend/app/agents -File -Filter '*.py').Count)"
"workbench_components=$((Get-ChildItem frontend/components/workbench -File -Filter '*.tsx').Count)"
```

Expected: numeric counts print successfully; use these values only as dated repository inventory, not as a product-quality score.

- [ ] **Step 3: Extract the actual API and workflow surfaces**

Run:

```powershell
rg -n "@router\.(get|post|put|patch|delete)" backend/app/api
rg -n "add_node|add_edge|add_conditional_edges" backend/app/workflows/langgraph_workflow.py
rg -n "class .*Agent" backend/app/agents
```

Expected: route decorators, graph nodes/edges, and agent classes are listed. Save the facts in working notes; do not infer implemented behavior from PRD text alone.

- [ ] **Step 4: Inspect available run evidence and model artifacts safely**

Run:

```powershell
Get-ChildItem data/outputs/reports -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,Length,LastWriteTime
Get-ChildItem data/workspace -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,LastWriteTime
Get-ChildItem -Recurse -File -Include *.pt,*.pth,*.ckpt,*.onnx,*.safetensors,*.pkl,*.joblib -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\node_modules\\|\\.venv\\|\\.git\\' } | Select-Object Length,FullName
```

Expected: representative reports/runs may exist; no repository-managed pretrained weight file is expected. Document the observed result rather than claiming a model file exists.

- [ ] **Step 5: Record discrepancies between current code and historical handoff text**

Compare `SESSION_HANDOFF.md`, the latest dated design specs, current route files, current graph, and current tests. Record concrete discrepancies such as historical test counts, completed sprint labels, data realism, current workbench layout, and run-resume behavior.

Expected: every discrepancy has a current code path, test, or artifact as its replacement source.

## Task 2: Harden Ignore Rules and Audit the Snapshot

**Files:**
- Modify: `.gitignore`
- Modify: `.env.example`
- Create: `docs/onboarding/11_GITHUB_CONTENTS.md`

- [ ] **Step 1: Extend `.gitignore` for observed local artifacts**

Add these focused rules while retaining the current rules:

```gitignore
frontend/tsconfig.tsbuildinfo
项目展示/.pptx-build/
data/browser_previews/
data/browser_traces/
browser-worker/data/
backend/data/
tmp/
logs/
.claude/
```

Expected: source, tests, formal docs, small demo CSV files, and final presentation assets remain eligible for tracking.

- [ ] **Step 2: Verify `.env.example` contains no credential values**

Run:

```powershell
Get-Content .env.example
git diff -- .env.example
```

Expected: key variables such as `DASHSCOPE_API_KEY`, `GITHUB_TOKEN`, `MATERIALS_PROJECT_API_KEY`, and `SEMANTIC_SCHOLAR_API_KEY` are empty; base URLs and local service defaults may remain.

- [ ] **Step 3: Run a tracked-and-untracked sensitive-pattern scan**

Run:

```powershell
$eligible = @(git ls-files) + @(git ls-files --others --exclude-standard)
$eligible | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | ForEach-Object {
  Select-String -LiteralPath $_ -Pattern 'sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{20,}|DASHSCOPE_API_KEY\s*=\s*\S+|GITHUB_TOKEN\s*=\s*\S+|BEGIN (RSA |OPENSSH )?PRIVATE KEY' -ErrorAction SilentlyContinue
}
```

Expected: no live credential match. Documentation examples with empty values are acceptable only after manual inspection.

- [ ] **Step 4: Check GitHub file-size limits before staging**

Run:

```powershell
$eligible = @(git ls-files) + @(git ls-files --others --exclude-standard)
$eligible | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | ForEach-Object { Get-Item -LiteralPath $_ } | Where-Object Length -ge 50MB | Sort-Object Length -Descending | Select-Object Length,FullName
```

Expected: no eligible file reaches GitHub's 100 MB hard limit; every file at or above 50 MB is explicitly reviewed and either justified or ignored.

- [ ] **Step 5: Draft the GitHub contents policy**

Write `docs/onboarding/11_GITHUB_CONTENTS.md` with: branch name, included categories, excluded categories, demo-data policy, model-weight status, formal presentation asset policy, secret-handling rules, and a note that raw workspaces/LLM logs stay local.

Expected: a member can tell why a visible local file may be absent from GitHub without assuming it was lost.

- [ ] **Step 6: Commit ignore and safety-boundary changes**

Run:

```powershell
git add -- .gitignore .env.example docs/onboarding/11_GITHUB_CONTENTS.md
git diff --cached --check
git diff --cached --stat
git commit -m "chore: define safe project snapshot boundaries"
```

Expected: only the three listed paths are committed.

## Task 3: Verify the Current Code Before Writing Status Claims

**Files:**
- Read: `scripts/check_dev_env.py`
- Read: `backend/tests/`
- Read: `frontend/package.json`
- Read: `experiments/seismic_event_classification/tests.py`
- Create later from output: `docs/onboarding/06_RESULTS_EVIDENCE.md`

- [ ] **Step 1: Check local tool and dependency readiness**

Run the repository's configured interpreter when available:

```powershell
if (Test-Path backend/.venv/Scripts/python.exe) {
  backend/.venv/Scripts/python.exe scripts/check_dev_env.py
} else {
  python scripts/check_dev_env.py
}
```

Expected: the script prints Python, module, Node, npm, Docker, workflow-engine, and Qwen-configured status without printing secret values.

- [ ] **Step 2: Validate Docker Compose configuration**

Run:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
```

Expected: exit code 0 with no Compose schema error.

- [ ] **Step 3: Run the full backend test suite**

Prefer the local virtual environment; otherwise use the running development container:

```powershell
if (Test-Path backend/.venv/Scripts/python.exe) {
  Push-Location backend
  .\.venv\Scripts\python.exe -m pytest -q
  Pop-Location
} else {
  docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q
}
```

Expected: exit code 0. Record the exact passed/skipped count and date. If tests fail, document the failing cases and classify affected features as partially completed or awaiting re-verification.

- [ ] **Step 4: Run frontend unit tests**

Run:

```powershell
Push-Location frontend
npm test
Pop-Location
```

Expected: Vitest exits 0; record the exact test-file and test counts.

- [ ] **Step 5: Run the production frontend build**

Run:

```powershell
Push-Location frontend
npm run build
Pop-Location
```

Expected: Next.js build exits 0. Treat build failure separately from unit-test status.

- [ ] **Step 6: Run the fixed seismic harness acceptance test with the template model**

Run in a temporary directory so the repository is not polluted:

```powershell
$handoverTemp = Join-Path ([System.IO.Path]::GetTempPath()) ("trustsci-harness-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $handoverTemp | Out-Null
Copy-Item experiments/seismic_event_classification/data.py,experiments/seismic_event_classification/baseline.py,experiments/seismic_event_classification/train.py,experiments/seismic_event_classification/tests.py,experiments/seismic_event_classification/harness_manifest.json -Destination $handoverTemp
Copy-Item experiments/seismic_event_classification/model_template.py -Destination (Join-Path $handoverTemp 'model.py')
Push-Location $handoverTemp
python tests.py
python train.py
Get-Content metrics.json
Get-Content comparison.json
Pop-Location
$resolvedTemp = (Resolve-Path -LiteralPath $handoverTemp).Path
$resolvedTempRoot = (Resolve-Path -LiteralPath ([System.IO.Path]::GetTempPath())).Path
if (-not $resolvedTemp.StartsWith($resolvedTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Refusing to remove a directory outside the system temporary root: $resolvedTemp"
}
Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
```

Expected: interface tests and training exit 0; metrics and comparison JSON are generated. The template may tie or lose to the fixed baseline; report the observed value without presenting it as a claimed improvement.

## Task 4: Create the Onboarding Entry and Status Documents

**Files:**
- Modify: `README.md`
- Create: `docs/onboarding/README.md`
- Create: `docs/onboarding/01_PROJECT_STATUS.md`
- Create: `docs/onboarding/06_RESULTS_EVIDENCE.md`

- [ ] **Step 1: Create the onboarding index**

Write `docs/onboarding/README.md` with three reading paths: 15-minute overview, developer setup, and PPT/technical-document preparation. Link all eleven onboarding files plus current API/architecture docs and the three PRDs.

Expected: every link uses a repository-relative path and resolves on GitHub.

- [ ] **Step 2: Write the evidence-backed completion matrix**

Write `docs/onboarding/01_PROJECT_STATUS.md` with columns: capability, current state, evidence, limitation, and recommended next action. Use only the four approved statuses: 已完成并验证、已实现待复验、部分完成、未完成/后续任务.

Cover services, three research modes, literature/citation/evidence, hypothesis Arena, baseline quality, code experiment loop, result analysis, report/export, browser preview, run lifecycle/recovery, frontend workbench, real-data readiness, and competition packaging.

Expected: synthetic seismic data, deterministic fallback, policy-level sandbox isolation, and historical-doc drift are visible limitations.

- [ ] **Step 3: Write results and evidence with dated verification output**

Write `docs/onboarding/06_RESULTS_EVIDENCE.md` containing: verification date, backend/frontend/build/Compose outcomes, harness metrics, representative saved-run summaries only after provenance inspection, and an explicit section titled `这些结果不能证明什么`.

Expected: no metric is copied from an unknown run; no full prompt, user input, API response, or raw LLM log is published.

- [ ] **Step 4: Rewrite the root README as a concise Chinese entry point**

Keep the project identity, services, safe quick start, URLs, research modes, and privacy note. Add a dated completion summary, link to `docs/onboarding/README.md`, and state that no API key enables deterministic demo/fallback behavior.

Expected: the root README remains under roughly 250 lines and points to detailed documents instead of duplicating them.

- [ ] **Step 5: Check links and completion terminology**

Run:

```powershell
$placeholderPatterns = @('T' + 'BD', 'T' + 'ODO', '待定', '稍后补充')
Get-ChildItem README.md,docs/onboarding -Recurse -File | Select-String -Pattern $placeholderPatterns
rg -n "已完成并验证|已实现待复验|部分完成|未完成/后续任务" docs/onboarding/01_PROJECT_STATUS.md
```

Expected: no placeholder phrase is present; the status matrix uses the approved terminology.

- [ ] **Step 6: Commit entry, status, and evidence documents**

Run:

```powershell
git add -- README.md docs/onboarding/README.md docs/onboarding/01_PROJECT_STATUS.md docs/onboarding/06_RESULTS_EVIDENCE.md
git diff --cached --check
git commit -m "docs: add verified project status and onboarding entry"
```

Expected: only the listed documentation paths are committed.

## Task 5: Document Architecture, Runtime, Inputs, and Algorithms

**Files:**
- Create: `docs/onboarding/02_ARCHITECTURE.md`
- Create: `docs/onboarding/03_RUNTIME_FLOW.md`
- Create: `docs/onboarding/04_INPUT_OUTPUT.md`
- Create: `docs/onboarding/05_MODELS_ALGORITHMS.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/API.md`

- [ ] **Step 1: Write the six-layer architecture guide**

Document frontend, backend API, workflow orchestration, agents/tools, local storage, and controlled experiments. For each unit, state what it does, how it is called, and what it depends on. Include compact text diagrams and source-file links.

Expected: Classic and LangGraph engines, browser-worker, run store/workspace, and the experiment sandbox have distinct boundaries.

- [ ] **Step 2: Write the actual runtime flow**

Trace request creation/start/status through route functions and workflow methods. Explain intent routing, planning, literature, citations, evidence, Arena, novelty, baseline gate, code experiment, feedback loops, reporting, persistence, retry/skip, pause/resume, and recovery.

Expected: optional branches and loops are not represented as unconditional linear steps.

- [ ] **Step 3: Write the input/output contract guide**

Document run creation fields, research modes, domain/question/constraints, manual baseline or experiment-assistance inputs, small bundled datasets, intermediate workspace artifacts, reports, audits, exports, and browser previews. Link detailed routes to `docs/API.md`.

Expected: examples contain no private values and distinguish user-supplied results from independently executed experiments.

- [ ] **Step 4: Write the model and algorithm guide**

Document Qwen/Bailian configuration and fallback, LCEL/LangGraph roles, agent-level reasoning tasks, literature ranking and verification, evidence selection, baseline discovery/quality rules, synthetic waveform generator, fixed LogisticRegression baseline, AI-written `SeismicModel`, accuracy/macro-F1/per-class F1, fairness comparison, and sandbox controls.

Expected: explicitly state whether pretrained weights are committed, how runtime model source is generated, and why the bundled synthetic data cannot establish real-world seismic performance.

- [ ] **Step 5: Add current-status links to legacy architecture/API docs**

Add a short notice near the top of `docs/ARCHITECTURE.md` and `docs/API.md` linking to the onboarding guides and stating that current code is authoritative when historical narrative differs.

Expected: existing detailed material is preserved; no API route is removed from documentation without checking code.

- [ ] **Step 6: Cross-check named symbols and routes**

Run:

```powershell
rg -n "LangGraphWorkflow|ScientistWorkflow|QwenClient|SandboxExecutor|SeismicModel|BaselineModel" docs/onboarding
rg -n "POST /api/runs|GET /api/runs|workspace|report" docs/onboarding docs/API.md
```

Expected: all major named components and lifecycle interfaces are covered and spelled consistently.

- [ ] **Step 7: Commit architecture and runtime documentation**

Run:

```powershell
git add -- docs/onboarding/02_ARCHITECTURE.md docs/onboarding/03_RUNTIME_FLOW.md docs/onboarding/04_INPUT_OUTPUT.md docs/onboarding/05_MODELS_ALGORITHMS.md docs/ARCHITECTURE.md docs/API.md
git diff --cached --check
git commit -m "docs: explain architecture runtime and algorithms"
```

Expected: only the listed documentation paths are committed.

## Task 6: Document Setup, Code Map, Next Work, and PPT Sources

**Files:**
- Create: `docs/onboarding/07_SETUP_GUIDE.md`
- Create: `docs/onboarding/08_CODEBASE_MAP.md`
- Create: `docs/onboarding/09_NEXT_WORK.md`
- Create: `docs/onboarding/10_PPT_SOURCE_OUTLINE.md`

- [ ] **Step 1: Write the setup guide from verified commands**

Include prerequisites, `.env.example` copy, Docker standard/dev commands, local backend alternative, frontend commands, service URLs, Qwen ping, environment checker, tests, and troubleshooting for Windows/WSL, ports, missing keys, slow Qwen responses, and unavailable external literature sources.

Expected: commands match current Compose files, package scripts, and `scripts/check_dev_env.py`.

- [ ] **Step 2: Write the codebase map**

Map root files, backend main/routes/workflows/agents/tools/schemas/storage/evidence, frontend app/components/lib, browser-worker, experiments, data samples, scripts, docs, and formal presentation assets. Provide a numbered reading path from API entry to report output.

Expected: generated/cache directories are labeled as non-source and omitted from the reading path.

- [ ] **Step 3: Write the prioritized next-work backlog**

Organize work into P0 competition/reproducibility, P1 scientific credibility, and P2 maintainability/experience. Every item must state evidence for the gap, concrete deliverable, acceptance criterion, dependencies, and suggested owner.

Expected two-member split:

- Member A: backend workflow, model/experiment, real dataset, evaluation, and reproducibility.
- Member B: frontend/API integration, demo packaging, documentation, test automation, and presentation assets.

Also identify shared review points so ownership does not create isolated knowledge silos.

- [ ] **Step 4: Write the PPT source outline**

Provide a 12–16 slide outline with slide objective, 3–5 key points, suggested repository evidence/screenshot, and the source document/file for each slide. Include problem, solution, architecture, trusted evidence chain, multi-agent workflow, experiment loop, input/output, algorithms, results, limitations, completion status, and roadmap.

Expected: the outline is reusable but does not claim to be a finished presentation.

- [ ] **Step 5: Validate repository-relative file links**

Use PowerShell to extract local Markdown links under `docs/onboarding/` and manually verify every repository-relative target exists. Links to future-generated files are not allowed because all eleven files exist by this task.

Expected: no broken repository-relative link.

- [ ] **Step 6: Commit setup and handover-planning documents**

Run:

```powershell
git add -- docs/onboarding/07_SETUP_GUIDE.md docs/onboarding/08_CODEBASE_MAP.md docs/onboarding/09_NEXT_WORK.md docs/onboarding/10_PPT_SOURCE_OUTLINE.md
git diff --cached --check
git commit -m "docs: add setup code map and team roadmap"
```

Expected: only the four listed documentation paths are committed.

## Task 7: Stage and Commit the Safe Current Source Snapshot

**Files:**
- Stage: eligible modified and untracked source, tests, configuration, plans, small samples, and formal assets.
- Exclude: everything documented in `.gitignore` and `docs/onboarding/11_GITHUB_CONTENTS.md`.

- [ ] **Step 1: Review all remaining eligible changes by category**

Run:

```powershell
git status --short
git diff --stat
git ls-files --others --exclude-standard
```

Expected: ignored local data/cache/build paths no longer appear. Every remaining untracked category is understood before staging.

- [ ] **Step 2: Stage source and test directories explicitly**

Run:

```powershell
git add -- backend frontend browser-worker experiments scripts docker-compose.yml docker-compose.dev.yml Makefile pytest.ini
git status --short
```

Expected: application source, tests, lockfiles, Docker files, and experiment harness are staged; ignored build artifacts remain absent.

- [ ] **Step 3: Stage approved root documents, small samples, plans, and formal presentation assets explicitly**

Run:

```powershell
git add -- PRD_v1.md PRD_v2.md PRD_v3.md prd_v3_sprint.md prd_v3_s1_plan.md prd_v3_s2_plan.md prd_v3_s3_plan.md prd_v3_s35_plan.md prd_v3_s4_plan.md prd_v3_s5_plan.md SESSION_HANDOFF.md docs data/seismic_demo/events.csv data/sample_datasets/solid_electrolyte_candidates.csv '项目展示/项目展示_TrustSci-Agent甲方功能展示_完整16页版.pptx' '项目展示/成品预览_完整16页'
```

Expected: only approved documents, samples, and final presentation assets are staged; raw run directories and `.pptx-build` are absent.

- [ ] **Step 4: Audit the complete staged set**

Run:

```powershell
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
git diff --cached --numstat
```

Expected: no `.env`, credential, raw LLM log, raw workspace, cache, build directory, or unexplained binary is staged.

- [ ] **Step 5: Re-run the sensitive-pattern scan on staged text**

Run:

```powershell
$staged = git diff --cached --name-only --diff-filter=ACMR
$staged | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | ForEach-Object {
  Select-String -LiteralPath $_ -Pattern 'sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{20,}|DASHSCOPE_API_KEY\s*=\s*\S+|GITHUB_TOKEN\s*=\s*\S+|BEGIN (RSA |OPENSSH )?PRIVATE KEY' -ErrorAction SilentlyContinue
}
```

Expected: no live credential match. Unstage and correct any suspect file before continuing.

- [ ] **Step 6: Commit the safe source snapshot**

Run:

```powershell
git commit -m "feat: capture current TrustSci-Agent project snapshot"
```

Expected: the source snapshot commit succeeds and the remaining worktree contains only intentionally local ignored files or later documentation corrections.

## Task 8: Run Independent Reader Testing and Correct Documentation

**Files:**
- Review/modify: `README.md`
- Review/modify: `docs/onboarding/*.md`

- [ ] **Step 1: Prepare ten reader questions**

Use these exact questions:

1. 项目的核心目标和比赛定位是什么？
2. 当前哪些能力已验证，哪些只是部分完成？
3. 新电脑最短启动路径是什么？
4. 一次研究任务从输入到报告经历哪些主要节点？
5. 系统接受哪些输入，产生哪些输出？
6. Qwen、LangGraph、传统机器学习和多智能体分别承担什么职责？
7. 已有地震实验结果是否可以代表真实数据效果？
8. 仓库是否包含预训练模型权重？模型代码如何产生？
9. 两位成员接下来分别负责什么，如何共同验收？
10. 哪些本地文件没有上传 GitHub，为什么？

- [ ] **Step 2: Test the questions with a fresh reader agent**

Provide only `README.md` and `docs/onboarding/*.md` to a fresh subagent. Ask it to answer the ten questions and identify ambiguous claims, missing prerequisites, internal contradictions, and assumed background knowledge.

Expected: answers are traceable to the supplied documents. Record every wrong or uncertain answer as a documentation defect.

- [ ] **Step 3: Run a second independent consistency review**

Provide the same documents to another fresh subagent and ask only for contradictions, broken navigation, unsupported metrics, confusing synthetic/real-data boundaries, and unclear ownership.

Expected: no unsupported claim is accepted merely because it appears in multiple documents.

- [ ] **Step 4: Correct all reader-test defects**

Edit the smallest relevant sections; do not duplicate large explanations across files. Re-run the ten questions against the corrected documents if any material ambiguity was found.

Expected: a new member can answer all ten questions without reading source code or historical PRDs.

- [ ] **Step 5: Commit reader-test corrections**

Run:

```powershell
git add -- README.md docs/onboarding
git diff --cached --check
git commit -m "docs: resolve onboarding reader-test gaps"
```

Expected: commit succeeds; if no correction was needed, do not create an empty commit.

## Task 9: Final Verification and GitHub Push

**Files:**
- Verify: entire committed branch.

- [ ] **Step 1: Confirm clean eligible state and branch history**

Run:

```powershell
git status --short --branch
git log --oneline --decorate -8
git diff origin/main...HEAD --stat
```

Expected: no unstaged eligible source/document change remains; ignored local artifacts may remain on disk but do not appear in status.

- [ ] **Step 2: Re-run proportional final verification**

Run backend tests, frontend tests, frontend build, Compose config validation, and the temporary seismic harness commands from Task 3 again after the source snapshot is committed.

Expected: all previously passing checks still pass. Any failure blocks a completion claim and is documented before push.

- [ ] **Step 3: Validate remote and GitHub authentication**

Run:

```powershell
git remote -v
git ls-remote --heads origin
```

Expected: `origin` points to `https://github.com/Summer-lc/TrustSci-Agent.git` and the remote is reachable without exposing credentials.

- [ ] **Step 4: Push only the dedicated branch**

Run:

```powershell
git push -u origin codex/project-handover-docs
```

Expected: push succeeds and upstream tracking is configured for `origin/codex/project-handover-docs`.

- [ ] **Step 5: Report final evidence**

Report the branch name, pushed commit, GitHub branch URL, verification outcomes, reader-test outcome, included/excluded scope, and any remaining limitations. State explicitly that `main` was not merged or modified remotely.

Expected: the handoff summary gives the two members a single starting link and does not require them to inspect local-only files.
