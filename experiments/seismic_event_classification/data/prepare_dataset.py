"""Generate the small deterministic seismic demo subset.

Produces data/seismic_demo/events.csv with event-level metadata. S1 only
profiles metadata; S4 will add waveform tensors. Run from repo root:

    python experiments/seismic_event_classification/data/prepare_dataset.py
"""
import csv
import random
from pathlib import Path

LABELS = ["earthquake", "explosion", "noise"]
STATIONS = ["STA01", "STA02", "STA03", "STA04"]
COUNTS = {"earthquake": 60, "explosion": 35, "noise": 25}  # 120 events
SAMPLING_RATE = 100
WINDOW_SECONDS = 30
CHANNELS = ["Z", "N", "E"]


def build_rows() -> list[dict]:
    rng = random.Random(20260629)
    rows: list[dict] = []
    event_id = 1
    for label, count in COUNTS.items():
        for _ in range(count):
            rows.append({
                "event_id": f"evt_{event_id:04d}",
                "label": label,
                "station": rng.choice(STATIONS),
                "sampling_rate": SAMPLING_RATE,
                "window_seconds": WINDOW_SECONDS,
                "channels": "/".join(CHANNELS),
                "split": "train" if event_id % 5 else ("val" if event_id % 3 == 0 else "test"),
            })
            event_id += 1
    return rows


def main() -> None:
    out_dir = Path("data/seismic_demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "events.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(build_rows()[0].keys()))
        writer.writeheader()
        writer.writerows(build_rows())
    print(f"wrote {path} with {sum(COUNTS.values())} events")


if __name__ == "__main__":
    main()
