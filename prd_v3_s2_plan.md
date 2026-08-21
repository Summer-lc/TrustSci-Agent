# v3 Sprint S2 实施计划：数据与 Baseline 发现层

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让系统能为地震分类 run 从真实 GitHub / Papers with Code 发现带公开代码的 baseline，并由 RepositoryVerifier 评估可复现性，前端 Seismic 工作区落地第一批真实面板（BaselineBoard + SeismicOverviewPanel）。

**Architecture:** 真实外部 API 调用（GitHub + Papers with Code）+ 优雅降级（网络失败返回空/None，不崩）。BaselineDiscovery 是确定性工具编排器（不调 LLM，搜源 + 启发式打分）；NoveltyChecker 与 RepositoryVerifier 是 LCEL LLM agent（`LLMClientRunnable`，照 S1 的 IntentRouter/IdeaIntake 模式）。baseline 发现是 **on-demand 端点**（用户在 BaselineBoard 点按钮触发），不自动塞进每个 run——避免外部 API 拖慢 run 和撞 rate limit，且不改 LangGraph 图。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / httpx / LangChain LCEL / pytest / Next.js + TypeScript。

## Global Constraints

- 新 LLM agent（NoveltyChecker / RepositoryVerifier）必须走 `LLMClientRunnable` 适配器（仍调 `QwenClient.complete()`），`agent` 字段分别为 `novelty_checker` / `repo_verifier`，保留 `data/outputs/llm_calls` 审计日志；malformed 输出落 fallback 不崩 run。
- 外部 HTTP（GitHub / PwC）必须**优雅降级**：任何 `httpx.HTTPError` / 解析失败 → 返回 `[]` / `None`，不抛异常到 workflow。客户端接受 `transport: httpx.AsyncBaseTransport | None` 参数供测试注入（照 `arxiv_client.py` 模式）。
- GitHub 认证可选：`settings.github_token` 默认空（匿名 60/hr）；非空时带 `Authorization: Bearer {token}`（5000/hr）。
- **不修改 LangGraph 图**（`langgraph_workflow.py` 本 Sprint 不动）。baseline 发现通过 on-demand API 端点触发，结果存 `run.baseline_candidates`，前端从 `GET /api/runs/{id}` 读取。
- YAGNI：S2 只做 baseline 发现 + 验证 + 前端展示。**baseline 代码实际执行 / 沙盒隔离 / clone** 推迟到 S4（Code Experiment Loop）；S2 的 RepositoryVerifier 只**检查并报告** repo 可复现性 + safety status，不执行任何外部代码。
- baseline 代码源通道只做 3 条：GitHub search（按论文标题/方法名）、Papers with Code search、用户手动给 repo URL（verify-repo 端点接受 `code_url` 覆盖）。**不做** arXiv/PDF/作者主页爬取（弱价值、高复杂度）。
- 不带 `DASHSCOPE_API_KEY` 时 LLM agent 走确定性 fallback；不带 `GITHUB_TOKEN` 时 GitHub 匿名调用。
- 文件路径相对仓库根 `d:/For work/TrustSci-Agent/`。后端测试在 Docker dev 栈跑：`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest <path> -v`。
- 不 commit（用户偏好，所有改动留本地工作区）。

## File Structure

- **Create** `backend/app/schemas/baseline.py` — `BaselineCandidate` 模型（PRD §11.3）。
- **Create** `backend/app/tools/baseline_sources.py` — `GithubBaselineClient` + `PapersWithCodeClient`（httpx，可注入 transport，纯函数解析）。
- **Create** `backend/app/agents/novelty_checker_agent.py` — NoveltyChecker LCEL agent + fallback。
- **Create** `backend/app/agents/baseline_discovery_agent.py` — 确定性工具编排器（搜源 + 启发式打分）。
- **Create** `backend/app/agents/repository_verifier_agent.py` — RepositoryVerifier LCEL agent + GitHub 工具 + fallback。
- **Create** `backend/tests/test_baseline_schemas.py`
- **Create** `backend/tests/test_baseline_sources.py`
- **Create** `backend/tests/test_novelty_checker_agent.py`
- **Create** `backend/tests/test_baseline_discovery_agent.py`
- **Create** `backend/tests/test_repository_verifier_agent.py`
- **Create** `backend/tests/test_baselines_api.py`
- **Create** `frontend/components/workbench/BaselineBoard.tsx`
- **Create** `frontend/components/workbench/SeismicOverviewPanel.tsx`
- **Modify** `backend/app/schemas/paper.py` — 加 `code_url: str | None = None`。
- **Modify** `backend/app/schemas/run.py` — 加 `baseline_candidates` / `novelty_report` 字段。
- **Modify** `backend/app/config.py` — 加 `github_token`。
- **Modify** `.env.example` — 加 `GITHUB_TOKEN=`。
- **Modify** `backend/app/api/routes_runs.py` — 加 `POST /baselines/discover` + `POST /baselines/{id}/verify-repo`。
- **Modify** `frontend/lib/api.ts` — `ResearchRun` 类型加 `baseline_candidates`/`novelty_report`/`paper.code_url`；新增 `discoverBaselines`/`verifyBaselineRepo`。
- **Modify** `frontend/components/workbench/Workbench.tsx` — seismic 工作区从 `seismic-empty` 换成 SeismicOverviewPanel + LiteratureBoard + BaselineBoard。

---

### Task 1: BaselineCandidate schema + Paper.code_url + ResearchRun 字段

**Files:**
- Create: `backend/app/schemas/baseline.py`
- Modify: `backend/app/schemas/paper.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_baseline_schemas.py`

**Interfaces:**
- Produces: `BaselineCandidate`（from `app.schemas.baseline`）；`Paper.code_url: str | None`；`ResearchRun.baseline_candidates: list[BaselineCandidate]`、`ResearchRun.novelty_report: dict | None`。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_baseline_schemas.py
from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


def test_baseline_candidate_defaults() -> None:
    bc = BaselineCandidate(
        baseline_id="baseline_001",
        paper_id="paper_001",
        paper_title="Deep seismic event classification",
        code_url="https://github.com/example/seismic-cnn",
        code_source="github_search",
        task_match="seismic event classification",
        input_type="waveform",
    )
    assert bc.reproducibility_score == 0.0
    assert bc.verified_repo is False
    assert bc.reproduction_status == "pending"
    assert bc.risks == []
    assert bc.run_command is None


def test_paper_has_code_url() -> None:
    p = Paper(paper_id="p1", title="t", code_url="https://github.com/x/y")
    assert p.code_url == "https://github.com/x/y"


