# V2 System Test Evidence

**Execution date:** 2026-09-05
**Result:** 16/16 checks passed
**Automated unit tests:** run separately with `pytest`

| ID | Scenario | Result | Evidence |
|----|----------|--------|----------|
| ST1 | Identical policies produce zero changes | PASS | `changed=0, unchanged=7, total=7` |
| ST2 | Single-rule timely-filing change attributes R-TF-90 | PASS | `transition=pass->fail, attributed=['R-TF-90']` |
| ST3 | Added POS rule attributes R-POS-22 | PASS | `transition=pass->manual_review, attributed=['R-POS-22']` |
| ST4 | Combined changes appear in impact summary | PASS | `changed=2, transitions={'pass->pass': 2, 'fail->fail': 2, 'manual_review->manual_review': 1, 'pass->fail': 1, 'pass->manual_review': 1}, impacts=['R-POS-22', 'R-TF-90']` |
| ST5 | Unchanged claim has empty attribution | PASS | `changed=False, attributed=[], outcome=pass` |
| ST6 | Payer mismatch yields manual_review under both policies | PASS | `baseline=manual_review, proposed=manual_review` |
| ST7 | Invalid policy dates rejected | PASS | `ValidationError: 1 validation error for Policy
  Value error, effective_end must be on or after effective_start [type=value_error, input_value={'policy_id': 'X', 'payer...026-01-01', 'rules': []}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error` |
| ST8 | Malformed claim import rejected with row context | PASS | `row 2: missing required fields: payer, service_date, submission_date, procedure_code, diagnosis_code, place_of_service` |
| ST9 | API rejects empty claim list | PASS | `status=422` |
| ST10 | API health endpoint responds | PASS | `status=200, body={'status': 'ok'}` |
| ST11 | V1 regression outcomes on fixture portfolio | PASS | `outcomes={'C001': 'pass', 'C002': 'fail', 'C003': 'fail', 'C004': 'pass', 'C005': 'manual_review', 'C006': 'pass', 'C007': 'pass'}` |
| ST12 | API /v2/compare returns impact summary | PASS | `status=200, changed=2, transitions={'pass->pass': 2, 'fail->fail': 2, 'manual_review->manual_review': 1, 'pass->fail': 1, 'pass->manual_review': 1}` |
| ST13 | V1 summary reports outcome counts and failure reasons | PASS | `counts={'pass': 4, 'fail': 2, 'manual_review': 1}, reasons=[('R-AUTH-27447', 1), ('R-TF-90', 1)]` |
| ST14 | V1 claim-level results export to CSV | PASS | `header=claim_id,policy_id,policy_version,outcome,deciding_rule,explanation, rows=7` |
| ST15 | Incomplete rule definition forces manual review | PASS | `outcome=manual_review, evaluable=[False]` |
| ST16 | Comparison completes within time budget on a larger portfolio | PASS | `claims=2100, elapsed=0.03s` |

## Exit criteria

- [x] Checklist executed with pass/fail evidence
- [x] Risk register updated at project closeout
- [x] Release tagged `v2.0`

## Notes

This evidence supports Version 2 complete system testing required by the project proposal: regression of Version 1 behavior plus comparison, attribution, and impact summary workflows.
