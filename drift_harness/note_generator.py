"""Module 2 - the system under test.

Takes one transcript, produces a structured SOAP clinical note via Claude. This
is intentionally a plausible, everyday ambient scribe - not a hardened one - so
the harness has something real to catch drifting.
"""

from __future__ import annotations

from .llm import generate_text

_SYSTEM = (
    "You are an ambient clinical scribe. Given a doctor-patient visit transcript, write a concise "
    "clinical note in SOAP format. Use exactly these four markdown headers, in order:\n"
    "**Subjective:**\n**Objective:**\n**Assessment:**\n**Plan:**\n\n"
    "Write in standard clinical prose. Be efficient - summarize, don't transcribe. Do not invent "
    "vitals or exam findings that were not stated. Return only the note."
)


def generate_note(transcript: str) -> str:
    """Generate a SOAP note for a transcript string."""
    user = f"Transcript:\n\n{transcript}\n\nWrite the SOAP note."
    return generate_text(_SYSTEM, user, max_tokens=2000)


if __name__ == "__main__":
    import sys

    from .transcript_generator import generate_case, _SCENARIOS

    if len(sys.argv) > 1:
        text = open(sys.argv[1], encoding="utf-8").read()
    else:
        text = generate_case(_SCENARIOS[0]).transcript
    print(generate_note(text))
