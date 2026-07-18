"""Module 4 - the judge ensemble.

Each auditor flag is re-examined by 3 independent Claude calls with different
framing. They vote to confirm or reject the flag and score clinical severity.
When the judges disagree, we surface the split explicitly instead of averaging
it away - disagreement is signal, not noise.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any

from .auditor import EVIDENCE_AUTHORITY, Finding
from .auditor import _format_fhir
from .llm import call_tool

# Three deliberately different lenses so the votes aren't just the same model
# agreeing with itself. Order matters only for display.
_JUDGE_FRAMINGS = [
    (
        "patient_safety",
        "You are a patient-safety officer. Your only concern is whether this documentation "
        "discrepancy, if it reached the medical chart, could lead to patient harm - a wrong "
        "treatment, a missed diagnosis, an unsafe assumption by the next clinician.",
    ),
    (
        "documentation_integrity",
        "You are a clinical documentation-integrity reviewer. You care whether the note "
        "faithfully and precisely represents what was actually said in the encounter, and "
        "whether the discrepancy would survive a compliance or medico-legal audit.",
    ),
    (
        "false_positive_skeptic",
        "You are reviewing whether an automated auditor raised a FALSE ALARM. Assume the flag "
        "might be over-eager. Push back: is there in fact adequate support in EITHER the "
        "transcript OR the FHIR chart, or is the flagged discrepancy clinically trivial? Only "
        "confirm if the flag genuinely holds against all sources.",
    ),
]

_TOOL = {
    "name": "cast_vote",
    "description": "Vote on whether an auditor's flag is a genuine, clinically meaningful discrepancy.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["confirm", "reject"],
                "description": "confirm = the flag is a real, meaningful discrepancy; reject = false alarm or trivial.",
            },
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Clinical severity if the flag stands.",
            },
            "rationale": {
                "type": "string",
                "description": "One or two sentences justifying the vote from your assigned perspective.",
            },
        },
        "required": ["verdict", "severity", "rationale"],
    },
}


@dataclass
class JudgeVote:
    judge: str
    verdict: str    # confirm | reject
    severity: str   # low | medium | high
    rationale: str


@dataclass
class JudgedFinding:
    finding: dict                       # the auditor Finding, as a dict
    votes: list[JudgeVote] = field(default_factory=list)
    consensus_verdict: str = ""         # confirm | reject | split
    severity_verdict: str = ""          # majority severity, or "split"
    disagreement: bool = False
    confirm_votes: int = 0
    reject_votes: int = 0


def _one_vote(
    framing: tuple[str, str],
    transcript: str,
    note: str,
    finding: Finding,
    fhir_context: dict[str, Any] | None = None,
) -> JudgeVote:
    name, lens = framing
    system = (
        f"{lens}\n\nYou are one of several independent judges reviewing a single flag raised by "
        "an automated note auditor. Judge only the flag in front of you. Be decisive.\n\n"
        + EVIDENCE_AUTHORITY
        + "Apply this same authority scale when you weigh the auditor's evidence: a discrepancy "
        "that a source with authority for that KIND of claim actually establishes is a real flag; "
        "one that rests only on a source with little authority for it (e.g. a patient's "
        "self-reassurance used to rule a concern out) should not be dismissed as trivial.\n\n"
        "You have THREE sources: the visit transcript, the patient's structured FHIR chart data, "
        "and (when present) the patient-facing after-visit summary. The FHIR chart records the "
        "patient's ACTUAL data and is authoritative - if the note misstates something the chart "
        "records correctly, the note is wrong, not the chart. A claim is adequately supported if "
        "EITHER the transcript OR the chart grounds it. Judge only the flag in front of you, "
        "against all sources. Be decisive."
    )
    user = (
        f"SOURCE TRANSCRIPT:\n{transcript}\n\n"
        f"STRUCTURED FHIR CHART DATA:\n{_format_fhir(fhir_context)}\n\n"
        f"GENERATED NOTE:\n{note}\n\n"
        "AUTOMATED AUDITOR FLAG:\n"
        f"  claim/issue: {finding.claim}\n"
        f"  auditor status: {finding.status}\n"
        f"  auditor evidence: {finding.transcript_evidence}\n"
        f"  auditor evidence source: {finding.evidence_source}\n"
        f"  auditor severity: {finding.severity}\n\n"
        "Verify the flag against the transcript AND the FHIR chart yourself - do not just trust "
        "the auditor's evidence text. Cast your vote."
    )
    data = call_tool(system, user, _TOOL, max_tokens=1200)
    return JudgeVote(judge=name, verdict=data["verdict"], severity=data["severity"], rationale=data["rationale"])


def _majority(values: list[str]) -> str:
    """Most common value; 'split' if there's a tie with no clear winner."""
    counts = {v: values.count(v) for v in set(values)}
    top = max(counts.values())
    winners = [v for v, c in counts.items() if c == top]
    return winners[0] if len(winners) == 1 else "split"


def judge_finding(
    transcript: str,
    note: str,
    finding: Finding,
    fhir_context: dict[str, Any] | None = None,
) -> JudgedFinding:
    """Run all 3 judges on one finding (in parallel) and aggregate."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        votes = list(
            pool.map(lambda fr: _one_vote(fr, transcript, note, finding, fhir_context), _JUDGE_FRAMINGS)
        )

    verdicts = [v.verdict for v in votes]
    confirm = verdicts.count("confirm")
    reject = verdicts.count("reject")
    consensus = "confirm" if confirm > reject else "reject" if reject > confirm else "split"
    severity_verdict = _majority([v.severity for v in votes])
    # Disagreement = the judges did not unanimously agree on the verdict.
    disagreement = len(set(verdicts)) > 1

    return JudgedFinding(
        finding=asdict(finding),
        votes=votes,
        consensus_verdict=consensus,
        severity_verdict=severity_verdict,
        disagreement=disagreement,
        confirm_votes=confirm,
        reject_votes=reject,
    )


def judge_findings(
    transcript: str,
    note: str,
    findings: list[Finding],
    max_findings: int | None = None,
    fhir_context: dict[str, Any] | None = None,
) -> list[JudgedFinding]:
    """Judge a list of (already flagged) findings, hardest first.

    max_findings caps how many we escalate to the ensemble - useful to keep the
    interactive endpoint snappy. We sort by auditor severity so the riskiest
    flags always get judged. `fhir_context` is the same structured chart data the
    auditor saw, so the judges verify FHIR-based flags against the chart itself.
    """
    order = {"high": 0, "medium": 1, "low": 2}
    ranked = sorted(findings, key=lambda f: order.get(f.severity, 3))
    if max_findings is not None:
        ranked = ranked[:max_findings]
    return [judge_finding(transcript, note, f, fhir_context) for f in ranked]


def to_dicts(judged: list[JudgedFinding]) -> list[dict]:
    out = []
    for j in judged:
        d = asdict(j)  # dataclasses (incl. nested JudgeVote) -> plain dicts
        out.append(d)
    return out
