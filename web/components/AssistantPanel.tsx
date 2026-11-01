"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamAssistantMessage, synthesizeSpeech, transcribeAudio } from "../lib/api";
import type { AssistantMessage, ResearchRun } from "../lib/types";

interface Props {
  run: ResearchRun;
  onEvidence: (evidenceId: string) => void;
}

interface RecorderSession {
  stop: () => Promise<Blob>;
  dispose: () => void;
}

function assistantLanguage(language: string | undefined): "auto" | "en" | "hi" {
  if (language?.toLowerCase().startsWith("hi")) return "hi";
  if (language?.toLowerCase().startsWith("en")) return "en";
  return "auto";
}

function mergeBuffers(chunks: Float32Array[]): Float32Array {
  const size = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const result = new Float32Array(size);
  let position = 0;
  for (const chunk of chunks) {
    result.set(chunk, position);
    position += chunk.length;
  }
  return result;
}

function resample(samples: Float32Array, fromRate: number, targetRate = 16000): Float32Array {
  if (fromRate === targetRate) return samples;
  const ratio = fromRate / targetRate;
  const output = new Float32Array(Math.round(samples.length / ratio));
  for (let index = 0; index < output.length; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(Math.floor((index + 1) * ratio), samples.length);
    let sum = 0;
    for (let source = start; source < end; source += 1) sum += samples[source] ?? 0;
    output[index] = sum / Math.max(1, end - start);
  }
  return output;
}

function wavBlob(samples: Float32Array, sampleRate: number): Blob {
  const bytes = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(bytes);
  const write = (offset: number, value: string) => [...value].forEach((character, index) => view.setUint8(offset + index, character.charCodeAt(0)));
  write(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, index) => view.setInt16(44 + index * 2, Math.max(-1, Math.min(1, sample)) * 0x7fff, true));
  return new Blob([bytes], { type: "audio/wav" });
}

async function startWavRecording(): Promise<RecorderSession> {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("Microphone recording is not supported in this browser.");
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  const AudioContextConstructor = window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextConstructor) {
    stream.getTracks().forEach((track) => track.stop());
    throw new Error("Web Audio is not supported in this browser.");
  }
  const context = new AudioContextConstructor();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const quiet = context.createGain();
  quiet.gain.value = 0;
  const chunks: Float32Array[] = [];
  processor.onaudioprocess = (event) => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
  source.connect(processor);
  processor.connect(quiet);
  quiet.connect(context.destination);

  const dispose = () => {
    processor.disconnect();
    source.disconnect();
    quiet.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    void context.close();
  };
  return {
    dispose,
    stop: async () => {
      const raw = mergeBuffers(chunks);
      const normalized = resample(raw, context.sampleRate, 16000);
      dispose();
      if (normalized.length < 1600) throw new Error("I could not hear enough audio. Please try again or type your question.");
      return wavBlob(normalized, 16000);
    },
  };
}

