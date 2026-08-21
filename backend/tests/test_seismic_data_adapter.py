from pathlib import Path

from app.tools.seismic_data import SeismicDataAdapter


def test_seismic_adapter_profiles_demo_subset(tmp_path: Path) -> None:
    # Copy the committed demo csv into a tmp data_dir so the test does not
    # depend on the repo working directory.
    demo_dir = tmp_path / "seismic_demo"
    demo_dir.mkdir()
    src = Path("data/seismic_demo/events.csv")
    (demo_dir / "events.csv").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    profile = SeismicDataAdapter(tmp_path).profile()

    assert profile.dataset_name == "demo_seismic_events"
    assert profile.num_events > 0
    assert set(profile.labels).issuperset({"earthquake", "explosion", "noise"})
    assert profile.sampling_rate == 100
    assert profile.window_seconds == 30
    assert profile.channels == ["Z", "N", "E"]
    assert profile.split_strategy == "event_level"
    assert profile.risks  # non-empty risk list
    assert profile.source_path and profile.source_path.endswith("events.csv")
