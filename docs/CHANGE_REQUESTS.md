# Change Request Log

Scope changes against the approved project proposal are recorded here before implementation, as required by `docs/CHANGE_CONTROL.md`.

## CR-001 — Drop SQLite persistence from the delivered scope
**Requested:** Week 6 (Version 1 system-test prep)  
**Status:** Approved and implemented

**Change:** The proposal named SQLite as the storage layer. The delivered system loads policies from JSON files and claims from CSV/JSON files, and evaluates them in memory.

**Reason:** Every graded capability (policy validation, evaluation, comparison, attribution) is exercised through files and later the API. A database adds schema and migration work without changing system behavior or improving testability.

**Impact:** Schedule reduced (mitigates R4). No requirement lost. Test scope unchanged: fixtures remain the test oracle. SQLAlchemy is not added to `requirements.txt`.

## CR-002 — Deliver a FastAPI browser UI plus JSON API
**Requested:** Week 6 (Version 1 system-test prep); implemented with Version 2  
**Status:** Approved and implemented

**Change:** The proposal described a browser-based FastAPI application. Version 1 stays a tested library. Version 2 serves a small browser UI from the same FastAPI process (`/` for evaluate and compare) and keeps JSON endpoints (`/v1/evaluate`, `/v1/evaluate/export`, `/v2/compare`) so system tests can run without a browser. There is no separate frontend framework.

**Reason:** Risk R4 (schedule) is mitigated by avoiding a standalone SPA and SQLite-backed screens. The rubric rewards system behavior and testing depth. Hosting the UI on FastAPI still matches the proposed browser-based delivery.

**Impact:** Users can run the V1 and V2 workflows in the browser. Automated tests continue to call the JSON API, which is more repeatable than UI-driver tests.

## CR-003 — Force manual review for incompletely configured rules
**Requested:** Week 9 (Version 2 system testing)  
**Status:** Approved and implemented

**Change:** A rule whose definition is incomplete for its category (for example a modifier rule with no required modifier) previously produced an explanation saying manual review was required while the claim still returned `pass`. The engine now marks such traces `evaluable=False` and returns `manual_review`.

**Reason:** Defect found during Version 2 testing (risk R9). The explanation and the outcome contradicted each other, which breaks the system's core promise of explainable, trustworthy results.

**Impact:** Behavior change in the Version 1 evaluation engine, carried into Version 2 comparison and attribution. Covered by unit test `test_incomplete_rule_forces_manual_review`, V1 system test V1-14, and V2 system test ST15.
