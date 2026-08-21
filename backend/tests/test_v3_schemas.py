from app.schemas.idea import IdeaBrief
from app.schemas.mode import ResearchMode
from app.schemas.run import ResearchConstraints, ResearchRun, ResearchRunCreate
from app.schemas.seismic import SeismicDataProfile


def test_research_run_defaults_mode_to_discovery() -> None:
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    assert run.mode == "discovery"
    assert run.idea_brief is None
    assert run.intent is None
    assert run.seismic_data_profile is None


def test_research_run_create_carries_mode() -> None:
    payload = ResearchRunCreate(domain="seismic_event_classification", question="q", mode="idea_refinement")
    run = ResearchRun(domain=payload.domain, question=payload.question, constraints=payload.constraints, mode=payload.mode)
    assert run.mode == "idea_refinement"


def test_idea_brief_round_trip() -> None:
    brief = IdeaBrief(
        research_problem="地震事件分类",
        user_idea="多通道波形与时频图融合",
        target_task="earthquake/explosion/noise classification",
        input_data=["three-component waveform", "spectrogram"],
        target_labels=["earthquake", "explosion", "noise"],
    )
    dumped = brief.model_dump()
    assert dumped["user_idea"] == "多通道波形与时频图融合"
    assert dumped["target_labels"] == ["earthquake", "explosion", "noise"]


def test_seismic_data_profile_defaults() -> None:
    profile = SeismicDataProfile(dataset_name="demo", num_events=10)
    assert profile.labels == {}
    assert profile.split_strategy == "event_level"
    assert profile.risks == []
