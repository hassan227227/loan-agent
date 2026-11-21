"""Lease-application review agent built on Claude's tool runner.

Claude plans the review and calls the tools below; every number and rule
comes from policy.py. Declines are held for a person to approve.

Usage:  python agent.py APP-1002
"""
from __future__ import annotations

import json
import os
import sys

import anthropic
from anthropic import beta_tool

from policy import DecisionLog, debt_to_income, load_applications, missing_documents, policy_outcome

MODEL = os.environ.get("LOAN_AGENT_MODEL", "claude-opus-5-5")
SYSTEM = (
    "You are a lease-application reviewer at a vehicle finance company. "
    "Review the application you are given by calling the tools: fetch the applicant, "
    "check documents, compute debt-to-income with the new payment, apply the credit policy, "
    "then record exactly the decision the policy returns. Never invent numbers or thresholds. "
    "Finish with a short decision memo for a credit analyst: decision, the figures used, "
    "missing documents if any, and the next step."
)

APPLICATIONS = load_applications()
LOG = DecisionLog()


@beta_tool
def get_application(app_id: str) -> str:
    """Fetch a lease application by id.

    Args:
        app_id: Application id, e.g. APP-1001.
    """
    app = APPLICATIONS.get(app_id)
    if app is None:
        return json.dumps({"error": f"No application with id {app_id}"})
    return json.dumps(app)


@beta_tool
def check_documents(app_id: str) -> str:
    """List required documents that are missing from an application.

    Args:
        app_id: Application id.
    """
    app = APPLICATIONS.get(app_id)
    if app is None:
        return json.dumps({"error": f"No application with id {app_id}"})
    return json.dumps({"missing": missing_documents(app["documents"])})


@beta_tool
def calculate_dti(monthly_income: float, monthly_debts: float, new_payment: float) -> str:
    """Compute debt-to-income including the proposed monthly lease payment.

    Args:
        monthly_income: Gross monthly income.
        monthly_debts: Existing monthly debt payments.
        new_payment: Proposed monthly lease payment.
    """
    try:
        return json.dumps({"dti": debt_to_income(monthly_income, monthly_debts, new_payment)})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@beta_tool
def apply_credit_policy(credit_score: int, dti: float) -> str:
    """Apply the credit policy. Returns approve, review or decline.

    Args:
        credit_score: Applicant credit score.
        dti: Debt-to-income ratio as a fraction, e.g. 0.35.
    """
    return json.dumps({"outcome": policy_outcome(credit_score, dti)})


@beta_tool
def record_decision(app_id: str, decision: str, reasons: list[str]) -> str:
    """Record the decision. Declines are held until a person approves them.

    Args:
        app_id: Application id.
        decision: One of approve, review, decline.
        reasons: Short reasons, each citing a figure or rule.
    """
    try:
        return json.dumps(LOG.record(app_id, decision, reasons))
    except ValueError as e:
        return json.dumps({"error": str(e)})


TOOLS = [get_application, check_documents, calculate_dti, apply_credit_policy, record_decision]


def review(app_id: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        tools=TOOLS,
        max_iterations=12,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": f"Review application {app_id}."}],
    )
    final = runner.until_done()
    if final.stop_reason == "refusal":
        memo = "The model declined to review this application."
    else:
        memo = "".join(b.text for b in final.content if b.type == "text").strip()
    return {"app_id": app_id, "memo": memo, "decision": LOG.decisions.get(app_id)}


if __name__ == "__main__":
    result = review(sys.argv[1] if len(sys.argv) > 1 else "APP-1001")
    print(result["memo"])
    print("\nRecorded:", json.dumps(result["decision"], indent=2))
