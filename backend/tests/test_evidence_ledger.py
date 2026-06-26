from app.evidence.ledger import evidence_from_papers
from app.schemas.paper import Paper


def test_evidence_from_papers_adds_granular_sentence_evidence() -> None:
    paper = Paper(
        paper_id="p1",
        title="Favorable Interfacial Chemomechanics in Solid-State Batteries",
        abstract=(
            "Li alloys of In/Sn are attractive alternatives, but their exploration has mostly been limited "
            "to low Li content compositions. Stable interfacial chemomechanics of the alloys allow long-term "
            "dendrite free Li cycling above 1000 h at relatively high current densities. Their variation in Li "
            "migration barrier with composition influences the observed Li cycling overpotential."
        ),
        verification_status="verified",
        verification_method="arxiv_id",
        verification_confidence=0.95,
        report_eligible=True,
    )

    items = evidence_from_papers([paper], "energy_materials")
    ids = [item.evidence_id for item in items]

    assert "ev_001" in ids
    assert "ev_001a" in ids
    assert any("migration barrier" in item.claim for item in items if item.evidence_id.startswith("ev_001"))
    assert all(item.verified for item in items)
    assert all(item.eligible_for_report for item in items)
