from app.config import Settings
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.tools.materials_data import build_materials_profiles, run_mean_baseline


class ScientificDataAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self) -> tuple[list[DatasetProfile], BaselineResultCard]:
        profiles = build_materials_profiles(
            self.settings.data_dir,
            materials_project_api_key=self.settings.materials_project_api_key,
        )
        result_card = run_mean_baseline(self.settings.data_dir)
        return profiles, result_card

