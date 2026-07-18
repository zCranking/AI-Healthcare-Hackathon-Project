# Clinical Note Drift Harness

An adversarial red-team harness that catches when an AI-generated clinical note
**silently drifts** from what was actually said in a doctor-patient transcript.

Ambient scribes (Abridge and friends) turn a visit conversation into a SOAP
note. The dangerous failure isn't a garbled note — it's a *plausible* one that
quietly asserts a medication the patient stopped, hardens a hedged "I don't
think so" into a clean denial, or drops a red-flag symptom buried in a tangent.
This harness treats the note-writer as a system under test and hunts for exactly
those drifts.

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
| 3 | `drift_harness/auditor.py` | Traces every note claim to the transcript; flags unsupported / contradicted / omitted (strict-JSON tool use) |
| 4 | `drift_harness/judge_ensemble.py` | 3 independently-framed Claude judges score each flag; **disagreement is surfaced, never averaged** |
| 5 | `drift_harness/orchestrator.py` | Plain-Python loop over N cases → aggregated JSON report |
| — | `drift_harness/dataset.py` | Loads the Abridge `synthetic-ambient-fhir-25` encounters so the harness runs on real partner data |
| 6 | `main.py` + `static/index.html` | FastAPI + vanilla-JS 3-panel UI (transcript · note · flagged discrepancies) |

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

## Design notes

- **Strict JSON everywhere it matters.** The auditor and each judge use Claude
  tool use with `strict` schemas, so the pipeline never parses prose.
- **Independent judges, not an average.** Three different framings
  (patient-safety, documentation-integrity, false-positive-skeptic) vote
  separately; a split verdict is shown as a split.
- **Ground truth for evaluation.** Synthetic cases ship the planted traps, so
  you can see whether the harness caught what it was supposed to.
- **Runs on real data.** The same pipeline audits Abridge's own clinician notes,
  or regenerates a note to stress-test our scribe.

Everything is synthetic; no real patient data is present.
