# Phase 8 test result — Sarvam evidence chat

**Status:** tested

- Conversation tests verify a grounded answer cites known evidence and an unrelated question receives an honest limitation.
- System instructions explicitly treat source text as data, never instructions; the server rejects unknown receipts and any substantive response sentence that lacks a valid selected-run receipt.
- Text conversations and citations persist; user audio is not part of the conversation schema.

## Limit

Run a live Sarvam multilingual and tool-response validation after `SARVAM_API_KEY` is configured.
