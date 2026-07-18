"""Module 3 - the auditor.

Traces every clinical claim in a generated note back to the transcript and flags
anything unsupported, contradicted, or omitted. Uses Claude tool use with a
strict JSON schema so the output is always machine-readable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .llm import call_tool

STATUSES = ["supported", "unsupported", "contradicted", "omitted"]
SEVERITIES = ["low", "medium", "high"]


@dataclass
class Finding:
    claim: str
    status: str                # supported | unsupported | contradicted | omitted
    transcript_evidence: str   # quote/paraphrase from transcript, or why none exists
    severity: str              # low | medium | high


_TOOL = {
    "name": "report_findings",
    "description": "Report the claim-by-claim audit of a clinical note against its source transcript.",
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
                            "description": "Direct textual basis from the transcript, or an explanation of why none exists.",
                        },
                        "severity": {
                            "type": "string",
                            "enum": SEVERITIES,
                            "description": "Clinical risk if this claim is wrong (low/medium/high).",
                        },
                    },
                    "required": ["claim", "status", "transcript_evidence", "severity"],
                },
            }
        },
        "required": ["findings"],
    },
}

_SYSTEM = (
    "You are a skeptical clinical fact-checker auditing an AI-generated SOAP note against the "
    "source doctor-patient transcript. Decompose the note into individual clinical claims "
    "(symptoms, medications, history, findings, plan items). For each claim, trace it to the "
    "transcript.\n\n"
    "Rules:\n"
    "- NEVER mark a claim 'supported' without a direct textual basis in the transcript. If you "
    "cannot quote or point to the transcript, it is not supported.\n"
    "- 'unsupported': the note asserts something the transcript does not establish.\n"
    "- 'contradicted': the note states something the transcript directly contradicts (e.g. lists "
    "a medication as active that the patient said they stopped; hardens a hedged 'I don't think "
    "so' into a clean denial).\n"
    "- 'omitted': the transcript contains a clinically relevant fact the note leaves out. State "
    "the omitted fact as the 'claim'.\n"
    "- Set severity by clinical risk: wrong medication or missed red-flag symptom is high; a "
    "minor phrasing gap is low.\n"
    "- Report supported claims too, briefly - they show coverage. Focus your effort on the "
    "unsupported, contradicted, and omitted ones."
)


def audit(transcript: str, note: str) -> list[Finding]:
    """Audit a note against its transcript. Returns a list of Findings."""
    user = (
        f"TRANSCRIPT:\n{transcript}\n\n"
        f"GENERATED NOTE:\n{note}\n\n"
        "Audit the note claim by claim and report your findings."
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
        print(f"[{f.status.upper():12} | {f.severity:6}] {f.claim}")
        print(f"    evidence: {f.transcript_evidence}\n")
