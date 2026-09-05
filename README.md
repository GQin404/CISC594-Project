# Payer Policy Change Impact Simulator

CISC 594 semester project: deterministic simulation of payer policy rules against synthetic claims, with Version 2 policy-change impact comparison.

## Stack
- Python 3.11+
- FastAPI
- pytest

## Quick start
```bash
pip install -r requirements.txt
pytest
uvicorn ppc_simulator.api:app --app-dir src --reload
```

## API
- `POST /v1/evaluate` — single-policy portfolio evaluation with summary
- `POST /v1/evaluate/export` — claim-level results as CSV
- `POST /v2/compare` — baseline vs proposed policy impact comparison

## Versions
- **v1.0** — policy validation, claim import, single-policy evaluation, explanations, summaries, CSV export
- **v2.0** — dual-policy portfolio replay, change detection, rule-level attribution, impact summaries

## Testing
```bash
pytest                                 # 16 unit and integration tests
set PYTHONPATH=src
python scripts/run_v1_system_tests.py  # 18 V1 system-test checks (17 on the v1.0 tag)
python scripts/run_system_tests.py     # 16 V2 system-test checks
```
Each script writes its own evidence file under `docs/`. The `v1.0` tag contains the 17-check pack used as the Version 1 release gate. After CR-003, `main` adds V1-14 (incomplete rules), for 18 checks.

## Change control
All development happens on feature branches and enters `main` through pull requests. Releases are annotated tags `v1.0` and `v2.0`. See `docs/CHANGE_CONTROL.md`.

## Repository documents
- `Project Proposal.md` (Markdown only; submission binaries are outside this repo)
- `docs/CHANGE_CONTROL.md` — branch, pull-request, and release process
- `docs/CHANGE_REQUESTS.md` — approved scope changes against the proposal
- `docs/V1_SYSTEM_TEST_EVIDENCE.md` — V1 system-test results
- `docs/V2_SYSTEM_TEST_CHECKLIST.md` and `docs/V2_SYSTEM_TEST_EVIDENCE.md`

Course submission artifacts such as the risk management report are kept outside this repository.
