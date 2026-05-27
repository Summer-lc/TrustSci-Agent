import json
from pathlib import Path

from app.schemas.llm import LLMCallLog


class LLMLogger:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def write(self, log: LLMCallLog) -> LLMCallLog:
        run_id = log.run_id or "adhoc"
        out_dir = self.data_dir / "outputs" / "llm_calls"
        out_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = out_dir / f"{run_id}.jsonl"
        log.log_path = str(jsonl_path)
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log.model_dump(mode="json"), ensure_ascii=False) + "\n")
        return log


def read_llm_logs(data_dir: Path, run_id: str) -> list[dict]:
    path = data_dir / "outputs" / "llm_calls" / f"{run_id}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

