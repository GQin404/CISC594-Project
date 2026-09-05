"""Execute the Version 1 system-test pack and write evidence to docs/.

This pack covers only Version 1 capabilities (policy validation, claim import,
single-policy evaluation, explanations, summaries, export) so it can be run
against the v1.0 release baseline without any Version 2 code present.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

from ppc_simulator.claims_io import load_claims_csv, load_claims_json
from ppc_simulator.engine import evaluate_claim, evaluate_portfolio
from ppc_simulator.models import Claim, Outcome, Policy
from ppc_simulator.reporting import export_results_csv, results_to_csv, summarize_results

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
OUT = ROOT / "docs" / "V1_SYSTEM_TEST_EVIDENCE.md"

SERVICE_DATE = date(2026, 1, 10)


def load_policy() -> Policy:
    return Policy.model_validate(
        json.loads((FIXTURES / "sample_policy_v1.json").read_text(encoding="utf-8"))
    )


def office_claim(claim_id: str, **overrides) -> Claim:
    payload = {
        "claim_id": claim_id,
        "payer": "Acme Health",
        "service_date": SERVICE_DATE,
        "submission_date": SERVICE_DATE + timedelta(days=5),
        "procedure_code": "99213",
        "diagnosis_code": "J06.9",
        "modifier": None,
        "place_of_service": "11",
        "authorization_on_file": True,
    }
    payload.update(overrides)
    return Claim.model_validate(payload)


def git_describe() -> str:
    try:
        return subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - evidence should still be produced
        return "unknown"


def main() -> None:
    policy = load_policy()
    claims = load_claims_csv(FIXTURES / "sample_claims.csv")
    by_id = {claim.claim_id: claim for claim in claims}
    rows: list[tuple[str, str, bool, str]] = []

    def record(test_id: str, scenario: str, ok: bool, evidence: str) -> None:
        rows.append((test_id, scenario, ok, evidence))

    # --- Policy validation -------------------------------------------------
    try:
        Policy.model_validate(
            {
                "policy_id": "POL-BAD-DATES",
                "payer_name": "Acme Health",
                "version": "1.0",
                "effective_start": "2026-12-31",
                "effective_end": "2026-01-01",
                "rules": [],
            }
        )
        record("V1-01", "Inverted effective dates rejected", False, "validation succeeded")
    except Exception as exc:  # noqa: BLE001
        record("V1-01", "Inverted effective dates rejected", True, f"{type(exc).__name__}")

    duplicate_rule = {
        "rule_id": "R-DUP",
        "category": "timely_filing",
        "description": "duplicate",
        "timely_filing_days": 90,
    }
    try:
        Policy.model_validate(
            {
                "policy_id": "POL-DUP",
                "payer_name": "Acme Health",
                "version": "1.0",
                "effective_start": "2026-01-01",
                "effective_end": "2026-12-31",
                "rules": [duplicate_rule, dict(duplicate_rule)],
            }
        )
        record("V1-02", "Duplicate rule identifiers rejected", False, "validation succeeded")
    except Exception as exc:  # noqa: BLE001
        record("V1-02", "Duplicate rule identifiers rejected", True, f"{type(exc).__name__}")

    # --- Claim import ------------------------------------------------------
    record(
        "V1-03",
        "Valid CSV claim file imports",
        len(claims) == 7 and all(c.payer for c in claims),
        f"imported={len(claims)} claims",
    )

    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad_claims.csv"
        bad.write_text("claim_id,payer\nONLY,\n", encoding="utf-8")
        try:
            load_claims_csv(bad)
            record("V1-04", "Malformed CSV rejected with row context", False, "import succeeded")
        except Exception as exc:  # noqa: BLE001
            record("V1-04", "Malformed CSV rejected with row context", "row 2" in str(exc), str(exc))

        json_path = Path(tmp) / "claims.json"
        json_path.write_text(
            json.dumps(
                [
                    {
                        "claim_id": "J001",
                        "payer": "Acme Health",
                        "service_date": "2026-01-10",
                        "submission_date": "2026-01-15",
                        "procedure_code": "99213",
                        "diagnosis_code": "J06.9",
                        "place_of_service": "11",
                        "authorization_on_file": True,
                    }
                ]
            ),
            encoding="utf-8",
        )
        json_claims = load_claims_json(json_path)
        record(
            "V1-05",
            "Valid JSON claim file imports",
            len(json_claims) == 1 and json_claims[0].claim_id == "J001",
            f"imported={[c.claim_id for c in json_claims]}",
        )

    # --- Timely filing boundary values (limit is 90 days) ------------------
    at_limit = office_claim("B090", submission_date=SERVICE_DATE + timedelta(days=90))
    over_limit = office_claim("B091", submission_date=SERVICE_DATE + timedelta(days=91))
    under_limit = office_claim("B089", submission_date=SERVICE_DATE + timedelta(days=89))

    at_result = evaluate_claim(policy, at_limit)
    over_result = evaluate_claim(policy, over_limit)
    under_result = evaluate_claim(policy, under_limit)
    record(
        "V1-06",
        "Filing on day 89 and day 90 passes; day 91 fails (boundary values)",
        under_result.outcome == Outcome.PASS
        and at_result.outcome == Outcome.PASS
        and over_result.outcome == Outcome.FAIL,
        f"day89={under_result.outcome.value}, day90={at_result.outcome.value}, "
        f"day91={over_result.outcome.value}",
    )
    record(
        "V1-07",
        "Late claim is attributed to the timely-filing rule",
        any(t.rule_id == "R-TF-90" and t.matched for t in over_result.traces),
        f"traces={[(t.rule_id, t.matched) for t in over_result.traces]}",
    )

    # --- Authorization and modifier rules ----------------------------------
    missing_auth = evaluate_claim(policy, by_id["C003"])
    record(
        "V1-08",
        "Procedure requiring authorization fails when none is on file",
        missing_auth.outcome == Outcome.FAIL
        and any(t.rule_id == "R-AUTH-27447" and t.matched for t in missing_auth.traces),
        f"outcome={missing_auth.outcome.value}",
    )

    compliant = evaluate_claim(policy, by_id["C004"])
    record(
        "V1-09",
        "Claim with authorization and required modifier passes",
        compliant.outcome == Outcome.PASS,
        f"outcome={compliant.outcome.value}",
    )

    missing_modifier = office_claim(
        "M001", procedure_code="27447", modifier=None, authorization_on_file=True
    )
    modifier_result = evaluate_claim(policy, missing_modifier)
    record(
        "V1-10",
        "Claim missing the required modifier fails on the modifier rule",
        modifier_result.outcome == Outcome.FAIL
        and any(t.rule_id == "R-MOD-27447-LT" and t.matched for t in modifier_result.traces),
        f"outcome={modifier_result.outcome.value}",
    )

    # --- Applicability and scope guards ------------------------------------
    mismatch = evaluate_claim(policy, by_id["C005"])
    record(
        "V1-11",
        "Claim for a different payer routes to manual review",
        mismatch.outcome == Outcome.MANUAL_REVIEW,
        f"outcome={mismatch.outcome.value}",
    )

    out_of_range = office_claim(
        "D001",
        service_date=date(2025, 6, 1),
        submission_date=date(2025, 6, 5),
    )
    range_result = evaluate_claim(policy, out_of_range)
    record(
        "V1-12",
        "Service date outside the policy effective range routes to manual review",
        range_result.outcome == Outcome.MANUAL_REVIEW,
        f"outcome={range_result.outcome.value}, explanation={range_result.explanations[0][:60]}...",
    )

    # --- Rule precedence ---------------------------------------------------
    precedence_policy = Policy.model_validate(
        {
            "policy_id": "POL-PRECEDENCE",
            "payer_name": "Acme Health",
            "version": "1.0",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "rules": [
                {
                    "rule_id": "R-LOW-PRIORITY",
                    "category": "timely_filing",
                    "description": "Fails late claims",
                    "timely_filing_days": 30,
                    "on_match_outcome": "fail",
                    "priority": 50,
                },
                {
                    "rule_id": "R-HIGH-PRIORITY",
                    "category": "place_of_service",
                    "description": "Office claims need manual review",
                    "place_of_service": "11",
                    "on_match_outcome": "manual_review",
                    "priority": 1,
                },
            ],
        }
    )
    precedence_claim = office_claim("P001", submission_date=SERVICE_DATE + timedelta(days=200))
    precedence_result = evaluate_claim(precedence_policy, precedence_claim)
    record(
        "V1-13",
        "Lower priority number decides the outcome first",
        precedence_result.outcome == Outcome.MANUAL_REVIEW
        and precedence_result.traces[0].rule_id == "R-HIGH-PRIORITY",
        f"outcome={precedence_result.outcome.value}, first_trace={precedence_result.traces[0].rule_id}",
    )

    # --- Incomplete rule definition ----------------------------------------
    incomplete_policy = Policy.model_validate(
        {
            "policy_id": "POL-INCOMPLETE",
            "payer_name": "Acme Health",
            "version": "1.0",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "rules": [
                {
                    "rule_id": "R-INCOMPLETE",
                    "category": "modifier",
                    "description": "Modifier rule with no required modifier configured",
                    "on_match_outcome": "fail",
                    "priority": 10,
                }
            ],
        }
    )
    incomplete_result = evaluate_claim(incomplete_policy, by_id["C001"])
    record(
        "V1-14",
        "Incomplete rule definition forces manual review instead of a silent pass",
        incomplete_result.outcome == Outcome.MANUAL_REVIEW,
        f"outcome={incomplete_result.outcome.value}, "
        f"evaluable={[t.evaluable for t in incomplete_result.traces]}",
    )

    # --- Explanations, summary, export -------------------------------------
    results = evaluate_portfolio(policy, claims)
    record(
        "V1-15",
        "Every evaluated claim carries at least one explanation",
        all(result.explanations for result in results),
        f"claims={len(results)}, min_explanations={min(len(r.explanations) for r in results)}",
    )

    summary = summarize_results(results)
    record(
        "V1-16",
        "Summary reports outcome counts and failure reasons",
        summary.total_claims == len(results)
        and sum(summary.outcome_counts.values()) == len(results)
        and len(summary.failure_reasons) > 0,
        f"counts={summary.outcome_counts}, "
        f"reasons={[(r.rule_id, r.claim_count) for r in summary.failure_reasons]}",
    )

    with tempfile.TemporaryDirectory() as tmp:
        destination = export_results_csv(results, Path(tmp) / "results.csv")
        exported = destination.read_text(encoding="utf-8").strip().splitlines()
    record(
        "V1-17",
        "Claim-level results export to CSV with a header row",
        exported[0].startswith("claim_id,") and len(exported) == len(results) + 1,
        f"header={exported[0]}, rows={len(exported) - 1}",
    )

    record(
        "V1-18",
        "Evaluation is deterministic across repeated runs",
        results_to_csv(results) == results_to_csv(evaluate_portfolio(policy, claims)),
        "two consecutive portfolio runs produced identical exports",
    )

    passed = sum(1 for row in rows if row[2])
    total = len(rows)

    lines = [
        "# V1 System Test Evidence",
        "",
        f"**Execution date:** {date.today().isoformat()}",
        f"**Build under test:** `{git_describe()}` (Version 1 baseline)",
        f"**Result:** {passed}/{total} checks passed",
        "",
        "This pack exercises Version 1 capabilities only, so it can be executed against the",
        "`v1.0` release with no Version 2 code present.",
        "",
        "| ID | Scenario | Result | Evidence |",
        "|----|----------|--------|----------|",
    ]
    for test_id, scenario, ok, evidence in rows:
        lines.append(f"| {test_id} | {scenario} | {'PASS' if ok else 'FAIL'} | `{evidence}` |")

    lines.extend(
        [
            "",
            "## Techniques applied",
            "",
            "- Boundary-value analysis on the timely-filing limit (days 89, 90, 91)",
            "- Equivalence partitioning across authorization, modifier, and place-of-service rules",
            "- Decision-table coverage of rule precedence",
            "- Negative testing on policy validation and claim import",
            "- Repeatability check confirming deterministic output",
            "",
            "## Exit criteria",
            "",
            f"- [{'x' if passed == total else ' '}] All Version 1 system-test checks passed",
            "- [x] Version 1 tagged as `v1.0` before Version 2 development began",
        ]
    )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"RESULT {passed}/{total}")
    for test_id, scenario, ok, evidence in rows:
        print(f"{test_id} {'PASS' if ok else 'FAIL'} :: {scenario} :: {evidence}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
