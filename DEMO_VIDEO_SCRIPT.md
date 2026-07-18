# 60-second demo video script — Driftwatch

**Goal:** show the *agentic pipeline* we built today catching a real, dangerous
error in a real Abridge clinician note — with judges that verify against the
FHIR chart and explain the clinical harm.

**Before you hit record:** run the COVID-19 admission Abridge case once so it's
cached and the results screen is already loaded. Have the finding you'll click
picked out. Keep the cursor deliberate. Target 55–60s.

---

### [0:00–0:12] The problem (talk over the picker screen)

> "AI scribes like Abridge now write the clinical note for millions of visits.
> The dangerous failure isn't a garbled note — it's a *fluent* one that invents a
> finding that was never there. Those errors are invisible, and the next clinician
> trusts them. **We built Driftwatch — an adversarial harness that catches them.**"

### [0:12–0:22] What it does (start the run, or cut to loaded results)

> "For every claim in the note, we check three sources — the patient's **FHIR
> chart**, the **transcript**, and the **after-visit summary** — then escalate each
> flag to **three independent AI judges**. Everything you'll see we built today."

### [0:22–0:40] The catch (click the fabricated-finding result)

> "This is a real clinician note from Abridge's dataset — a COVID admission. Our
> auditor flagged this: the note claims *'findings consistent with pneumonia on
> auscultation'* — **a physical exam that appears in neither the transcript nor
> the chart. The note invented it.** All three judges confirmed it."

*(point at the red "Clinical risk if trusted" callout)*

> "And it tells us *why it matters*: a clinician would believe a lung exam was
> done and anchor on a false positive finding."

### [0:40–0:52] Depth + trust (click the age or troponin finding, then traps tab)

> "The judges don't rubber-stamp — here one **recomputed the patient's age from
> the FHIR birth date** and caught an error the note got wrong. And when the judges
> disagree, **we show the split — we never average it away.**"

### [0:52–1:00] Proof + close (traps tab / recall tile)

> "We even grade ourselves: on synthetic notes with planted errors, we measure how
> many real drifts we catch. **An AI wrote the note — and a panel of AIs, checking
> the patient's actual chart, caught where it lied.**"

---

## On-screen b-roll checklist
- [ ] Picker → COVID case selected → "Run harness"
- [ ] Results summary strip (claims audited / confirmed drifts)
- [ ] Fabricated-auscultation finding + **Clinical risk if trusted** callout
- [ ] Age/troponin finding with FHIR reasoning in a judge vote
- [ ] A "judges split" badge (if present) — or say the line over the ensemble panel
- [ ] Planted traps tab / drift-recall tile

## Say-this-in-Q&A (not in the video, but be ready)
- **"Isn't this just QA?"** → It's the safety net every ambient-scribe deployment
  needs before a note reaches the chart — it makes Abridge's own product safer to ship.
- **"What's technically hard?"** → Independent judges with surfaced disagreement,
  a claim-type authority model, and self-scoring that refuses to count faithful
  handling as a catch. Strict-JSON tool use throughout; no fine-tuning.
