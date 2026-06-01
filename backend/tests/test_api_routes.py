from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_system_health_and_config() -> None:
    health = client.get("/api/system/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    config = client.get("/api/system/config")
    assert config.status_code == 200
    assert "qwen_model" in config.json()
    assert "browser_worker_url" in config.json()
    assert "semantic_scholar_configured" in config.json()



def test_data_profiles_and_baseline() -> None:
    profiles = client.get("/api/data/profiles")
    assert profiles.status_code == 200
    assert any(item["name"] == "bundled_solid_electrolyte_candidates" for item in profiles.json())

    baseline = client.post("/api/data/baseline")
    assert baseline.status_code == 200
    assert baseline.json()["name"] == "solid_electrolyte_mean_baseline"


def test_run_detail_endpoints_before_execution() -> None:
    payload = {
        "domain": "energy_materials",
        "question": "Generate a test hypothesis.",
        "constraints": {"max_papers": 1, "enable_semantic_scholar": True},
    }
    created = client.post("/api/runs", json=payload)
    assert created.status_code == 200
    assert created.json()["constraints"]["enable_semantic_scholar"] is True
    run_id = created.json()["run_id"]

    assert client.get(f"/api/runs/{run_id}/papers").json() == []
    assert client.get(f"/api/runs/{run_id}/evidence").json() == []
    assert client.get(f"/api/runs/{run_id}/hypotheses").json() == []
    assert client.get(f"/api/runs/{run_id}/llm-calls").json() == []
    assert client.get(f"/api/runs/{run_id}/report").status_code == 404
