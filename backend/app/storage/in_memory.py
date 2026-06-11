from threading import Lock

from app.schemas.run import ResearchRun


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, ResearchRun] = {}
        self._lock = Lock()

    def create(self, run: ResearchRun) -> ResearchRun:
        with self._lock:
            self._runs[run.run_id] = run
            return run

    def get(self, run_id: str) -> ResearchRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def save(self, run: ResearchRun) -> ResearchRun:
        with self._lock:
            self._runs[run.run_id] = run
            return run

    def delete(self, run_id: str) -> None:
        with self._lock:
            self._runs.pop(run_id, None)

    def list(self) -> list[ResearchRun]:
        with self._lock:
            return list(self._runs.values())


run_store = RunStore()
