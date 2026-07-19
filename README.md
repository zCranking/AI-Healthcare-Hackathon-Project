# Veritas Charting

An adversarial red-team harness that catches when an AI-generated clinical note
**silently drifts** from what was actually said in a doctor-patient transcript.

Ambient scribes (Abridge and friends) turn a visit conversation into a SOAP
note. The dangerous failure isn't a garbled note — it's a *plausible* one that
quietly asserts a medication the patient stopped, hardens a hedged "I don't
think so" into a clean denial, invents a repeat vital sign, or misstates the
patient's age against their chart. This harness treats the note-writer as a
system under test and hunts for exactly those drifts.

**Every claim is checked against three sources**, in a strict authority order:

1. **The patient's FHIR chart** — *authoritative*. Real recorded data (problem
   list, medications, demographics, this encounter's Conditions / Observations /
   Procedures / Immunizations). If the note misstates something the chart records
   correctly, the note is wrong — not the chart.
2. **The visit transcript** — what was actually said.
3. **The after-visit summary** — corroborating context; it echoes the note, so it
   never *confirms* a claim on its own, but a genuine contradiction is flagged.

Both the auditor **and** all three judges see all three sources, so a
chart-based contradiction is verified against the chart itself — not a paraphrase.

## What we built at the hackathon

Everything here was built during the Abridge Hackathon. There is no pre-existing
product underneath — the entire agentic pipeline is original work for this event:

- **A 5-stage agentic pipeline** — synthetic transcript generator (with planted
  ground-truth traps) → SOAP note-writer (the system under test) → claim-by-claim
  auditor → 3-judge ensemble → self-scoring evaluator. (`drift_harness/`)
- **Three-source grounding on real Abridge data** — every claim is checked
  against the patient's **FHIR chart** (authoritative), the **transcript**, and
  the **after-visit summary**, loaded from the provided `synthetic-ambient-fhir-25`
  corpus. (`dataset.py`, `auditor.py`)
- **A claim-type evidence-authority model** — authority shifts with the claim
  (FHIR for measured facts, clinician for judgment, patient for their own body /
  adherence), shared verbatim by the auditor **and** all three judges.
  (`auditor.py:EVIDENCE_AUTHORITY`)
