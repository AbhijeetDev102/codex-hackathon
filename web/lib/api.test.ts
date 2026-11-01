import { afterEach, describe, expect, it, vi } from "vitest";
import { loadRun, startResearch, streamAssistantMessage } from "./api";
import { savedCompanies } from "./demo-data";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("live API safety", () => {
  it("does not replace a failed live start with unrelated replay facts", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(startResearch(savedCompanies[1])).rejects.toThrow("Could not start live research");
  });

  it("explicitly requests a fixture only for a built-in demo card", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "fixture-run" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);

    const run = await startResearch(savedCompanies[0], true);

    expect(run.fixture).toBe(true);
    expect(run.replay).toBe(false);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      company_id: "wework",
      cik: "1533523",
      use_replay: true,
    });
  });

  it("keeps the caller responsible for preserving the last live view when refresh fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("unavailable", { status: 503 })));
    await expect(loadRun("live-run-123", savedCompanies[1])).rejects.toThrow("Could not refresh live research");
  });
});

describe("assistant event adapter", () => {
  it("maps streamed citation IDs to visible evidence receipts", async () => {
    const sse = [
      'event: assistant.text.delta\ndata: {"text":"Verified answer."}\n\n',
      'event: assistant.final\ndata: {"message_id":"message-1","conversation_id":"conversation-1","language":"en","citations":["E-001","E-002"]}\n\n',
    ].join("");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(sse, { headers: { "Content-Type": "text/event-stream" } })));
    const deltas: string[] = [];
    let final: { messageId: string; citations: Array<{ evidence_id: string }>; conversationId?: string } | undefined;

    await streamAssistantMessage("live-run-123", "What happened?", undefined, {
      onDelta: (text) => deltas.push(text),
      onFinal: (result) => { final = result; },
    });

    expect(deltas).toEqual(["Verified answer."]);
    expect(final).toEqual({
      messageId: "message-1",
      conversationId: "conversation-1",
      language: "en",
      citations: [{ evidence_id: "E-001" }, { evidence_id: "E-002" }],
    });
  });
});
