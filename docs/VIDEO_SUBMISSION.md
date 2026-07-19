# 1-Minute Pitch Video — What to Include

The submission requires a **~1 minute** video that **highlights the specific
features, code, and functionality your team built during the hackathon**. Judges
must clearly see what *you* made. Everything below is tuned to that rule.

> A detailed, word-for-word timed script lives in `DEMO_VIDEO_SCRIPT.md`. This
> file is the **checklist of what must be in the video** and why.

---

## The 5 things this video MUST show

1. **The problem, in one sentence** — AI scribes write notes that *fluently lie*
   (invent findings, harden hedges), and those errors are invisible and trusted.
2. **What you built** — an agentic pipeline that audits the scribe against three
   sources (FHIR chart, transcript, after-visit summary) with a 3-judge ensemble.
3. **A real catch, on screen** — the fabricated physical-exam finding on the real
   Abridge COVID case, with the **Clinical risk if trusted** callout visible.
4. **The trust/depth moment** — a judge recomputing age from the FHIR birth date,
   and/or a **judges-split** badge (we surface disagreement, never average it).
5. **The proof + close** — the **drift-recall** self-scoring, and the one-line
   close: *"An AI wrote the note; a panel of AIs, checking the patient's real
   chart, caught where it lied."*

If you only have 60 seconds, those five beats — in that order — are the video.

---

## Recommended structure (timeboxed to ~60s)

| Time | Beat | On screen |
|------|------|-----------|
| 0:00–0:10 | Hook + problem | Title card or the app picker; say the "fluent note that lies" line |
| 0:10–0:20 | What we built (three sources + 3 judges) | Results summary strip after a run |
| 0:20–0:40 | The catch + harm | Click the fabricated-auscultation finding; show the red harm callout |
| 0:40–0:52 | Depth + trust | A judge vote recomputing age from FHIR; a split badge if present |
| 0:52–1:00 | Proof + close | Planted-traps tab / drift-recall tile; the closing line |

---

## Must-do's for compliance & clarity

- **Show the actual app and code/functionality you built** — screen-record the
  running product, not slides of concepts. Judges must identify your original work.
- **Name it as your hackathon build** — say "we built this today" (only if true)
  so there's no ambiguity about original contributions.
- **Show it on real Abridge data** — say the encounter is from the provided
  `synthetic-ambient-fhir-25` dataset. It signals real-world fit.
- **Make the link accessible** — unlisted YouTube / public Loom / direct file the
  judges can open without a login.

## Do NOT
- Don't spend time on the picker/loading UI — pre-run so results are on screen fast.
- Don't read the whole SOAP note aloud — point at the *one* invented claim.
- Don't over-explain architecture — the *catch* and the *harm* sell it; save
  depth for live Q&A.
- Don't let a 30–60s live run happen on camera — record the results already loaded.

---

## Production tips
- **Pre-run the COVID case** so the results screen is loaded before you record.
- Record at 1080p, zoom the browser to ~125% so finding cards and the harm
  callout are legible on a phone.
- Keep the cursor deliberate; pause ~1s on the harm callout and the recall tile.
- Add 2–3 on-screen text captions for the key phrases ("invented exam finding",
  "recomputed from FHIR", "we grade ourselves") — judges often watch muted.
- One clean take of narration over the screen recording beats a fancy edit.

## The exact words to open and close with
- **Open:** *"AI scribes now write the clinical note for millions of visits — and
  the dangerous failure is a fluent note that invents things that were never said.
  We built Veritas Charting to catch them."*
- **Close:** *"An AI wrote the note. A panel of AIs, checking the patient's real
  FHIR chart, caught where it lied — and told us why it matters."*
