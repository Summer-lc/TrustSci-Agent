from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_attach_manual_baseline_before_start() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={
            "strategy": "manual_upload",
            "manual": {
                "name": "User baseline",
                "description": "Prior RF baseline.",
                "metrics": [{"name": "accuracy", "value": 0.8}],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_strategy"] == "manual_upload"
    assert body["manual_baseline"]["manual"]["name"] == "User baseline"


def test_attach_ai_generated_baseline_before_start() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={"strategy": "ai_generated"},
    )
    assert response.status_code == 200
    assert response.json()["baseline_strategy"] == "ai_generated"


def test_attach_baseline_404() -> None:
    response = client.post("/api/runs/run_missing/baseline-intake", json={"strategy": "none"})
    assert response.status_code == 404


def test_attach_baseline_after_start_returns_409() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    started = client.post(f"/api/runs/{created['run_id']}/start")
    assert started.status_code == 200
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={"strategy": "none"},
    )
    assert response.status_code == 409


def test_manual_baseline_validation_422() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={"strategy": "manual_upload"},
    )
    assert response.status_code == 422
