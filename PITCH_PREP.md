# Driftwatch — Pitch Prep & Judging Playbook

Everything you need to walk into first-round judging confident. Read this once
end-to-end, then skim the **Wow factors** and **Q&A** the morning of.

**One-line pitch:** *An AI scribe wrote the clinical note. A panel of AIs,
checking the patient's real FHIR chart, catches where it quietly lied — and tells
you how sure they are and what harm it could cause.*

**The problem in one breath:** Ambient AI scribes (Abridge and peers) now write
the note for millions of visits. The dangerous failure isn't a garbled note — it's
a *fluent, plausible* one that invents a physical exam, hardens a hedged "I don't
think so" into "denies," lists a stopped medication as active, or misstates the
patient's age against their chart. These are invisible to a human skimming a
good-looking note, and the next clinician trusts them. **That's a patient-safety
problem hiding inside good grammar — and we built the safety net for it.**

---

## 1. The WOW factors — what to emphasize (ranked)

Lead with these. Each has a one-liner to say and the reason it lands.

### ⭐ 1. We audit the scribe itself (the meta move)
> *"Everyone else is building a scribe. We built the thing that checks the
> scribe. At an Abridge event, we're the guardrail for the exact product you
> ship."*

**Why it wows:** it's the fresh angle (Creativity, 25%). It's directly relevant
to the host. It reframes AI safety as a product Abridge *needs*, not a competitor.

### ⭐ 2. Three-source grounding with FHIR as the authority
> *"Every claim in the note is checked against three sources — the patient's FHIR
> chart, the visit transcript, and the after-visit summary — and the chart wins.
> If the note says the patient is 81 and the chart's birth date says 80, the note
> is wrong, not the chart."*

**Why it wows:** it's not "ask the LLM if the note looks right." It's grounded in
the patient's actual structured data, and it **recomputes derivable facts** (age
from `birthDate`, etc.) rather than pattern-matching. Show the age catch live.

### ⭐ 3. An adversarial 3-judge ensemble that surfaces disagreement
> *"Each flag goes to three independent judges with different jobs — patient
> safety, documentation integrity, and a false-alarm skeptic. When they disagree,
> we show the split. We never average it away — in medicine, 'the reviewers
> didn't agree' is exactly what a human should see."*

**Why it wows:** shows engineering judgment and clinical humility. Averaging would
hide the most important cases. This is a deliberate safety-architecture decision.

### ⭐ 4. The judges verify against the chart themselves — they don't rubber-stamp
> *"The judges don't just trust the auditor's summary. Each one re-reads the
> transcript and the FHIR chart and re-derives the fact. We literally watched a
> judge recompute the patient's age from the birth date."*

**Why it wows:** it's the difference between a real verification system and a
telephone game. It's why our confirmations are trustworthy.

### ⭐ 5. Clinical-harm-if-trusted statements
> *"Every confirmed error comes with a one-line clinical consequence — what
> happens if the next clinician believes this note. A fabricated lung exam →
> 'a clinician would think auscultation was done and anchor on a false finding.'"*

**Why it wows:** turns a list of flags into clinical stories. It's the "so what"
judges (and clinicians) care about.

### ⭐ 6. Honest self-scoring (drift recall)
> *"We grade ourselves. On synthetic notes with planted errors, we measure how
> many real drifts we catch — and we refuse to inflate the number: if the scribe
> handled a trap correctly, staying silent is right, not a miss. We even show our
> misses."*

**Why it wows:** most hackathon teams *claim* their thing works. We *measure* it,
with an honest metric that could make us look worse — which is exactly why judges
trust it.

### ⭐ 7. Real catches on real Abridge data (not a toy)
> *"Running on Abridge's own `synthetic-ambient-fhir-25` encounters, with zero
> planted traps, we caught a fabricated physical exam, an unreported cardiac lab,
> an implausible albumin value, and an age error — all confirmed by the judges."*

**Why it wows:** Impact + Execution. It works on the partner's real data format.

### ⭐ 8. Precise, not trigger-happy
> *"It's not a smoke alarm that goes off at toast. It cleared an age that matched
> the chart, and it rejected irrelevant 'omissions' like marital status as
> clinically trivial. It flags what matters and stays quiet on what doesn't."*

**Why it wows:** anticipates the "doesn't it over-flag?" skepticism and disarms it.

### ⭐ 9. Strict-JSON tool use everywhere, no fine-tuning
> *"Every reasoning step — auditor, each judge, the scorer — uses Claude tool use
> with strict schemas, so the pipeline never parses free text. Reliability comes
> from architecture, not fine-tuning — which means it's auditable and works with
> any model."*

**Why it wows:** technical credibility (Technical Complexity, 20%) and a smart
answer to "did you fine-tune?" (no — and here's why that's a feature).

---

## 2. How everything works — the guided tour

Use this to explain any component, where the idea came from, and why it exists.

