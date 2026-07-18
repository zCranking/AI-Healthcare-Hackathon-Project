"""Module 5b - the self-scoring evaluator (LLM-aligned).

For synthetic cases we KNOW the ground truth: every trap planted in the
transcript is reported alongside it. This module measures whether the harness
caught the drift those traps induced - the headline metric that proves the
harness works instead of just asserting it.

The subtlety that makes the number honest: a planted trap is only an OPPORTUNITY
to drift. If the scribe handled it faithfully (e.g. correctly documented a
stopped medication), there is no error to catch, and the auditor staying silent
is CORRECT - not a miss. So for each trap we ask two questions:

  1. did the generated note actually drift (violate the trap's expected behavior)?
  2. if it drifted, did the auditor catch it?

Recall is then measured only over the traps the scribe actually drifted on - the
auditor's true detection rate on real errors. Matching is semantic, so we use
one Claude tool call per case. Abridge/custom cases carry no traps, so scoring
is skipped for them.
"""

from __future__ import annotations

from typing import Any

from .llm import call_tool

_TOOL = {
    "name": "score_detection",
    "description": (
        "For each planted trap, judge whether the note drifted and, if so, whether the auditor "
        "caught it."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "trap_results": {
                "type": "array",
                "description": "Exactly one entry per planted trap, in the same order given.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "trap_index": {
                            "type": "integer",
                            "description": "The 0-based index of the trap being scored.",
                        },
                        "note_drifted": {
                            "type": "boolean",
                            "description": (
                                "True if the GENERATED NOTE actually mishandled this trap - i.e. "
                                "violated the trap's expected behavior (asserted a stopped med as "
                                "active, hardened a hedge into a clean denial, omitted the buried "
                                "detail, over-asserted a dismissed symptom). False if the note "
                                "handled it faithfully - in which case the auditor is correct to "
                                "stay silent."
                            ),
                        },
                        "caught": {
                            "type": "boolean",
                            "description": (
                                "True if some flagged auditor finding clearly corresponds to this "
                                "trap's error (same underlying issue, worded differently is fine)."
                            ),
                        },
                        "confirmed_by_judges": {
                            "type": "boolean",
                            "description": "True if the matching finding was CONFIRMED by the judge ensemble.",
                        },
                        "matched_claim": {
                            "type": "string",
                            "description": "The claim text of the matching finding, or '' if not caught.",
                        },
                        "note": {
                            "type": "string",
                            "description": "One short sentence justifying the drift/catch judgement.",
                        },
                    },
                    "required": [
                        "trap_index",
                        "note_drifted",
                        "caught",
                        "confirmed_by_judges",
                        "matched_claim",
                        "note",
                    ],
                },
            }
        },
        "required": ["trap_results"],
    },
}

_SYSTEM = (
    "You are grading an automated clinical-note auditor against ground truth. You are given the "
    "traps deliberately planted in a visit transcript, the SOAP note a scribe generated, and the "
    "findings the auditor produced (with whether a judge ensemble confirmed each one).\n\n"
    "For every planted trap, make TWO independent judgements:\n"
    "1. note_drifted: did the generated note actually get this wrong - violate the trap's expected "
    "behavior? A trap is only an opportunity to err; if the note handled it faithfully, there is "
    "NOTHING to catch and note_drifted is false.\n"
    "2. caught: did any flagged auditor finding surface this trap's error? Match on clinical "
    "meaning, not exact words. Be strict - a vague finding that does not address the error is not "
    "a catch. A finding is additionally confirmed_by_judges only if the ensemble confirmed it.\n\n"
    "Only drifts that were NOT caught are true misses; faithful handling that the auditor left "
    "alone is correct behavior, not a miss."
)


def _fmt_traps(traps: list[dict[str, Any]]) -> str:
    out = []
    for i, t in enumerate(traps):
        out.append(
            f"[trap {i}] type={t.get('trap_type', '?')}\n"
            f"    planted: {t.get('description', '')}\n"
            f"    a faithful note should: {t.get('expected_note_behavior', '')}"
        )
    return "\n".join(out)


def _fmt_findings(findings: list[dict[str, Any]], judged: list[dict[str, Any]]) -> str:
    verdict_by_claim: dict[str, str] = {}
    for j in judged:
        f = j.get("finding") or {}
        verdict_by_claim[f.get("claim", "")] = j.get("consensus_verdict", "")
    flagged = [f for f in findings if f.get("status") != "supported"]
    if not flagged:
        return "(the auditor flagged nothing)"
    out = []
    for f in flagged:
        v = verdict_by_claim.get(f.get("claim", ""))
        label = f"judges: {v}" if v else "not escalated"
        out.append(
            f"- [{f.get('status')}/{f.get('evidence_source')}] {f.get('claim')} ({label})\n"
            f"    evidence: {f.get('transcript_evidence', '')}"
        )
    return "\n".join(out)


def score_case(
    traps: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    judged: list[dict[str, Any]],
    note: str = "",
) -> dict[str, Any]:
    """Score one case's drift detection against its planted traps.

    Recall is measured over the traps the scribe actually drifted on (not all
    planted traps), so faithful handling the auditor correctly ignores does not
    count against it. Returns {} when there are no traps (Abridge/custom).
    """
    if not traps:
        return {}

    user = (
        "PLANTED TRAPS (ground truth):\n"
        f"{_fmt_traps(traps)}\n\n"
        "GENERATED NOTE (the system under test):\n"
        f"{note}\n\n"
        "AUDITOR FINDINGS:\n"
        f"{_fmt_findings(findings, judged)}\n\n"
        "Score every trap. Return exactly one result per trap, in order."
    )
    data = call_tool(_SYSTEM, user, _TOOL, max_tokens=3500)
    results = data.get("trap_results", [])

    total = len(traps)
    drifted = [r for r in results if r.get("note_drifted")]
    n_drifted = len(drifted)
    caught = sum(1 for r in drifted if r.get("caught"))
    confirmed = sum(1 for r in drifted if r.get("caught") and r.get("confirmed_by_judges"))
    missed = [
        {"trap_index": r.get("trap_index"), "trap": traps[r["trap_index"]], "note": r.get("note", "")}
        for r in drifted
        if not r.get("caught") and isinstance(r.get("trap_index"), int) and r["trap_index"] < total
    ]

    matched_claims = {r.get("matched_claim", "") for r in results if r.get("caught")}
    confirmed_claims = {
        (j.get("finding") or {}).get("claim", "")
        for j in judged
        if j.get("consensus_verdict") == "confirm"
    }
    unplanned = len([c for c in confirmed_claims if c and c not in matched_claims])

    return {
        "traps_total": total,
        "traps_faithful": total - n_drifted,      # scribe handled these correctly
        "traps_drifted": n_drifted,               # scribe actually erred here
        "drift_caught": caught,                   # drifted AND auditor caught
        "drift_confirmed": confirmed,             # drifted AND caught AND judge-confirmed
        "recall": round(caught / n_drifted, 3) if n_drifted else None,
        "confirmed_recall": round(confirmed / n_drifted, 3) if n_drifted else None,
        "missed_drifts": missed,                  # the dangerous ones: real drift, not caught
        "unplanned_confirmed_flags": unplanned,
        "per_trap": results,
    }
