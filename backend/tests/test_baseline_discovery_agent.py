import pytest

from app.agents.baseline_discovery_agent import (
    BaselineDiscoveryAgent,
    _search_query,
    _task_query,
)
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
    papers = [Paper(paper_id="p1", title="Seismic event classification with CNN", arxiv_id="2401.00001", baseline_eligible=True)]
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
    papers = [Paper(paper_id="p1", title="Some method", baseline_eligible=True)]
    candidates = await agent.arun(papers, task="x", run_id="r")
    assert candidates == []


def test_search_query_is_short() -> None:
    paper = Paper(
        paper_id="p",
        title="Seismic Event and Phase Detection Using Time-Frequency Representations",
    )
    query = _search_query(paper, "seismic event classification")
    tokens = query.split()
    assert len(tokens) <= 4, f"Expected at most 4 tokens, got {len(tokens)}: {query}"
    low_tokens = [t.lower() for t in tokens]
    assert "and" not in low_tokens, f"Stopword 'and' found in query: {query}"
    assert "using" not in low_tokens, f"Stopword 'using' found in query: {query}"


def test_task_query_drops_stopwords() -> None:
    # No stopwords present — should return as-is.
    assert _task_query("seismic event classification") == "seismic event classification"
    # "a" and "for" are stopwords — should be dropped.
    result = _task_query("a method for seismic classification")
    low_tokens = result.lower().split()
    assert "a" not in low_tokens, f"Stopword 'a' found in result: {result}"
    assert "for" not in low_tokens, f"Stopword 'for' found in result: {result}"
    assert "seismic" in low_tokens
    assert "classification" in low_tokens
