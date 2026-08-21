# backend/app/tools/sandbox_executor.py
"""Controlled subprocess sandbox for the S4 Code Experiment Loop.

Copies the fixed harness (data/baseline/train/tests/manifest) + the LLM-written
model.py into an isolated per-run directory and runs only whitelisted scripts
(`python tests.py` / `python train.py`) with a timeout. Same backend container
(no sidecar); network isolation is policy-level (no pip, deps pre-installed) —
true OS-level isolation is deferred to S7 hardening."""
from __future__ import annotations

import shutil
import subprocess
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app.tools.code_safety import validate_generated_model

_HARNESS_FILES = ("data.py", "baseline.py", "train.py", "tests.py", "harness_manifest.json")
_ARTIFACTS = ("metrics.json", "comparison.json", "tests_failed.flag")


@dataclass
class SandboxRunResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


class SandboxExecutor:
    ALLOWED = ("tests.py", "train.py")

    def __init__(self, harness_dir: Path, timeout: int = 120) -> None:
        self.harness_dir = Path(harness_dir)
        self.timeout = timeout

    def prepare(self, sandbox_dir: Path, model_py_source: str) -> None:
        validate_generated_model(model_py_source)
        sandbox_dir = Path(sandbox_dir)
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.clear_artifacts(sandbox_dir)
        for fn in _HARNESS_FILES:
            src = self.harness_dir / fn
            if src.exists():
                shutil.copy(src, sandbox_dir / fn)
        (sandbox_dir / "model.py").write_text(model_py_source, encoding="utf-8")

    def clear_artifacts(self, sandbox_dir: Path) -> None:
        sandbox_dir = Path(sandbox_dir)
        if not sandbox_dir.exists():
            return
        for name in _ARTIFACTS:
            path = sandbox_dir / name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        for cache_dir in sandbox_dir.glob("__pycache__"):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)

    def run(self, sandbox_dir: Path, script: str) -> SandboxRunResult:
        if script not in self.ALLOWED:
            raise ValueError(f"disallowed script: {script!r} (whitelist={self.ALLOWED})")
        sandbox_dir = Path(sandbox_dir)
        try:
            bootstrap = f"import runpy,sys;sys.path.insert(0,'.');runpy.run_path({script!r},run_name='__main__')"
            safe_env = {key: value for key, value in os.environ.items()
                        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONIOENCODING"}}
            safe_env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.run(
                [sys.executable, "-I", "-c", bootstrap],
                cwd=str(sandbox_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=safe_env,
            )
            return SandboxRunResult(proc.returncode, proc.stdout, proc.stderr, False)
        except subprocess.TimeoutExpired as e:
            return SandboxRunResult(
                -1, e.stdout or "", e.stderr or "", True)
