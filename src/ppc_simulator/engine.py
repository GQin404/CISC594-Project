"""Deterministic single-policy evaluation engine (Version 1 core)."""

from __future__ import annotations

from .models import Claim, EvaluationResult, Outcome, Policy, Rule, RuleCategory, RuleTrace


def _rule_applies(rule: Rule, claim: Claim) -> bool:
    if rule.procedure_code and rule.procedure_code != claim.procedure_code:
        return False
    if rule.place_of_service and rule.place_of_service != claim.place_of_service:
        return False
    return True


def _evaluate_rule(rule: Rule, claim: Claim) -> RuleTrace:
    if not _rule_applies(rule, claim):
        return RuleTrace(
            rule_id=rule.rule_id,
            category=rule.category,
            matched=False,
            explanation=f"Rule {rule.rule_id} does not apply to claim {claim.claim_id}.",
        )

    if rule.category == RuleCategory.AUTHORIZATION and rule.authorization_required:
        matched = not claim.authorization_on_file
        explanation = (
            f"Authorization required for procedure {claim.procedure_code}; "
            f"authorization_on_file={claim.authorization_on_file}."
        )
        return RuleTrace(rule_id=rule.rule_id, category=rule.category, matched=matched, explanation=explanation)

    if rule.category == RuleCategory.MODIFIER and rule.modifier_required:
        matched = claim.modifier != rule.modifier_required
        explanation = (
            f"Modifier {rule.modifier_required} required; claim has modifier={claim.modifier!r}."
        )
        return RuleTrace(rule_id=rule.rule_id, category=rule.category, matched=matched, explanation=explanation)

    if rule.category == RuleCategory.PLACE_OF_SERVICE and rule.place_of_service:
        # _rule_applies already confirmed the place of service matches.
        explanation = (
            f"Place-of-service rule targets {rule.place_of_service}; "
            f"claim place_of_service={claim.place_of_service}."
        )
        return RuleTrace(rule_id=rule.rule_id, category=rule.category, matched=True, explanation=explanation)

    if rule.category == RuleCategory.TIMELY_FILING and rule.timely_filing_days is not None:
        days = (claim.submission_date - claim.service_date).days
        matched = days > rule.timely_filing_days
        explanation = (
            f"Timely-filing limit is {rule.timely_filing_days} days; "
            f"claim was submitted {days} day(s) after service."
        )
        return RuleTrace(rule_id=rule.rule_id, category=rule.category, matched=matched, explanation=explanation)

    return RuleTrace(
        rule_id=rule.rule_id,
        category=rule.category,
        matched=False,
        explanation=(
            f"Rule {rule.rule_id} is incomplete for category {rule.category.value}; "
            "the claim cannot be decided automatically and requires manual review."
        ),
    )


def policy_in_effect(policy: Policy, claim: Claim) -> bool:
    return policy.effective_start <= claim.service_date <= policy.effective_end


def evaluate_claim(policy: Policy, claim: Claim) -> EvaluationResult:
    if policy.payer_name != claim.payer:
        return EvaluationResult(
            claim_id=claim.claim_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            outcome=Outcome.MANUAL_REVIEW,
            explanations=[f"Claim payer {claim.payer!r} does not match policy payer {policy.payer_name!r}."],
            traces=[],
        )

    if not policy_in_effect(policy, claim):
        return EvaluationResult(
            claim_id=claim.claim_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            outcome=Outcome.MANUAL_REVIEW,
            explanations=[
                f"Service date {claim.service_date} is outside policy effective range "
                f"{policy.effective_start}–{policy.effective_end}."
            ],
            traces=[],
        )

    ordered = sorted(policy.rules, key=lambda r: r.priority)
    traces: list[RuleTrace] = []
    explanations: list[str] = []
    outcome = Outcome.PASS

    for rule in ordered:
        trace = _evaluate_rule(rule, claim)
        traces.append(trace)
        if not trace.matched:
            if "incomplete for category" in trace.explanation:
                explanations.append(trace.explanation)
            continue
        explanations.append(trace.explanation)
        if rule.on_match_outcome == Outcome.MANUAL_REVIEW:
            outcome = Outcome.MANUAL_REVIEW
            break
        if rule.on_match_outcome == Outcome.FAIL:
            outcome = Outcome.FAIL
            break

    if outcome == Outcome.PASS and not explanations:
        explanations.append("Claim satisfied all applicable policy rules.")

    return EvaluationResult(
        claim_id=claim.claim_id,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        outcome=outcome,
        explanations=explanations,
        traces=traces,
    )


def evaluate_portfolio(policy: Policy, claims: list[Claim]) -> list[EvaluationResult]:
    return [evaluate_claim(policy, claim) for claim in claims]
