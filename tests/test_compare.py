from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from ppc_simulator.claims_io import load_claims_csv
from ppc_simulator.compare import attribute_change, compare_claim, compare_portfolio
from ppc_simulator.engine import evaluate_claim
from ppc_simulator.models import Outcome, Policy


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
