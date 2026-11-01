# Sarvam research assistant

## In simple language

The Sarvam assistant lets a user ask questions about one research run by chat or short voice recording. It can explain verified evidence, but it cannot change research, launch a run, or turn a guess into a fact.

## Implemented code map

- `/api/app/providers/sarvam.py` calls Sarvam's raw chat, speech-to-text, and text-to-speech APIs. It does not use a managed voice agent, so the application keeps control over evidence and citations.
- `/api/app/services/conversation.py` selects only supported claims, verified events, verified outcomes, and their receipts; it validates returned citations before storing a response.
- `/api/app/routes/assistant.py` exposes streamed chat, transcription, and synthesized-speech routes.
- `/api/app/models.py` stores `conversations` and `conversation_messages`; it has no table for microphone audio.
- `/web/components/AssistantPanel.tsx` records 16 kHz mono WAV audio, displays chat/citations, and plays temporary reply audio.
- `/web/lib/api.ts` reads the assistant event stream and sends audio only for the current request.
- The live adapter uses Sarvam's raw endpoints and current model contracts: `sarvam-105b` at `/v1/chat/completions`, `saaras:v4` at `/speech-to-text`, and `bulbul:v4-flash` at `/text-to-speech`.
- Provider-contract references: [Sarvam chat](https://docs.sarvam.ai/api/token-factory/chat-completions), [Saaras speech-to-text](https://docs.sarvam.ai/api/api-guides-tutorials/models/saaras), and [Bulbul text-to-speech](https://docs.sarvam.ai/api/api-guides-tutorials/models/bulbul).

## Data flow and storage

1. The browser sends typed text or a maximum 30-second, 16 kHz mono WAV file.
2. For voice, Saaras transcription returns text. The browser then submits the same evidence-grounded chat request as a typed question.
3. The conversation service builds a restricted context from the selected run. Source text is treated as data, never as instructions.
4. Sarvam-105B may answer only from that context. Every substantive response sentence must carry a valid selected-run receipt; missing, unknown, or incomplete citation coverage is replaced with an honest local fallback.
5. Bulbul speech synthesis returns response bytes directly to the browser. The system stores text, language, timestamps, and citations—not user audio or generated audio.

English, Hindi, and Devanagari/mixed-language questions use automatic language selection unless the caller explicitly requests English or Hindi.

## Safe failures and limits

- A run that is not complete returns progress information rather than premature findings.
- Questions without relevant verified evidence receive “I cannot confirm that from the verified evidence in this analysis.”
- Replay mode deliberately disables live voice; the cited typed conversation remains available offline.
- Missing Sarvam credentials, microphone denial, silence, invalid WAV files, wrong sample rate, oversized uploads, or provider errors leave the text/evidence interface usable.
- Leaving the assistant view or switching runs releases the active microphone stream and clears its 30-second timer immediately; a recording cannot continue into another run.
- The service validates `E-...` citations against the selected run and requires citation coverage sentence by sentence, blocking cross-run citation leakage, uncited follow-on claims, and source-text prompt injection.

## Concrete tests

- `api/tests/test_replay_and_conversation.py` verifies grounded fallback answers cite `E-001`, unrelated questions are refused, and a model reply with an unknown receipt or uncited follow-on assertion is replaced before storage.
- `api/tests/test_api_replay.py` verifies the public assistant message endpoint returns a cited replay answer.
- `api/tests/test_sarvam_provider.py` locks the Saaras automatic-language and Bulbul v4 Flash request shapes without making a paid network call.
- Sarvam-focused tests explicitly override real `.env` keys and speaker choices, so local test runs never send requests to a developer's account or depend on their selected voice.
- On 2026-11-01, minimal live Sarvam chat and TTS requests succeeded; the live Peloton assistant endpoint also returned a cited server-sent response.
- Manual browser checks cover microphone permission denial, the 30-second cutoff, navigation away while recording, replay-mode voice notice, English/Hindi input, and speech-provider failure fallback.
