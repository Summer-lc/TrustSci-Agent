import csv
import json
import statistics
from pathlib import Path
from typing import Any

import httpx

from app.schemas.data import BaselineResultCard, DatasetProfile


MATBENCH_SOURCE_URL = "https://arxiv.org/abs/2005.00707"
MATERIALS_PROJECT_API_URL = "https://api.materialsproject.org/materials/summary/"
MATERIALS_PROJECT_DOCS_URL = "https://docs.materialsproject.org/downloading-data/using-the-api"


def build_materials_profiles(data_dir: Path, materials_project_api_key: str = "") -> list[DatasetProfile]:
    profiles = [_profile_local_solid_electrolyte_csv(data_dir)]
    profiles.extend(_matbench_reference_profiles())
    profiles.append(_materials_project_adapter_profile(materials_project_api_key))
    return profiles


async def query_materials_project_candidates(
    formulas: list[str],
    api_key: str,
    limit_per_formula: int = 3,
) -> list[dict[str, Any]]:
    if not api_key:
        return []
    headers = {"X-API-KEY": api_key}
    fields = "material_id,formula_pretty,band_gap,energy_above_hull,is_stable"
    docs: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for formula in formulas:
            response = await client.get(
                MATERIALS_PROJECT_API_URL,
                headers=headers,
                params={"formula": formula, "fields": fields, "chunk_size": limit_per_formula},
            )
            response.raise_for_status()
            payload = response.json()
            docs.extend(payload.get("data") or [])
    return docs


def run_mean_baseline(data_dir: Path) -> BaselineResultCard:
    dataset_path = data_dir / "sample_datasets" / "solid_electrolyte_candidates.csv"
    rows = _read_csv(dataset_path)
    target = "ionic_conductivity_log10_s_cm"
    values = [float(row[target]) for row in rows]
    split = max(1, int(len(values) * 0.6))
    train = values[:split]
    test = values[split:] or values[-1:]
    prediction = statistics.mean(train)
    abs_errors = [abs(value - prediction) for value in test]
    mae = statistics.mean(abs_errors)
    mean_test = statistics.mean(test)
    ss_res = sum((value - prediction) ** 2 for value in test)
    ss_tot = sum((value - mean_test) ** 2 for value in test)
    r2 = 0.0 if ss_tot == 0 else 1 - ss_res / ss_tot

    card = BaselineResultCard(
        name="solid_electrolyte_mean_baseline",
        dataset=str(dataset_path),
        target=target,
        model="mean predictor over training split",
        train_rows=len(train),
        test_rows=len(test),
        metrics={"MAE": round(mae, 4), "R2": round(r2, 4)},
        result_summary=(
            "A deterministic mean baseline ran on the bundled solid-electrolyte candidate table. "
            "It is intentionally simple and provides a result-card contract for later Matbench/Materials Project benchmarks."
        ),
    )
    out_dir = data_dir / "outputs" / "result_cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{card.name}.json"
    path.write_text(json.dumps(card.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    card.artifact_path = str(path)
    return card


def _profile_local_solid_electrolyte_csv(data_dir: Path) -> DatasetProfile:
    path = data_dir / "sample_datasets" / "solid_electrolyte_candidates.csv"
    rows = _read_csv(path)
    fields = list(rows[0].keys()) if rows else []
    return DatasetProfile(
        name="bundled_solid_electrolyte_candidates",
        source="local CSV demo dataset",
        source_url=str(path),
        rows=len(rows),
        fields=fields,
        target="ionic_conductivity_log10_s_cm",
        task_type="regression / ranking",
        notes="Small bundled table for end-to-end workflow verification; replace with Materials Project or Matbench data for final submission experiments.",
    )


def _matbench_reference_profiles() -> list[DatasetProfile]:
    return [
        DatasetProfile(
            name="matbench_jdft2d",
            source="Matbench benchmark metadata",
            source_url=MATBENCH_SOURCE_URL,
            rows=636,
            fields=["structure", "exfoliation_energy"],
            target="exfoliation energy",
            task_type="regression",
            notes="Representative small Matbench task useful for fast baseline integration.",
        ),
        DatasetProfile(
            name="matbench_mp_e_form",
            source="Matbench benchmark metadata",
            source_url=MATBENCH_SOURCE_URL,
            rows=132752,
            fields=["structure", "formation_energy_per_atom"],
            target="formation energy",
            task_type="regression",
            notes="Large Materials Project-derived Matbench task for structure-property prediction.",
        ),
        DatasetProfile(
            name="matbench_expt_gap",
            source="Matbench benchmark metadata",
            source_url=MATBENCH_SOURCE_URL,
            rows=4604,
            fields=["composition", "experimental_band_gap"],
            target="experimental band gap",
            task_type="regression",
            notes="Experimental property task suited for low-cost composition-only baselines.",
        ),
    ]


def _materials_project_adapter_profile(api_key: str) -> DatasetProfile:
    return DatasetProfile(
        name="materials_project_summary_adapter",
        source="Materials Project API",
        source_url=MATERIALS_PROJECT_DOCS_URL,
        rows=None,
        fields=["material_id", "formula_pretty", "band_gap", "energy_above_hull", "is_stable"],
        target="stability and electronic descriptors",
        task_type="candidate retrieval / feature enrichment",
        availability="configured" if api_key else "requires MATERIALS_PROJECT_API_KEY",
        notes="Uses the Materials Project summary endpoint when an API key is provided.",
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

