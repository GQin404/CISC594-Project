"""Version 1 result summaries and claim-level export."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from pydantic import BaseModel, Field

from .models import EvaluationResult, Outcome


class FailureReason(BaseModel):
    rule_id: str
    claim_count: int


class ResultSummary(BaseModel):
    total_claims: int
    outcome_counts: dict[str, int]
    failure_reasons: list[FailureReason] = Field(default_factory=list)


def summarize_results(results: list[EvaluationResult]) -> ResultSummary:
    """Aggregate claim-level outcomes and the rules that most often blocked claims."""
    outcome_counts = {outcome.value: 0 for outcome in Outcome}
    rule_counts: dict[str, int] = {}

    for result in results:
        outcome_counts[result.outcome.value] += 1
        if result.outcome == Outcome.PASS:
            continue
        for trace in result.traces:
            if trace.matched or not trace.evaluable:
                rule_counts[trace.rule_id] = rule_counts.get(trace.rule_id, 0) + 1
                break

    failure_reasons = [
        FailureReason(rule_id=rule_id, claim_count=count)
        for rule_id, count in sorted(rule_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]
    return ResultSummary(
        total_claims=len(results),
        outcome_counts=outcome_counts,
        failure_reasons=failure_reasons,
    )


EXPORT_COLUMNS = ["claim_id", "policy_id", "policy_version", "outcome", "deciding_rule", "explanation"]


def _deciding_rule(result: EvaluationResult) -> str:
    for trace in result.traces:
        if trace.matched or not trace.evaluable:
            return trace.rule_id
    return ""


def results_to_csv(results: list[EvaluationResult]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)
    for result in results:
        writer.writerow(
            [
                result.claim_id,
                result.policy_id,
                result.policy_version,
                result.outcome.value,
                _deciding_rule(result),
                " ".join(result.explanations),
            ]
        )
    return buffer.getvalue()


def export_results_csv(results: list[EvaluationResult], path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(results_to_csv(results), encoding="utf-8")
    return destination
