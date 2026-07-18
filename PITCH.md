# Driftwatch — the safety net for AI clinical scribes

## The problem (30 seconds)

Ambient AI scribes (Abridge and peers) now write the clinical note for millions
of visits. The failure mode nobody sees isn't a garbled note — it's a
**confident, fluent note that quietly lies about the visit**:

- lists a medication the patient said they *stopped* as still active,
- hardens a hedged *"I don't think so"* into a clean *"denies,"*
- invents a repeat vital sign that was never taken,
- states the wrong age against the patient's own chart.

These are invisible to a human skimming a plausible note — and the next
clinician trusts them. **That's a patient-safety problem hiding inside good
grammar.**

## What we built

**Driftwatch is an adversarial red-team harness that treats the scribe as a
system under test.** For every claim in a generated note it asks: *is this
actually true?* — checking three sources in a strict authority order:

1. **FHIR chart (authoritative)** — the patient's real recorded data.
2. **Visit transcript** — what was actually said.
3. **After-visit summary** — corroborating context.

Every flag is escalated to **three independent Claude judges** (patient-safety,
documentation-integrity, false-positive-skeptic) who each re-verify against the
chart and transcript themselves and vote. **Disagreement is surfaced as a split,
never averaged away** — because in medicine, "the reviewers didn't agree" is
exactly what a human should see.

## Why it's credible — we score ourselves

We don't just claim it works. Synthetic cases ship **planted ground-truth
errors**, and the harness grades itself on **drift recall** — of the errors the
scribe *actually made*, how many did we catch. (Traps the scribe handled
faithfully don't count — silence there is correct, and we refuse to inflate the
number with them.)

> **Drift recall: __%__** across N synthetic stress tests *(filled from the latest batch)*.

## The catches are real — on real data

Running against **Abridge's own clinician notes** (the `synthetic-ambient-fhir-25`
corpus), with zero planted traps, the harness caught genuine in-the-wild drift:

| Encounter | Drift caught | Judge verdict |
|---|---|---|
| COVID-19 admission | Note invented **repeat vitals (BP 97/53, RR 24.15)** never recorded in transcript or chart | confirmed 3–0 |
| COVID-19 admission | Age stated **81**; chart `birthDate` → actually **80** | confirmed 3–0 |
| Annual wellness | Age stated **47**; chart → actually **46** | confirmed 3–0 |
| Annual physical | *"Social isolation newly documented"* — chart shows it's a **pre-existing** problem | confirmed 3–0 |

Each confirmed drift carries a one-line **clinical-harm-if-trusted** statement —
the *so what* a clinician needs.

Critically, the harness is **precise, not trigger-happy**: it correctly *cleared*
an age of 31 that matched the chart, and rejected demographic "omissions"
(marital status, education) as clinically irrelevant noise. It recomputes facts
from the raw chart rather than pattern-matching.

## Why this wins

- **Real partner data, real catches** — not a toy demo.
- **Self-scoring with an honest metric** — we measure recall on actual drift and
  show our misses.
- **Verifiability by design, no fine-tuning** — reliability comes from structure
  (three sources, strict-JSON tool use, an adversarial judge panel), so it's
  auditable and model-agnostic.
- **Built for the human in the loop** — splits and harm statements are
  first-class, because a safety tool that hides uncertainty isn't a safety tool.

## 90-second demo script

1. Open on the **COVID-19 admission** case (pre-selected). *"This is a real
   clinician note from Abridge's dataset."* → **Run harness.**
2. Land on results. Point at the **fabricated repeat vitals** finding →
   *"The note reports a repeat blood pressure that was never taken."* Read the
   **clinical-harm** callout.
3. Open the **age** finding → *"The judges recomputed age from the FHIR birth
   date and caught an off-by-one — independently, all three."*
4. Switch to a **synthetic** run → **Planted traps** tab → *"We plant known
   errors and grade ourselves. Here's our drift recall, and here's a miss we
   don't hide."*
5. Close: *"An AI wrote the note. A different set of AIs, checking the patient's
   real chart, caught where it lied — and told us how sure they were."*
