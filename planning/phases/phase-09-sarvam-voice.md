# Phase 9 — Sarvam push-to-talk voice

**Status:** tested

## Goal

Allow a user to speak a question and hear the same evidence-grounded answer.

## Scope

- Capture at most 30 seconds of 16 kHz mono WAV in the browser.
- Use Saaras v4 for transcription and Bulbul v4 Flash for assistant speech.
- Show transcript and citations before or alongside playback.
- Do not save microphone audio; keep the text exchange only.
- Preserve usable text chat when microphone permission, transcription, or speech synthesis fails.

## Gate

Test English, Hindi, and mixed-language turns plus denied microphone, silence, oversized recording, missing provider key, and replay-mode text fallback.

## Implementation record

- Code: `/web/components/AssistantPanel.tsx`, `/api/app/routes/assistant.py`, and `/api/app/providers/sarvam.py`.
- Inputs: a browser-created 16 kHz mono WAV file and an approved assistant message. Outputs: transient transcription and transient synthesized speech.
- Safety: audio is not written to the database or fixture cache; text chat remains usable if voice fails.
- Lifecycle safety: changing runs or unmounting the assistant stops the active microphone track and clears the recording timer.
- Provider contract: Saaras receives `model=saaras:v4`, `mode=transcribe`, and `language_code=auto`; Bulbul receives `model=bulbul:v4-flash`, `text`, `language_code`, and explicit WAV/16 kHz output settings.
