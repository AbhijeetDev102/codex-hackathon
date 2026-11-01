# Planning records

This folder is the durable, plain-language history of the project. It explains what was built, why it exists, how to test it, and what still needs work.

## How to use these records

- Start with [roadmap.md](roadmap.md) to see the phase order and current gate.
- Read [implementation-status.md](implementation-status.md) for the current code map, prototype limits, and final acceptance evidence.
- Read `phases/` for the work and acceptance checks for one phase.
- Read `components/` to understand a part of the code without reading every source file.
- Read `decisions/` for choices that should not be silently reversed later.
- Read `test-results/` for commands, results, and manual checks that support a phase gate.

## Required update rule

Every completed work item updates the affected component page, its phase page, `change-log.md`, and a test-result record. Create an ADR when a change affects public behaviour, data storage, a provider, safety, or the project architecture.

Use these status values consistently: `planned`, `in_progress`, `blocked`, `tested`, and `accepted`. A phase is `accepted` only after its tests are recorded and the project owner approves its gate.

## Plain-language standard

Write for a future teammate who did not build the project. Each component page must say what the code does, where it lives, what enters and leaves it, which outside services it uses, how it fails safely, and how it is tested.
