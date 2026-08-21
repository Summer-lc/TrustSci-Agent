# v3 Sprint S3.5 实施计划：Baseline Quality Gate

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 baseline 发现从"宽搜 GitHub(混数据集+噪声)"升级为"只从 method/model 文献里找、repo 也判定是不是 model_code、按 baseline 优先级验证"——让找到的 baseline 是真模型代码而非数据集。重搜循环留到 S5,本 sprint 不做。

**Architecture:** 新增 `PaperTypeClassifier`(LCEL)给每篇论文标 `paper_role`(method_model / dataset_benchmark / survey_review / application_only / unknown)+ `baseline_eligible`;BaselineDiscovery 只对 `baseline_eligible` 论文找 code(关掉 task 级宽搜,消除噪声);RepositoryVerifier 增强,判定 `repo_type`(model_code/dataset_only/benchmark_suite/docs_only/unknown)+ `is_model_baseline` + `matches_paper_method`,dataset-only repo 不能 verified;`baseline_priority_score` 两阶段(验证前用 paper_role+stars+repo 名启发式排序选 top-3;验证后用 repo_type/match/reproducibility 更新)。前端 LiteratureBoard 显示 paper_role,BaselineBoard 显示 repo_type/is_model_baseline/priority/rejection_reason。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / LangChain LCEL / pytest / Next.js。

## Global Constraints

- 新 LLM agent(PaperTypeClassifier)走 `LLMClientRunnable`(`build_agent_prompt`),`agent="paper_classifier"`,malformed 落 fallback。
- 只对 `run.domain == "seismic_event_classification"` 生效;非 seismic 不变,测试不破。
- **不做重搜循环**(S5):本轮若 method-baseline 不足,诚实输出"baseline 不足",不自动重检索。
- dataset-only repo: `is_model_baseline=False`、`verified_repo=False`、`reproduction_status="failed"`(或 suspicious),`baseline_rejection_reason` 写明。
- `baseline_priority_score` ∈ [0,1]:验证前初始值用于排序选 top-3;验证后由 RepositoryVerifier 更新。
- 关掉 task 级宽 GitHub 搜索(噪声源);保留 paper-code(摘要/PDF 挖)+ per-paper 标题搜 + PwC(连不上则空)。
- `code_url` 来源用 `paper.code_url_source`("abstract"/"pdf")记真来源,修掉之前 `paper_pdf` 标签 bug。
- 不 commit。后端测试在 Docker dev 栈:`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest <path> -v`。
- 文件路径相对仓库根 `d:/For work/TrustSci-Agent/`。

## File Structure

- **Create** `backend/app/agents/paper_type_classifier_agent.py`
- **Create** `backend/tests/test_s35_schemas.py`
- **Create** `backend/tests/test_paper_type_classifier_agent.py`
- **Create** `backend/tests/test_s35_baseline_quality.py`
- **Modify** `backend/app/schemas/paper.py` — 加 `paper_role/baseline_eligible/baseline_rejection_reason/code_url_source`。
- **Modify** `backend/app/schemas/baseline.py` — 加 `repo_type/is_model_baseline/baseline_priority_score/baseline_rejection_reason/stars`。
- **Modify** `backend/app/tools/code_url_extractor.py` — 挖到 code_url 时记 `paper.code_url_source`。
- **Modify** `backend/app/agents/baseline_discovery_agent.py` — 只对 eligible 论文找 code;关 task 级宽搜;设 `stars`;算初始 `baseline_priority_score`;paper-code 候选用 repo 名启发式设 `is_model_baseline`/`repo_type`。
- **Modify** `backend/app/agents/repository_verifier_agent.py` — verdict + prompt 增 `repo_type/is_model_baseline/matches_paper_method`;dataset-only 不 verified;更新 `baseline_priority_score`。
- **Modify** `backend/app/workflows/scientist_workflow.py` — 加 `_classify_papers` step(seismic, literature_mining 之后);`_verify_baselines_auto` 改成按 `baseline_priority_score` 排序 top-3。
- **Modify** `backend/app/workflows/langgraph_workflow.py` — 加 `paper_classification` 节点(seismic, literature_mining 之后, scientific_data_profile 之前)。
- **Modify** `frontend/lib/api.ts` — Paper 加 `paper_role/baseline_eligible/baseline_rejection_reason`;BaselineCandidate 加 `repo_type/is_model_baseline/baseline_priority_score/baseline_rejection_reason/stars`。
- **Modify** `frontend/components/workbench/LiteratureBoard.tsx` — 显示 paper_role / baseline_eligible。
- **Modify** `frontend/components/workbench/BaselineBoard.tsx` — 显示 repo_type / is_model_baseline / priority_score / rejection_reason;按 priority 排序。

---

### Task 1: schema 字段(Paper + BaselineCandidate)+ code_url_source

**Files:**
- Modify: `backend/app/schemas/paper.py`
- Modify: `backend/app/schemas/baseline.py`
- Modify: `backend/app/tools/code_url_extractor.py`
- Test: `backend/tests/test_s35_schemas.py`

