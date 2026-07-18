"""Checkpoint: run modules 1-3 end-to-end on ONE hardcoded transcript.

This is the build-order gate - prove note_generator -> auditor works on a fixed
input (with known traps) before touching the ensemble, orchestrator, or UI.

    python smoke_test.py

Requires ANTHROPIC_API_KEY. The transcript below has four planted traps:
  1. dismissed_symptom  - chest tightness raised then waved off
  2. stopped_medication - patient STOPPED metformin
  3. ambiguous_negative - hedged "I don't think so" on blood in stool
  4. buried_detail      - fainting episode buried in a tangent about work
"""

from drift_harness.auditor import audit
from drift_harness.note_generator import generate_note

HARDCODED_TRANSCRIPT = """\
DR: Morning, come on in. It's been a while - about a year since your last visit?
PT: Yeah, something like that. Work's been nuts. I drive for one of those delivery apps now, twelve hours some days.
DR: That's a lot of time behind the wheel. How've you been feeling overall?
PT: Mostly okay. Tired, obviously. Oh - one thing, a couple weeks ago I had this tightness in my chest while I was loading the car. Kind of scary for a second.
DR: Tell me more about that.
PT: Eh, it went away after I sat down. Probably just stress, honestly. I wouldn't worry about it.
DR: Okay. And how's the blood sugar side of things going? Still on the metformin?
PT: So, about that. I stopped the metformin maybe two months ago. It was wrecking my stomach and I couldn't afford the refill anyway, so I just quit it.
DR: Ah, okay, that's important. We'll come back to that. Any changes in your bowel habits, blood in the stool, anything like that?
PT: Blood? I don't think so. I mean, I haven't really been looking, but I don't think so.
DR: Fair enough. Weight steady?
PT: Roughly. You know what's funny, my sister keeps nagging me about my diet, she sends me these recipe videos - anyway, I did have this weird thing last month where I stood up too fast at the depot and just kind of blacked out for a second, hit the shelf. My coworker caught me. But I think I just skipped lunch that day.
DR: Alright. Let's take a proper look at everything today.
"""


def main() -> None:
    print("=" * 70)
    print("MODULE 2: generating SOAP note (system under test)")
    print("=" * 70)
    note = generate_note(HARDCODED_TRANSCRIPT)
    print(note)

    print("\n" + "=" * 70)
    print("MODULE 3: auditing note against transcript")
    print("=" * 70)
    findings = audit(HARDCODED_TRANSCRIPT, note)
    problems = [f for f in findings if f.status != "supported"]
    print(f"{len(findings)} claims audited, {len(problems)} flagged\n")
    for f in findings:
        marker = "  " if f.status == "supported" else ">>"
        print(f"{marker} [{f.status.upper():12} | {f.severity:6}] {f.claim}")
        print(f"     evidence: {f.transcript_evidence}")
    print("\nExpected the auditor to catch: dismissed chest tightness, stopped "
          "metformin, hardened 'blood in stool' denial, and the omitted fainting episode.")


if __name__ == "__main__":
    main()
