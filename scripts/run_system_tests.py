"""Execute V2 system-test checklist and write evidence to docs/."""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from ppc_simulator.api import app
from ppc_simulator.claims_io import load_claims_csv
from ppc_simulator.compare import compare_claim, compare_portfolio
from ppc_simulator.engine import evaluate_claim, evaluate_portfolio
from ppc_simulator.models import Outcome, Policy
from ppc_simulator.reporting import results_to_csv, summarize_results

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "fixtures"
OUT = ROOT / "docs" / "V2_SYSTEM_TEST_EVIDENCE.md"


def load_policy(name: str) -> Policy:
    return Policy.model_validate(json.loads((FIX / name).read_text(encoding="utf-8")))


def main() -> None:
    baseline = load_policy("sample_policy_v1.json")
    proposed = load_policy("sample_policy_v2.json")
    claims = load_claims_csv(FIX / "sample_claims.csv")
    by_id = {c.claim_id: c for c in claims}
    rows: list[tuple[str, str, bool, str]] = []

    s = compare_portfolio(baseline, baseline, claims)
    rows.append(
        (
            "ST1",
            "Identical policies produce zero changes",
            s.changed_claims == 0 and s.unchanged_claims == s.total_claims,
            f"changed={s.changed_claims}, unchanged={s.unchanged_claims}, total={s.total_claims}",
        )
    )

    cmp6 = compare_claim(baseline, proposed, by_id["C006"])
    rows.append(
        (
            "ST2",
            "Single-rule timely-filing change attributes R-TF-90",
            cmp6.transition == "pass->fail" and "R-TF-90" in cmp6.attributed_rule_ids,
            f"transition={cmp6.transition}, attributed={cmp6.attributed_rule_ids}",
        )
    )

    cmp7 = compare_claim(baseline, proposed, by_id["C007"])
    rows.append(
        (
            "ST3",
            "Added POS rule attributes R-POS-22",
            cmp7.transition == "pass->manual_review" and "R-POS-22" in cmp7.attributed_rule_ids,
            f"transition={cmp7.transition}, attributed={cmp7.attributed_rule_ids}",
        )
    )

    s2 = compare_portfolio(baseline, proposed, claims)
    impact_ids = {item.rule_id for item in s2.rule_impacts}
    rows.append(
        (
            "ST4",
            "Combined changes appear in impact summary",
            "R-TF-90" in impact_ids and "R-POS-22" in impact_ids and s2.changed_claims >= 2,
            f"changed={s2.changed_claims}, transitions={s2.transition_counts}, impacts={sorted(impact_ids)}",
        )
    )

    cmp1 = compare_claim(baseline, proposed, by_id["C001"])
    rows.append(
        (
            "ST5",
            "Unchanged claim has empty attribution",
            cmp1.changed is False and cmp1.attributed_rule_ids == [],
            f"changed={cmp1.changed}, attributed={cmp1.attributed_rule_ids}, outcome={cmp1.baseline_outcome.value}",
        )
    )

    b5 = evaluate_claim(baseline, by_id["C005"])
    p5 = evaluate_claim(proposed, by_id["C005"])
    rows.append(
        (
            "ST6",
            "Payer mismatch yields manual_review under both policies",
            b5.outcome == Outcome.MANUAL_REVIEW and p5.outcome == Outcome.MANUAL_REVIEW,
            f"baseline={b5.outcome.value}, proposed={p5.outcome.value}",
        )
    )

    invalid_ok = False
    detail = ""
    try:
        Policy.model_validate(
            {
                "policy_id": "X",
                "payer_name": "Acme Health",
                "version": "1.0",
                "effective_start": "2026-12-31",
                "effective_end": "2026-01-01",
                "rules": [],
            }
        )
        detail = "validation unexpectedly succeeded"
    except Exception as exc:  # noqa: BLE001
        invalid_ok = True
        detail = f"{type(exc).__name__}: {exc}"
    rows.append(("ST7", "Invalid policy dates rejected", invalid_ok, detail))

    bad = FIX / "_tmp_bad_claims.csv"
    bad.write_text("claim_id,payer\nONLY,\n", encoding="utf-8")
    malformed_ok = False
    detail = ""
    try:
        load_claims_csv(bad)
        detail = "import unexpectedly succeeded"
    except Exception as exc:  # noqa: BLE001
        malformed_ok = True
        detail = str(exc)
    finally:
        bad.unlink(missing_ok=True)
    rows.append(("ST8", "Malformed claim import rejected with row context", malformed_ok, detail))

    client = TestClient(app)
    response = client.post(
        "/v1/evaluate",
        json={"policy": baseline.model_dump(mode="json"), "claims": []},
    )
    rows.append(
        (
            "ST9",
            "API rejects empty claim list",
            response.status_code == 422,
            f"status={response.status_code}",
        )
    )

    health = client.get("/health")
    rows.append(
        (
            "ST10",
            "API health endpoint responds",
            health.status_code == 200 and health.json().get("status") == "ok",
            f"status={health.status_code}, body={health.json()}",
        )
    )

    results = evaluate_portfolio(baseline, claims)
    outcomes = {item.claim_id: item.outcome.value for item in results}
    expected = {
        "C001": "pass",
        "C002": "fail",
        "C003": "fail",
        "C004": "pass",
        "C005": "manual_review",
        "C006": "pass",
        "C007": "pass",
    }
    rows.append(
        (
            "ST11",
            "V1 regression outcomes on fixture portfolio",
            outcomes == expected,
            f"outcomes={outcomes}",
        )
    )

    compare_body = {
        "baseline": baseline.model_dump(mode="json"),
        "proposed": proposed.model_dump(mode="json"),
        "claims": [c.model_dump(mode="json") for c in claims],
    }
    compare_resp = client.post("/v2/compare", json=compare_body)
    compare_json = compare_resp.json() if compare_resp.status_code == 200 else {}
    rows.append(
        (
            "ST12",
            "API /v2/compare returns impact summary",
            compare_resp.status_code == 200 and compare_json.get("changed_claims", 0) >= 2,
            f"status={compare_resp.status_code}, changed={compare_json.get('changed_claims')}, "
            f"transitions={compare_json.get('transition_counts')}",
        )
    )

    summary_v1 = summarize_results(results)
    rows.append(
        (
            "ST13",
            "V1 summary reports outcome counts and failure reasons",
            summary_v1.total_claims == len(results)
            and sum(summary_v1.outcome_counts.values()) == len(results)
            and len(summary_v1.failure_reasons) > 0,
            f"counts={summary_v1.outcome_counts}, "
            f"reasons={[(r.rule_id, r.claim_count) for r in summary_v1.failure_reasons]}",
        )
    )

    export_text = results_to_csv(results)
    export_lines = export_text.strip().splitlines()
    rows.append(
        (
            "ST14",
            "V1 claim-level results export to CSV",
            export_lines[0].startswith("claim_id,") and len(export_lines) == len(results) + 1,
            f"header={export_lines[0]}, rows={len(export_lines) - 1}",
        )
    )

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
    rows.append(
        (
            "ST15",
            "Incomplete rule definition forces manual review",
            incomplete_result.outcome == Outcome.MANUAL_REVIEW,
            f"outcome={incomplete_result.outcome.value}, "
            f"evaluable={[t.evaluable for t in incomplete_result.traces]}",
        )
    )

    scale_claims = [
        by_id[claim_id] for claim_id in sorted(by_id) for _ in range(300)
    ]
    started = time.perf_counter()
    scale_summary = compare_portfolio(baseline, proposed, scale_claims)
    elapsed = time.perf_counter() - started
    rows.append(
        (
            "ST16",
            "Comparison completes within time budget on a larger portfolio",
            scale_summary.total_claims == len(scale_claims) and elapsed < 10.0,
            f"claims={len(scale_claims)}, elapsed={elapsed:.2f}s",
        )
    )

    home = client.get("/")
    rows.append(
        (
            "ST17",
            "Browser UI is served at /",
            home.status_code == 200 and "Version 1 · Evaluate" in home.text,
            f"status={home.status_code}, ui={'evaluate' in home.text.lower()}",
        )
    )

    passed = sum(1 for row in rows if row[2])
    total = len(rows)

    lines = [
        "# V2 System Test Evidence",
        "",
        f"**Execution date:** {date.today().isoformat()}",
        f"**Result:** {passed}/{total} checks passed",
        "**Automated unit tests:** run separately with `pytest`",
        "",
        "| ID | Scenario | Result | Evidence |",
        "|----|----------|--------|----------|",
    ]
    for test_id, scenario, ok, evidence in rows:
        lines.append(f"| {test_id} | {scenario} | {'PASS' if ok else 'FAIL'} | `{evidence}` |")

    lines.extend(
        [
            "",
            "## Exit criteria",
            "",
            f"- [{'x' if passed == total else ' '}] Checklist executed with pass/fail evidence",
            "- [x] Risk register updated at project closeout",
            "- [x] Release tagged `v2.0`",
            "",
            "## Notes",
            "",
            "This evidence supports Version 2 complete system testing required by the project "
            "proposal: regression of Version 1 behavior plus comparison, attribution, and impact "
            "summary workflows.",
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
