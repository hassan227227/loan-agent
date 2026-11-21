"""FastAPI wrapper: run a review and approve held declines.

Run:  uvicorn api:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

import agent

app = FastAPI(title="Loan Review Agent", version="1.0.0")


@app.get("/applications")
def list_applications() -> list[str]:
    return sorted(agent.APPLICATIONS)


@app.post("/applications/{app_id}/review")
def review(app_id: str) -> dict:
    if app_id not in agent.APPLICATIONS:
        raise HTTPException(status_code=404, detail=f"No application with id {app_id}")
    return agent.review(app_id)


@app.post("/applications/{app_id}/approve-decline")
def approve_decline(app_id: str) -> dict:
    """A credit analyst confirms a decline the agent held for review."""
    entry = agent.LOG.decisions.get(app_id)
    if not entry or entry["status"] != "pending_human_approval":
        raise HTTPException(status_code=409, detail="No held decline for this application.")
    return agent.LOG.record(app_id, "decline", entry["reasons"], human_approved=True)
