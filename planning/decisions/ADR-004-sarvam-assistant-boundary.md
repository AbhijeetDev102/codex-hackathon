# ADR-004: Sarvam assistant boundary and privacy

**Status:** accepted

## Decision

Sarvam is a read-only assistant scoped to one run. It can discuss only approved claims, verified events, metrics, report content, and cited evidence. It cannot start research, modify reports, or create facts. Text transcripts and citations are stored; microphone audio is processed transiently and not retained.

## Why

Conversation is useful for explaining a report, but it must not bypass the project’s evidence controls or add unnecessary audio-retention risk.
