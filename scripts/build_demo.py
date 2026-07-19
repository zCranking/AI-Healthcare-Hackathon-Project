"""Regenerate demo/sample_run.json — the saved run the static demo replays.

`static/index.html` falls back to demo mode when no backend is reachable (e.g.
on GitHub Pages) and renders this file instead of calling /api/*. Re-run this
after changing the pipeline so the published demo reflects current behaviour.

    python scripts/build_demo.py                # default hero case
    python scripts/build_demo.py --index 3      # a different Abridge encounter
    python scripts/build_demo.py --max-findings 8

Requires ANTHROPIC_API_KEY (it performs a real run).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from drift_harness import dataset, llm, orchestrator

_ROOT = Path(__file__).resolve().parent.parent
_OUT = _ROOT / "static" / "demo" / "sample_run.json"

# COVID-19 admission: the auditor catches fabricated repeat vitals against the
# FHIR chart, which is the sharpest single demonstration in the corpus.
_DEFAULT_INDEX = 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=int, default=_DEFAULT_INDEX,
                    help=f"Abridge encounter index (default {_DEFAULT_INDEX})")
    ap.add_argument("--max-findings", type=int, default=6,
                    help="cap on flags escalated to the judges (default 6)")
    ap.add_argument("--regenerate-note", action="store_true",
                    help="regenerate the note with our scribe instead of auditing Abridge's")
    args = ap.parse_args()

    calls = 0
    _orig = llm.client.messages.create

    def _counting(**kw):
        nonlocal calls
        calls += 1
        return _orig(**kw)

    llm.client.messages.create = _counting

    print(f"model={llm.MODEL}  running Abridge case [{args.index}] ...")
    started = time.time()
    result = orchestrator.run_abridge(
        [args.index],
        regenerate_note=args.regenerate_note,
        max_findings=args.max_findings,
    )[0]
    elapsed = time.time() - started

    print(f"  {elapsed:.1f}s across {calls} LLM calls")
    for k in ("claims_audited", "flagged", "escalated_to_judges",
              "confirmed_discrepancies", "high_severity_confirmed"):
        print(f"    {k:24} {result.summary.get(k)}")

    payload = {
        "_comment": (
            "A real, unedited run of the Veritas Charting pipeline, saved so the UI is "
            "explorable as a static page with no API key. Regenerate: python scripts/build_demo.py"
        ),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": llm.MODEL,
        "elapsed_seconds": round(elapsed, 1),
        "llm_calls": calls,
        "encounters": dataset.list_titles(),
        "run": result.to_dict(),
    }

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {_OUT.relative_to(_ROOT)}  ({_OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