**Interfaces:**
- Produces: `Paper.paper_role/baseline_eligible/baseline_rejection_reason/code_url_source`;`BaselineCandidate.repo_type/is_model_baseline/baseline_priority_score/baseline_rejection_reason/stars`。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_s35_schemas.py
from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


def test_paper_baseline_role_fields_default() -> None:
    p = Paper(paper_id="p1", title="t")
    assert p.paper_role == "unknown"
    assert p.baseline_eligible is False
    assert p.baseline_rejection_reason is None
    assert p.code_url_source is None


def test_baseline_candidate_quality_fields_default() -> None:
    c = BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="t",
                          code_url="https://github.com/a/b", code_source="github_search",
                          task_match="seismic", input_type="waveform")
    assert c.repo_type == "unknown"
    assert c.is_model_baseline is False
    assert c.baseline_priority_score == 0.0
    assert c.baseline_rejection_reason is None
    assert c.stars == 0


def test_code_url_extractor_records_source(tmp_path, monkeypatch) -> None:
    from app.tools.code_url_extractor import extract_code_urls
    p = Paper(paper_id="p1", title="t", abstract="see https://github.com/foo/bar for code", pdf_url=None)
    out = extract_code_urls([p])
    assert out[0].code_url == "https://github.com/foo/bar"
    assert out[0].code_url_source == "abstract"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s35_schemas.py -v`
Expected: FAIL (missing fields)

- [ ] **Step 3: Add fields + record source**

In `backend/app/schemas/paper.py`, add fields (after `code_url`):

```python
    paper_role: str = "unknown"  # method_model | dataset_benchmark | survey_review | application_only | unknown
    baseline_eligible: bool = False
    baseline_rejection_reason: str | None = None
    code_url_source: str | None = None  # abstract | pdf
```

In `backend/app/schemas/baseline.py`, add fields (after `risks`):

```python
    repo_type: str = "unknown"  # model_code | dataset_only | benchmark_suite | docs_only | unknown
    is_model_baseline: bool = False
    baseline_priority_score: float = 0.0
    baseline_rejection_reason: str | None = None
    stars: int = 0
```

In `backend/app/tools/code_url_extractor.py`, update `extract_code_urls` (abstract pass) and `extract_code_urls_async` (pdf pass) to set `paper.code_url_source`:

```python
def extract_code_urls(papers: list[Paper], *, max_pdf: int = _MAX_PDF_DOWNLOADS, transport=None) -> list[Paper]:
    for paper in papers:
        if paper.code_url:
            continue
        url = _mine_text(paper.abstract or "")
        if url:
            paper.code_url = url
            paper.code_url_source = "abstract"
    return papers
```

And in `extract_code_urls_async`, the PDF branch:

```python
        url = _mine_text(text)
        if url:
            paper.code_url = url
            paper.code_url_source = "pdf"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s35_schemas.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 2: PaperTypeClassifierAgent（LCEL）

**Files:**
- Create: `backend/app/agents/paper_type_classifier_agent.py`
- Test: `backend/tests/test_paper_type_classifier_agent.py`

**Interfaces:**
- Consumes: `LLMClient`、`list[Paper]`。
- Produces: `PaperTypeClassifierAgent.arun(papers, *, run_id) -> list[Paper]`（原地设 `paper_role/baseline_eligible/baseline_rejection_reason`,返回 papers）。只有 `paper_role=="method_model"` 的 `baseline_eligible=True`。fallback:确定性启发式(标题/摘要含 "dataset"/"benchmark"/"survey"/"review" → 对应角色;否则 method_model)。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_paper_type_classifier_agent.py
import pytest

from app.agents.paper_type_classifier_agent import PaperTypeClassifierAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.paper import Paper


class FakeLLM:
    provider = "fake"
    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []
    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


def _papers() -> list[Paper]:
    return [
        Paper(paper_id="p1", title="EQTransformer: deep learning model", abstract="We propose a model."),
        Paper(paper_id="p2", title="STEAD: a global dataset", abstract="We introduce a dataset."),
        Paper(paper_id="p3", title="A survey of seismic ML", abstract="We review."),
    ]


@pytest.mark.asyncio
async def test_classifier_assigns_roles() -> None:
    llm = FakeLLM({"papers": [
        {"paper_id": "p1", "paper_role": "method_model", "baseline_eligible": True, "reason": "proposes a model"},
        {"paper_id": "p2", "paper_role": "dataset_benchmark", "baseline_eligible": False, "reason": "is a dataset"},
        {"paper_id": "p3", "paper_role": "survey_review", "baseline_eligible": False, "reason": "is a survey"},
    ]})
    agent = PaperTypeClassifierAgent(llm)
    out = await agent.arun(_papers(), run_id="run_x")
    by_id = {p.paper_id: p for p in out}
    assert by_id["p1"].paper_role == "method_model" and by_id["p1"].baseline_eligible is True
    assert by_id["p2"].paper_role == "dataset_benchmark" and by_id["p2"].baseline_eligible is False
    assert by_id["p2"].baseline_rejection_reason == "is a dataset"
    assert by_id["p3"].baseline_eligible is False
    assert llm.requests[0].agent == "paper_classifier"


