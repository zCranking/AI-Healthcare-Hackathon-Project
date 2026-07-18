"""Shared Anthropic client and thin call helpers.

One place to configure the model and how we talk to Claude, so every pipeline
module stays small. Key comes from the ANTHROPIC_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()  # pick up .env in local dev; no-op if absent

# The system under test and its judges all run on the same model so the demo is
# apples-to-apples. Sonnet 4.6 is fast enough for an interactive frontend.
MODEL = "claude-sonnet-4-6"

if not os.environ.get("ANTHROPIC_API_KEY"):
    # Fail loud and early rather than deep inside an API call.
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, "
        "or export ANTHROPIC_API_KEY in the shell."
    )

client = anthropic.Anthropic()


def generate_text(system: str, user: str, max_tokens: int = 4096) -> str:
    """One-shot text generation. Returns the concatenated text blocks."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def call_tool(
    system: str,
    user: str,
    tool: dict[str, Any],
    max_tokens: int = 8000,
) -> dict[str, Any]:
    """Force a single structured tool call and return its validated input dict.

    `tool` is a standard Anthropic tool definition with a strict JSON schema.
    tool_choice forces the model to emit exactly that tool, so the caller always
    gets JSON matching the schema instead of prose it has to parse.
    """
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise RuntimeError(f"Model did not call tool {tool['name']!r}; got {resp.stop_reason}")
