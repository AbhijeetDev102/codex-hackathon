# Delivery roadmap

| Phase | Status | Goal | Gate |
| --- | --- | --- | --- |
| 0 | tested | Planning baseline and contracts | Documents reconciled and planning system created; owner approval is pending |
| 1 | tested | Runnable platform foundation | Compose config, backend/API, and frontend checks pass; Docker daemon unavailable |
| 2 | tested | Evidence ingestion and replay | Evidence/source mapping verified in four fixtures |
| 3 | tested | Financial, outcome, and inflection analysis | Deterministic analysis unit tests pass |
| 4 | tested | Evidence-backed event timeline | Source-linked timeline endpoint/UI pass using synthetic replay data |
| 5 | tested | LangGraph reasoning and verification | Unsupported claims excluded from reports |
| 6 | tested | Product UI and progress | Typecheck, Vitest, and production build pass |
| 7 | tested | Patterns and demo resilience | Four-case survivor control passes in replay mode |
| 8 | tested | Sarvam evidence chat | Citation/refusal behavior passes locally; live-key validation is pending |
| 9 | tested | Sarvam push-to-talk voice | Safe capture/fallback paths are tested; live-provider validation is pending |
| 10 | blocked | Final acceptance | Needs Docker Compose and live-provider/manual checks |

## Gate process

1. Implement the phase scope only.
2. Run the listed automated and manual checks.
3. Save command output and observations under `test-results/`.
4. Update the phase and component documents in simple language.
5. Mark the phase `tested` and present the evidence for approval.
6. Only then mark it `accepted` and begin the following phase.

The implementation is demo-first. Live providers are optional when keys are unavailable; replay-mode tests are mandatory.