def test_research_run_baseline_fields_default_empty() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints())
    assert run.baseline_candidates == []
    assert run.novelty_report is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_schemas.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'app.schemas.baseline'`

- [ ] **Step 3: Write the schema**

```python
# backend/app/schemas/baseline.py
from pydantic import BaseModel, Field


class BaselineCandidate(BaseModel):
    baseline_id: str
    paper_id: str
    paper_title: str
    paper_doi: str | None = None
    paper_url: str | None = None
    code_url: str | None = None
    code_source: str  # github_search | paperswithcode | user_provided
    task_match: str
    input_type: str  # waveform | spectrogram | multi_channel_waveform | unknown
    labels_supported: list[str] = Field(default_factory=list)
    dataset_used: str | None = None
    metrics_reported: list[str] = Field(default_factory=list)
    reproducibility_score: float = 0.0  # 0..1, filled by RepositoryVerifier
    license: str | None = None
    run_command: str | None = None
    verified_repo: bool = False
    reproduction_status: str = "pending"  # pending | verified | suspicious | failed
    risks: list[str] = Field(default_factory=list)
```

In `backend/app/schemas/paper.py`, add the field (after `pdf_url: str | None = None`):

```python
    code_url: str | None = None
```

In `backend/app/schemas/run.py`, add imports (after `from app.schemas.seismic import SeismicDataProfile`):

```python
from app.schemas.baseline import BaselineCandidate
```

Add fields to `ResearchRun` (after `seismic_data_profile`):

```python
    baseline_candidates: list[BaselineCandidate] = Field(default_factory=list)
    novelty_report: dict | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_schemas.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 2: GitHub + Papers with Code 源客户端 + config

**Files:**
- Create: `backend/app/tools/baseline_sources.py`
- Modify: `backend/app/config.py`
- Modify: `.env.example`
- Test: `backend/tests/test_baseline_sources.py`

**Interfaces:**
- Produces: `GithubBaselineClient(token="", transport=None)` with async `search_repos(query, limit) -> list[dict]`、`repo_metadata(repo_url) -> dict | None`、`repo_readme(repo_url) -> str | None`、`repo_file_tree(repo_url) -> list[str]`、`latest_commit(repo_url) -> str | None`；纯函数 `_parse_search_items(payload)`、`_parse_repo(payload)`、`_extract_owner_repo(repo_url)`。`PapersWithCodeClient(transport=None)` with async `search(task, limit) -> list[dict]` + `_parse_results(payload)`。每个返回 dict 形状：repo 项 `{full_name, html_url, description, stars, license, default_branch, pushed_at, open_issues}`；PwC 项 `{paper_title, code_url, stars, task}`。
- Consumes: `settings.github_token`（可选）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_baseline_sources.py
from app.tools.baseline_sources import (
    GithubBaselineClient,
    PapersWithCodeClient,
    _extract_owner_repo,
    _parse_repo,
    _parse_search_items,
    _parse_results,
)


def test_extract_owner_repo_from_urls() -> None:
    assert _extract_owner_repo("https://github.com/example/seismic-cnn") == ("example", "seismic-cnn")
    assert _extract_owner_repo("https://github.com/example/seismic-cnn/tree/main") == ("example", "seismic-cnn")
    assert _extract_owner_repo("not a url") is None


def test_parse_search_items() -> None:
    payload = {"items": [
        {"full_name": "a/b", "html_url": "https://github.com/a/b", "description": "d",
         "stargazers_count": 10, "license": {"spdx_id": "MIT"}, "default_branch": "main",
         "pushed_at": "2024-01-01", "open_issues_count": 2},
    ]}
    items = _parse_search_items(payload)
    assert len(items) == 1
    assert items[0]["full_name"] == "a/b"
    assert items[0]["stars"] == 10
    assert items[0]["license"] == "MIT"


def test_parse_search_items_malformed_returns_empty() -> None:
    assert _parse_search_items({}) == []
    assert _parse_search_items("nope") == []


def test_parse_repo() -> None:
    payload = {"full_name": "a/b", "html_url": "https://github.com/a/b", "description": "d",
               "stargazers_count": 5, "license": {"spdx_id": "Apache-2.0"}, "default_branch": "main",
               "pushed_at": "2024-02-01", "open_issues_count": 0}
    repo = _parse_repo(payload)
    assert repo["full_name"] == "a/b"
    assert repo["license"] == "Apache-2.0"


def test_parse_results_pwc() -> None:
    payload = {"results": [{"paper": {"title": "SeismicNet"}, "repository": {"url": "https://github.com/x/seismicnet", "stars": 3}}]}
    items = _parse_results(payload)
    assert items[0]["paper_title"] == "SeismicNet"
    assert items[0]["code_url"] == "https://github.com/x/seismicnet"


def test_clients_default_token_empty() -> None:
    assert GithubBaselineClient().token == ""
    assert PapersWithCodeClient() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_sources.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'app.tools.baseline_sources'`

- [ ] **Step 3: Write the source clients**

```python
# backend/app/tools/baseline_sources.py
import re
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
PWC_API = "https://paperswithcode.com/v1/search"
USER_AGENT = "TrustSci-Agent/0.1"


