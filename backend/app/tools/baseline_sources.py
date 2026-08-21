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
            async with httpx.AsyncClient(timeout=30, transport=self.transport, follow_redirects=True) as client:
                resp = await client.get(url, params=params, headers=self._headers(headers))
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return None

    async def _get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport, follow_redirects=True) as client:
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
            async with httpx.AsyncClient(timeout=30, transport=self.transport, follow_redirects=True) as client:
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
