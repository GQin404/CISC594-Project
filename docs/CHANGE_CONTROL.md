# Change Control Process — Payer Policy Change Impact Simulator

## Version control
- GitHub repository with instructor access: https://github.com/GQin404/CISC594-Project
- `main` is the integration baseline (releasable history only). It is the GitHub default branch (the assignment's `master` equivalent).
- All new development happens on a branch other than `main`. Branch names use `feat/`, `fix/`, `docs/`, or `test/` plus a short description.
- Pull requests are the only way code enters `main`.
- After `v2.0`, further working-baseline changes still use a feature branch and pull request. They do not create a new version tag. Checkout `v2.0` for the Version 2 release gate; checkout `main` for the current working baseline.
- Annotated tags mark each released version: `v1.0`, `v2.0`.

## Change workflow
1. Record the requirement or defect as a change request in `CHANGE_REQUESTS.md` and/or a risk-register entry.
2. Create a feature branch from the current `main` baseline.
3. Implement the change together with the tests that cover it.
4. Open a pull request against `main` that names the week/milestone, the tests run, and any change-request ID.
5. Merge only after the review checklist below is complete and the automated tests that apply at that milestone are green.
6. For a version release: run the complete system-test pack, record evidence under `docs/`, merge that evidence PR, then tag `main`.

Because this is a single-developer project, the author also performs the PR review against the checklist. The PR is still a formal gate: work stays off `main` until tests are recorded and the merge is explicit.

## Change-request states
- **Proposed:** The requirement, defect, reason, and expected impact have been recorded.
- **Approved:** The change is accepted for implementation after scope, schedule, risk, design, and test effects are reviewed.
- **In progress:** Work is isolated on a named branch and its tests are being developed.
- **Verified:** Applicable automated and system tests pass and the pull-request checklist is complete.
- **Implemented:** The verified pull request is merged into the current working baseline.
- **Deferred or rejected:** The request is retained in the log with the reason it will not enter the current baseline.

For this single-student project, approval and review are self-review steps. `CHANGE_REQUESTS.md` records the final status and evidence for each request.

## Pull-request review checklist
- Unit tests that exist at this milestone (`pytest`) pass
- Change is limited to one coherent purpose
- Fixtures or expected-result oracles are updated if behavior changed
- A change request is recorded if the proposal or version boundary is affected
- The version's system-test pack is re-run when the change could affect a release baseline

## Release gates
| Version | System-test pack | Evidence | Tag |
|---------|------------------|----------|-----|
| V1 | `scripts/run_v1_system_tests.py` | `docs/V1_SYSTEM_TEST_EVIDENCE.md` | `v1.0` |
| V2 | `scripts/run_system_tests.py` | `docs/V2_SYSTEM_TEST_EVIDENCE.md` | `v2.0` |

A version is tagged only after its system-test pack passes in full and the evidence file is on `main`. Version 2 development does not start until `v1.0` exists.

## Scope changes
Any change that adds a rule category, alters version boundaries, drops a proposed component, or expands V2 scope requires a short change-request note covering schedule, risk, design, and test impact before implementation.
