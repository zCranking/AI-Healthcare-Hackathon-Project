"""Loader for the Abridge synthetic-ambient-fhir-25 dataset (plain Python, no LLM).

Lets the harness run on real partner transcript+note pairs, not just synthetic
trap cases. Each record already ships a clinician note, so for these cases we can
audit the *provided* note directly, or regenerate one to test our own scribe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# .../AI-Healthcare-Hackathon-Project/drift_harness/dataset.py -> project root
_ROOT = Path(__file__).resolve().parent.parent
_DATA = (
    _ROOT
    / "synthetic-ambient-fhir-25"
    / "synthetic-ambient-fhir-25"
    / "synthetic-ambient-fhir-25.jsonl"
)


@dataclass
class AbridgeCase:
    id: str
    visit_title: str
    date: str
    transcript: str
    note: str  # the dataset's own clinician note


@lru_cache(maxsize=1)
def load_cases() -> list[AbridgeCase]:
    """Load all Abridge encounters. Cached after first read."""
    if not _DATA.exists():
        raise FileNotFoundError(
            f"Abridge dataset not found at {_DATA}. Expected the "
            "synthetic-ambient-fhir-25 folder alongside this project."
        )
    cases: list[AbridgeCase] = []
    with _DATA.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            cases.append(
                AbridgeCase(
                    id=r["id"],
                    visit_title=r["metadata"].get("visit_title", ""),
                    date=r["metadata"].get("date", ""),
                    transcript=r["transcript"],
                    note=r["note"],
                )
            )
    return cases


def get_case(index: int) -> AbridgeCase:
    return load_cases()[index]


def list_titles() -> list[dict]:
    """Lightweight index for a UI dropdown."""
    return [
        {"index": i, "visit_title": c.visit_title, "date": c.date}
        for i, c in enumerate(load_cases())
    ]


if __name__ == "__main__":
    cases = load_cases()
    print(f"Loaded {len(cases)} Abridge encounters:")
    for i, c in enumerate(cases):
        print(f"  [{i:2}] {c.date}  {c.visit_title}")
