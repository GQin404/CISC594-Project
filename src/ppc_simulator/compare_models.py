"""Version 2 models for policy comparison and impact analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .models import EvaluationResult, Outcome


class ClaimComparison(BaseModel):
    claim_id: str
    baseline_outcome: Outcome
    proposed_outcome: Outcome
    changed: bool
    transition: str
    attributed_rule_ids: list[str] = Field(default_factory=list)
    attribution_notes: list[str] = Field(default_factory=list)
    baseline_result: EvaluationResult
    proposed_result: EvaluationResult


class RuleImpact(BaseModel):
    rule_id: str
    affected_claim_count: int
    percent_of_portfolio: float
    percent_of_changes: float


class ImpactSummary(BaseModel):
    total_claims: int
    changed_claims: int
    unchanged_claims: int
    transition_counts: dict[str, int]
    rule_impacts: list[RuleImpact]
    comparisons: list[ClaimComparison]
