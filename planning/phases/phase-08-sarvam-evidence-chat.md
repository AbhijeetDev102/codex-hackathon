# Phase 8 — Sarvam evidence chat

**Status:** tested

## Goal

Let a user ask natural-language questions about a selected run without weakening the evidence rules.

## Scope

- Add Sarvam-105B through a `ConversationProvider`; keys remain server-side.
- Persist conversation text, language, and citations only.
- Retrieve only supported claims, verified events, metrics, report content, and allowed evidence excerpts.
- Support English, Hindi, and code-mixed prompts with automatic detection.
- Validate every factual response citation before it reaches the browser.

## Gate

Answers cite valid evidence, missing evidence receives an honest limitation, and tests cover prompt injection, an unknown evidence ID, and an attempt to alter a report.

## Implementation record

- Code: `/api/app/services/conversation.py`, `/api/app/providers/sarvam.py`, `/api/app/routes/assistant.py`, and the assistant panel.
- Inputs: supported claims, verified events, outcome data, and allowed evidence excerpts. Outputs: citation-validated streamed text plus a stored text transcript.
- Trust gate: every substantive Sarvam response sentence must carry only an approved receipt from the selected run; invalid or incomplete citation coverage is replaced by a deterministic limitation/fallback.
- Tests: grounded replies include known evidence IDs, invalid/unknown receipts and uncited follow-on statements are rejected, and unrelated questions are refused. Live Sarvam multilingual validation remains pending API credentials.
