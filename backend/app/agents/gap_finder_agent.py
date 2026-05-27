from app.schemas.evidence import EvidenceItem


class GapFinderAgent:
    def run(self, evidence: list[EvidenceItem]) -> list[dict]:
        verified = [item for item in evidence if item.verified]
        anchors = verified[:3] or evidence[:3]
        ids = [item.evidence_id for item in anchors]
        return [
            {
                "gap_id": "gap_001",
                "gap": "Existing studies are often split between literature-level mechanism descriptions and structured dataset modeling; the bridge between mechanistic text evidence and quantitative verification remains underdeveloped.",
                "evidence": ids,
                "potential_value": "A literature-augmented validation plan can improve hypothesis traceability and make screening decisions easier to audit.",
            }
        ]

