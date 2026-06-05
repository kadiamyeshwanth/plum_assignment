# MVP Backend Prototype

This folder contains a minimal FastAPI prototype for the Plum OPD adjudication assignment.

Quick start (Python 3.10+ recommended):

1. Create a virtual environment and install requirements

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the API locally

```bash
uvicorn app:app --reload --port 8000
```

3. Run the test runner (uses `test_cases.json` in repo root)

```bash
python run_tests.py
```

Notes:
- `decision_engine.py` implements a small rule-based engine that mirrors rules in `adjudication_rules.md` and `policy_terms.json`.
- `extractor.py` is a placeholder for OCR/LLM extraction.
- This is a prototype to get the adjudication logic wired up quickly; it is not production-ready.
