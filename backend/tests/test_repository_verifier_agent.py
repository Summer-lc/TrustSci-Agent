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
    github = FakeGithub(metadata={"license": "MIT", "stars": 20}, file_tree=["README.md", "requirements.txt", "model.py"])
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