- **Deterministic evidence-source weighting** — the authority model applied as
  code, not just prose: a contradiction against an authoritative source (the FHIR
  chart, or the spoken record for the patient's own body / adherence) is escalated
  one severity level before ranking. The bump is auditable, never silent — each
  finding keeps its original severity (`severity_raw`) and the reason
  (`weight_reason`). (`auditor.py:apply_evidence_weighting`)
- **An adversarial 3-judge ensemble** — patient-safety, documentation-integrity,
  and false-positive-skeptic lenses vote independently; **disagreement is
  surfaced as a split, never averaged away**; each emits a *clinical-harm-if-
  trusted* statement. (`judge_ensemble.py`)
- **Honest self-scoring** — grades the harness against planted traps on **drift
  recall**, counting only traps the scribe actually drifted on. (`scorer.py`)
- **A live 3-panel web app** — FastAPI + vanilla JS to run any encounter and
  trace each finding to its source with per-judge votes. Self-contained (no build
  step, no external assets): a medical-blue theme with a light/dark toggle
  (persisted, no flash), and animated skeleton placeholders while a run streams
  in. (`main.py`, `static/`)

Strict-JSON Claude tool use is used at every reasoning step (auditor, each judge,
scorer) so the pipeline never parses free-text. No fine-tuning — reliability
comes from architecture, so it's auditable and model-agnostic.

## Pipeline

```
transcript ──▶ note_generator ──▶ auditor ──▶ judge_ensemble ──▶ report
 (synthetic     (system under      (claim-by-    (3 independent
  w/ planted     test: SOAP         claim trace,   Claude judges,
  traps, OR      note via           strict JSON    confirm/reject +
  real Abridge   Claude)            tool use)      severity; splits
  encounter)                                       surfaced, not averaged)
```

| Module | File | Role |
|--------|------|------|
| 1 | `drift_harness/transcript_generator.py` | Synthetic transcripts with deliberately planted traps + ground-truth trap list |
| 2 | `drift_harness/note_generator.py` | SOAP note from a transcript — the **system under test** |
| 3 | `drift_harness/auditor.py` | Traces every note claim to the transcript + FHIR chart; flags unsupported / contradicted / omitted (strict-JSON tool use); deterministic evidence-source severity weighting |
| 4 | `drift_harness/judge_ensemble.py` | 3 independently-framed Claude judges score each flag against all three sources; **disagreement is surfaced, never averaged**; each emits a *clinical-harm-if-trusted* statement |
| 5 | `drift_harness/orchestrator.py` | Plain-Python loop over N cases → aggregated JSON report |
| 5b | `drift_harness/scorer.py` | **Self-scoring**: grades the harness against planted traps and reports drift recall (see below) |
| — | `drift_harness/dataset.py` | Loads the Abridge `synthetic-ambient-fhir-25` encounters + builds the FHIR chart / AVS ground-truth context |
| 6 | `main.py` + `static/index.html` | FastAPI + vanilla-JS 3-panel UI (transcript · note · flagged discrepancies); medical-blue theme, light/dark toggle, skeleton loading |

Model: `claude-sonnet-4-6` (single model for note, audit, and judges — apples-to-apples). Configured in `drift_harness/llm.py`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env         # then paste your key into .env
# or: export ANTHROPIC_API_KEY=sk-ant-...
```

## Run

**Checkpoint — modules 1–3 on one hardcoded transcript, printed to console:**
```bash
python smoke_test.py
```

**Full pipeline over N cases → JSON report in `results/`:**
```bash
python -m drift_harness.orchestrator --mode synthetic --n 2
python -m drift_harness.orchestrator --mode abridge --indices 0,3,7
python -m drift_harness.orchestrator --mode abridge --indices 0 --regenerate-note
```

**Web app:**
```bash
uvicorn main:app --reload
# open http://127.0.0.1:8000
```

In the UI, pick an **Abridge encounter**, a fresh **synthetic trap case**, or
**paste your own** transcript, then *Run harness*. Left = transcript, middle =
note, right = flagged discrepancies with severity color and per-judge votes.

## Self-scoring: drift recall

Synthetic cases ship their **planted traps** as ground truth, so the harness
grades itself (`scorer.py`). The metric is deliberately honest:

> A planted trap is only an *opportunity* to drift. If the scribe handled it
> faithfully (e.g. correctly documented a stopped medication), there is nothing
> to catch — the auditor staying silent is **correct**, not a miss.

So for each trap the grader asks two questions: *did the note actually drift?*
and *if so, did the harness catch it?* **Drift recall** is measured only over the
traps the scribe actually drifted on — the auditor's true detection rate on real
errors, not diluted by faithful handling it correctly ignored. Misses (real
drift that slipped through) are surfaced explicitly, never hidden.

```
recall = drifts caught / drifts the scribe actually made
```

This shows up live in the UI (the **drift recall** tile and the annotated
*Planted traps* tab) and in the report's `evaluation` block.

## Design notes

- **FHIR is authoritative.** The chart is the patient's real data; the note is
  the thing on trial. A note that misstates the chart is contradicted — the
  auditor and judges recompute derivable facts (age from `birthDate`) rather
  than trusting the note.
- **Strict JSON everywhere it matters.** The auditor, each judge, and the scorer
  use Claude tool use with `strict` schemas, so the pipeline never parses prose.
- **Independent judges, not an average.** Three different framings
  (patient-safety, documentation-integrity, false-positive-skeptic) vote
  separately against all three sources; a split verdict is shown as a split.
- **Judges verify, they don't rubber-stamp.** Each judge sees the transcript and
  the FHIR chart and re-checks the flag itself — so a chart-based catch is
  confirmed against the chart, not the auditor's paraphrase of it.
- **Authority is enforced in code, not just asked for.** Beyond the shared
  `EVIDENCE_AUTHORITY` prompt, `apply_evidence_weighting` deterministically bumps
  a contradiction against an authoritative source up one severity level, so the
  riskiest drifts rank first for the judges. It records `severity_raw` and a
  `weight_reason`, so every escalation is explainable.
- **Consequences, not just labels.** Each confirmed drift carries a
  *clinical-harm-if-trusted* sentence — what could go wrong if the next clinician
  believes the note.
- **Runs on real data.** The same pipeline audits Abridge's own clinician notes,
  or regenerates a note to stress-test our scribe.

Everything is synthetic; no real patient data is present.
