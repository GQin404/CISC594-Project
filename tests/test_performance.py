"""Scale check for risk R7: comparison performance on larger claim portfolios."""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"

from ppc_simulator.compare import compare_portfolio
from ppc_simulator.models import Claim, Policy

PORTFOLIO_SIZE = 2000
TIME_BUDGET_SECONDS = 10.0


def load_policy(name: str) -> Policy:
    return Policy.model_validate(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def generate_claims(count: int) -> list[Claim]:
    service = date(2026, 1, 10)
    return [
        Claim(
            claim_id=f"G{index:05d}",
            payer="Acme Health",
            service_date=service,
            submission_date=service + timedelta(days=index % 120),
            procedure_code="99213" if index % 2 else "27447",
            diagnosis_code="J06.9",
            modifier="LT" if index % 3 == 0 else None,
            place_of_service="22" if index % 5 == 0 else "11",
            authorization_on_file=index % 4 != 0,
        )
        for index in range(count)
    ]


@pytest.mark.parametrize("size", [PORTFOLIO_SIZE])
def test_comparison_scales_to_larger_portfolio(size):
    baseline = load_policy("sample_policy_v1.json")
    proposed = load_policy("sample_policy_v2.json")
    claims = generate_claims(size)

    started = time.perf_counter()
    summary = compare_portfolio(baseline, proposed, claims)
    elapsed = time.perf_counter() - started

    assert summary.total_claims == size
    assert summary.changed_claims + summary.unchanged_claims == size
    assert elapsed < TIME_BUDGET_SECONDS, f"comparison took {elapsed:.2f}s for {size} claims"
