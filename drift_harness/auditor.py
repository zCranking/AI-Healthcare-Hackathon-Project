"""Module 3 - the auditor.

Traces every clinical claim in a generated note back to its ground truth and
flags anything unsupported, contradicted, or omitted. There are TWO independent
sources of ground truth: the visit transcript AND the patient's structured FHIR
chart data. A claim grounded in the chart (but never spoken aloud) is still
supported - so the auditor must check both before flagging. Uses Claude tool use
with a strict JSON schema so the output is always machine-readable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .llm import call_tool

STATUSES = ["supported", "unsupported", "contradicted", "omitted"]
SEVERITIES = ["low", "medium", "high"]
EVIDENCE_SOURCES = ["transcript", "fhir", "both", "neither"]


@dataclass
class Finding:
    claim: str
    status: str                # supported | unsupported | contradicted | omitted
    transcript_evidence: str   # textual basis from transcript and/or FHIR, or why none exists
    evidence_source: str       # transcript | fhir | both | neither
    severity: str              # low | medium | high


_TOOL = {
    "name": "report_findings",
    "description": (
        "Report the claim-by-claim audit of a clinical note against its two ground-truth "
        "sources: the visit transcript and the patient's structured FHIR chart data."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "A single clinical claim as stated in the note.",
                        },
                        "status": {"type": "string", "enum": STATUSES},
                        "transcript_evidence": {
                            "type": "string",
                            "description": (
                                "The specific quote from the transcript and/or label from the FHIR "
                                "chart that supports or refutes the claim. If neither source contains "
                                "it, say so explicitly."
                            ),
                        },
                        "evidence_source": {
                            "type": "string",
                            "enum": EVIDENCE_SOURCES,
                            "description": (
                                "Which source justifies this finding: 'transcript' if only the "
                                "transcript grounds it, 'fhir' if only the chart data does, 'both' if "
                                "both do, 'neither' if no source contains it (the basis for flagging "
                                "unsupported/contradicted)."
                            ),
                        },
                        "severity": {
                            "type": "string",
                            "enum": SEVERITIES,
                            "description": "Clinical risk if this claim is wrong (low/medium/high).",
                        },
                    },
                    "required": ["claim", "status", "transcript_evidence", "evidence_source", "severity"],
                },
            }
        },
        "required": ["findings"],
    },
}

_SYSTEM = (
    "You are a skeptical clinical fact-checker auditing an AI-generated SOAP note. Decompose the "
    "note into individual clinical claims (symptoms, medications, history, findings, plan items) "
    "and check each one.\n\n"
    "You have TWO independent sources of ground truth: the visit transcript, and the patient's "
    "structured FHIR chart data (active conditions, medications, demographics, and this "
    "encounter's recorded resources). A claim in the note is SUPPORTED if it appears in EITHER "
    "source. Only flag a claim as unsupported or contradicted if it appears in NEITHER the "
    "transcript NOR the FHIR data. Do not assume something is false just because it is missing "
    "from the transcript - check the FHIR data before flagging anything. Only flag genuinely "
    "absent or contradicted claims, not claims that are grounded in the chart but were not spoken "
    "aloud.\n\n"
    "When the note states a value that is DERIVABLE from a FHIR field (e.g. age from birth_date "
    "plus encounter date, or a BMI category from a recorded BMI), compute the correct value and "
    "compare: if the note matches the computed value it is 'supported' with evidence_source "
    "'fhir'; if the note's value DIFFERS from the correct computed value it is 'contradicted' with "
    "evidence_source 'fhir'. Never mark a derivable value 'unsupported'/'neither' merely because "
    "it was not spoken aloud, and never mark a correctly matching value 'contradicted'.\n\n"
    "Status definitions:\n"
    "- 'supported': the claim is established by the transcript, the FHIR data, or both.\n"
    "- 'unsupported': the note asserts something that appears in NEITHER source.\n"
    "- 'contradicted': the note states something that a source directly refutes (e.g. lists a "
    "medication as active that the patient said they stopped; hardens a hedged 'I don't think so' "
    "into a clean denial; asserts a specific number/detail that neither source establishes).\n"
    "- 'omitted': a source contains a clinically relevant fact the note leaves out. State the "
    "omitted fact as the 'claim'.\n\n"
    "For every finding set 'evidence_source' to name which source (or lack thereof) justifies it: "
    "'transcript', 'fhir', 'both', or 'neither'. A flag (unsupported/contradicted) should almost "
    "always be 'neither' - if you cannot, reconsider whether it is really a flag.\n\n"
    "Set severity by clinical risk: wrong medication or missed red-flag symptom is high; a minor "
    "phrasing gap is low. Report supported claims too, briefly - they show coverage - but focus "
    "your effort on the unsupported, contradicted, and omitted ones."
)


def _format_fhir(fhir_context: dict[str, Any] | None) -> str:
    """Render the structured FHIR context into a readable block for the prompt."""
    if not fhir_context:
        return (
            "No structured FHIR chart data was provided for this case. Judge claims against the "
            "transcript alone; a claim absent from the transcript has no second source to fall "
            "back on."
        )
    lines: list[str] = []
    enc_date = fhir_context.get("encounter_date")
    if enc_date:
        lines.append(
            f"Encounter date: {enc_date} (use this to compute age from birth_date)."
        )
    demo = fhir_context.get("patient_demographics") or {}
    if demo:
        parts = [f"{k}: {v}" for k, v in demo.items() if v]
        if parts:
            lines.append("Patient demographics: " + "; ".join(parts))
        lines.append(
            "(Note: the chart records only these demographic fields - there is NO field for "
            "number of children, household size, or similar.)"
        )
    for key, header in [
        ("condition_labels", "Active/known conditions (chart problem list)"),
        ("medication_labels", "Medications on the chart"),
    ]:
        vals = fhir_context.get(key) or []
        if vals:
            lines.append(f"{header}:\n  - " + "\n  - ".join(str(v) for v in vals))
    enc = fhir_context.get("encounter_resource_labels") or {}
    for rtype, vals in enc.items():
        if vals:
            shown = vals[:25]
            more = f" (+{len(vals) - len(shown)} more)" if len(vals) > len(shown) else ""
            lines.append(f"This encounter's {rtype} resources{more}:\n  - " + "\n  - ".join(shown))
    return "\n".join(lines) if lines else "FHIR context provided but contained no usable labels."


def audit(
    transcript: str,
    note: str,
    fhir_context: dict[str, Any] | None = None,
) -> list[Finding]:
    """Audit a note against its transcript AND structured FHIR chart data.

    fhir_context is a dict with (any of) 'condition_labels', 'medication_labels',
    'patient_demographics', 'encounter_resource_labels', 'resource_counts'. Pass
    None for synthetic/custom cases that have no chart data.
    """
    user = (
        f"VISIT TRANSCRIPT:\n{transcript}\n\n"
        f"STRUCTURED FHIR CHART DATA:\n{_format_fhir(fhir_context)}\n\n"
        f"GENERATED NOTE:\n{note}\n\n"
        "Audit the note claim by claim against BOTH sources and report your findings."
    )
    data = call_tool(_SYSTEM, user, _TOOL, max_tokens=8000)
    return [Finding(**f) for f in data["findings"]]


def flagged(findings: list[Finding]) -> list[Finding]:
    """Just the problems - drop the 'supported' claims."""
    return [f for f in findings if f.status != "supported"]


def to_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]


if __name__ == "__main__":
    from .note_generator import generate_note
    from .transcript_generator import generate_case, _SCENARIOS

    case = generate_case(_SCENARIOS[0])
    note = generate_note(case.transcript)
    for f in audit(case.transcript, note):
        print(f"[{f.status.upper():12} | {f.evidence_source:10} | {f.severity:6}] {f.claim}")
        print(f"    evidence: {f.transcript_evidence}\n")
