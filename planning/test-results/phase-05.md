# Phase 5 test result — Graph and verification

**Status:** tested

- The pinned LangGraph `0.6.11` workflow compiles and executes in tests.
- A claim without a valid evidence ID is rejected, retained only as audit data, and excluded from graph state used by reports.
- The report contains only supported claims; the bounded revision route cannot exceed two rounds.
- Backend lint passes and the backend suite passes.
