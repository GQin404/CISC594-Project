# Payer Policy Change Impact Simulator

CISC 594 semester project: deterministic simulation of payer policy rules against synthetic claims.

## Stack
- Python 3.11+
- pytest

## Quick start
```bash
pip install -r requirements.txt
pytest
```

## Versions
- **v1.0** (this baseline) — policy validation, claim import, single-policy evaluation, explanations, summaries, CSV export
- **v2.0** (planned) — dual-policy portfolio replay, change detection, rule-level attribution, impact summaries

## Testing
```bash
pytest                                 # unit tests
set PYTHONPATH=src
python scripts/run_v1_system_tests.py  # Version 1 system-test pack
```

## Change control
Development happens on feature branches and is merged to `main` through pull requests. See `docs/CHANGE_CONTROL.md`.

## Documents
- `Project Proposal.md`
- `docs/CHANGE_CONTROL.md`
- `docs/CHANGE_REQUESTS.md`
- `docs/V1_SYSTEM_TEST_EVIDENCE.md`
