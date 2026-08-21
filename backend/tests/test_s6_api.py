from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_attach_assistance_and_get_summary() -> None:
    created = client.post("/api/runs", json={"question": "Analyze", "mode": "experiment_assistance"}).json()
    payload = {"objective": "Compare classifiers", "method_summary": "FFT model",
               "baseline_metrics": [{"name": "accuracy", "value": 0.8}],
               "method_metrics": [{"name": "accuracy", "value": 0.86}]}
    attached = client.post(f"/api/runs/{created['run_id']}/experiment-assistance", json=payload)
    assert attached.status_code == 200
    summary = client.get(f"/api/runs/{created['run_id']}/v3-summary")
    assert summary.status_code == 200
    assert summary.json()["mode"] == "experiment_assistance"


def test_attach_assistance_rejects_wrong_mode() -> None:
    created = client.post("/api/runs", json={"question": "Analyze", "mode": "discovery"}).json()
    response = client.post(f"/api/runs/{created['run_id']}/experiment-assistance",
                           json={"objective": "Compare", "method_summary": "Method", "logs": ["done"]})
    assert response.status_code == 409
