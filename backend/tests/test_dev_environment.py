from pathlib import Path

from scripts.check_dev_env import collect_status


ROOT = Path(__file__).resolve().parents[2]


def test_env_example_contains_every_runtime_key() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "QWEN_MODEL",
        "WORKFLOW_ENGINE", "DATA_DIR", "GITHUB_TOKEN", "NEXT_PUBLIC_API_BASE",
    ):
        assert f"{key}=" in text


def test_environment_check_never_returns_secret_values(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "secret-value")
    status = collect_status()
    assert "secret-value" not in repr(status)
    assert status["qwen_configured"] is True
    assert "python" in status