### The pipeline at a glance
```
transcript ─▶ note_generator ─▶ auditor ─▶ judge_ensemble ─▶ scorer ─▶ report
 (real Abridge   (SOAP note =     (claim-by-   (3 independent   (self-
  encounter OR    system under     claim vs 3   judges, vote +    grades vs
  synthetic w/    test)            sources)     harm + split)     planted traps)
  planted traps)
```

### Stage 1 — Transcript source (`dataset.py`, `transcript_generator.py`)
- **What:** either a **real Abridge encounter** (transcript + clinician note +
  FHIR chart + after-visit summary, from `synthetic-ambient-fhir-25`) or a
  **synthetic** transcript we generate with deliberately **planted traps**
  (stopped medication, hardened negative, dismissed symptom, buried detail) whose
  ground truth we record.
- **Where it came from:** Abridge provided the dataset; we built the loader that
  extracts the FHIR chart context and the synthetic generator for stress-testing.
- **Why:** real data proves it works in the wild; synthetic data with known
  answers lets us *measure* ourselves (Stage 5).
- **Workflow meaning:** this is the raw material a real scribe would see.

### Stage 2 — Note generator = the system under test (`note_generator.py`)
- **What:** turns a transcript into a SOAP note via Claude. This *is* the "AI
  scribe" we're auditing.
- **Why:** to have something to catch drifting. We treat it as a black box under
  test — the same way you'd red-team any model.
- **Workflow meaning:** stands in for Abridge's note-generation step.

### Stage 3 — The auditor (`auditor.py`)
- **What:** decomposes the note into individual clinical claims and labels each
  **supported / unsupported / contradicted / omitted**, with an `evidence_source`
  (transcript / fhir / both / neither) and severity. Uses strict-JSON tool use.
- **The three sources & authority:** checks the **transcript**, the **FHIR chart**
  (authoritative — real recorded data), and the **after-visit summary**
  (corroborating; it echoes the note so it can't confirm a claim alone, but a
  contradiction is flagged).
