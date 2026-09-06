"""UI integration and scenario tests.

These follow the same HTTP contract the browser page uses: load fixtures from
`/fixtures/...`, then POST `/v1/evaluate`, `/v1/evaluate/export`, or `/v2/compare`.
Client-side CSV parsing is mirrored from `static/app.js`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ppc_simulator.api import app

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
client = TestClient(app)


def parse_claims_csv_like_ui(text: str) -> list[dict]:
    lines = text.replace("\ufeff", "").strip().splitlines()
    if len(lines) < 2:
        raise ValueError("Claims CSV needs a header row and at least one claim.")
    headers = [item.strip() for item in lines[0].split(",")]
    claims = []
    required = [
        "claim_id",
        "payer",
        "service_date",
        "submission_date",
        "procedure_code",
        "diagnosis_code",
        "place_of_service",
    ]
    for index, line in enumerate(lines[1:], start=2):
        cols = line.split(",")
        row = {header: (cols[i] if i < len(cols) else "").strip() for i, header in enumerate(headers)}
        missing = [key for key in required if not row.get(key)]
        if missing:
            raise ValueError(f"CSV row {index} is missing: {', '.join(missing)}")
        auth = (row.get("authorization_on_file") or "false").lower()
        claims.append(
            {
                "claim_id": row["claim_id"],
                "payer": row["payer"],
                "service_date": row["service_date"],
                "submission_date": row["submission_date"],
                "procedure_code": row["procedure_code"],
                "diagnosis_code": row["diagnosis_code"],
                "modifier": row.get("modifier") or None,
                "place_of_service": row["place_of_service"],
                "authorization_on_file": auth in {"1", "true", "yes", "y"},
            }
        )
    return claims


def ui_sample_payload(policy_name: str = "sample_policy_v1.json") -> dict:
    policy = client.get(f"/fixtures/{policy_name}")
    claims = client.get("/fixtures/sample_claims.csv")
    assert policy.status_code == 200
    assert claims.status_code == 200
    return {"policy": policy.json(), "claims": parse_claims_csv_like_ui(claims.text)}


def test_ui_static_assets_load():
    home = client.get("/")
    css = client.get("/static/app.css")
    js = client.get("/static/app.js")
    assert home.status_code == 200
    assert css.status_code == 200
    assert js.status_code == 200
    assert "/v1/evaluate" in js.text
    assert "/v2/compare" in js.text
    assert "escapeHtml(" in js.text
    assert "parseClaims(" in js.text
    assert "applySubset(" in js.text
    assert "failure_reasons" in js.text
    assert "percent_of_portfolio" in js.text
    assert "eval-sample" in home.text
    assert "eval-sample-json" in home.text
    assert "eval-subset" in home.text
    assert "cmp-sample" in home.text


def test_evaluate_sample_portfolio_scenario():
    data = client.post("/v1/evaluate", json=ui_sample_payload()).json()
    counts = data["summary"]["outcome_counts"]
    by_id = {row["claim_id"]: row for row in data["results"]}
    assert data["summary"]["total_claims"] == 7
    assert counts["pass"] == 4
    assert counts["fail"] == 2
    assert counts["manual_review"] == 1
    assert by_id["C001"]["outcome"] == "pass"
    assert by_id["C002"]["outcome"] == "fail"
    assert by_id["C003"]["outcome"] == "fail"
    assert by_id["C005"]["outcome"] == "manual_review"
    assert any(trace["rule_id"] == "R-TF-90" and trace["matched"] for trace in by_id["C002"]["traces"])
    assert by_id["C001"]["explanations"]


def test_export_csv_after_evaluation_scenario():
    csv_text = client.post("/v1/evaluate/export", json=ui_sample_payload()).text
    lines = csv_text.strip().splitlines()
    assert lines[0] == "claim_id,policy_id,policy_version,outcome,deciding_rule,explanation"
    assert len(lines) == 8
    assert any(line.startswith("C002,") and ",fail,R-TF-90," in line for line in lines)


def test_compare_v1_v2_sample_scenario():
    baseline = client.get("/fixtures/sample_policy_v1.json").json()
    proposed = client.get("/fixtures/sample_policy_v2.json").json()
    claims = parse_claims_csv_like_ui(client.get("/fixtures/sample_claims.csv").text)
    data = client.post(
        "/v2/compare",
        json={"baseline": baseline, "proposed": proposed, "claims": claims},
    ).json()
    by_id = {row["claim_id"]: row for row in data["comparisons"]}
    assert data["changed_claims"] == 2
    assert data["unchanged_claims"] == 5
    assert by_id["C006"]["baseline_outcome"] == "pass"
    assert by_id["C006"]["proposed_outcome"] == "fail"
    assert by_id["C006"]["attributed_rule_ids"] == ["R-TF-90"]
    assert by_id["C007"]["baseline_outcome"] == "pass"
    assert by_id["C007"]["proposed_outcome"] == "manual_review"
    assert by_id["C007"]["attributed_rule_ids"] == ["R-POS-22"]
    impacted = {item["rule_id"]: item for item in data["rule_impacts"]}
    assert impacted["R-TF-90"]["affected_claim_count"] == 1
    assert impacted["R-POS-22"]["affected_claim_count"] == 1
    assert impacted["R-TF-90"]["percent_of_portfolio"] == 14.29
    assert impacted["R-TF-90"]["percent_of_changes"] == 50.0


def test_json_claims_fixture_evaluates_the_same_portfolio():
    policy = client.get("/fixtures/sample_policy_v1.json").json()
    claims = client.get("/fixtures/sample_claims.json").json()
    data = client.post("/v1/evaluate", json={"policy": policy, "claims": claims}).json()
    assert data["summary"]["total_claims"] == 7
    assert {item["rule_id"] for item in data["summary"]["failure_reasons"]} >= {"R-TF-90", "R-AUTH-27447"}


def test_claim_subset_evaluates_only_selected_ids():
    payload = ui_sample_payload()
    payload["claims"] = [claim for claim in payload["claims"] if claim["claim_id"] == "C006"]
    data = client.post("/v1/evaluate", json=payload).json()
    assert data["summary"]["total_claims"] == 1
    assert data["results"][0]["claim_id"] == "C006"
    assert data["results"][0]["outcome"] == "pass"


def test_identical_policies_produce_zero_changes():
    payload = ui_sample_payload()
    data = client.post(
        "/v2/compare",
        json={"baseline": payload["policy"], "proposed": payload["policy"], "claims": payload["claims"]},
    ).json()
    assert data["changed_claims"] == 0
    assert data["unchanged_claims"] == 7
    assert all(not row["changed"] and row["attributed_rule_ids"] == [] for row in data["comparisons"])


def test_invalid_policy_dates_rejected():
    payload = ui_sample_payload()
    payload["policy"]["effective_start"] = "2026-12-31"
    payload["policy"]["effective_end"] = "2026-01-01"
    response = client.post("/v1/evaluate", json=payload)
    assert response.status_code == 422
    assert "effective_end" in response.text


def test_empty_claims_rejected():
    payload = ui_sample_payload()
    payload["claims"] = []
    assert client.post("/v1/evaluate", json=payload).status_code == 422
    assert client.post(
        "/v2/compare",
        json={"baseline": payload["policy"], "proposed": payload["policy"], "claims": []},
    ).status_code == 422


def test_malformed_policy_json_rejected():
    response = client.post("/v1/evaluate", json={"policy": {"policy_id": "X"}, "claims": ui_sample_payload()["claims"]})
    assert response.status_code == 422


def test_ui_csv_parser_rejects_incomplete_row():
    with __import__("pytest").raises(ValueError, match="row 2 is missing"):
        parse_claims_csv_like_ui("claim_id,payer\nC001,\n")


def test_incomplete_rule_from_ui_payload_is_manual_review():
    payload = ui_sample_payload()
    payload["policy"]["rules"] = [
        {
            "rule_id": "R-INCOMPLETE",
            "category": "modifier",
            "description": "Modifier rule with no required modifier configured",
            "on_match_outcome": "fail",
            "priority": 10,
        }
    ]
    data = client.post("/v1/evaluate", json=payload).json()
    first = data["results"][0]
    assert first["outcome"] == "manual_review"
    assert any(not trace["evaluable"] for trace in first["traces"])


def test_evaluate_summary_includes_failure_reasons():
    data = client.post("/v1/evaluate", json=ui_sample_payload()).json()
    reasons = {item["rule_id"]: item["claim_count"] for item in data["summary"]["failure_reasons"]}
    assert reasons["R-TF-90"] == 1
    assert reasons["R-AUTH-27447"] == 1
