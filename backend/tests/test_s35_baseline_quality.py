# backend/tests/test_s35_baseline_quality.py
import pytest

from app.agents.baseline_discovery_agent import BaselineDiscoveryAgent, _initial_priority_score
from app.agents.repository_verifier_agent import RepositoryVerifierAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper


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
    assert out.matches_task_domain is True
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
async def test_verifier_rejects_generic_model_repo_when_domain_misses() -> None:
    llm = FakeLLM({"matches_paper": True, "reproducibility_score": 0.8, "reproduction_status": "verified",
                   "run_command": "python train.py", "risks": [], "reason": "generic model",
                   "repo_type": "model_code", "is_model_baseline": True,
                   "matches_paper_method": True, "matches_task_domain": False})
    gh = FakeGithub(metadata={"license": "MIT", "stars": 10, "description": "Gaussian RBF neural network"},
                    file_tree=["train.py", "models/", "requirements.txt"],
                    readme="Generic Gaussian RBF neural network implementation.")
    cand = _cand(paper_title="Learning Active Subspaces with Gaussian RBFNN",
                 code_url="https://github.com/dannyzx/Gaussian-RBFNN")
    out = await RepositoryVerifierAgent(llm, gh).arun(cand, run_id="r")
    assert out.repo_type == "model_code"
    assert out.is_model_baseline is True
    assert out.matches_task_domain is False
    assert out.verified_repo is False
    assert "not seismic" in (out.baseline_rejection_reason or "")


@pytest.mark.asyncio
async def test_verifier_fallback_rejects_dataset_repo_by_heuristic() -> None:
    # No useful LLM output -> heuristic. Repo name "seismic-dataset" + file_tree data/ -> dataset_only.
    gh = FakeGithub(metadata={"license": None, "stars": 1}, file_tree=["data/", "README.md"])
    out = await RepositoryVerifierAgent(FakeLLM(None), gh).arun(
        _cand(code_url="https://github.com/a/seismic-dataset"), run_id="r")
    assert out.repo_type in {"dataset_only", "unknown"}
    assert out.is_model_baseline is False


# ---- Discovery-agent tests (Task 4) ----

class FakeGithubForDiscovery:
    async def search_repos(self, query, limit=5):
        return [{"full_name": "a/seismic-cnn", "html_url": "https://github.com/a/seismic-cnn", "description": "CNN model",
                 "stars": 12, "license": "MIT", "default_branch": "main", "pushed_at": "", "open_issues": 0}]


class FakePwcForDiscovery:
    async def search(self, task, limit=5): return []


@pytest.mark.asyncio
async def test_discovery_only_uses_eligible_papers() -> None:
    agent = BaselineDiscoveryAgent(FakeGithubForDiscovery(), FakePwcForDiscovery())
    papers = [
        Paper(paper_id="p1", title="Seismic CNN model", baseline_eligible=True, code_url="https://github.com/a/model"),
        Paper(paper_id="p2", title="STEAD dataset", baseline_eligible=False, code_url="https://github.com/a/dataset"),
    ]
    cands = await agent.arun(papers, task="seismic event classification", run_id="r")
    urls = {c.code_url for c in cands}
    assert "https://github.com/a/model" in urls  # eligible paper's code included
    assert "https://github.com/a/dataset" not in urls  # non-eligible paper's code excluded
    by_url = {c.code_url: c for c in cands}
    assert by_url["https://github.com/a/model"].verified_repo is False
    assert by_url["https://github.com/a/model"].reproduction_status == "pending"


def test_initial_priority_score_penalizes_dataset_name() -> None:
    c = BaselineCandidate(baseline_id="b", paper_id="p", paper_title="t",
                          code_url="https://github.com/a/seismic-dataset", code_source="github_search",
                          task_match="seismic", input_type="waveform", stars=5)
    score = _initial_priority_score(c, paper_role="method_model")
    assert score < 0.5  # dataset-named repo penalized


@pytest.mark.asyncio
async def test_verifier_requires_minimum_reproducibility_score() -> None:
    llm = FakeLLM({"matches_paper": True, "reproducibility_score": 0.4, "reproduction_status": "verified",
                   "run_command": "python train.py", "risks": [], "reason": "weak",
                   "repo_type": "model_code", "is_model_baseline": True,
                   "matches_paper_method": True, "matches_task_domain": True})
    gh = FakeGithub(metadata={"license": "MIT", "stars": 10}, file_tree=["train.py", "models/", "requirements.txt"])
    out = await RepositoryVerifierAgent(llm, gh).arun(_cand(), run_id="r")
    assert out.verified_repo is False
    assert out.reproduction_status == "suspicious"
    assert "reproducibility_score below" in (out.baseline_rejection_reason or "")
