"""Run-scoped Sarvam chat and transient voice endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import get_sarvam_provider
from ..models import ResearchRun
from ..providers.base import ProviderError, ProviderUnavailable
from ..providers.sarvam import SarvamProvider
from ..schemas import AssistantMessageRequest, SpeechRequest, TranscriptionResponse
from ..services.conversation import ConversationService, wav_duration_ms

router = APIRouter(prefix="/research/{run_id}/assistant", tags=["assistant"])


def _run_or_404(db: Session, run_id: str) -> ResearchRun:
    run = db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Research run was not found."})
    return run


def _service(db: Session, settings: Settings, sarvam: SarvamProvider) -> ConversationService:
    return ConversationService(db, settings, sarvam)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/messages")
async def send_assistant_message(
    run_id: str,
    request: AssistantMessageRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    sarvam: SarvamProvider = Depends(get_sarvam_provider),
) -> StreamingResponse:
    run = _run_or_404(db, run_id)
    service = _service(db, settings, sarvam)
    try:
        reply = await service.reply(
            run,
            conversation_id=request.conversation_id,
            text=request.text,
            language=request.language,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail={"code": "conversation_not_found", "message": str(error)}) from error

    async def event_stream() -> AsyncIterator[str]:
        # The response stays stream-shaped for incremental Sarvam support without changing the public API.
        yield _sse("assistant.text.delta", {"text": reply.text})
        yield _sse(
            "assistant.final",
            {
                "conversation_id": reply.conversation_id,
                "message_id": reply.message_id,
                "text": reply.text,
                "citations": reply.citations,
                "language": reply.language,
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe_voice_turn(
    run_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    sarvam: SarvamProvider = Depends(get_sarvam_provider),
) -> TranscriptionResponse:
    _run_or_404(db, run_id)
    if file.content_type not in {"audio/wav", "audio/wave", "audio/x-wav"}:
        raise HTTPException(status_code=415, detail={"code": "wav_required", "message": "Upload a 16 kHz mono WAV recording."})
    audio = await file.read(settings.max_voice_bytes + 1)
    if len(audio) > settings.max_voice_bytes:
        raise HTTPException(status_code=413, detail={"code": "audio_too_large", "message": "Voice recording is too large."})
    try:
        duration_ms = wav_duration_ms(audio)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_audio", "message": str(error)}) from error
    if duration_ms > settings.max_voice_seconds * 1000:
        raise HTTPException(status_code=422, detail={"code": "audio_too_long", "message": "Record a question of 30 seconds or less."})
    try:
        transcript = await sarvam.transcribe(audio, filename=file.filename or "question.wav")
    except ProviderUnavailable as error:
        raise HTTPException(status_code=503, detail={"code": "voice_unavailable", "message": str(error)}) from error
    except ProviderError as error:
        raise HTTPException(status_code=502, detail={"code": "transcription_failed", "message": str(error)}) from error
    return TranscriptionResponse(
        text=transcript["text"], language=transcript.get("language", "auto"), duration_ms=duration_ms
    )


@router.post("/speech")
async def synthesize_assistant_speech(
    run_id: str,
    request: SpeechRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    sarvam: SarvamProvider = Depends(get_sarvam_provider),
) -> StreamingResponse:
    _run_or_404(db, run_id)
    service = _service(db, settings, sarvam)
    try:
        message = service.message_for_speech(run_id, request.message_id)
        audio, media_type = await sarvam.synthesize(message.content, language=message.language)
    except LookupError as error:
        raise HTTPException(status_code=404, detail={"code": "message_not_found", "message": str(error)}) from error
    except ProviderUnavailable as error:
        raise HTTPException(status_code=503, detail={"code": "voice_unavailable", "message": str(error)}) from error
    except ProviderError as error:
        raise HTTPException(status_code=502, detail={"code": "speech_failed", "message": str(error)}) from error
    # Deliberately return bytes directly: generated audio is not stored in a table or fixture.
    return StreamingResponse(iter([audio]), media_type=media_type, headers={"Cache-Control": "no-store"})