export default function AssistantPanel({ run, onEvidence }: Props) {
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Ask about this research run. I answer from verified evidence only and will say when the record cannot support an answer.",
      created_at: new Date().toISOString(),
    },
  ]);
  const [draft, setDraft] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceMessage, setVoiceMessage] = useState<string>();
  const recorderRef = useRef<RecorderSession | null>(null);
  const stopTimer = useRef<number | undefined>(undefined);

  // A recording belongs to one run only. Navigating away or switching companies
  // must release the microphone immediately instead of waiting for the timer.
  useEffect(() => {
    setMessages([{ id: "welcome", role: "assistant", content: "Ask about this research run. I answer from verified evidence only and will say when the record cannot support an answer.", created_at: new Date().toISOString() }]);
    setConversationId(undefined);
    setVoiceMessage(undefined);
    return () => {
      window.clearTimeout(stopTimer.current);
      recorderRef.current?.dispose();
      recorderRef.current = null;
    };
  }, [run.id]);

  const send = useCallback(async (rawText: string, language: "auto" | "en" | "hi" = "auto") => {
    const text = rawText.trim();
    if (!text || sending) return;
    const userMessage: AssistantMessage = { id: `user-${Date.now()}`, role: "user", content: text, created_at: new Date().toISOString() };
    const pendingId = `assistant-pending-${Date.now()}`;
    setMessages((current) => [...current, userMessage, { id: pendingId, role: "assistant", content: "", created_at: new Date().toISOString() }]);
    setDraft("");
    setSending(true);
    setVoiceMessage(undefined);
    try {
      await streamAssistantMessage(run.id, text, conversationId, {
        onDelta: (delta) => setMessages((current) => current.map((message) => message.id === pendingId ? { ...message, content: `${message.content}${delta}` } : message)),
        onFinal: ({ messageId, citations, language, conversationId: returnedConversationId }) => {
          setMessages((current) => current.map((message) => message.id === pendingId ? { ...message, id: messageId, citations, language } : message));
          setConversationId(returnedConversationId ?? `conversation-${run.id}`);
        },
      }, language);
    } catch (error) {
      setMessages((current) => current.map((message) => message.id === pendingId ? {
        ...message,
        content: `I could not reach the research assistant. You can still inspect the evidence directly. (${error instanceof Error ? error.message : "Unknown error"})`,
      } : message));
    } finally {
      setSending(false);
    }
  }, [conversationId, run.id, sending]);

  const stopRecording = useCallback(async () => {
    const session = recorderRef.current;
    if (!session) return;
    window.clearTimeout(stopTimer.current);
    recorderRef.current = null;
    setRecording(false);
    try {
      const audio = await session.stop();
      setVoiceMessage("Transcribing your question…");
      const result = await transcribeAudio(run.id, audio);
      setVoiceMessage(`Heard: ${result.text}`);
      await send(result.text, assistantLanguage(result.language));
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "Voice transcription failed. Please type your question.");
    }
  }, [run.id, send]);

  const toggleRecording = async () => {
    if (recorderRef.current) {
      await stopRecording();
      return;
    }
    if (run.replay) {
      setVoiceMessage("Voice needs a live Sarvam connection. Replay mode remains available through typed chat.");
      return;
    }
    try {
      recorderRef.current = await startWavRecording();
      setRecording(true);
      setVoiceMessage("Recording — tap again to send. The maximum recording length is 30 seconds.");
      stopTimer.current = window.setTimeout(() => void stopRecording(), 30_000);
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "Microphone access was unavailable.");
    }
  };

  const play = async (message: AssistantMessage) => {
    if (run.replay) {
      setVoiceMessage("Spoken replies are unavailable in replay mode. The verified text remains visible above.");
      return;
    }
    try {
      setVoiceMessage("Preparing spoken reply…");
      const audio = await synthesizeSpeech(run.id, message.id);
      const url = URL.createObjectURL(audio);
      const player = new Audio(url);
      player.onended = () => URL.revokeObjectURL(url);
      await player.play();
      setVoiceMessage(undefined);
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "Speech synthesis failed. The text answer is still available.");
    }
  };

  return (
    <section className="assistant-panel" aria-label="Evidence assistant">
      <div className="assistant-heading">
        <div>
          <p className="eyebrow">Sarvam research assistant</p>
          <h2>Ask the evidence</h2>
        </div>
        <span className="trust-badge">Read-only · cited</span>
      </div>
      <p className="assistant-note">English, Hindi, and mixed-language questions are supported. The assistant cannot change this report or create new findings.</p>

      <div className="message-list" aria-live="polite">
        {messages.map((message) => (
          <article key={message.id} className={`message ${message.role}`}>
            <div className="message-role">{message.role === "assistant" ? "Research assistant" : "You"}</div>
            <p>{message.content || <span className="typing">Thinking</span>}</p>
            {message.role === "assistant" && message.content && (
              <div className="message-actions">
                {message.citations?.map((citation) => (
                  <button key={citation.evidence_id} type="button" className="citation" onClick={() => onEvidence(citation.evidence_id)}>
                    {citation.evidence_id}
                  </button>
                ))}
                {!message.id.startsWith("welcome") && <button type="button" className="text-button" onClick={() => void play(message)}>Listen</button>}
              </div>
            )}
          </article>
        ))}
      </div>

      {voiceMessage && <p className="voice-status" role="status">{voiceMessage}</p>}
      <form className="assistant-compose" onSubmit={(event) => { event.preventDefault(); void send(draft); }}>
        <label className="sr-only" htmlFor="assistant-question">Ask a question about this run</label>
        <textarea id="assistant-question" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about cash, events, outcome, or evidence…" rows={2} disabled={sending} />
        <div className="compose-actions">
          <button type="button" className={`voice-button ${recording ? "recording" : ""}`} onClick={() => void toggleRecording()} aria-pressed={recording} disabled={sending}>
            {recording ? "Stop & send" : "Voice question"}
          </button>
          <button className="primary-button" type="submit" disabled={!draft.trim() || sending}>{sending ? "Checking…" : "Ask"}</button>
        </div>
      </form>
    </section>
  );
}
