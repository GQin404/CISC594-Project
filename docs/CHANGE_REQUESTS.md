# Change Request Log

Scope changes against the approved project proposal are recorded here before implementation, as required by `docs/CHANGE_CONTROL.md`.

## CR-001 — Drop SQLite persistence from the delivered scope
**Requested:** Week 6 (Version 1 system-test prep)  
**Status:** Approved and implemented

**Change:** The proposal named SQLite as the storage layer. The delivered system loads policies from JSON files and claims from CSV/JSON files, and evaluates them in memory.

**Reason:** Every graded capability (policy validation, evaluation, comparison, attribution) is exercised through files and later the API. A database adds schema and migration work without changing system behavior or improving testability.

**Impact:** Schedule reduced (mitigates R4). No requirement lost. Test scope unchanged: fixtures remain the test oracle. SQLAlchemy is not added to `requirements.txt`.

## CR-002 — Deliver the workflow as an HTTP API instead of a browser UI
**Requested:** Week 6 (Version 1 system-test prep)  
**Status:** Approved; HTTP API implementation scheduled with Version 2 delivery

**Change:** The proposal described a browser-based application. The same workflows will be exposed through FastAPI endpoints (`/v1/evaluate`, `/v1/evaluate/export`, `/v2/compare`) instead of a browser UI.

**Reason:** Risk R4 (schedule) is mitigated by removing non-essential UI work. The rubric rewards system behavior and testing depth, not presentation.

**Impact:** Schedule reduced. System tests can exercise the API directly, which is more repeatable than UI testing. Version 1 remains complete as a library plus system-test pack; the HTTP surface is delivered with Version 2.
