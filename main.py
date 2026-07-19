"""Module 6 - FastAPI app.

Endpoints:
  GET  /                -> the single-page UI
  GET  /api/abridge     -> list of Abridge encounters (for the dropdown)
  POST /api/run         -> run one case through the full pipeline, return the result
  GET  /api/results     -> the most recent runs (newest first)

Run:  uvicorn main:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from drift_harness import dataset, orchestrator
from drift_harness.transcript_generator import generate_cases

_STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Veritas Charting")
app.mount("/static", StaticFiles(directory=_STATIC), name="static")

# Newest-first in-memory history so the GET endpoint has something to serve.
_HISTORY: list[dict[str, Any]] = []
_MAX_HISTORY = 25


class RunRequest(BaseModel):
    mode: Literal["synthetic", "abridge", "custom"]
    index: Optional[int] = None          # abridge: which encounter
    regenerate_note: bool = False        # abridge: regenerate note vs audit provided one
    transcript: Optional[str] = None     # custom: pasted transcript
    note: Optional[str] = None           # custom: optional pasted note
    max_findings: int = 6                # cap on flags escalated to the judges


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/api/abridge")
def abridge_index() -> list[dict[str, Any]]:
    return dataset.list_titles()


@app.get("/api/results")
def results() -> list[dict[str, Any]]:
    return _HISTORY


@app.post("/api/run")
def run(req: RunRequest) -> dict[str, Any]:
    if req.mode == "synthetic":
        case = generate_cases(1)[0]
        from dataclasses import asdict
        result = orchestrator.run_case(
            transcript=case.transcript,
            note=None,
            source="synthetic",
            label=case.scenario,
            ground_truth_traps=[asdict(t) for t in case.traps],
            max_findings=req.max_findings,
        )
    elif req.mode == "abridge":
        if req.index is None:
            raise HTTPException(400, "abridge mode requires an 'index'")
        try:
            c = dataset.get_case(req.index)
        except IndexError:
            raise HTTPException(404, f"no Abridge case at index {req.index}")
        result = orchestrator.run_case(
            transcript=c.transcript,
            note=None if req.regenerate_note else c.note,
            source="abridge",
            label=f"[{req.index}] {c.visit_title}",
            fhir_context=c.fhir_context,
            max_findings=req.max_findings,
        )
    else:  # custom
        if not req.transcript or not req.transcript.strip():
            raise HTTPException(400, "custom mode requires a 'transcript'")
        result = orchestrator.run_case(
            transcript=req.transcript,
            note=req.note,
            source="custom",
            label="custom paste",
            max_findings=req.max_findings,
        )

    payload = result.to_dict()
    _HISTORY.insert(0, payload)
    del _HISTORY[_MAX_HISTORY:]
    return payload