class GithubBaselineClient:
    """GitHub baseline source: search repos + fetch repo metadata for verification.

    All HTTP is graceful: any error returns [] / None, never raises into the
    workflow. `transport` is injectable for tests (httpx.MockTransport).
    """

    def __init__(self, token: str = "", transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.token = token.strip()
        self.transport = transport

    async def search_repos(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query or limit <= 0:
            return []
        params = {"q": query, "per_page": max(1, min(limit, 30)), "sort": "stars", "order": "desc"}
        payload = await self._get(f"{GITHUB_API}/search/repositories", params=params)
        return _parse_search_items(payload)[:limit]

    async def repo_metadata(self, repo_url: str) -> dict[str, Any] | None:
        owner_repo = _extract_owner_repo(repo_url)
        if not owner_repo:
            return None
        payload = await self._get(f"{GITHUB_API}/repos/{owner_repo[0]}/{owner_repo[1]}")
        return _parse_repo(payload) if payload else None

    async def repo_readme(self, repo_url: str) -> str | None:
        owner_repo = _extract_owner_repo(repo_url)
        if not owner_repo:
            return None
        headers = self._headers({"Accept": "application/vnd.github.raw"})
        return await self._get_text(f"{GITHUB_API}/repos/{owner_repo[0]}/{owner_repo[1]}/readme", headers=headers)

    async def repo_file_tree(self, repo_url: str) -> list[str]:
        owner_repo = _extract_owner_repo(repo_url)
        if not owner_repo:
            return []
        payload = await self._get(f"{GITHUB_API}/repos/{owner_repo[0]}/{owner_repo[1]}/contents")
        if not isinstance(payload, list):
            return []
        return [str(item.get("name")) for item in payload if isinstance(item, dict) and item.get("name")]

    async def latest_commit(self, repo_url: str) -> str | None:
        owner_repo = _extract_owner_repo(repo_url)
        if not owner_repo:
            return None
        payload = await self._get(f"{GITHUB_API}/repos/{owner_repo[0]}/{owner_repo[1]}/commits", params={"per_page": 1})
        if not isinstance(payload, list) or not payload:
            return None
        return str(payload[0].get("sha")) if isinstance(payload[0], dict) else None

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    async def _get(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                resp = await client.get(url, params=params, headers=self._headers(headers))
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return None

    async def _get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                resp = await client.get(url, headers=self._headers(headers))
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPError:
            return None


class PapersWithCodeClient:
    """Papers with Code baseline source."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def search(self, task: str, limit: int = 5) -> list[dict[str, Any]]:
        task = (task or "").strip()
        if not task or limit <= 0:
            return []
        payload = await self._get(PWC_API, params={"q": task})
        return _parse_results(payload)[:limit]

    async def _get(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                resp = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return None


def _extract_owner_repo(repo_url: str) -> tuple[str, str] | None:
    if not repo_url:
        return None
    match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:[/$]|$)", str(repo_url).strip())
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    repo = re.sub(r"\.git$", "", repo)
    if not owner or not repo:
        return None
    return (owner, repo)


def _parse_search_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append({
            "full_name": str(item.get("full_name", "")),
            "html_url": str(item.get("html_url", "")),
            "description": str(item.get("description") or ""),
            "stars": int(item.get("stargazers_count") or 0),
            "license": _license_spdx(item.get("license")),
            "default_branch": str(item.get("default_branch") or "main"),
            "pushed_at": str(item.get("pushed_at") or ""),
            "open_issues": int(item.get("open_issues_count") or 0),
        })
    return out


def _parse_repo(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or not payload.get("full_name"):
        return None
    return {
        "full_name": str(payload.get("full_name")),
        "html_url": str(payload.get("html_url", "")),
        "description": str(payload.get("description") or ""),
        "stars": int(payload.get("stargazers_count") or 0),
        "license": _license_spdx(payload.get("license")),
        "default_branch": str(payload.get("default_branch") or "main"),
        "pushed_at": str(payload.get("pushed_at") or ""),
        "open_issues": int(payload.get("open_issues_count") or 0),
    }


def _parse_results(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    out: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        paper = item.get("paper") if isinstance(item.get("paper"), dict) else {}
        repo = item.get("repository") if isinstance(item.get("repository"), dict) else {}
        code_url = repo.get("url") or repo.get("html_url")
        if not code_url:
            continue
        out.append({
            "paper_title": str(paper.get("title") or ""),
            "code_url": str(code_url),
            "stars": int(repo.get("stars") or 0),
            "task": str(item.get("task") or ""),
        })
    return out


def _license_spdx(license_obj: Any) -> str | None:
    if isinstance(license_obj, dict):
        spdx = license_obj.get("spdx_id")
        if spdx and spdx != "NOASSERTION":
            return str(spdx)
    return None
```

In `backend/app/config.py`, add to `Settings` (after `materials_project_api_key`):

```python
    github_token: str = ""
```

In `.env.example`, add a line (near the other optional keys):

```
GITHUB_TOKEN=
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_sources.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 3: NoveltyCheckerAgent（LCEL）

**Files:**
- Create: `backend/app/agents/novelty_checker_agent.py`
- Test: `backend/tests/test_novelty_checker_agent.py`

**Interfaces:**
- Consumes: `LLMClient`、`list[Paper]`、`IdeaBrief | None`、`ResearchRun`。
- Produces: `NoveltyCheckerAgent.arun(papers, idea_brief, run_id) -> dict`：`{similar_work: list[dict], has_public_code: bool, overlap_points: list[str], retainable_novelty: list[str], claims_to_downgrade: list[str], optimization_directions: list[str]}`。存于 `run.novelty_report`。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_novelty_checker_agent.py
import pytest

from app.agents.novelty_checker_agent import NoveltyCheckerAgent, SYSTEM_PROMPT
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


def _papers() -> list[Paper]:
    return [Paper(paper_id="p1", title="Seismic event classification with CNN", code_url="https://github.com/x/y")]


@pytest.mark.asyncio
async def test_novelty_checker_returns_report() -> None:
    llm = FakeLLM({
        "similar_work": [{"title": "Seismic CNN", "code_url": "https://github.com/x/y"}],
        "has_public_code": True,
        "overlap_points": ["CNN on waveforms"],
        "retainable_novelty": ["multi-channel fusion"],
        "claims_to_downgrade": ["novelty of CNN baseline"],
        "optimization_directions": ["add spectrogram branch"],
    })
    agent = NoveltyCheckerAgent(llm)
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints())
    report = await agent.arun(_papers(), None, run_id=run.run_id)
    assert report["has_public_code"] is True
    assert report["retainable_novelty"] == ["multi-channel fusion"]
    assert llm.requests[0].agent == "novelty_checker"
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_novelty_checker_falls_back_on_bad_output() -> None:
    for bad in ("nope", None, [1], 5, {"has_public_code": "x"}):
        agent = NoveltyCheckerAgent(FakeLLM(bad))
        report = await agent.arun(_papers(), None, run_id="run_x")
        assert isinstance(report["similar_work"], list)
        assert isinstance(report["retainable_novelty"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_novelty_checker_agent.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'app.agents.novelty_checker_agent'`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/novelty_checker_agent.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.idea import IdeaBrief
from app.schemas.paper import Paper

SYSTEM_PROMPT = """You are the Novelty / Related Work Checker for TrustSci-Agent v3 (Idea Refinement mode).
Given a user idea and the retrieved papers, assess overlap and retainable novelty.
Return JSON only with keys:
- similar_work: list of objects {title, code_url?} closest to the user idea
- has_public_code: bool, whether any similar work has public code
- overlap_points: list of strings where the user idea overlaps existing work
- retainable_novelty: list of strings the user can still claim as novel
- claims_to_downgrade: list of claims that should be weakened
- optimization_directions: list of suggested improvements
Do not invent papers. Only reference papers from the provided list."""

USER_TEMPLATE = """User idea: {user_idea}
Retrieved papers:
{papers_json}

Assess novelty and overlap."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])


class NoveltyReportParser(Runnable):
    def __init__(self, fallback: dict) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> dict:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)


class NoveltyCheckerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def arun(self, papers: list[Paper], idea_brief: IdeaBrief | None, *, run_id: str) -> dict:
        fallback = _fallback_report(papers, idea_brief)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run_id, agent="novelty_checker")
            | NoveltyReportParser(fallback=fallback)
        )
        return await chain.ainvoke(_prompt_vars(papers, idea_brief))


