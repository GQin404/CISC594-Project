from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from ppc_simulator.claims_io import load_claims_csv
from ppc_simulator.compare import attribute_change, compare_claim, compare_portfolio
from ppc_simulator.engine import evaluate_claim
from ppc_simulator.models import Claim, Outcome, Policy


FIXTURES = ROOT / "data" / "fixtures"


@pytest.fixture
def baseline() -> Policy:
    payload = json.loads((FIXTURES / "sample_policy_v1.json").read_text(encoding="utf-8"))
    return Policy.model_validate(payload)


@pytest.fixture
def proposed() -> Policy:
    payload = json.loads((FIXTURES / "sample_policy_v2.json").read_text(encoding="utf-8"))
    return Policy.model_validate(payload)


@pytest.fixture
def claims():
    return load_claims_csv(FIXTURES / "sample_claims.csv")


def test_identical_policies_no_changes(baseline, claims):
    summary = compare_portfolio(baseline, baseline, claims)
    assert summary.changed_claims == 0
    assert summary.unchanged_claims == summary.total_claims


def test_single_rule_change_timely_filing_attribution(baseline, proposed, claims):
    claim = next(c for c in claims if c.claim_id == "C006")
    assert evaluate_claim(baseline, claim).outcome == Outcome.PASS
    assert evaluate_claim(proposed, claim).outcome == Outcome.FAIL

    comparison = compare_claim(baseline, proposed, claim)
    assert comparison.changed is True
    assert comparison.transition == "pass->fail"
    assert "R-TF-90" in comparison.attributed_rule_ids


def test_added_rule_place_of_service_attribution(baseline, proposed, claims):
    claim = next(c for c in claims if c.claim_id == "C007")
    comparison = compare_claim(baseline, proposed, claim)
    assert comparison.transition == "pass->manual_review"
    assert "R-POS-22" in comparison.attributed_rule_ids


def test_combined_changes_impact_summary(baseline, proposed, claims):
    summary = compare_portfolio(baseline, proposed, claims)
    assert summary.total_claims == 7
    assert summary.changed_claims >= 2
    assert "pass->fail" in summary.transition_counts
    assert "pass->manual_review" in summary.transition_counts

    impacted = {item.rule_id for item in summary.rule_impacts}
    assert "R-TF-90" in impacted
    assert "R-POS-22" in impacted
    for item in summary.rule_impacts:
        assert 0 <= item.percent_of_portfolio <= 100
        assert 0 <= item.percent_of_changes <= 100


def test_attribute_change_ignores_unchanged_outcomes(baseline, proposed, claims):
    claim = next(c for c in claims if c.claim_id == "C001")
    left = evaluate_claim(baseline, claim)
    right = evaluate_claim(proposed, claim)
    attributed, notes = attribute_change(baseline, proposed, left, right)
    assert left.outcome == right.outcome == Outcome.PASS
    assert attributed == []
    assert notes == []


def _policy(**overrides) -> Policy:
    payload = {
        "policy_id": "POL-TRANS",
        "payer_name": "Acme Health",
        "version": "1.0",
        "effective_start": "2026-01-01",
        "effective_end": "2026-12-31",
        "rules": [],
    }
    payload.update(overrides)
    return Policy.model_validate(payload)


def _claim(**overrides) -> Claim:
    payload = {
        "claim_id": "T001",
        "payer": "Acme Health",
        "service_date": "2026-01-10",
        "submission_date": "2026-04-15",
        "procedure_code": "99213",
        "diagnosis_code": "J06.9",
        "modifier": None,
        "place_of_service": "11",
        "authorization_on_file": True,
    }
    payload.update(overrides)
    return Claim.model_validate(payload)


TF_90 = {
    "rule_id": "R-TF-90",
    "category": "timely_filing",
    "description": "Filing window",
    "timely_filing_days": 90,
    "on_match_outcome": "fail",
    "priority": 10,
}


def test_fail_to_pass_when_filing_window_widens():
    baseline = _policy(rules=[TF_90])
    proposed = _policy(version="2.0", rules=[{**TF_90, "timely_filing_days": 120}])
    comparison = compare_claim(baseline, proposed, _claim())
    assert comparison.transition == "fail->pass"
    assert "R-TF-90" in comparison.attributed_rule_ids


def test_fail_to_manual_review_when_higher_priority_pos_rule_added():
    pos = {
        "rule_id": "R-POS-11",
        "category": "place_of_service",
        "description": "POS 11 review",
        "place_of_service": "11",
        "on_match_outcome": "manual_review",
        "priority": 1,
    }
    comparison = compare_claim(
        _policy(rules=[TF_90]),
        _policy(version="2.0", rules=[pos, TF_90]),
        _claim(),
    )
    assert comparison.transition == "fail->manual_review"
    assert "R-POS-11" in comparison.attributed_rule_ids


def test_manual_review_to_pass_when_claim_enters_effective_range():
    comparison = compare_claim(
        _policy(effective_start="2026-06-01", effective_end="2026-12-31"),
        _policy(version="2.0"),
        _claim(submission_date="2026-01-12"),
    )
    assert comparison.transition == "manual_review->pass"


def test_manual_review_to_fail_when_in_range_policy_applies_timely_filing():
    comparison = compare_claim(
        _policy(effective_start="2026-06-01", effective_end="2026-12-31"),
        _policy(version="2.0", rules=[TF_90]),
        _claim(),
    )
    assert comparison.transition == "manual_review->fail"
    assert "R-TF-90" in comparison.attributed_rule_ids


def test_precedence_change_swaps_fail_and_manual_review():
    auth = {
        "rule_id": "R-AUTH-27447",
        "category": "authorization",
        "description": "Auth required",
        "procedure_code": "27447",
        "authorization_required": True,
        "on_match_outcome": "fail",
        "priority": 10,
    }
    pos = {
        "rule_id": "R-POS-22",
        "category": "place_of_service",
        "description": "POS 22 review",
        "place_of_service": "22",
        "on_match_outcome": "manual_review",
        "priority": 20,
    }
    claim = _claim(
        procedure_code="27447",
        authorization_on_file=False,
        place_of_service="22",
        submission_date="2026-01-12",
    )
    comparison = compare_claim(
        _policy(rules=[auth, pos]),
        _policy(version="2.0", rules=[{**auth, "priority": 30}, {**pos, "priority": 5}]),
        claim,
    )
    assert comparison.transition == "fail->manual_review"
    assert "R-POS-22" in comparison.attributed_rule_ids
