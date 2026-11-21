# Loan Review Agent

![tests](https://github.com/hassan227227/loan-agent/actions/workflows/ci.yml/badge.svg)

An AI agent that reviews vehicle-lease applications the way a credit analyst would: it fetches the application, checks documents, computes debt-to-income, applies the credit policy and writes a decision memo. Built with Python, Claude's tool runner and FastAPI.

```
analyst ──► POST /applications/{id}/review
               │
               ▼
        Claude (tool runner) ──calls──► get_application
               │                       check_documents
               │                       calculate_dti        ← policy.py (plain, tested Python)
               │                       apply_credit_policy
               │                       record_decision ──► decline? held for a person
               ▼
         decision memo + recorded decision
```

## Design choices

- **Rules live in code, not in the prompt.** Thresholds (score 700/620, DTI 40%/50%), the DTI formula and the required-document list are plain Python in `policy.py` with boundary tests. The model decides the order of steps and writes the memo; it can't change a number.
- **Human in the loop for adverse decisions.** `record_decision` holds every decline as `pending_human_approval` until an analyst confirms it via `POST /applications/{id}/approve-decline`.
- **Typed tools from docstrings.** Tools are plain functions with `@beta_tool`; the SDK builds the JSON schemas from type hints and docstrings, and the tool runner drives the loop.
- **Bounded loop.** `max_iterations=12` caps runaway tool use; refusals are handled explicitly, and a server-side fallback model takes over if the main model declines.

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...          # Windows: set ANTHROPIC_API_KEY=...

python agent.py APP-1002              # review one application from the CLI
uvicorn api:app --reload              # or run the API
curl -X POST localhost:8000/applications/APP-1003/review
curl -X POST localhost:8000/applications/APP-1003/approve-decline

pytest -q                             # tests run offline, no API key needed
```

`data/applications.json` holds three fictional applications that land on approve, review and decline.

## Files

| File | What it does |
|---|---|
| `policy.py` | Credit rules, DTI, document checks, decision log with the human-approval gate |
| `agent.py` | Tool definitions and the agent loop; CLI entry point |
| `api.py` | FastAPI endpoints for review and decline approval |
| `test_policy.py` | Boundary tests for the policy and tool contracts |

## Next steps

- Persist decisions in PostgreSQL with an audit trail
- Extract application fields from uploaded PDFs
- An eval set of past applications to measure memo quality (see [llm-eval-kit](https://github.com/hassan227227/llm-eval-kit))

## Author

Hassan Raza · [Portfolio](https://hassan227227.github.io) · [LinkedIn](https://www.linkedin.com/in/iamhassan890)
