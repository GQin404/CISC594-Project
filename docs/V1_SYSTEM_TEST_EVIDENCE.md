# V1 System Test Evidence

**Execution date:** 2026-09-05
**Build under test:** `v1.0-3-g3191816` (Version 1 baseline)
**Result:** 18/18 checks passed

This pack exercises Version 1 capabilities only, so it can be executed against the
`v1.0` release with no Version 2 code present.

| ID | Scenario | Result | Evidence |
|----|----------|--------|----------|
| V1-01 | Inverted effective dates rejected | PASS | `ValidationError` |
| V1-02 | Duplicate rule identifiers rejected | PASS | `ValidationError` |
| V1-03 | Valid CSV claim file imports | PASS | `imported=7 claims` |
| V1-04 | Malformed CSV rejected with row context | PASS | `row 2: missing required fields: payer, service_date, submission_date, procedure_code, diagnosis_code, place_of_service` |
| V1-05 | Valid JSON claim file imports | PASS | `imported=['J001']` |
| V1-06 | Filing on day 89 and day 90 passes; day 91 fails (boundary values) | PASS | `day89=pass, day90=pass, day91=fail` |
| V1-07 | Late claim is attributed to the timely-filing rule | PASS | `traces=[('R-TF-90', True)]` |
| V1-08 | Procedure requiring authorization fails when none is on file | PASS | `outcome=fail` |
| V1-09 | Claim with authorization and required modifier passes | PASS | `outcome=pass` |
| V1-10 | Claim missing the required modifier fails on the modifier rule | PASS | `outcome=fail` |
| V1-11 | Claim for a different payer routes to manual review | PASS | `outcome=manual_review` |
| V1-12 | Service date outside the policy effective range routes to manual review | PASS | `outcome=manual_review, explanation=Service date 2025-06-01 is outside policy effective range 20...` |
| V1-13 | Lower priority number decides the outcome first | PASS | `outcome=manual_review, first_trace=R-HIGH-PRIORITY` |
| V1-14 | Incomplete rule definition forces manual review instead of a silent pass | PASS | `outcome=manual_review, evaluable=[False]` |
| V1-15 | Every evaluated claim carries at least one explanation | PASS | `claims=7, min_explanations=1` |
| V1-16 | Summary reports outcome counts and failure reasons | PASS | `counts={'pass': 4, 'fail': 2, 'manual_review': 1}, reasons=[('R-AUTH-27447', 1), ('R-TF-90', 1)]` |
| V1-17 | Claim-level results export to CSV with a header row | PASS | `header=claim_id,policy_id,policy_version,outcome,deciding_rule,explanation, rows=7` |
| V1-18 | Evaluation is deterministic across repeated runs | PASS | `two consecutive portfolio runs produced identical exports` |

## Techniques applied

- Boundary-value analysis on the timely-filing limit (days 89, 90, 91)
- Equivalence partitioning across authorization, modifier, and place-of-service rules
- Decision-table coverage of rule precedence
- Negative testing on policy validation and claim import
- Repeatability check confirming deterministic output

## Exit criteria

- [x] All Version 1 system-test checks passed
- [x] Version 1 tagged as `v1.0` before Version 2 development began