def _prompt_vars(papers: list[Paper], idea_brief: IdeaBrief | None) -> dict:
    user_idea = (idea_brief.user_idea if idea_brief and idea_brief.user_idea else "")
    papers_json = [{"title": p.title, "code_url": p.code_url, "doi": p.doi} for p in papers[:10]]
    import json
    return {"user_idea": user_idea, "papers_json": json.dumps(papers_json, ensure_ascii=False)}


def _normalize(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback
    return {
        "similar_work": _list_of_dicts(content.get("similar_work")),
        "has_public_code": bool(content.get("has_public_code", fallback["has_public_code"])),
        "overlap_points": _string_list(content.get("overlap_points")),
        "retainable_novelty": _string_list(content.get("retainable_novelty")),
        "claims_to_downgrade": _string_list(content.get("claims_to_downgrade")),
        "optimization_directions": _string_list(content.get("optimization_directions")),
    } or fallback


def _fallback_report(papers: list[Paper], idea_brief: IdeaBrief | None) -> dict:
    has_code = any(p.code_url for p in papers)
    return {
        "similar_work": [{"title": p.title, "code_url": p.code_url} for p in papers if p.code_url],
        "has_public_code": has_code,
        "overlap_points": [],
        "retainable_novelty": [idea_brief.user_idea] if idea_brief and idea_brief.user_idea else [],
        "claims_to_downgrade": [],
        "optimization_directions": [],
    }


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_novelty_checker_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 4: BaselineDiscoveryAgent（确定性工具编排）

**Files:**
- Create: `backend/app/agents/baseline_discovery_agent.py`
- Test: `backend/tests/test_baseline_discovery_agent.py`

**Interfaces:**
- Consumes: `GithubBaselineClient`、`PapersWithCodeClient`、`list[Paper]`。
- Produces: `BaselineDiscoveryAgent.arun(papers, task, run_id) -> list[BaselineCandidate]`。每候选 `code_source` ∈ {github_search, paperswithcode}，`reproducibility_score` 为初始启发式（README/license 推断放到 Task 5 RepositoryVerifier，这里只给 0.0 占位 + 启发式 risks）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_baseline_discovery_agent.py
import pytest

from app.agents.baseline_discovery_agent import BaselineDiscoveryAgent
from app.schemas.paper import Paper


class FakeGithub:
    def __init__(self, repos):
        self._repos = repos

    async def search_repos(self, query, limit=5):
        return self._repos


class FakePwc:
    def __init__(self, items):
        self._items = items

    async def search(self, task, limit=5):
        return self._items


@pytest.mark.asyncio
async def test_discovery_builds_candidates_from_sources() -> None:
    github = FakeGithub([
        {"full_name": "a/seismic-cnn", "html_url": "https://github.com/a/seismic-cnn", "description": "CNN for seismic events",
         "stars": 12, "license": "MIT", "default_branch": "main", "pushed_at": "2024-01-01", "open_issues": 1},
    ])
    pwc = FakePwc([
        {"paper_title": "SeismicNet", "code_url": "https://github.com/x/seismicnet", "stars": 3, "task": "seismic"},
    ])
    agent = BaselineDiscoveryAgent(github, pwc)
    papers = [Paper(paper_id="p1", title="Seismic event classification with CNN", arxiv_id="2401.00001")]
    candidates = await agent.arun(papers, task="seismic event classification", run_id="run_x")

    urls = {c.code_url for c in candidates}
    assert "https://github.com/a/seismic-cnn" in urls
    assert "https://github.com/x/seismicnet" in urls
    by_url = {c.code_url: c for c in candidates}
    assert by_url["https://github.com/a/seismic-cnn"].code_source == "github_search"
    assert by_url["https://github.com/x/seismicnet"].code_source == "paperswithcode"
    assert all(c.verified_repo is False for c in candidates)
    assert all(c.reproduction_status == "pending" for c in candidates)


@pytest.mark.asyncio
async def test_discovery_dedups_and_degrades_on_empty() -> None:
    agent = BaselineDiscoveryAgent(FakeGithub([]), FakePwc([]))
    papers = [Paper(paper_id="p1", title="Some method")]
    candidates = await agent.arun(papers, task="x", run_id="r")
    assert candidates == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_discovery_agent.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/baseline_discovery_agent.py
from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.tools.baseline_sources import GithubBaselineClient, PapersWithCodeClient


class BaselineDiscoveryAgent:
    """Deterministic baseline discovery: search GitHub + Papers with Code by
    paper titles/task, build BaselineCandidate list with initial heuristics.

    No LLM call here — pure tool orchestration. RepositoryVerifier (Task 5)
    deepens reproducibility_score/risks per candidate.
    """

    def __init__(self, github: GithubBaselineClient, pwc: PapersWithCodeClient) -> None:
        self.github = github
        self.pwc = pwc

    async def arun(self, papers: list[Paper], task: str, *, run_id: str) -> list[BaselineCandidate]:
        candidates: list[BaselineCandidate] = []
        seen_urls: set[str] = set()

        for paper in papers[:5]:
            query = _search_query(paper)
            for repo in await self.github.search_repos(query, limit=3):
                url = repo.get("html_url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(_candidate_from_github(paper, repo, task))

        for item in await self.pwc.search(task, limit=5):
            url = item.get("code_url") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(_candidate_from_pwc(item, task))

        return candidates[:15]


def _search_query(paper: Paper) -> str:
    base = paper.title or paper.arxiv_id or ""
    # strip punctuation, keep compact for GitHub search
    return " ".join(base.split())[:120] + " seismic"


def _candidate_from_github(paper: Paper, repo: dict, task: str) -> BaselineCandidate:
    return BaselineCandidate(
        baseline_id=f"baseline_{abs(hash((paper.paper_id, repo.get('full_name', '')))) % 10**8:08d}",
        paper_id=paper.paper_id,
        paper_title=paper.title,
        paper_doi=paper.doi,
        paper_url=paper.source_url,
        code_url=repo.get("html_url"),
        code_source="github_search",
        task_match=task,
        input_type="waveform",
        license=repo.get("license"),
        risks=_github_risks(repo),
    )


def _candidate_from_pwc(item: dict, task: str) -> BaselineCandidate:
    return BaselineCandidate(
        baseline_id=f"baseline_{abs(hash(('pwc', item.get('code_url', '')))) % 10**8:08d}",
        paper_id="",
        paper_title=item.get("paper_title") or "",
        code_url=item.get("code_url"),
        code_source="paperswithcode",
        task_match=task,
        input_type="unknown",
        risks=[],
    )


def _github_risks(repo: dict) -> list[str]:
    risks: list[str] = []
    if not repo.get("license"):
        risks.append("no license detected — reuse may be restricted")
    if repo.get("open_issues", 0) > 20:
        risks.append(f"high open issue count ({repo['open_issues']}) may indicate instability")
    if repo.get("stars", 0) < 3:
        risks.append("low star count — maturity/reproducibility uncertain")
    return risks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_discovery_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 5: RepositoryVerifierAgent（LCEL + GitHub 工具）

**Files:**
- Create: `backend/app/agents/repository_verifier_agent.py`
- Test: `backend/tests/test_repository_verifier_agent.py`

**Interfaces:**
- Consumes: `LLMClient`、`GithubBaselineClient`、`BaselineCandidate`。
- Produces: `RepositoryVerifierAgent.arun(candidate, run_id) -> BaselineCandidate`（更新 `verified_repo`/`reproduction_status`/`reproducibility_score`/`risks`/`run_command`/`license`）。LLM 判断 repo 是否匹配论文 + 推断 run_command + risk 理由；fallback 用确定性启发式（README+requirements+license 存在性）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_repository_verifier_agent.py
import pytest

from app.agents.repository_verifier_agent import RepositoryVerifierAgent, SYSTEM_PROMPT
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
    def __init__(self, *, metadata, file_tree, readme="README", commit="abc123"):
        self._meta = metadata
        self._tree = file_tree
        self._readme = readme
        self._commit = commit

    async def repo_metadata(self, repo_url):
        return self._meta

    async def repo_file_tree(self, repo_url):
        return self._tree

    async def repo_readme(self, repo_url):
        return self._readme

    async def latest_commit(self, repo_url):
        return self._commit


def _candidate() -> BaselineCandidate:
    return BaselineCandidate(
        baseline_id="b1", paper_id="p1", paper_title="Seismic CNN",
        code_url="https://github.com/a/seismic-cnn", code_source="github_search",
        task_match="seismic event classification", input_type="waveform",
    )


@pytest.mark.asyncio
async def test_verifier_updates_candidate_from_llm() -> None:
    llm = FakeLLM({
        "matches_paper": True, "reproducibility_score": 0.82, "reproduction_status": "verified",
        "run_command": "python train.py", "risks": ["deps pinned loosely"], "reason": "README + requirements present",
    })
    github = FakeGithub(metadata={"license": "MIT", "stars": 20}, file_tree=["README.md", "requirements.txt", "train.py"])
    agent = RepositoryVerifierAgent(llm, github)
    out = await agent.arun(_candidate(), run_id="run_x")
    assert out.verified_repo is True
    assert out.reproduction_status == "verified"
    assert out.reproducibility_score == 0.82
    assert out.run_command == "python train.py"
    assert llm.requests[0].agent == "repo_verifier"
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_verifier_falls_back_to_heuristic_on_bad_llm() -> None:
    github = FakeGithub(metadata={"license": "MIT", "stars": 20}, file_tree=["README.md", "requirements.txt"])
    agent = RepositoryVerifierAgent(FakeLLM("garbage"), github)
    out = await agent.arun(_candidate(), run_id="run_x")
    assert out.verified_repo is True
    assert 0.0 < out.reproducibility_score <= 1.0
    assert out.reproduction_status in {"verified", "suspicious"}


@pytest.mark.asyncio
async def test_verifier_marks_suspicious_when_missing_requirements() -> None:
    github = FakeGithub(metadata={"license": None, "stars": 1}, file_tree=["README.md"])
    agent = RepositoryVerifierAgent(FakeLLM(None), github)
    out = await agent.arun(_candidate(), run_id="run_x")
    assert out.verified_repo is False or out.reproduction_status == "suspicious"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_repository_verifier_agent.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/repository_verifier_agent.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.baseline import BaselineCandidate
from app.tools.baseline_sources import GithubBaselineClient

SYSTEM_PROMPT = """You are the Repository Verifier for TrustSci-Agent v3.
Given a baseline candidate (paper title + repo URL) and the repo's metadata, README excerpt, file tree, and latest commit, judge whether the repo matches the paper and how reproducible it is.
Return JSON only with keys:
- matches_paper: bool
- reproducibility_score: float in [0,1]
- reproduction_status: one of "verified", "suspicious", "failed"
- run_command: string or null (best-guess run command from README, e.g. "python train.py --config config.yaml")
- risks: list of strings
- reason: one sentence
Do not invent files or commands not suggested by the README/file tree."""

USER_TEMPLATE = """Paper title: {paper_title}
Repo URL: {code_url}
Repo metadata: {metadata}
File tree: {file_tree}
Latest commit: {commit}
README excerpt: {readme}

Judge repo match and reproducibility."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])


class RepoVerdictParser(Runnable):
    def __init__(self, fallback: dict) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> dict:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)


class RepositoryVerifierAgent:
    def __init__(self, llm: LLMClient, github: GithubBaselineClient) -> None:
        self.llm = llm
        self.github = github

    async def arun(self, candidate: BaselineCandidate, *, run_id: str) -> BaselineCandidate:
        metadata = await self.github.repo_metadata(candidate.code_url or "") or {}
        file_tree = await self.github.repo_file_tree(candidate.code_url or "") or []
        readme = (await self.github.repo_readme(candidate.code_url or "") or "")[:1500]
        commit = await self.github.latest_commit(candidate.code_url or "")
        fallback = _heuristic_verdict(candidate, metadata, file_tree, commit)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run_id, agent="repo_verifier")
            | RepoVerdictParser(fallback=fallback)
        )
        verdict = await chain.ainvoke(_prompt_vars(candidate, metadata, file_tree, readme, commit))
        return _apply(candidate, verdict, metadata)


def _prompt_vars(candidate: BaselineCandidate, metadata: dict, file_tree: list[str], readme: str, commit: str | None) -> dict:
    import json
    return {
        "paper_title": candidate.paper_title,
        "code_url": candidate.code_url or "",
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "file_tree": ", ".join(file_tree) if file_tree else "(empty)",
        "commit": commit or "unknown",
        "readme": readme or "(no README)",
    }


def _normalize(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback
    status = str(content.get("reproduction_status", fallback["reproduction_status"]))
    if status not in {"verified", "suspicious", "failed"}:
        status = fallback["reproduction_status"]
    return {
        "matches_paper": bool(content.get("matches_paper", fallback["matches_paper"])),
        "reproducibility_score": _score(content.get("reproducibility_score", fallback["reproducibility_score"])),
        "reproduction_status": status,
        "run_command": _opt_str(content.get("run_command")),
        "risks": _string_list(content.get("risks")) or fallback["risks"],
        "reason": _opt_str(content.get("reason")) or fallback["reason"],
    }


def _heuristic_verdict(candidate: BaselineCandidate, metadata: dict, file_tree: list[str], commit: str | None) -> dict:
    tree_lower = {f.lower() for f in file_tree}
    has_readme = any("readme" in f for f in tree_lower)
    has_reqs = any("requirements" in f or "environment.yml" in f or "setup.py" in f or "pyproject.toml" in f for f in tree_lower)
    has_license = bool(metadata.get("license"))
    score = 0.3 + (0.2 if has_readme else 0) + (0.2 if has_reqs else 0) + (0.15 if has_license else 0) + (0.15 if commit else 0)
    status = "verified" if (has_readme and has_reqs and score >= 0.7) else ("suspicious" if score >= 0.4 else "failed")
    risks = []
    if not has_reqs:
        risks.append("no requirements/environment file — dependency versions unclear")
    if not has_license:
        risks.append("no license — reuse restricted")
    if not has_readme:
        risks.append("no README — run instructions unclear")
    return {
        "matches_paper": True,
        "reproducibility_score": round(min(1.0, score), 2),
        "reproduction_status": status,
        "run_command": None,
        "risks": risks,
        "reason": "Heuristic verdict from README/requirements/license/commit presence.",
    }


def _apply(candidate: BaselineCandidate, verdict: dict, metadata: dict) -> BaselineCandidate:
    updated = candidate.model_copy(deep=True)
    updated.verified_repo = bool(verdict["matches_paper"]) and verdict["reproduction_status"] == "verified"
    updated.reproduction_status = verdict["reproduction_status"]
    updated.reproducibility_score = verdict["reproducibility_score"]
    updated.run_command = verdict["run_command"]
    risks = list(candidate.risks)
    for r in verdict["risks"]:
        if r not in risks:
            risks.append(r)
    updated.risks = risks
    if metadata.get("license") and not updated.license:
        updated.license = metadata.get("license")
    return updated


def _score(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_repository_verifier_agent.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 6: API 端点 discover + verify-repo

**Files:**
- Modify: `backend/app/api/routes_runs.py`
- Test: `backend/tests/test_baselines_api.py`

**Interfaces:**
- Produces: `POST /api/runs/{run_id}/baselines/discover`（跑 NoveltyChecker[若 idea_brief] + BaselineDiscovery，写 `run.novelty_report` + `run.baseline_candidates`，返回 run）；`POST /api/runs/{run_id}/baselines/{baseline_id}/verify-repo`（对指定候选跑 RepositoryVerifier，更新并返回 run）。
- Consumes: `GithubBaselineClient`、`PapersWithCodeClient`、`NoveltyCheckerAgent`、`BaselineDiscoveryAgent`、`RepositoryVerifierAgent`（通过 `build_workflow(get_settings())` 复用其装配，或直接 `get_settings()` 构造）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_baselines_api.py
from app.main import app
from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store
from fastapi.testclient import TestClient

client = TestClient(app)


def _seed_run() -> ResearchRun:
    run = ResearchRun(domain="seismic_event_classification", question="fuse waveform with spectrogram", constraints=ResearchConstraints(), mode="idea_refinement")
    run.papers = [Paper(paper_id="p1", title="Seismic event classification with CNN", arxiv_id="2401.00001")]
    return run_store.create(run)


def test_discover_endpoint_populates_candidates(monkeypatch) -> None:
    run = _seed_run()
    from app.api import routes_runs
    # The route calls the module-level helper; patch it so no real GitHub/PwC HTTP fires.
    monkeypatch.setattr(routes_runs, "_discover_baselines_for_run", _discover_stub)

    resp = client.post(f"/api/runs/{run.run_id}/baselines/discover")
    assert resp.status_code == 200
    body = resp.json()
    assert body["baseline_candidates"]
    assert body["baseline_candidates"][0]["code_url"] == "https://github.com/a/b"
    assert body["novelty_report"] is not None
    run_store.delete(run.run_id)


async def _discover_stub(run):
    from app.schemas.baseline import BaselineCandidate
    run.baseline_candidates = [BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="Seismic CNN", code_url="https://github.com/a/b", code_source="github_search", task_match="seismic", input_type="waveform")]
    run.novelty_report = {"similar_work": [], "has_public_code": False, "overlap_points": [], "retainable_novelty": [], "claims_to_downgrade": [], "optimization_directions": []}
    return run


def test_verify_repo_endpoint_updates_candidate(monkeypatch) -> None:
    run = _seed_run()
    run.baseline_candidates = [BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="Seismic CNN", code_url="https://github.com/a/b", code_source="github_search", task_match="seismic", input_type="waveform")]
    run_store.save(run)

    async def fake_verify(candidate, *, run_id):
        candidate.verified_repo = True
        candidate.reproduction_status = "verified"
        candidate.reproducibility_score = 0.8
        return candidate

    from app.api import routes_runs
    monkeypatch.setattr(routes_runs, "_verify_repo_for_candidate", fake_verify)

    resp = client.post(f"/api/runs/{run.run_id}/baselines/b1/verify-repo")
    assert resp.status_code == 200
    cand = next(c for c in resp.json()["baseline_candidates"] if c["baseline_id"] == "b1")
    assert cand["verified_repo"] is True
    assert cand["reproducibility_score"] == 0.8
    run_store.delete(run.run_id)
```

> Note: this test monkeypatches module-level helper functions `_discover_baselines_for_run` and `_verify_repo_for_candidate` in `routes_runs`. The route handlers must call these helpers (not inline the logic) so they are patchable. `run_store.delete` already exists for cleanup.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baselines_api.py -v`
Expected: FAIL — routes do not exist yet (`404` / attribute error on helpers).

- [ ] **Step 3: Add the routes + helpers**

In `backend/app/api/routes_runs.py`, add imports near the top:

```python
from app.agents.baseline_discovery_agent import BaselineDiscoveryAgent
from app.agents.novelty_checker_agent import NoveltyCheckerAgent
from app.agents.repository_verifier_agent import RepositoryVerifierAgent
from app.schemas.baseline import BaselineCandidate
from app.tools.baseline_sources import GithubBaselineClient, PapersWithCodeClient
```

Add a small module-level component holder (lazily built from settings) after the `router = APIRouter(...)` line:

```python
class _BaselineComponents:
    def __init__(self, settings):
        self.github_client = GithubBaselineClient(settings.github_token)
        self.pwc_client = PapersWithCodeClient()
        self.novelty_checker = NoveltyCheckerAgent(_build_llm(settings))
        self.baseline_discovery = BaselineDiscoveryAgent(self.github_client, self.pwc_client)
        self.repo_verifier = RepositoryVerifierAgent(_build_llm(settings), self.github_client)


def _build_llm(settings):
    from app.llm.registry import build_llm_client
    return build_llm_client(settings)


def _baseline_components() -> _BaselineComponents:
    # cache per-process; rebuilt only if settings change is not needed for tests
    # because tests monkeypatch the helper functions, not the components.
    global _BASELINE_CACHE
    if _BASELINE_CACHE is None:
        _BASELINE_CACHE = _BaselineComponents(get_settings())
    return _BASELINE_CACHE


_BASELINE_CACHE = None
```

Add the two helper functions (module-level, so tests can monkeypatch them):

```python
async def _discover_baselines_for_run(run: ResearchRun) -> ResearchRun:
    comps = _baseline_components()
    task = "seismic event classification" if run.domain == "seismic_event_classification" else run.domain
    if run.idea_brief is not None or any(p.code_url for p in run.papers):
        run.novelty_report = await comps.novelty_checker.arun(run.papers, run.idea_brief, run_id=run.run_id)
    run.baseline_candidates = await comps.baseline_discovery.arun(run.papers, task, run_id=run.run_id)
    _write_workspace(run)
    return run_store.save(run)


async def _verify_repo_for_candidate(candidate: BaselineCandidate, *, run_id: str) -> BaselineCandidate:
    comps = _baseline_components()
    return await comps.repo_verifier.arun(candidate, run_id=run_id)
```

Add the two routes (place them with the other run routes, before the helper section at the bottom):

```python
@router.post("/{run_id}/baselines/discover", response_model=ResearchRun)
async def discover_baselines(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    if not run.papers:
        raise HTTPException(status_code=400, detail="run has no papers yet; run literature search first")
    return await _discover_baselines_for_run(run)


@router.post("/{run_id}/baselines/{baseline_id}/verify-repo", response_model=ResearchRun)
async def verify_baseline_repo(run_id: str, baseline_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    candidate = next((c for c in run.baseline_candidates if c.baseline_id == baseline_id), None)
    if candidate is None:
        raise HTTPException(status_code=404, detail="baseline candidate not found")
    updated = await _verify_repo_for_candidate(candidate, run_id=run.run_id)
    idx = run.baseline_candidates.index(candidate)
    run.baseline_candidates[idx] = updated
    _write_workspace(run)
    return run_store.save(run)
```

> Note on `run_store.delete` used in tests: it already exists in `backend/app/storage/in_memory.py` (`RunStore.delete(run_id)`), so no store change is needed for the tests to clean up.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baselines_api.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run full suite to confirm no regression**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q`
Expected: all green.

- [ ] **Step 6: Skip commit (local-only).**

---

### Task 7: 前端 BaselineBoard + SeismicOverviewPanel + 接入 seismic 工作区

**Files:**
- Create: `frontend/components/workbench/BaselineBoard.tsx`
- Create: `frontend/components/workbench/SeismicOverviewPanel.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Test: manual (no frontend test infra).

**Interfaces:**
- Produces: `BaselineBoard({run, busy, onDiscover, onVerify})` 列出 `run.baseline_candidates`，每个候选显示 paper_title / code_url(link) / code_source / reproducibility_score / verified_repo / reproduction_status / risks + "Verify Repo" 按钮；顶部 "Discover Baselines" 按钮。`SeismicOverviewPanel({run})` 显示 `run.mode` / `run.intent` / `run.idea_brief` / `run.seismic_data_profile`。`discoverBaselines(runId)` / `verifyBaselineRepo(runId, baselineId)` API 函数。`ResearchRun` 类型加 `baseline_candidates` / `novelty_report` / `paper.code_url`。

- [ ] **Step 1: Add API functions + types to `frontend/lib/api.ts`**

In the `ResearchRun` type, add to each paper object a `code_url?: string;` field, and add two top-level fields after `seismic_data_profile?` (which S1 already added):

```typescript
  baseline_candidates?: Array<{
    baseline_id: string;
    paper_id: string;
    paper_title: string;
    paper_doi?: string;
    paper_url?: string;
    code_url?: string;
    code_source: string;
    task_match: string;
    input_type: string;
    labels_supported: string[];
    dataset_used?: string;
    metrics_reported: string[];
    reproducibility_score: number;
    license?: string;
    run_command?: string;
    verified_repo: boolean;
    reproduction_status: string;
    risks: string[];
  }>;
  novelty_report?: {
    similar_work: Array<Record<string, string>>;
    has_public_code: boolean;
    overlap_points: string[];
    retainable_novelty: string[];
    claims_to_downgrade: string[];
    optimization_directions: string[];
  };
```

Add `code_url?: string;` inside the `papers` array item type (after `pdf_url?: string;`).

Add the two API functions (after `selectHypothesis`):

```typescript
export async function discoverBaselines(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/baselines/discover`, { method: "POST" });
}

export async function verifyBaselineRepo(runId: string, baselineId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/baselines/${baselineId}/verify-repo`, { method: "POST" });
}
```

- [ ] **Step 2: Create `frontend/components/workbench/SeismicOverviewPanel.tsx`**

```tsx
import { Activity, Waves } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function SeismicOverviewPanel({ run }: { run: ResearchRun | null }) {
  const intent = run?.intent;
  const idea = run?.idea_brief;
  const profile = run?.seismic_data_profile;
  return (
    <section className="panel span-4">
      <div className="panel-heading">
        <h2><Waves size={16} /> Seismic Overview</h2>
        <span className="badge"><Activity size={13} />{run?.mode || "discovery"}</span>
      </div>
      {intent && (
        <div className="item">
          <div className="item-title">Intent</div>
          <div className="muted">inferred={String(intent.mode)} · confidence={String(intent.confidence)}</div>
          <div className="muted">{intent.reason}</div>
        </div>
      )}
      {idea && (
        <div className="item">
          <div className="item-title">User Idea</div>
          <div className="muted">{idea.user_idea}</div>
          {idea.target_labels?.length ? <div className="muted">labels: {idea.target_labels.join(", ")}</div> : null}
          {idea.unknowns?.length ? <div className="muted">unknowns: {idea.unknowns.join("; ")}</div> : null}
        </div>
      )}
      {profile && (
        <div className="item">
          <div className="item-title">Seismic Data Profile</div>
          <div className="muted">{profile.num_events} events · {Object.entries(profile.labels).map(([k, v]) => `${k}:${v}`).join(", ")}</div>
          <div className="muted">channels: {profile.channels.join("/")}</div>
          {profile.risks?.length ? <div className="muted">risks: {profile.risks.join("; ")}</div> : null}
        </div>
      )}
      {!intent && !idea && !profile && <p className="muted">等待 intent router / idea intake / seismic profile 完成。</p>}
    </section>
  );
}
```

- [ ] **Step 3: Create `frontend/components/workbench/BaselineBoard.tsx`**

```tsx
import { ExternalLink, GitBranch, Search } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function BaselineBoard({
  run,
  busy,
  onDiscover,
  onVerify
}: {
  run: ResearchRun | null;
  busy: boolean;
  onDiscover: () => void;
  onVerify: (baselineId: string) => void;
}) {
  const candidates = run?.baseline_candidates || [];
  return (
    <section className="panel span-8">
      <div className="panel-heading">
        <h2><GitBranch size={16} /> Baseline Board</h2>
        <div className="actions">
          <span className="badge">{candidates.length} candidates</span>
          <button className="secondary" onClick={onDiscover} disabled={busy}>
            <Search size={14} /> 发现 Baseline
          </button>
        </div>
      </div>
      <div className="list">
        {candidates.map((c) => (
          <article className="item" key={c.baseline_id}>
            <div className="item-title">{c.paper_title || "(no paper)"}</div>
            <div className="item-meta">
              {c.code_source} · {c.input_type}
              {c.license ? ` · ${c.license}` : ""}
            </div>
            {c.code_url && (
              <a className="secondary link-button" href={c.code_url} target="_blank" rel="noreferrer">
                <ExternalLink size={14} /> {c.code_url}
              </a>
            )}
            <div className="item-actions">
              <span className={`badge ${c.verified_repo ? "good" : c.reproduction_status === "suspicious" ? "warn" : ""}`}>
                {c.reproduction_status}
              </span>
              <span className="badge">score {c.reproducibility_score.toFixed(2)}</span>
              {c.run_command && <span className="badge">{c.run_command}</span>}
              <button className="secondary" onClick={() => onVerify(c.baseline_id)} disabled={busy}>
                Verify Repo
              </button>
            </div>
            {c.risks.length > 0 && <p className="muted">risks: {c.risks.join("; ")}</p>}
          </article>
        ))}
        {!candidates.length && <p className="muted">点击「发现 Baseline」从 GitHub / Papers with Code 检索带代码的 baseline。</p>}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Wire into `frontend/components/workbench/Workbench.tsx`**

Add imports (with the other panel imports near the top):

```tsx
import { BaselineBoard } from "./BaselineBoard";
import { SeismicOverviewPanel } from "./SeismicOverviewPanel";
import { discoverBaselines, verifyBaselineRepo } from "../../lib/api";
```

Add a `baselineBusy` state (near the other `*Busy` states):

```tsx
  const [baselineBusy, setBaselineBusy] = useState(false);
```

Add handlers (near `handleSelectHypothesis` / other handlers):

```tsx
  async function handleDiscoverBaselines() {
    if (!run) return;
    setBaselineBusy(true);
    setError("");
    try {
      const next = await discoverBaselines(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Baseline discovery failed");
    } finally {
      setBaselineBusy(false);
    }
  }

  async function handleVerifyBaseline(baselineId: string) {
    if (!run) return;
    setBaselineBusy(true);
    setError("");
    try {
      const next = await verifyBaselineRepo(run.run_id, baselineId);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Repo verification failed");
    } finally {
      setBaselineBusy(false);
    }
  }
```

Replace the empty seismic section (the line `{activeVersion === "seismic" ? (\n        <section className="content seismic-empty" aria-label="Seismic Expert workspace" />\n      ) : (`) with a real workspace:

```tsx
      {activeVersion === "seismic" ? (
        <section className="content">
          <div className="topbar">
            <div className="title-block">
              <h1>地震科研专家</h1>
              <p>{run?.question || draft.question}</p>
            </div>
            <div className="topbar-badges">
              <span className="badge">Seismic</span>
              <span className="badge">{run ? `${run.status} / ${run.current_stage}` : "待启动"}</span>
            </div>
          </div>
          <StatusStrip config={config} run={run} />
          <div className="grid">
            <SeismicOverviewPanel run={run} />
            <LiteratureBoard run={run} />
            <BaselineBoard
              run={run}
              busy={baselineBusy}
              onDiscover={handleDiscoverBaselines}
              onVerify={handleVerifyBaseline}
            />
            <WorkspacePanel run={run} />
          </div>
        </section>
      ) : (
```

Ensure `LiteratureBoard`, `StatusStrip`, and `WorkspacePanel` are already imported (they are — `LiteratureBoard` import needs adding if not present; check the existing import block and add `import { LiteratureBoard } from "./LiteratureBoard";` if missing).

- [ ] **Step 5: Manual verification (frontend is in dev/hot-reload mode)**

Open http://localhost:3000:
1. Choose **Seismic Expert** → 创意精修 → 启动 a seismic run. Wait for papers to appear.
2. The Seismic workspace now shows **Seismic Overview** (mode/intent/idea_brief/seismic profile), **Literature Board** (papers), **Baseline Board** (empty initially).
3. Click **发现 Baseline** → BaselineBoard fills with GitHub/PwC candidates (real API calls; may take a few seconds; failures degrade to empty).
4. Click **Verify Repo** on a candidate → reproducibility_score / reproduction_status / risks update.
5. Confirm Classic Workflow still renders and runs unchanged.

- [ ] **Step 6: Skip commit (local-only).**

---

## S2 验收（全量回归）

- [ ] **Step 7: Run the full backend test suite**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q
```

Expected: all green, including new tests `test_baseline_schemas`, `test_baseline_sources`, `test_novelty_checker_agent`, `test_baseline_discovery_agent`, `test_repository_verifier_agent`, `test_baselines_api`, plus S1 + v1/v2 regression.

- [ ] **Step 8: S2 acceptance criteria check** (vs `prd_v3_sprint.md` S2)

1. 地震问题检索真实论文 → LiteratureBoard 显示 ✓（现有 literature_search + S1）
2. 发现带 code baseline → BaselineBoard「发现 Baseline」从 GitHub/PwC 返回候选 ✓（Task 4 + 6）
3. repo 可信度评分 → RepositoryVerifier 输出 reproducibility_score/risks/status ✓（Task 5 + 6）
4. 未验证 repo 不进自动运行 → S2 只验证+报告，不执行任何外部代码（执行推迟 S4）✓
5. 前端 Baseline Board + Literature Board（地震）→ Task 7 ✓

## 已知 S2 局限（后续 Sprint 处理）

- baseline 实际 clone / 沙盒执行 / 隔离目录 / 命令白名单 → S4 Code Experiment Loop。
- baseline repo 缓存 → S7 Hardening（spec 已列）。
- NoveltyChecker 当前只在 discover 端点触发（有 idea_brief 时），不自动跑进 workflow。
- arXiv/PDF/作者主页爬取代码链接通道未做（弱价值），只做 GitHub search + PwC + 用户手动。
- BaselineDiscovery 是确定性启发式，不用 LLM；RepositoryVerifier 用 LLM 判断匹配/推断 run_command。
