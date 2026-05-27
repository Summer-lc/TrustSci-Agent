import csv
from pathlib import Path
from typing import Any


def profile_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    fields = reader.fieldnames or []
    missing = {field: 0 for field in fields}
    for row in rows:
        for field in fields:
            if row.get(field) in (None, ""):
                missing[field] += 1
    return {
        "path": str(path),
        "rows": len(rows),
        "fields": fields,
        "missing": missing,
        "task_hint": "property prediction / ranking / ablation planning",
    }

