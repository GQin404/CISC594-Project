# V2 System Test Checklist

## Preconditions
- [x] V1 regression suite green (`pytest` — 18 passed)
- [x] Fixtures present: `sample_policy_v1.json`, `sample_policy_v2.json`, `sample_claims.csv`
- [x] Change-control notes current (`docs/CHANGE_CONTROL.md`, `docs/CHANGE_REQUESTS.md`)

## Comparison scenarios (Version 2)
- [x] Identical baseline/proposed policies produce zero changed claims (ST1)
- [x] Single-rule parameter change (timely filing 90→60) attributes `R-TF-90` (ST2)
- [x] Added rule (place of service 22) attributes `R-POS-22` (ST3)
- [x] Combined changes appear in the impact summary with counts and percentages (ST4)
- [x] Unchanged claims keep their outcome and carry no attribution (ST5)

## Version 1 regression
- [x] Payer mismatch yields manual review under both policies (ST6)
- [x] Fixture portfolio outcomes match expected results (ST11)
- [x] Summary reports outcome counts and failure reasons (ST13)
- [x] Claim-level results export to CSV (ST14)
- [x] Incomplete rule definition forces manual review (ST15)

## Negative / robustness
- [x] Invalid policy effective dates rejected (ST7)
- [x] Malformed claim import rejected with row context (ST8)
- [x] API rejects an empty claim list (ST9)
- [x] `/health` responds (ST10), `/` serves the browser UI (ST17), and `/v2/compare` returns an impact summary (ST12)

## Scale
- [x] Comparison completes within the time budget on a larger portfolio (ST16)

## Exit criteria for `v2.0`
- [x] Checklist executed with pass/fail evidence (`docs/V2_SYSTEM_TEST_EVIDENCE.md` — **17/17 PASS**)
- [x] Risk register updated at project closeout
- [x] Release tagged `v2.0`

## How to re-run
```bash
pip install -r requirements.txt
pytest
set PYTHONPATH=src
python scripts/run_system_tests.py
```
