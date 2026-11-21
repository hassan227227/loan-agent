"""Deterministic business rules the agent calls as tools.

Money decisions stay in plain, testable code. The model orchestrates the
steps and writes the memo; it never invents a threshold.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "applications.json"

REQUIRED_DOCUMENTS = ("proof_of_income", "government_id", "proof_of_address")
AUTO_APPROVE_SCORE = 700
MANUAL_REVIEW_SCORE = 620
MAX_AUTO_DTI = 0.40
MAX_REVIEW_DTI = 0.50


def load_applications(path: Path = DATA_FILE) -> dict[str, dict]:
    return {a["id"]: a for a in json.loads(path.read_text(encoding="utf-8"))}


def debt_to_income(monthly_income: float, monthly_debts: float, new_payment: float) -> float:
    """Debt-to-income ratio including the new lease payment."""
    if monthly_income <= 0:
        raise ValueError("monthly_income must be positive")
    if monthly_debts < 0 or new_payment < 0:
        raise ValueError("debts and payment cannot be negative")
    return round((monthly_debts + new_payment) / monthly_income, 4)


def missing_documents(documents: list[str]) -> list[str]:
    have = set(documents)
    return [d for d in REQUIRED_DOCUMENTS if d not in have]


def policy_outcome(credit_score: int, dti: float) -> str:
    """Return 'approve', 'review' or 'decline' per the credit policy."""
    if credit_score < MANUAL_REVIEW_SCORE or dti > MAX_REVIEW_DTI:
        return "decline"
    if credit_score >= AUTO_APPROVE_SCORE and dti < MAX_AUTO_DTI:
        return "approve"
    return "review"


@dataclass
class DecisionLog:
    """Records decisions. Declines are held until a person approves them."""

    decisions: dict[str, dict] = field(default_factory=dict)

    def record(self, app_id: str, decision: str, reasons: list[str], human_approved: bool = False) -> dict:
        if decision not in {"approve", "review", "decline"}:
            raise ValueError(f"unknown decision: {decision}")
        status = "pending_human_approval" if decision == "decline" and not human_approved else "recorded"
        entry = {"app_id": app_id, "decision": decision, "reasons": reasons, "status": status}
        self.decisions[app_id] = entry
        return entry
