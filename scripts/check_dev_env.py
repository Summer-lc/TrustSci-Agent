from __future__ import annotations

import importlib.util
import os
import shutil
import sys

REQUIRED_MODULES = ("fastapi", "pydantic", "reportlab", "rapidfuzz", "langgraph", "numpy", "sklearn")


def collect_status() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "modules": {name: importlib.util.find_spec(name) is not None for name in REQUIRED_MODULES},
        "node_available": shutil.which("node") is not None,
        "npm_available": shutil.which("npm") is not None,
        "docker_available": shutil.which("docker") is not None,
        "workflow_engine": os.getenv("WORKFLOW_ENGINE", "classic"),
        "qwen_configured": bool(os.getenv("DASHSCOPE_API_KEY", "").strip()),
    }


def main() -> int:
    status = collect_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    modules = status["modules"]
    return 0 if isinstance(modules, dict) and all(modules.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
