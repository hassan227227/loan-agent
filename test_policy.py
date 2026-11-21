import json

import pytest

import agent
from policy import DecisionLog, debt_to_income, load_applications, missing_documents, policy_outcome


def test_dti_includes_new_payment():
    assert debt_to_income(5000, 1000, 500) == 0.3


def test_dti_rejects_bad_input():
    with pytest.raises(ValueError):
        debt_to_income(0, 100, 100)
    with pytest.raises(ValueError):
        debt_to_income(1000, -1, 100)


@pytest.mark.parametrize(
    "score,dti,expected",
    [
        (742, 0.22, "approve"),
        (700, 0.399, "approve"),
        (700, 0.40, "review"),
        (655, 0.30, "review"),
        (619, 0.20, "decline"),
        (760, 0.51, "decline"),
    ],
)
def test_policy_boundaries(score, dti, expected):
    assert policy_outcome(score, dti) == expected


def test_missing_documents():
    assert missing_documents(["government_id"]) == ["proof_of_income", "proof_of_address"]
    assert missing_documents(["proof_of_income", "government_id", "proof_of_address"]) == []


def test_declines_are_held_for_a_person():
    log = DecisionLog()
    assert log.record("A", "decline", ["score 598"])["status"] == "pending_human_approval"
    assert log.record("A", "decline", ["score 598"], human_approved=True)["status"] == "recorded"
    assert log.record("B", "approve", ["ok"])["status"] == "recorded"
    with pytest.raises(ValueError):
        log.record("C", "maybe", [])


def test_sample_data_covers_all_outcomes():
    apps = load_applications()
    outcomes = {
        policy_outcome(a["credit_score"], debt_to_income(a["monthly_income"], a["monthly_debts"], a["proposed_monthly_payment"]))
        for a in apps.values()
    }
    assert outcomes == {"approve", "review", "decline"}


def test_tools_return_json_and_handle_unknown_ids():
    assert "error" in json.loads(agent.get_application.func("NOPE"))
    assert json.loads(agent.check_documents.func("APP-1002")) == {"missing": ["proof_of_address"]}
    assert json.loads(agent.apply_credit_policy.func(598, 0.6)) == {"outcome": "decline"}


def test_tool_schemas_are_generated_from_docstrings():
    names = [t.to_dict()["name"] for t in agent.TOOLS]
    assert names == ["get_application", "check_documents", "calculate_dti", "apply_credit_policy", "record_decision"]
    schema = agent.calculate_dti.to_dict()["input_schema"]
    assert set(schema["required"]) == {"monthly_income", "monthly_debts", "new_payment"}