- **The `EVIDENCE_AUTHORITY` model:** authority isn't fixed — it shifts with the
  claim type. Objective facts (vitals, labs, coded dx, meds) → the chart. Clinical
  judgment (assessment, what's concerning) → the clinician. The patient's own body
  and behavior (symptoms, "I stopped taking it") → the patient. So a note that
  adopts a patient's self-reassurance as clinical fact is flagged.
- **Where it came from:** the core insight that a faithful note can be grounded in
  the chart even if not spoken aloud — so you must check the chart before flagging,
  and recompute derivable values rather than assume.
- **Why:** this is the heart — turning "does this look right?" into a claim-by-claim,
  source-grounded trace.
- **Workflow meaning:** the first-pass reviewer that catches candidate errors.

### Stage 4 — The judge ensemble (`judge_ensemble.py`)
- **What:** every flagged claim goes to **three independent Claude judges** with
  distinct lenses — **patient-safety**, **documentation-integrity**, and
  **false-positive-skeptic** — who each **see all three sources** and vote
  confirm/reject + severity, plus a **`harm_if_trusted`** sentence.
- **Disagreement handling:** if they don't agree, we mark it a **split** and show
  it — never averaged.
- **Where it came from:** LLM-as-judge is unreliable solo; three adversarial
  framings (especially the skeptic) reduce false confirmations, and the skeptic
  specifically guards against over-flagging.
- **Why:** confidence through independent verification, and honesty about
  uncertainty.
- **Workflow meaning:** the review board that decides which flags a clinician
  should actually see, and how urgent.

### Stage 5 — The self-scoring evaluator (`scorer.py`)
- **What:** for synthetic cases, aligns the harness's findings to the planted
  traps and computes **drift recall**. Crucially it asks two questions per trap:
  *did the scribe actually drift?* and *if so, did we catch it?* Recall counts
  only traps the scribe drifted on — faithful handling the auditor correctly
  ignored is **not** a miss.
- **Where it came from:** we noticed a naïve "caught / planted" ratio punished the
  harness for the scribe being *good*. We fixed the metric to be honest.
- **Why:** credibility. It's the number that proves the harness works, with misses
  surfaced.
- **Workflow meaning:** the QA metric a deployment team would track over time.

### Orchestration & UI (`orchestrator.py`, `main.py`, `static/index.html`)
- **Orchestrator:** plain-Python loop, aggregates a JSON report (no LLM calls of
  its own — deterministic control flow).
- **UI:** FastAPI + vanilla JS. Three panels — pick an encounter, run, and trace
  each finding to its source with per-judge votes, the harm callout, the split
  badge, and a **drift-recall tile**.
- **`llm.py`:** one shared Claude client; `claude-sonnet-4-6`; strict-JSON tool
  helper. Same model for note, audit, and judges = apples-to-apples.

---

## 3. Q&A — be ready for first-round judges

Answers are written to be said out loud in ~15–20 seconds.

### Impact / product
**Q: Isn't this just a QA layer, not a real workflow?**
> It's the safety net every ambient-scribe deployment needs *before* a note
> reaches the chart. Abridge can't ship notes a clinician blindly trusts without
> something catching silent drift — that's us. It makes their product safer to
> ship, which is a workflow, not an add-on.

**Q: Who's the user? Where does it sit?**
> It runs between the scribe and the EHR. The clinician sees only the confirmed,
> ranked flags with the harm statement — a 10-second review instead of re-reading
> the whole note against the chart.

**Q: How big is the pain point?**
> Ambient scribes touch millions of visits. Even a small silent-error rate is huge
> at that volume, and each one propagates to the next clinician. This is a
> scale problem, not an edge case.

**Q: Why would Abridge (or any scribe vendor) want this?**
> Trust is their whole moat. A public, auditable safety net that catches and
> explains drift is a competitive advantage and a regulatory story.

### Technical
**Q: Did you fine-tune anything?**
> No — deliberately. Reliability comes from architecture: three sources, strict
> JSON tool use, and an adversarial judge panel. That makes it auditable and
> model-agnostic — swap the model and it still works. Fine-tuning would've been
> less robust and un-provable in a day.

**Q: What stops the auditor/judges from hallucinating?**
> Three things: strict-JSON tool schemas so output is structured, grounding every
> claim in named sources (with the chart authoritative), and an independent
> 3-judge vote where a skeptic is specifically tasked with refuting over-eager
> flags. Disagreement is surfaced, not hidden.

**Q: Isn't LLM-as-judge unreliable?**
> Solo, yes. We use three *independent* framings and require them to re-verify
> against the sources themselves, not trust the auditor. And we never average —
> a split is shown as a split so a human adjudicates the hard ones.

**Q: What's actually technically hard here?**
> The claim-type authority model, the independent-judge design with surfaced
> disagreement, and an *honest* self-scoring metric that refuses to count faithful
> handling as a catch. Getting the metric right was the subtle part.

**Q: How do you know it's not just over-flagging everything?**
> It cleared a correct age and rejected clinically irrelevant omissions like
> marital status. The false-positive-skeptic judge exists exactly for this, and
> our metric would expose it if we were noisy.

**Q: What model, and how much does a run cost/take?**
> Claude Sonnet 4.6 across the board. A full case is ~30–60 seconds — transcript
> (if synthetic), note, audit, three judges per flag in parallel, and scoring.

**Q: How does the FHIR piece actually work?**
> We parse the encounter's FHIR resources — problem list, medications, demographics,
> Conditions/Observations/Procedures/Immunizations — into a structured context the
> auditor and judges both see, and we recompute derivable facts like age from
> `birthDate` against the encounter date.

### Data / ethics / limits
**Q: Is this real patient data?**
> No — it's Abridge's provided synthetic-but-FHIR-structured corpus. No real PHI.

**Q: What are the limitations / what would you do next?**
> Today it's a batch/interactive audit. Next: stream it inline as the note is
> written, expand the derivable-fact library (dosing, interactions), and calibrate
> severity against clinician-labeled ground truth. And a human-in-the-loop
> adjudication queue for the splits.

**Q: What happens on a split — who decides?**
> A human. That's the point — we escalate genuine ambiguity to a clinician instead
> of pretending to resolve it. The split *is* the output for those cases.

### The rules question (be ready, it's a DQ trap)
**Q: What did you build today vs. before?**
> [Answer truthfully and specifically — name the components built during the event.
> If anything is scaffolding from before, say so plainly. See README's "What we
> built at the hackathon" section and make sure it's accurate to your timeline.]

**Q: Is the repo public?**
> Yes. [Confirm before judging.]

---

## 4. The 3-minute live demo run-of-show

1. **(0:00–0:30) Problem + one-liner.** Say the "fluent note that lies" framing.
   Land the "we audit the scribe itself" hook.
2. **(0:30–1:45) The catch.** COVID Abridge case (pre-run so it's loaded). Click
   the **fabricated auscultation** finding → read the claim → *"this exam appears
   in neither the transcript nor the chart; the note invented it; all three judges
   confirmed."* Point at the **Clinical risk if trusted** callout.
3. **(1:45–2:30) Depth + trust.** Click the **age** (or troponin) finding → *"a
   judge recomputed age from the FHIR birth date."* Show a **split** if present →
   *"we surface disagreement, never average it."*
4. **(2:30–3:00) Proof + close.** Traps tab / **drift-recall tile** → *"we grade
   ourselves honestly."* Close on: *"An AI wrote the note — a panel of AIs,
   checking the patient's real chart, caught where it lied."*

**Demo hygiene:** pre-run the hero case so latency doesn't bite. Have the exact
findings you'll click chosen in advance. Pull your teammate's latest UI first.
Have a backup screenshot/recording in case the live run stalls.

---

## 5. 30-second morning checklist
- [ ] Repo is **public**.
- [ ] README "What we built" section is **accurate to your timeline**.
- [ ] App runs; hero COVID case pre-loaded and pre-run.
- [ ] You can each say the one-liner from memory.
- [ ] You know which 2–3 findings you'll click, in order.
- [ ] Backup recording/screenshots ready.
- [ ] Submission form done: public repo link + 1-min video + both teammates added.
