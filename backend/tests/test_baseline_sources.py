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
