# Phase 9 test result — Sarvam voice

**Status:** tested

- The browser creates 16 kHz mono WAV audio and enforces a 30-second maximum.
- The API rejects non-WAV, stereo, wrong-sample-rate, over-size, and over-length recordings before provider submission.
- Replay mode clearly falls back to typed chat, and microphone/transcription/synthesis errors leave text chat usable.
- `api/tests/test_sarvam_provider.py` verifies the current Saaras v4 and Bulbul v4 Flash REST payloads locally; it made no external Sarvam request.
- 2026-11-01 audit remediation: the frontend now disposes microphone tracks and its 30-second timer when the assistant unmounts or the selected research run changes.
- A minimal live Sarvam chat request and a minimal Bulbul TTS request passed on 2026-11-01. The end-to-end assistant endpoint returned a cited server-sent response for a live research run.
- The Sarvam unit tests now explicitly override `.env` credentials and `SARVAM_TTS_SPEAKER`; all 16 backend tests pass with real local keys present.

## Limit

English, Hindi, and code-mixed audio quality must be tested against a live Sarvam account and selected speaker configuration. Manual browser verification must also confirm microphone release after navigation away from an active recording.
