"""Version 2: dual-policy portfolio replay, change detection, and attribution."""

from __future__ import annotations

from .compare_models import ClaimComparison, ImpactSummary, RuleImpact
from .engine import evaluate_claim
from .models import Claim, EvaluationResult, Outcome, Policy, Rule


def _rule_signature(rule: Rule) -> tuple:
    return (
        rule.category.value,
        rule.procedure_code,
        rule.place_of_service,
        rule.modifier_required,
        rule.authorization_required,
        rule.timely_filing_days,
        rule.on_match_outcome.value,
        rule.priority,
    )


def deciding_rule_id(result: EvaluationResult) -> str | None:
    if result.outcome == Outcome.PASS:
        return None
    for trace in result.traces:
        if trace.matched or not trace.evaluable:
            return trace.rule_id
    return None


def _matched_rule_ids(result: EvaluationResult) -> set[str]:
    return {trace.rule_id for trace in result.traces if trace.matched or not trace.evaluable}


def attribute_change(
    baseline: Policy,
    proposed: Policy,
    baseline_result: EvaluationResult,
    proposed_result: EvaluationResult,
) -> tuple[list[str], list[str]]:
    """Return attributed rule IDs and human-readable notes for an outcome change."""
    if baseline_result.outcome == proposed_result.outcome:
        return [], []

    baseline_rules = {rule.rule_id: rule for rule in baseline.rules}
    proposed_rules = {rule.rule_id: rule for rule in proposed.rules}

    notes: list[str] = []
    attributed: list[str] = []

    baseline_decider = deciding_rule_id(baseline_result)
    proposed_decider = deciding_rule_id(proposed_result)

    added = sorted(set(proposed_rules) - set(baseline_rules))
    removed = sorted(set(baseline_rules) - set(proposed_rules))
    shared = sorted(set(baseline_rules) & set(proposed_rules))

    changed_defs = [
        rule_id
        for rule_id in shared
        if _rule_signature(baseline_rules[rule_id]) != _rule_signature(proposed_rules[rule_id])
    ]

    baseline_matched = _matched_rule_ids(baseline_result)
    proposed_matched = _matched_rule_ids(proposed_result)

    for rule_id in added:
        if rule_id in proposed_matched or rule_id == proposed_decider:
            attributed.append(rule_id)
            notes.append(f"Added rule {rule_id} contributed to the proposed outcome.")

    for rule_id in removed:
        if rule_id in baseline_matched or rule_id == baseline_decider:
            attributed.append(rule_id)
            notes.append(f"Removed rule {rule_id} contributed to the baseline outcome.")

    for rule_id in changed_defs:
        match_flipped = (rule_id in baseline_matched) != (rule_id in proposed_matched)
        is_decider = rule_id in {baseline_decider, proposed_decider}
        if match_flipped or is_decider:
            attributed.append(rule_id)
            notes.append(
                f"Changed rule {rule_id} differs between policy versions and affects this claim."
            )

    # Fallback: if outcomes differ but no structural rule diff matched, cite deciders.
    if not attributed:
        if proposed_decider:
            attributed.append(proposed_decider)
            notes.append(f"Proposed deciding rule {proposed_decider} produced the new outcome.")
        if baseline_decider and baseline_decider not in attributed:
            attributed.append(baseline_decider)
            notes.append(f"Baseline deciding rule {baseline_decider} produced the prior outcome.")
        if not attributed:
            notes.append(
                "Outcome changed but no single rule attribution could be determined; "
                "review evaluation traces."
            )

    # Preserve order, drop duplicates
    deduped: list[str] = []
    for rule_id in attributed:
        if rule_id not in deduped:
            deduped.append(rule_id)
    return deduped, notes


def compare_claim(baseline: Policy, proposed: Policy, claim: Claim) -> ClaimComparison:
    baseline_result = evaluate_claim(baseline, claim)
    proposed_result = evaluate_claim(proposed, claim)
    changed = baseline_result.outcome != proposed_result.outcome
    transition = f"{baseline_result.outcome.value}->{proposed_result.outcome.value}"
    attributed: list[str] = []
    notes: list[str] = []
    if changed:
        attributed, notes = attribute_change(baseline, proposed, baseline_result, proposed_result)
    return ClaimComparison(
        claim_id=claim.claim_id,
        baseline_outcome=baseline_result.outcome,
        proposed_outcome=proposed_result.outcome,
        changed=changed,
        transition=transition,
        attributed_rule_ids=attributed,
        attribution_notes=notes,
        baseline_result=baseline_result,
        proposed_result=proposed_result,
    )


def compare_portfolio(baseline: Policy, proposed: Policy, claims: list[Claim]) -> ImpactSummary:
    comparisons = [compare_claim(baseline, proposed, claim) for claim in claims]
    total = len(comparisons)
    changed = [item for item in comparisons if item.changed]
    transition_counts: dict[str, int] = {}
    rule_counts: dict[str, int] = {}

    for item in comparisons:
        transition_counts[item.transition] = transition_counts.get(item.transition, 0) + 1
        if item.changed:
            for rule_id in item.attributed_rule_ids:
                rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

    changed_n = len(changed)
    rule_impacts = [
        RuleImpact(
            rule_id=rule_id,
            affected_claim_count=count,
            percent_of_portfolio=round((count / total) * 100, 2) if total else 0.0,
            percent_of_changes=round((count / changed_n) * 100, 2) if changed_n else 0.0,
        )
        for rule_id, count in sorted(rule_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]

    return ImpactSummary(
        total_claims=total,
        changed_claims=changed_n,
        unchanged_claims=total - changed_n,
        transition_counts=transition_counts,
        rule_impacts=rule_impacts,
        comparisons=comparisons,
    )
