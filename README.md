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
Then open http://127.0.0.1:8000 for the browser UI (Evaluate and Compare). API docs are at `/docs`.

## Browser UI
- `/` — Version 1 evaluation and Version 2 comparison
- Load CSV or JSON sample fixtures, or paste policy JSON and claims as CSV or a JSON array
- Optional claim-ID subset (blank = entire file)
- JSON API used by the page and by system tests:
  - `POST /v1/evaluate`
  - `POST /v1/evaluate/export`
  - `POST /v2/compare`

## Versions
- **v1.0** — policy validation, claim import, single-policy evaluation, explanations, summaries, CSV export
- **v2.0** — dual-policy portfolio replay, change detection, rule-level attribution, impact summaries, FastAPI browser UI

## Testing
```bash
pytest                                 # 36 unit and integration tests
set PYTHONPATH=src
python scripts/run_v1_system_tests.py  # 18 V1 system-test checks (17 on the v1.0 tag)
python scripts/run_system_tests.py     # 17 V2 system-test checks
```
The `v1.0` tag contains the 17-check pack used as the Version 1 release gate. After CR-003, `main` adds V1-14 (incomplete rules), for 18 checks. The `v2.0` tag is the Version 2 release gate (`pytest` 18; V2 pack 17/17). `main` is ahead of `v2.0` with closeout UI work (`pytest` 36).

## Change control
All development through `v2.0` happened on feature branches and entered `main` through pull requests. A tested closeout commit after `v2.0` is on `main` and is not a new version tag. See `docs/CHANGE_CONTROL.md`.

## Repository documents
- `Project Proposal.md` (Markdown only; submission binaries are outside this repo)
- `docs/CHANGE_CONTROL.md` — branch, pull-request, and release process
- `docs/CHANGE_REQUESTS.md` — approved scope changes against the proposal
- `docs/V1_SYSTEM_TEST_EVIDENCE.md` — V1 system-test results
- `docs/V2_SYSTEM_TEST_CHECKLIST.md` and `docs/V2_SYSTEM_TEST_EVIDENCE.md`

Course submission artifacts such as the risk management report are kept outside this repository.
