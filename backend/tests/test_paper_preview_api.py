from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.browser import BrowserCaptureResult


client = TestClient(app)


def test_preview_uses_browser_worker_and_then_cache(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    trace_dir = data_dir / "browser_traces"
    trace_dir.mkdir(parents=True)
    calls = 0

    async def fake_capture(_self, payload):
        nonlocal calls
        calls += 1
        screenshot = trace_dir / "trace_1.png"
        screenshot.write_bytes(b"png")
        return BrowserCaptureResult(
            trace_id="trace_1",
            url=str(payload.url),
            domain="example.org",
            status_code=200,
            title="Paper",
            html_path=str(trace_dir / "trace_1.html"),
            screenshot_path=str(screenshot),
        )

    monkeypatch.setattr(
        "app.api.routes_browser.get_settings",
        lambda: SimpleNamespace(data_dir=data_dir, browser_worker_url="http://worker"),
    )
    monkeypatch.setattr(
        "app.api.routes_browser.BrowserWorkerClient.capture",
        fake_capture,
    )
    payload = {"paper_id": "p1", "source_url": "https://example.org/paper"}

    first = client.post("/api/browser/paper-preview", json=payload)
    second = client.post("/api/browser/paper-preview", json=payload)

    assert first.status_code == 200
    assert first.json()["kind"] == "web_snapshot"
    assert first.json()["screenshot_url"] == "/api/browser/artifacts/trace_1.png"
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert calls == 1


def test_preview_failure_returns_metadata_fallback(monkeypatch, tmp_path: Path) -> None:
    async def fake_capture(_self, _payload):
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr(
        "app.api.routes_browser.get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path, browser_worker_url="http://worker"),
    )
    monkeypatch.setattr(
        "app.api.routes_browser.BrowserWorkerClient.capture",
        fake_capture,
    )

    response = client.post(
        "/api/browser/paper-preview",
        json={"paper_id": "p2", "source_url": "https://example.org/no-pdf"},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "metadata_only"
    assert "browser unavailable" in response.json()["error_summary"]


def test_preview_challenge_returns_metadata_without_screenshot(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    trace_dir = data_dir / "browser_traces"
    trace_dir.mkdir(parents=True)

    async def fake_capture(_self, payload):
        screenshot = trace_dir / "challenge.png"
        screenshot.write_bytes(b"captcha")
        return BrowserCaptureResult(
            trace_id="trace_challenge",
            url=str(payload.url),
            domain="publisher.example",
            status_code=403,
            title="Just a moment...",
            html_path=str(trace_dir / "challenge.html"),
            screenshot_path=str(screenshot),
            blocked_reason="human_verification",
        )

    monkeypatch.setattr(
        "app.api.routes_browser.get_settings",
        lambda: SimpleNamespace(data_dir=data_dir, browser_worker_url="http://worker"),
    )
    monkeypatch.setattr(
        "app.api.routes_browser.BrowserWorkerClient.capture",
        fake_capture,
    )

    response = client.post(
        "/api/browser/paper-preview",
        json={"paper_id": "p3", "source_url": "https://publisher.example/paper"},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "metadata_only"
    assert response.json()["screenshot_url"] is None
    assert "人机验证" in response.json()["error_summary"]


def test_cached_challenge_snapshot_is_replaced_with_metadata(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    preview_dir = data_dir / "browser_previews"
    preview_dir.mkdir(parents=True)
    source_url = "https://publisher.example/cached-challenge"
    payload = {"paper_id": "p4", "source_url": source_url}

    import hashlib

    cache_key = hashlib.sha256(f"p4\n{source_url}".encode("utf-8")).hexdigest()
    (preview_dir / f"{cache_key}.json").write_text(
        '{"paper_id":"p4","source_url":"https://publisher.example/cached-challenge",'
        '"kind":"web_snapshot","title":"Just a moment...",'
        '"screenshot_url":"/api/browser/artifacts/challenge.png",'
        '"original_url":"https://publisher.example/cached-challenge","cached":false}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.api.routes_browser.get_settings",
        lambda: SimpleNamespace(data_dir=data_dir, browser_worker_url="http://worker"),
    )

    response = client.post("/api/browser/paper-preview", json=payload)

    assert response.status_code == 200
    assert response.json()["kind"] == "metadata_only"
    assert response.json()["screenshot_url"] is None
    assert response.json()["cached"] is True
    assert "人机验证" in response.json()["error_summary"]


def test_browser_artifact_route_rejects_path_traversal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.api.routes_browser.get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path, browser_worker_url="http://worker"),
    )

    response = client.get("/api/browser/artifacts/not-an-image.txt")

    assert response.status_code == 404
