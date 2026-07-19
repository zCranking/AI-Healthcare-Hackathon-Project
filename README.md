# Veritas Charting

**An adversarial red-team harness that catches when an AI-generated clinical note
silently drifts from what was actually said in a doctor-patient visit.**

[![Live demo](https://img.shields.io/badge/live%20demo-open-2f6fdb)](https://zcranking.github.io/AI-Healthcare-Hackathon-Project/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab)](https://www.python.org/)
[![Model](https://img.shields.io/badge/model-claude--sonnet--4--6-8a63d2)](https://docs.claude.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

<!-- ═══════════════════════════════════════════════════════════════
     SCREENSHOT 1 — HERO  (the single most important image)
     What to capture: the results view on the COVID-19 admission case,
     with a HIGH-severity confirmed finding visible in the right panel.
     Full browser width, light mode, ~1600px wide.
     Save as: assets/hero.png
     ══════════════════════════════════════════════════════════════ -->

![Veritas Charting — flagged discrepancies traced to source](assets/hero.png)

> Ambient scribes turn a visit into a SOAP note. The dangerous failure isn't a
> garbled note — it's a **fluent, plausible** one that quietly asserts a
> medication the patient stopped, or hardens a hedged *"I don't think so"* into
> a clean *"denies."* This harness treats the note-writer as a system under test
> and hunts for exactly those drifts.

**[▶ Try the live demo](https://zcranking.github.io/AI-Healthcare-Hackathon-Project/)** — a real
saved pipeline run, no API key required.

## How it works

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

<!-- ═══════════════════════════════════════════════════════════════
     SCREENSHOT 2 — EVIDENCE TRACE
     What to capture: ONE finding expanded, showing its evidence quote and
     all three judge votes side by side. Ideally pick a finding where the
     judges SPLIT — that's the differentiator no other project will have.
     Crop tight to the card, ~1000px wide.
     Save as: assets/judges.png
     ══════════════════════════════════════════════════════════════ -->

![Three independent judges voting on a single flagged claim](assets/judges.png)

## What's in here

Built during the Abridge Hackathon — the entire agentic pipeline is original
work, with no pre-existing product underneath:

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

### Static demo (no API key)

`static/index.html` probes for a backend at startup. With none reachable it
falls back to **demo mode** and replays a real saved run from
`static/demo/sample_run.json`, so the whole UI stays explorable as a plain static page.
That's what the [live demo](https://zcranking.github.io/AI-Healthcare-Hackathon-Project/)
serves — one HTML file plus one JSON file, no build step and no server.

To publish it, point GitHub Pages at the repo root and open
`static/index.html`, or regenerate the fixture after changing the pipeline:

```bash
python scripts/build_demo.py
```

## Repo map

```
drift_harness/     the pipeline (see the module table above)
main.py            FastAPI app — serves the UI and /api/*
static/index.html  the entire frontend: no build step, no external assets
demo/              saved run replayed by the static demo
scripts/           regenerate the demo fixture
docs/              hackathon pitch, demo script, judging prep
synthetic-ambient-fhir-25/   the provided Abridge corpus (synthetic)
results/           JSON reports written by the orchestrator (gitignored)
```

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

<!-- ═══════════════════════════════════════════════════════════════
     SCREENSHOT 3 — SELF-SCORING
     What to capture: run a SYNTHETIC case, then screenshot the summary
     tiles (drift recall) together with the "Planted traps" tab showing
     each trap marked caught / faithful / missed.
     This is the credibility shot — it proves the harness measures itself.
     Save as: assets/drift-recall.png
     ══════════════════════════════════════════════════════════════ -->

![Drift recall scored against planted ground-truth traps](assets/drift-recall.png)

## Performance

The pipeline is latency-bound by LLM round-trips, not compute. Latency tracks
**output** tokens, not input — a long system prompt is cheap, a long findings
list is not.

Measured on Abridge case `[1]` (COVID-19 admission), `max_findings=6`:

| Phase | Calls | Time | Note |
|-------|------:|-----:|------|
| Audit | 1 | **79.6s** | One sequential call; emitted 64 claims, 8 flagged |
| Judges | 18 | **8.4s** | 6 findings × 3 judges, dispatched as one parallel wave |
| **Total** | **19** | **~88s** | |

The judge ensemble dispatches every `(finding, judge)` pair into a **single
parallel wave** rather than judging findings one after another
(`judge_ensemble.py:judge_findings`). The votes are independent, so serializing
across findings was pure added latency — at 18 calls this is ~8s instead of
~51s.

That leaves the **audit call as ~90% of runtime**, and its cost scales with how
many claims it enumerates. Most of those are `supported` — they exist to show
audit coverage (the "claims audited" tile and the *All* filter), not because
anything downstream reads them. So there's a real tradeoff available:

| Lever | Effect |
|-------|--------|
| `max_findings` | Caps judge calls. Cheap now that judging is parallel — raising it costs little |
| Enumerating `supported` claims | The dominant cost. Dropping them would cut audit latency substantially at the price of the coverage view |
| Per-call variance | Individual Claude calls vary a lot run-to-run; one slow call can add 30–60s. Measure across several runs before concluding a change helped |

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
