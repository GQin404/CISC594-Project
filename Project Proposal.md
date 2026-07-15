# Project Proposal: Payer Policy Change Impact Simulator

## System Overview and Problem Definition

Healthcare revenue cycle management (RCM) teams must update claim-processing rules when payers change reimbursement policies involving prior authorization, modifiers, place-of-service restrictions, or filing deadlines. Organizations may discover the effects only after claims are denied, causing delayed payment, appeals, and added administrative work.

The proposed **Payer Policy Change Impact Simulator** will let users model payer policies and evaluate them against synthetic claims before operational use. RCM analysts will assess potential denial impact, policy-configuration staff will create and revise structured rules, and software testers or QA personnel will build scenarios and verify expected outcomes. The system will produce deterministic, explainable results showing whether each claim passes, fails, or requires manual review.

To keep the semester scope realistic, the system will support a limited set of administrative rule categories rather than reproduce complete payer adjudication. Only synthetic or properly de-identified data will be used; the system will not provide medical advice or make clinical decisions. The planned implementation is a browser-based application using Python and FastAPI with SQLite storage, with automated tests written in pytest.

## Major Features and System Scope

### Policy and Rule Management

Users will create structured payer policies containing identifiers, effective dates, version numbers, conditions, and outcomes. For example, a rule may require authorization for a selected procedure and place of service. Before saving a policy, the system will reject invalid date ranges, duplicate identifiers, and incomplete conditions, making rule behavior reproducible and testable.

### Synthetic Claim Dataset Management

Users will import synthetic claims in a documented CSV or JSON format. Claim fields may include service and submission dates, payer, procedure and diagnosis codes, modifier, place of service, and authorization status. The system will report malformed or unsupported records and allow users to select claim subsets for targeted scenarios, such as submissions exactly on a filing deadline.

### Policy Evaluation and Explainable Results

The simulation engine will classify each selected claim as **pass**, **fail**, or **manual review required**. Each result will identify the evaluated rule, relevant claim values, and a human-readable explanation so users can distinguish a policy failure from incomplete claim data. Summary reports will show result counts and common failure reasons, while claim-level results can be inspected and exported.

### Policy Version Comparison and Portfolio Replay

In Version 2, users will evaluate the same claim portfolio against a current and proposed policy. The system will identify claims whose outcomes changed and connect each difference to the responsible rule. Impact summaries will report the number and percentage of affected claims, helping users focus review on the highest-impact changes.

The first three features form the complete Version 1 workflow; policy comparison and portfolio replay are deliberately reserved for Version 2.

## Versioning and Incremental Development

### Version 1: Single-Policy Simulation

Version 1 will include policy creation and validation, synthetic claim import, single-policy evaluation, explanations, and summary reports. This foundation belongs first because comparisons cannot be trusted until individual policies are evaluated correctly. After a complete system test, the release and test report will be preserved under the `v1.0` tag before Version 2 begins.

### Version 2: Policy Change Impact Analysis

Version 2 will add policy-version comparison, portfolio replay, changed-outcome classification, rule-level attribution, and impact summaries. This changes the workflow from evaluating one policy to determining what changes under a proposed replacement and why. A complete system test will cover both inherited and new behavior before the release is tagged `v2.0`.

## System Testing Strategy

Each version will be built and completely system tested before development proceeds. Version 1 testing will use equivalence partitioning, boundary-value analysis, decision tables, and state-transition testing to cover policy creation, claim import, rule execution, explanations, and exports. Cases will include malformed input, missing values, invalid date ranges, exact filing deadlines, overlapping conditions, and conflicting rules.

Version 2 will repeat the Version 1 regression suite and add identical policies, single and combined rule changes, effective-date boundaries, changed precedence, and every possible outcome transition. Complexity increases because tests must verify both each policy's decision and the detected difference and cause. Controlled synthetic datasets with predefined expected results will provide reliable test oracles.

## Intelligent-System Positioning

The simulator will not be described as smart, intelligent, predictive, or AI-enabled. Explicit, deterministic rules are appropriate because users must reproduce and explain every result. The system provides administrative decision support but does not predict denials or make autonomous clinical or reimbursement decisions.

## Risks and Risk Management

The general scope risk is that real payer policies are ambiguous and more complex than a semester project can support; limiting the system to defined administrative rule categories and representative synthetic policies will mitigate it. The Version 1 risk is inaccurate results from rule precedence or date handling, addressed through validation, boundary tests, and manually verified datasets. The Version 2 risk is incorrect attribution when several rules change together; stable rule identifiers, evaluation traces, and individual and combined change tests will mitigate it. Performance will also be evaluated with generated portfolios of increasing size.

A risk register will track each risk's probability, impact, mitigation, status, and affected version and will be reviewed at every milestone.

## Version Control and Change Management

The source will be maintained in a Git repository accessible to the instructor. Tracked issues and feature branches will represent planned changes, and pull requests will reference the relevant requirement or defect, include test evidence, and be merged only after review and passing tests. Releases will be tagged `v1.0` and `v2.0`. Scope changes will be recorded as change requests and evaluated for effects on schedule, risk, design, and system tests before implementation.
