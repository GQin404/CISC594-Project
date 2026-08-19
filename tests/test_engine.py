from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from ppc_simulator.claims_io import load_claims_csv
from ppc_simulator.engine import evaluate_claim, evaluate_portfolio
from ppc_simulator.models import Outcome, Policy
from ppc_simulator.reporting import export_results_csv, summarize_results


FIXTURES = ROOT / "data" / "fixtures"


@pytest.fixture
def policy() -> Policy:
    payload = json.loads((FIXTURES / "sample_policy_v1.json").read_text(encoding="utf-8"))
    return Policy.model_validate(payload)


@pytest.fixture
def claims():
    return load_claims_csv(FIXTURES / "sample_claims.csv")


def test_policy_rejects_inverted_dates():
    with pytest.raises(ValueError):
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


def test_timely_filing_boundary_pass(policy, claims):
    claim = next(c for c in claims if c.claim_id == "C001")
    result = evaluate_claim(policy, claim)
    assert result.outcome == Outcome.PASS


def test_timely_filing_over_limit_fail(policy, claims):
    claim = next(c for c in claims if c.claim_id == "C002")
    result = evaluate_claim(policy, claim)
    assert result.outcome == Outcome.FAIL
    assert any(t.rule_id == "R-TF-90" and t.matched for t in result.traces)


def test_authorization_missing_fail(policy, claims):
    claim = next(c for c in claims if c.claim_id == "C003")
    result = evaluate_claim(policy, claim)
    assert result.outcome == Outcome.FAIL
    assert any(t.rule_id == "R-AUTH-27447" and t.matched for t in result.traces)


def test_authorization_and_modifier_present_pass(policy, claims):
    claim = next(c for c in claims if c.claim_id == "C004")
    result = evaluate_claim(policy, claim)
    assert result.outcome == Outcome.PASS


def test_payer_mismatch_manual_review(policy, claims):
    claim = next(c for c in claims if c.claim_id == "C005")
    result = evaluate_claim(policy, claim)
    assert result.outcome == Outcome.MANUAL_REVIEW


def test_portfolio_summary_counts(policy, claims):
    results = evaluate_portfolio(policy, claims)
    outcomes = {r.claim_id: r.outcome for r in results}
    assert outcomes["C001"] == Outcome.PASS
    assert outcomes["C002"] == Outcome.FAIL
    assert len(results) == 7


def test_result_summary_counts_and_failure_reasons(policy, claims):
    summary = summarize_results(evaluate_portfolio(policy, claims))
    assert summary.total_claims == 7
    assert sum(summary.outcome_counts.values()) == 7
    assert summary.outcome_counts["fail"] == 2
    assert {reason.rule_id for reason in summary.failure_reasons} >= {"R-TF-90", "R-AUTH-27447"}


def test_export_results_csv(policy, claims, tmp_path):
    results = evaluate_portfolio(policy, claims)
    destination = export_results_csv(results, tmp_path / "results.csv")
    lines = destination.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("claim_id,policy_id,policy_version,outcome")
    assert len(lines) == len(results) + 1
