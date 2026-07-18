"""Loader for the Abridge synthetic-ambient-fhir-25 dataset (plain Python, no LLM).

Lets the harness run on real partner transcript+note pairs, not just synthetic
trap cases. Each record already ships a clinician note, so for these cases we can
audit the *provided* note directly, or regenerate one to test our own scribe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

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
    fhir_context: dict[str, Any] = field(default_factory=dict)  # structured chart ground truth


def _resource_display(resource: dict[str, Any]) -> str | None:
    """Pull a human-readable label out of a FHIR resource (best effort)."""
    for key in ("code", "medicationCodeableConcept", "valueCodeableConcept", "vaccineCode"):
        cc = resource.get(key)
        if isinstance(cc, dict):
            if cc.get("text"):
                return cc["text"]
            for coding in cc.get("coding", []):
                if coding.get("display"):
                    return coding["display"]
    return resource.get("code", {}).get("text") if isinstance(resource.get("code"), dict) else None


def build_fhir_context(record: dict[str, Any]) -> dict[str, Any]:
    """Extract a compact structured-chart context from one raw dataset record.

    Pulls the longitudinal problem/medication lists, patient demographics, and
    this encounter's recorded resources - the second source of ground truth the
    auditor checks a claim against before flagging it.
    """
    pc = record.get("patient_context", {})
    summary = pc.get("longitudinal_summary", {}) or {}
    patient = pc.get("patient", {}) or {}

    marital = ""
    ms = patient.get("maritalStatus", {})
    if isinstance(ms, dict):
        marital = ms.get("text") or (ms.get("coding", [{}])[0].get("display", "") if ms.get("coding") else "")

    demographics = {
        "gender": patient.get("gender", ""),
        "birth_date": patient.get("birthDate", ""),
        "marital_status": marital,
    }

    enc_labels: dict[str, list[str]] = {}
    related = record.get("encounter_fhir", {}).get("related_resources", {}) or {}
    for rtype, resources in related.items():
        labels = []
        for r in resources:
            label = _resource_display(r)
            if label:
                labels.append(label)
        if labels:
            # dedupe, preserve order
            seen: set[str] = set()
            enc_labels[rtype] = [x for x in labels if not (x in seen or seen.add(x))]

    return {
        "encounter_date": record.get("metadata", {}).get("date", ""),
        "condition_labels": summary.get("condition_labels", []),
        "medication_labels": summary.get("medication_labels", []),
        "patient_demographics": demographics,
        "resource_counts": summary.get("resource_counts", {}),
        "encounter_resource_labels": enc_labels,
        # Patient-facing after-visit summary. Per its provenance it is extractively
        # derived from the clinical note's assessment & plan and is NOT clinically
        # reviewed - corroborating context (esp. for plan/next-step omissions), not
        # an independent source of truth.
        "after_visit_summary": record.get("after_visit_summary", ""),
        "after_visit_summary_provenance": record.get("after_visit_summary_provenance", {}) or {},
    }


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
                    fhir_context=build_fhir_context(r),
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