@pytest.mark.asyncio
async def test_classifier_falls_back_on_bad_output() -> None:
    agent = PaperTypeClassifierAgent(FakeLLM("garbage"))
    out = await agent.arun(_papers(), run_id="run_x")
    # Fallback: STEAD (dataset in title) -> dataset_benchmark/eligible False; survey -> survey_review; EQTransformer -> method_model
    by_id = {p.paper_id: p for p in out}
    assert by_id["p1"].baseline_eligible is True
    assert by_id["p2"].baseline_eligible is False
    assert by_id["p3"].baseline_eligible is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_paper_type_classifier_agent.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/paper_type_classifier_agent.py
import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.paper import Paper

SYSTEM_PROMPT = """You are the Paper Type Classifier for TrustSci-Agent v3 baseline quality gate.
Classify each paper into exactly one paper_role:
- method_model: the paper proposes/implements a model or method (potential baseline with code)
- dataset_benchmark: the paper introduces a dataset or benchmark (dataset provenance only, NOT a model baseline)
- survey_review: a survey/review paper (no original method)
- application_only: applies existing methods without a reusable model artifact
- unknown: cannot determine
Return JSON only: {"papers": [{"paper_id": "...", "paper_role": "...", "reason": "..."}]}.
Only method_model papers are baseline-eligible. Do not invent citations."""

USER_TEMPLATE = """Papers:
{papers_json}

Classify each paper's role."""


class PaperTypeClassifierAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, papers: list[Paper], *, run_id: str) -> list[Paper]:
        fallback = {p.paper_id: _fallback_role(p) for p in papers}
        if self.llm is None:
            _apply_roles(papers, fallback)
            return papers
        prompt = build_agent_prompt(SYSTEM_PROMPT)
        chain = (
            prompt
            | LLMClientRunnable(self.llm).bind(fallback={"papers": []}, run_id=run_id, agent="paper_classifier")
            | FallbackParser(lambda content: _normalize(content, papers, fallback), {p.paper_id: _fallback_role(p) for p in papers})
        )
        normalized = await chain.ainvoke({"user_prompt": USER_TEMPLATE.format(papers_json=_payload(papers))})
        _apply_roles(papers, normalized)
        return papers


def _payload(papers: list[Paper]) -> str:
    return json.dumps([{"paper_id": p.paper_id, "title": p.title, "abstract": (p.abstract or "")[:400]} for p in papers], ensure_ascii=False)


def _normalize(content, papers: list[Paper], fallback: dict) -> dict:
    if not isinstance(content, dict) or not isinstance(content.get("papers"), list):
        return fallback
    by_id = {str(r.get("paper_id")): r for r in content["papers"] if isinstance(r, dict) and r.get("paper_id")}
    out: dict = {}
    for p in papers:
        raw = by_id.get(p.paper_id)
        role = str(raw.get("paper_role", "")).strip() if isinstance(raw, dict) else ""
        if role not in {"method_model", "dataset_benchmark", "survey_review", "application_only", "unknown"}:
            out[p.paper_id] = fallback[p.paper_id]
        else:
            reason = str(raw.get("reason") or "").strip() if isinstance(raw, dict) else ""
            out[p.paper_id] = {"paper_role": role, "reason": reason}
    return out


def _apply_roles(papers: list[Paper], roles: dict) -> None:
    for p in papers:
        r = roles.get(p.paper_id, {"paper_role": "unknown", "reason": ""})
        p.paper_role = r.get("paper_role", "unknown")
        p.baseline_eligible = (p.paper_role == "method_model")
        p.baseline_rejection_reason = None if p.baseline_eligible else (r.get("reason") or f"role={p.paper_role}")


