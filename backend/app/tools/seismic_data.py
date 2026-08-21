import csv
from collections import Counter
from pathlib import Path

from app.schemas.seismic import SeismicDataProfile

DEMO_DATASET_NAME = "demo_seismic_events"


class SeismicDataAdapter:
    """Profile the bundled seismic demo subset (S1: metadata only).

    S4 will extend this to read waveform tensors and produce train/val/test
    splits for the Code Experiment Loop. S1 only profiles event metadata so
    the workspace can show a seismic data profile before experiments exist.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def profile(self) -> SeismicDataProfile:
        path = self.data_dir / "seismic_demo" / "events.csv"
        rows = _read_csv(path)
        labels = dict(Counter(row["label"] for row in rows))
        channels = rows[0]["channels"].split("/") if rows and rows[0].get("channels") else []
        sampling_rate = int(rows[0]["sampling_rate"]) if rows and rows[0].get("sampling_rate") else None
        window_seconds = int(rows[0]["window_seconds"]) if rows and rows[0].get("window_seconds") else None
        risks = _risks(labels, rows)
        return SeismicDataProfile(
            dataset_name=DEMO_DATASET_NAME,
            num_events=len(rows),
            labels=labels,
            channels=channels or ["Z", "N", "E"],
            sampling_rate=sampling_rate,
            window_seconds=window_seconds,
            split_strategy="event_level",
            risks=risks,
            source_path=str(path),
        )


def _risks(labels: dict, rows: list[dict]) -> list[str]:
    risks: list[str] = []
    total = sum(labels.values()) or 1
    minority = [label for label, count in labels.items() if count / total < 0.15]
    if minority:
        risks.append(f"class imbalance: {', '.join(minority)} below 15% share")
    stations = {row.get("station") for row in rows}
    if len(stations) >= 2:
        risks.append("station leakage: ensure station-level split to test cross-station generalization")
    if "noise" in labels and labels.get("noise", 0) / total < 0.25:
        risks.append("minority class noise may need class weighting or resampling")
    return risks or ["no major risks detected in the demo subset"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