def _fallback_role(paper: Paper) -> dict:
    text = f"{paper.title or ''} {paper.abstract or ''}".lower()
    if any(k in text for k in ("dataset", "benchmark", "data set")):
        return {"paper_role": "dataset_benchmark", "reason": "title/abstract indicates a dataset"}
    if any(k in text for k in ("survey", "review", "a review of")):
        return {"paper_role": "survey_review", "reason": "title/abstract indicates a survey/review"}
    if any(k in text for k in ("we propose", "we present", "model", "method", "cnn", "transformer", "network")):
        return {"paper_role": "method_model", "reason": "title/abstract indicates a method/model"}
    return {"paper_role": "unknown", "reason": "could not determine"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_paper_type_classifier_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 3: RepositoryVerifierAgent 增强（repo_type / is_model_baseline / priority_score）

**Files:**
- Modify: `backend/app/agents/repository_verifier_agent.py`
- Test: `backend/tests/test_s35_baseline_quality.py` (partial — repo verifier cases)

**Interfaces:**
- Produces: verdict 增 `repo_type`/`is_model_baseline`/`matches_paper_method`;`_apply` 设这些字段 + 更新 `baseline_priority_score`;dataset-only repo → `is_model_baseline=False, verified_repo=False`。

- [ ] **Step 1: Write the failing test (in test_s35_baseline_quality.py)**

```python
# backend/tests/test_s35_baseline_quality.py
import pytest

from app.agents.repository_verifier_agent import RepositoryVerifierAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.baseline import BaselineCandidate


class FakeLLM:
    provider = "fake"
    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []
    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


class FakeGithub:
    def __init__(self, *, metadata, file_tree, readme="README", commit="abc"):
        self._m, self._t, self._r, self._c = metadata, file_tree, readme, commit
    async def repo_metadata(self, u): return self._m
    async def repo_file_tree(self, u): return self._t
    async def repo_readme(self, u): return self._r
    async def latest_commit(self, u): return self._c


def _cand(**kw) -> BaselineCandidate:
    base = dict(baseline_id="b1", paper_id="p1", paper_title="Seismic CNN", code_url="https://github.com/a/b",
                code_source="github_search", task_match="seismic", input_type="waveform", stars=10)
    base.update(kw)
    return BaselineCandidate(**base)


@pytest.mark.asyncio
async def test_verifier_flags_model_code_repo() -> None:
    llm = FakeLLM({"matches_paper": True, "reproducibility_score": 0.8, "reproduction_status": "verified",
                   "run_command": "python train.py", "risks": [], "reason": "ok",
                   "repo_type": "model_code", "is_model_baseline": True, "matches_paper_method": True})
    gh = FakeGithub(metadata={"license": "MIT", "stars": 10}, file_tree=["train.py", "models/", "requirements.txt"])
    out = await RepositoryVerifierAgent(llm, gh).arun(_cand(), run_id="r")
    assert out.repo_type == "model_code"
    assert out.is_model_baseline is True
    assert out.verified_repo is True
    assert out.baseline_priority_score > 0.5


@pytest.mark.asyncio
async def test_verifier_rejects_dataset_only_repo() -> None:
    llm = FakeLLM({"matches_paper": True, "reproducibility_score": 0.5, "reproduction_status": "verified",
                   "run_command": None, "risks": [], "reason": "dataset",
                   "repo_type": "dataset_only", "is_model_baseline": False, "matches_paper_method": False})
    gh = FakeGithub(metadata={"license": "CC-BY-4.0", "stars": 50}, file_tree=["data/", "README.md"])
    out = await RepositoryVerifierAgent(llm, gh).arun(_cand(), run_id="r")
    assert out.repo_type == "dataset_only"
    assert out.is_model_baseline is False
    assert out.verified_repo is False  # dataset-only cannot be a verified model baseline
    assert out.baseline_rejection_reason


@pytest.mark.asyncio
async def test_verifier_fallback_rejects_dataset_repo_by_heuristic() -> None:
    # No useful LLM output -> heuristic. Repo name "seismic-dataset" + file_tree data/ -> dataset_only.
    gh = FakeGithub(metadata={"license": None, "stars": 1}, file_tree=["data/", "README.md"])
    out = await RepositoryVerifierAgent(FakeLLM(None), gh).arun(
        _cand(code_url="https://github.com/a/seismic-dataset"), run_id="r")
    assert out.repo_type in {"dataset_only", "unknown"}
    assert out.is_model_baseline is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s35_baseline_quality.py -v`
Expected: FAIL (repo_type/is_model_baseline not set)

- [ ] **Step 3: Modify RepositoryVerifierAgent**

In `backend/app/agents/repository_verifier_agent.py`, extend the SYSTEM_PROMPT to require `repo_type`/`is_model_baseline`/`matches_paper_method` in the JSON. Append to the SYSTEM_PROMPT's required-keys list:

```
- repo_type: one of "model_code", "dataset_only", "benchmark_suite", "docs_only", "unknown"
- is_model_baseline: bool (true only if repo_type is model_code AND it implements a trainable/evaluable model)
- matches_paper_method: bool (repo implements the paper's method)
A dataset-only repo must NOT be is_model_baseline=true.
```

Extend `_normalize` to read these (with fallback to heuristic):

```python
def _normalize(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback
    status = str(content.get("reproduction_status", fallback["reproduction_status"]))
    if status not in {"verified", "suspicious", "failed"}:
        status = fallback["reproduction_status"]
    repo_type = str(content.get("repo_type", fallback["repo_type"]))
    if repo_type not in {"model_code", "dataset_only", "benchmark_suite", "docs_only", "unknown"}:
        repo_type = fallback["repo_type"]
    is_model = bool(content.get("is_model_baseline", fallback["is_model_baseline"])) if repo_type != "dataset_only" else False
    return {
        "matches_paper": bool(content.get("matches_paper", fallback["matches_paper"])),
        "matches_paper_method": bool(content.get("matches_paper_method", fallback["matches_paper_method"])),
        "reproducibility_score": _score(content.get("reproducibility_score", fallback["reproducibility_score"])),
        "reproduction_status": status,
        "run_command": _opt_str(content.get("run_command")),
        "risks": _string_list(content.get("risks")) or fallback["risks"],
        "reason": _opt_str(content.get("reason")) or fallback["reason"],
        "repo_type": repo_type,
        "is_model_baseline": is_model,
    }
```

Extend `_heuristic_verdict` to also produce `repo_type`/`is_model_baseline`/`matches_paper_method` based on file_tree + repo name:

```python
def _heuristic_verdict(candidate, metadata, file_tree, commit) -> dict:
    tree_lower = {f.lower() for f in file_tree}
    name_lower = (candidate.code_url or "").lower()
    looks_dataset = any(k in name_lower for k in ("dataset", "data")) or any(
        f.startswith("data") or f == "data" for f in tree_lower)
    has_model_files = any("train" in f or "model" in f or "eval" in f for f in tree_lower)
    if looks_dataset and not has_model_files:
        repo_type = "dataset_only"
        is_model = False
    elif has_model_files:
        repo_type = "model_code"
        is_model = True
    else:
        repo_type = "unknown"
        is_model = False
    # (keep existing reproducibility heuristic for score/status)
    has_readme = any("readme" in f for f in tree_lower)
    has_reqs = any("requirements" in f or "environment.yml" in f or "setup.py" in f or "pyproject.toml" in f for f in tree_lower)
    has_license = bool(metadata.get("license"))
    score = 0.3 + (0.2 if has_readme else 0) + (0.2 if has_reqs else 0) + (0.15 if has_license else 0) + (0.15 if commit else 0)
    status = "verified" if (has_readme and has_reqs and score >= 0.7 and is_model) else ("suspicious" if score >= 0.4 else "failed")
    risks = []
    if not has_reqs: risks.append("no requirements/environment file")
    if not has_license: risks.append("no license")
    return {
        "matches_paper": True, "matches_paper_method": is_model,
        "reproducibility_score": round(min(1.0, score), 2), "reproduction_status": status,
        "run_command": None, "risks": risks, "reason": "Heuristic verdict from file tree.",
        "repo_type": repo_type, "is_model_baseline": is_model,
    }
```

Extend `_apply` to set the new fields + `baseline_priority_score` (post-verify) + dataset-only rejection:

```python
def _apply(candidate: BaselineCandidate, verdict: dict, metadata: dict) -> BaselineCandidate:
    updated = candidate.model_copy(deep=True)
    updated.repo_type = verdict["repo_type"]
    updated.is_model_baseline = verdict["is_model_baseline"]
    # dataset-only can never be a verified model baseline
    if verdict["repo_type"] == "dataset_only":
        updated.verified_repo = False
        updated.reproduction_status = "failed"
        updated.is_model_baseline = False
        updated.baseline_rejection_reason = "dataset-only repo, not a model baseline"
    else:
        updated.verified_repo = bool(verdict["matches_paper"]) and verdict["is_model_baseline"] and verdict["reproduction_status"] == "verified"
        updated.reproduction_status = verdict["reproduction_status"]
        if not updated.verified_repo and not verdict["is_model_baseline"]:
            updated.baseline_rejection_reason = updated.baseline_rejection_reason or f"repo_type={verdict['repo_type']}, not a model baseline"
    updated.reproducibility_score = verdict["reproducibility_score"]
    updated.run_command = verdict["run_command"]
    risks = list(candidate.risks)
    for r in verdict["risks"]:
        if r not in risks: risks.append(r)
    updated.risks = risks
    if metadata.get("license") and not updated.license: updated.license = metadata.get("license")
    if metadata.get("stars"): updated.stars = int(metadata.get("stars") or 0)
    updated.baseline_priority_score = _priority_score(updated, verdict)
    return updated


def _priority_score(c: BaselineCandidate, verdict: dict) -> float:
    # post-verify: BaselineCandidate does not carry paper_role, so use the
    # repo-side signals the verifier just produced.
    repo_model = 1.0 if verdict["is_model_baseline"] else 0.0
    match = 1.0 if verdict.get("matches_paper_method") else 0.0
    repro = verdict["reproducibility_score"]
    stars = min(1.0, (c.stars or 0) / 50.0)
    penalty = 0.5 if verdict["repo_type"] == "dataset_only" else 0.0
    score = 0.40 * repo_model + 0.25 * match + 0.20 * repro + 0.05 * stars - penalty
    return round(max(0.0, min(1.0, score)), 3)
```

> Note: `BaselineCandidate` does not carry `paper_role`; the post-verify priority uses `is_model_baseline` + `matches_paper_method` + `reproducibility_score` + `stars` − dataset penalty. The pre-verify initial score (Task 4) uses `paper_role` + `stars` + repo-name heuristic. Both live on `baseline_priority_score` (overwritten by verifier).

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s35_baseline_quality.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 4: BaselineDiscoveryAgent — 只用 eligible 论文 + 关 task 宽搜 + 初始 priority_score + stars

**Files:**
- Modify: `backend/app/agents/baseline_discovery_agent.py`
- Test: `backend/tests/test_s35_baseline_quality.py` (append discovery cases)

**Interfaces:**
- Produces: `arun` 只对 `paper.baseline_eligible` 的论文做 paper-code + per-paper 标题搜;**删除 task 级宽搜**(`_candidate_from_github_task` 不再调用);候选设 `stars`;算初始 `baseline_priority_score`(paper_role + stars + repo 名 dataset 启发式);paper-code 候选用 repo 名启发式设 `repo_type`/`is_model_baseline`(dataset 名 → dataset_only)。

- [ ] **Step 1: Append failing tests**

```python
# append to backend/tests/test_s35_baseline_quality.py
from app.agents.baseline_discovery_agent import BaselineDiscoveryAgent, _initial_priority_score
from app.schemas.paper import Paper


class FakeGithub:
    async def search_repos(self, query, limit=5):
        return [{"full_name": "a/seismic-cnn", "html_url": "https://github.com/a/seismic-cnn", "description": "CNN model",
                 "stars": 12, "license": "MIT", "default_branch": "main", "pushed_at": "", "open_issues": 0}]


class FakePwc:
    async def search(self, task, limit=5): return []


@pytest.mark.asyncio
async def test_discovery_only_uses_eligible_papers() -> None:
    agent = BaselineDiscoveryAgent(FakeGithub(), FakePwc())
    papers = [
        Paper(paper_id="p1", title="Seismic CNN model", baseline_eligible=True, code_url="https://github.com/a/model"),
        Paper(paper_id="p2", title="STEAD dataset", baseline_eligible=False, code_url="https://github.com/a/dataset"),
    ]
    cands = await agent.arun(papers, task="seismic event classification", run_id="r")
    urls = {c.code_url for c in cands}
    assert "https://github.com/a/model" in urls  # eligible paper's code included
    assert "https://github.com/a/dataset" not in urls  # non-eligible paper's code excluded


def test_initial_priority_score_penalizes_dataset_name() -> None:
    c = BaselineCandidate(baseline_id="b", paper_id="p", paper_title="t",
                          code_url="https://github.com/a/seismic-dataset", code_source="github_search",
                          task_match="seismic", input_type="waveform", stars=5)
    score = _initial_priority_score(c, paper_role="method_model")
    assert score < 0.5  # dataset-named repo penalized
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s35_baseline_quality.py -v`
Expected: FAIL (task search still runs / eligible filter missing / _initial_priority_score missing)

- [ ] **Step 3: Modify BaselineDiscoveryAgent**

In `backend/app/agents/baseline_discovery_agent.py`:
- In `arun`, change the paper loops to iterate only eligible papers: `for paper in (papers or [])[:MAX_PAPERS] if paper.baseline_eligible` — i.e. filter `eligible = [p for p in (papers or [])[:MAX_PAPERS] if p.baseline_eligible]` and loop over `eligible`.
- **Remove the task-level broad search block** (the `# 1) Task-level GitHub search` block with `_task_query`/`_candidate_from_github_task`). Delete it entirely.
- In `_candidate_from_github` and `_candidate_from_paper_code_url`, set `stars=repo.get("stars")` (github) / `stars=0` (paper-code) and `baseline_priority_score=_initial_priority_score(candidate, paper_role=paper.paper_role)`.
- For `_candidate_from_paper_code_url`: set `repo_type` via repo-name heuristic (dataset name → "dataset_only", else "model_code" assumed since paper-declared) and `is_model_baseline` accordingly.
- Add `_initial_priority_score`:

```python
def _initial_priority_score(candidate: BaselineCandidate, *, paper_role: str = "unknown") -> float:
    url = (candidate.code_url or "").lower()
    name_looks_dataset = any(k in url for k in ("dataset", "data"))
    paper_method = 1.0 if paper_role == "method_model" else 0.4
    repo_model_signal = 0.0 if name_looks_dataset else 0.5
    stars = min(1.0, (candidate.stars or 0) / 50.0)
    penalty = 0.5 if name_looks_dataset else 0.0
    score = 0.30 * paper_method + 0.30 * repo_model_signal + 0.05 * stars - penalty
    return round(max(0.0, min(1.0, score)), 3)
```

- `_candidate_from_paper_code_url` now sets:

```python
def _candidate_from_paper_code_url(paper: Paper, task: str) -> BaselineCandidate:
    url = paper.code_url or ""
    name_looks_dataset = any(k in url.lower() for k in ("dataset", "data"))
    repo_type = "dataset_only" if name_looks_dataset else "model_code"
    is_model = not name_looks_dataset
    source = paper.code_url_source or "paper_abstract"  # real source now tracked
    cand = BaselineCandidate(
        baseline_id=_stable_id(("paper", paper.paper_id, url)),
        paper_id=paper.paper_id, paper_title=paper.title, paper_doi=paper.doi, paper_url=paper.source_url,
        code_url=url, code_source=source, task_match=task, input_type="unknown",
        license=None, verified_repo=is_model, reproduction_status="pending" if is_model else "failed",
        repo_type=repo_type, is_model_baseline=is_model,
        baseline_rejection_reason=None if is_model else "dataset-only repo (paper-declared)",
        stars=0,
    )
    cand.baseline_priority_score = _initial_priority_score(cand, paper_role=paper.paper_role)
    return cand
```

- `_candidate_from_github` now sets `stars` and initial priority:

```python
def _candidate_from_github(paper: Paper, repo: dict, task: str) -> BaselineCandidate:
    cand = BaselineCandidate(
        baseline_id=_stable_id((paper.paper_id, repo.get("full_name", ""))),
        paper_id=paper.paper_id, paper_title=paper.title, paper_doi=paper.doi, paper_url=paper.source_url,
        code_url=repo.get("html_url"), code_source="github_search", task_match=task, input_type="unknown",
        license=repo.get("license"), risks=_github_risks(repo),
        stars=int(repo.get("stars") or 0),
    )
    cand.baseline_priority_score = _initial_priority_score(cand, paper_role=paper.paper_role)
    return cand
```

- Update the existing `test_baseline_discovery_agent.py` tests if they relied on task-level search / non-eligible papers — re-run them and adjust expectations (the FakeGithub there returns repos for any query; with task search removed, only per-paper search runs; ensure the existing happy-path test still asserts the per-paper candidate URL).

- [ ] **Step 4: Run tests to verify they pass + regression**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s35_baseline_quality.py tests/test_baseline_discovery_agent.py tests/test_repository_verifier_agent.py -v`
Expected: PASS (fix any pre-existing discovery test that assumed task search).

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 5: 接入 workflow — paper_classification step + 按 priority 验证 top-3

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py`
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Test: `backend/tests/test_arena_workflow_integration.py` (append) or new `test_s35_workflow.py`

**Interfaces:**
- Produces: seismic chain 加 `paper_classification` step(literature_mining 之后、scientific_data_profile 之前);`_verify_baselines_auto` 改成 `sorted([c for c in candidates if c.is_model_baseline or c.repo_type == "unknown"], key=lambda c: c.baseline_priority_score, reverse=True)[:3]`。

- [ ] **Step 1: Append failing test**

```python
# append to backend/tests/test_arena_workflow_integration.py (or test_s35_workflow.py)
@pytest.mark.asyncio
async def test_seismic_classifies_papers_and_verifies_by_priority(monkeypatch) -> None:
    from app.config import Settings
    from app.schemas.paper import Paper
    from app.schemas.run import ResearchConstraints, ResearchRun
    from app.workflows.scientist_workflow import ScientistWorkflow
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))

    async def fake_classify(self, papers, *, run_id):
        for p in papers: p.paper_role, p.baseline_eligible = "method_model", True
        return papers
    monkeypatch.setattr(wf.paper_classifier.__class__, "arun", fake_classify)

    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")
    run.papers = [Paper(paper_id="p1", title="Seismic CNN")]
    await wf._classify_papers(run)
    assert run.papers[0].paper_role == "method_model"
    assert run.papers[0].baseline_eligible is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_arena_workflow_integration.py -v`
Expected: FAIL (no `paper_classifier` / `_classify_papers`)

- [ ] **Step 3: Modify ScientistWorkflow**

In `backend/app/workflows/scientist_workflow.py`:
- Import: `from app.agents.paper_type_classifier_agent import PaperTypeClassifierAgent`.
- In `__init__`, add: `self.paper_classifier = PaperTypeClassifierAgent(self.llm)`.
- Add the step method:

```python
    async def _classify_papers(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.papers:
            run.steps[-1].summary = "Skipped paper classification."
            return
        await self.paper_classifier.arun(run.papers, run_id=run.run_id)
        eligible = sum(1 for p in run.papers if p.baseline_eligible)
        run.steps[-1].summary = f"Classified {len(run.papers)} papers; {eligible} method-model (baseline-eligible)."
```

- In `_run_after_evidence_review` (the seismic branch built in S3), insert `paper_classification` between `literature_mining` and `scientific_data_profile`. The current seismic branch starts with `await self._step(run, "scientific_data_profile", self._profile_scientific_data)`. Insert before it:

```python
        if run.domain == "seismic_event_classification":
            await self._step(run, "paper_classification", self._classify_papers)
        await self._step(run, "scientific_data_profile", self._profile_scientific_data)
        if run.domain == "seismic_event_classification":
            await self._step(run, "arena", self._run_arena)
            ...
```

(Re-structure so `paper_classification` runs after `literature_mining` — note `_run_after_evidence_review` is called after literature_mining in the chain, so inserting `paper_classification` as the first step there puts it right after literature_mining. ✓)

- Update `_verify_baselines_auto` (from S3) to sort by `baseline_priority_score` and target model/unknown candidates:

```python
    async def _verify_baselines_auto(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.baseline_candidates:
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
        run.steps[-1].summary = f"Verified {len(to_verify)} by priority; {model_baselines} verified model baselines."
```

- [ ] **Step 4: Modify LangGraphWorkflow**

In `backend/app/workflows/langgraph_workflow.py` `_build_graph`: the seismic chain currently has `literature_mining → scientific_data_profile` (via `_route_after_mining` → scientific_data_profile). Add a `paper_classification` node and insert it between `literature_mining` and `scientific_data_profile` for seismic. Simplest: change `_route_after_mining` to route seismic to `paper_classification` (when not pausing), and add edge `paper_classification → scientific_data_profile`:

```python
        graph.add_node("paper_classification", self._make_step_node("paper_classification", "_classify_papers"))
        # change _route_after_mining:
    def _route_after_mining(self, state: WorkflowState) -> str:
        run = state["run"]
        if run.constraints.workflow_mode == "guided" and not run.evidence_frozen:
            return "pause_evidence"
        return "paper_classification"
    # and add edge:
        graph.add_edge("paper_classification", "scientific_data_profile")
```

(Non-seismic also routes through `paper_classification` — but `_classify_papers` is a no-op for non-seismic, so it's harmless and keeps the graph simple. Alternatively add a conditional; the no-op is simpler.)

- [ ] **Step 5: Run tests + full suite**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_arena_workflow_integration.py tests/test_langgraph_workflow.py -v`
Then: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q`
Expected: PASS (the non-seismic langgraph step list now includes `paper_classification` as a no-op step — UPDATE the `test_langgraph_workflow_completes_sync_run` step_names assertion to include `paper_classification` after `literature_mining`).

> IMPORTANT: update the step_names assertion in `test_langgraph_workflow_completes_sync_run` to insert `"paper_classification"` after `"literature_mining"` (it's a no-op for the non-seismic run but still appears in run.steps).

- [ ] **Step 6: Skip commit (local-only).**

---

### Task 6: 前端 — LiteratureBoard 显示 paper_role + BaselineBoard 显示 repo_type/priority

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/workbench/LiteratureBoard.tsx`
- Modify: `frontend/components/workbench/BaselineBoard.tsx`
- Test: manual.

- [ ] **Step 1: Add types to `frontend/lib/api.ts`**

In the `papers` array item type, add:
```typescript
    paper_role?: string;
    baseline_eligible?: boolean;
    baseline_rejection_reason?: string | null;
```

In the `baseline_candidates` item type, add:
```typescript
    repo_type?: string;
    is_model_baseline?: boolean;
    baseline_priority_score?: number;
    baseline_rejection_reason?: string | null;
    stars?: number;
```

- [ ] **Step 2: LiteratureBoard — show paper_role / baseline_eligible**

In `frontend/components/workbench/LiteratureBoard.tsx`, in each paper `item-actions`, add badges:
```tsx
              {paper.paper_role && (
                <span className={`badge ${paper.baseline_eligible ? "good" : "warn"}`}>{paper.paper_role}</span>
              )}
              {paper.baseline_eligible === false && paper.baseline_rejection_reason && (
                <span className="badge warn" title={paper.baseline_rejection_reason}>excluded</span>
              )}
```

- [ ] **Step 3: BaselineBoard — show repo_type / is_model_baseline / priority / rejection_reason; sort by priority**

In `frontend/components/workbench/BaselineBoard.tsx`, sort candidates by `baseline_priority_score` desc, and in each candidate's item-actions add:
```tsx
              <span className={`badge ${c.is_model_baseline ? "good" : "warn"}`}>{c.repo_type || "unknown"}</span>
              <span className="badge">priority {(c.baseline_priority_score || 0).toFixed(2)}</span>
              {c.baseline_rejection_reason && (
                <span className="badge warn" title={c.baseline_rejection_reason}>rejected</span>
              )}
```
And change the candidates list to sort: `const candidates = [...(run?.baseline_candidates || [])].sort((a,b) => (b.baseline_priority_score||0) - (a.baseline_priority_score||0));`

- [ ] **Step 4: Manual verification**

Open http://localhost:3000 → Seismic Expert → 启动. After `paper_classification` step: LiteratureBoard shows each paper's `paper_role` (method_model/dataset_benchmark/...) + excluded badge. After baseline steps: BaselineBoard sorted by priority, shows repo_type (model_code/dataset_only/...) + is_model_baseline + priority + rejected reason. Dataset repos (STEAD) show as dataset_only/rejected.

- [ ] **Step 5: Skip commit (local-only).**

---

## S3.5 验收

- [ ] **Step 6: Full backend suite**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q
```
Expected: all green incl. new s35 tests + regression (update langgraph step_names assertion for paper_classification).

- [ ] **Step 7: Live acceptance**

Seismic run: LiteratureBoard shows paper_role on each paper (STEAD → dataset_benchmark/excluded); BaselineBoard has NO dataset-only repos marked as verified; model_code repos verified with priority score; top-3 verified by priority (not insertion order).

## 已知 S3.5 局限

- 重搜循环(有效 baseline 不足时重新检索文献)→ S5。
- PaperTypeClassifier / repo_type 判定靠 LLM,有误判可能;前端标出 reason 供人工核。
- paper-code 候选的 repo_type 用 repo 名启发式(粗);S5 重搜时可深查。
