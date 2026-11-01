import { answerFromReplay, replayRun, savedCompanies } from "./demo-data";
import type {
  AssistantCitation,
  Claim,
  Company,
  Confidence,
  Evidence,
  Hypothesis,
  Metric,
  NodeState,
  OutcomeKind,
  ResearchRun,
} from "./types";

const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

function isReplay(): boolean {
  return !apiBase || apiBase.includes("localhost:8000") === false && typeof window === "undefined";
}

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function searchCompanies(query: string): Promise<Company[]> {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return savedCompanies;
  try {
    const response = await fetch(`${apiBase}/api/companies/search?q=${encodeURIComponent(query)}`, { cache: "no-store" });
    const payload = await asJson<Company[] | { items?: Company[]; results?: Company[] }>(response);
    return Array.isArray(payload) ? payload : (payload.results ?? payload.items ?? []);
  } catch {
    return savedCompanies.filter((company) =>
      [company.legal_name, company.ticker, company.cik].filter(Boolean).join(" ").toLowerCase().includes(normalized),
    );
  }
}

export async function startResearch(company: Company, useReplay = false): Promise<ResearchRun> {
  try {
    const response = await fetch(`${apiBase}/api/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: company.id, cik: company.cik, legal_name: company.legal_name, use_replay: useReplay }),
    });
    const result = await asJson<{ run?: ResearchRun; id?: string; run_id?: string }>(response);
    if (result.run) return result.run;
    if (result.id || result.run_id) return pendingRun(result.id ?? result.run_id ?? "pending-run", company, useReplay);
    throw new Error("The research service did not return a run identifier.");
  } catch (error) {
    throw new Error(`Could not start live research: ${error instanceof Error ? error.message : "service unavailable"}`);
  }
}

/** A neutral live shell prevents replay facts from being shown as a new company's data. */
function pendingRun(id: string, company: Company, fixture = false): ResearchRun {
  return {
    ...replayRun,
    id,
    company,
    state: "running",
    replay: false,
    fixture,
    node_status: replayRun.node_status.map((node, index) => ({ ...node, state: index === 0 ? "running" : "queued", detail: undefined })),
    evidence: [],
    events: [],
    metrics: [],
    inflections: [],
    hypotheses: [],
    claims: [],
    outcome: {
      kind: "unknown",
      label: "Outcome not assessed",
      assessed_at: new Date().toISOString(),
      summary: "Research is still collecting and verifying evidence.",
      evidence_ids: [],
    },
    patterns: { archetype: "Not available yet", score: 0, description: "Pattern matching begins after verified hypotheses are available.", similar_cases: [] },
    verification: { checked: 0, supported: 0, removed: 0 },
    report: {
      title: `${company.legal_name}: research in progress`,
      summary: "No conclusions are available until the verification stage is complete.",
      limitations: ["Research is still in progress."],
    },
  };
}

function confidence(value: unknown): Confidence {
  const normalized = String(value ?? "insufficient").toLowerCase();
  if (normalized === "high") return "High";
  if (normalized === "moderate") return "Moderate";
  if (normalized === "low") return "Low";
  return "Insufficient";
}

function metricLabel(metric: string): Metric["metric"] {
  const labels: Record<string, Metric["metric"]> = {
    revenue: "Revenue",
    cash: "Cash",
    net_loss: "Net loss",
    operating_cash_flow: "Operating cash flow",
  };
  return labels[metric] ?? "Operating cash flow";
}

function outcomeLabel(status: string): string {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function nodeState(value: unknown): NodeState {
  return ["queued", "running", "done", "skipped", "failed"].includes(String(value))
    ? String(value) as NodeState
    : "queued";
}

function claimFromCitation(evidenceId: string): Claim {
  return {
    id: `receipt-${evidenceId}`,
    text: `Evidence receipt ${evidenceId}`,
    evidence_ids: [evidenceId],
    result: "supported",
  };
}

async function endpoint<T>(runId: string, suffix: string): Promise<T> {
  const response = await fetch(`${apiBase}/api/research/${encodeURIComponent(runId)}${suffix}`, { cache: "no-store" });
  return asJson<T>(response);
}

/** Map the API's normalized records to the presentational dashboard model. */
export async function loadRun(runId: string, company: Company = replayRun.company, fixture = false): Promise<ResearchRun> {
  if (runId.startsWith("demo-")) return { ...replayRun, id: runId, replay: true };
  try {
    const [status, timeline, financials, outcomeResponse, inflectionsResponse, hypothesesResponse, claimsResponse, patternsResponse, reportResponse] = await Promise.all([
      endpoint<{
      id: string;
      state: ResearchRun["state"];
      started_at: string;
      node_status?: Record<string, string | { state?: string; detail?: string }>;
      }>(runId, ""),
      endpoint<{ events: any[] }>(runId, "/timeline"),
      endpoint<{ metrics: any[] }>(runId, "/financials"),
      endpoint<{ outcome: any | null }>(runId, "/outcome"),
      endpoint<{ inflections: any[] }>(runId, "/inflections"),
      endpoint<{ hypotheses: any[] }>(runId, "/hypotheses"),
      endpoint<{ claims: any[] }>(runId, "/claims"),
      endpoint<any>(runId, "/patterns"),
      endpoint<{ report: any | null }>(runId, "/report"),
    ]);
    const nodeStatus = Object.entries(status.node_status ?? {}).map(([key, value]) => ({
      key,
      label: key.replaceAll("_", " "),
      state: nodeState(typeof value === "string" ? value : value.state),
      detail: typeof value === "string" ? undefined : value.detail,
    }));
    const supportedClaims: Claim[] = (claimsResponse.claims ?? [])
      .filter((claim) => claim.result === "supported")
      .map((claim) => ({
        id: String(claim.id),
        text: String(claim.text),
        evidence_ids: Array.isArray(claim.cited_evidence) ? claim.cited_evidence.map(String) : [],
        result: "supported" as const,
        reason: claim.reason ? String(claim.reason) : undefined,
      }));
    const claimForEvidence = (evidenceIds: unknown): Claim[] => {
      const ids = Array.isArray(evidenceIds) ? evidenceIds.map(String) : [];
      const matches = supportedClaims.filter((claim) => claim.evidence_ids.some((id) => ids.includes(id)));
      return matches.length > 0 ? matches : ids.map(claimFromCitation);
    };
    const rawOutcome = outcomeResponse.outcome;
    const rawReport = reportResponse.report ?? {};
    const rawPatterns = patternsResponse ?? {};
    const rawSimilarCases = Array.isArray(rawPatterns.similar_cases)
      ? rawPatterns.similar_cases
      : Array.isArray(rawPatterns.similar_case_keys) ? rawPatterns.similar_case_keys : [];
    return {
      id: status.id,
      company,
      state: status.state,
      started_at: status.started_at,
      replay: fixture && ["completed", "completed_with_limits", "failed"].includes(status.state),
      fixture,
      node_status: nodeStatus.length > 0 ? nodeStatus : replayRun.node_status,
      evidence: [],
      events: (timeline.events ?? []).map((event) => ({
        id: String(event.id),
        date: String(event.date),
        date_precision: event.date_precision,
        category: String(event.category),
        description: String(event.description),
        evidence_ids: Array.isArray(event.evidence_ids) ? event.evidence_ids.map(String) : [],
        confidence: confidence(event.confidence),
      })),
      metrics: (financials.metrics ?? [])
        .filter((metric) => ["revenue", "cash", "net_loss", "operating_cash_flow"].includes(String(metric.metric)))
        .map((metric) => ({
          metric: metricLabel(String(metric.metric)),
          period: String(metric.period).replace("-", " "),
          value: String(metric.unit).toUpperCase() === "USD" ? Number(metric.value) / 1_000_000 : Number(metric.value),
          unit: "USD millions" as const,
          kind: metric.kind === "derived" ? "derived" as const : "disclosed" as const,
          evidence_id: metric.evidence_id ? String(metric.evidence_id) : undefined,
        })),
      inflections: (inflectionsResponse.inflections ?? []).map((inflection) => ({
        id: String(inflection.id),
        period: String(inflection.period).replace("-", " "),
        metric: metricLabel(String(inflection.metric)),
        size: Number(inflection.size),
        explanation: String(inflection.explanation),
        evidence_ids: Array.isArray(inflection.evidence_ids) ? inflection.evidence_ids.map(String) : [],
      })),
      outcome: {
        kind: (rawOutcome?.status ?? "unknown") as OutcomeKind,
        label: outcomeLabel(String(rawOutcome?.status ?? "unknown")),
        assessed_at: status.started_at,
        summary: String(rawOutcome?.summary ?? "The outcome has not been assessed yet."),
        evidence_ids: Array.isArray(rawOutcome?.evidence_ids) ? rawOutcome.evidence_ids.map(String) : [],
      },
      hypotheses: (hypothesesResponse.hypotheses ?? []).map((hypothesis, index): Hypothesis => ({
        id: String(hypothesis.id ?? `hypothesis-${index}`),
        title: `Explanation ${index + 1}`,
        mechanism: String(hypothesis.mechanism),
        supports: claimForEvidence(hypothesis.supports),
        contradicts: claimForEvidence(hypothesis.contradicts),
        missing: Array.isArray(hypothesis.missing) ? hypothesis.missing.map(String) : [],
        confidence: confidence(hypothesis.confidence),
        critic_notes: String(hypothesis.critic_notes ?? "No additional critic note was recorded."),
      })),
      claims: (claimsResponse.claims ?? []).map((claim) => ({
        id: String(claim.id),
        text: String(claim.text),
        evidence_ids: Array.isArray(claim.cited_evidence) ? claim.cited_evidence.map(String) : [],
        result: claim.result === "supported" ? "supported" as const : "unsupported" as const,
        reason: claim.reason ? String(claim.reason) : undefined,
      })),
      patterns: {
        archetype: String(rawPatterns.archetype ?? rawPatterns.archetype_key ?? "No good match"),
        score: Number(rawPatterns.score ?? 0),
        description: Array.isArray(rawPatterns.similarities)
          ? `Similar signals: ${rawPatterns.similarities.join(", ")}.`
          : "No sufficiently supported pattern match is available.",
        similar_cases: rawSimilarCases.slice(0, 2).map((item: any) => ({
          name: typeof item === "string" ? item.replaceAll("_", " ") : String(item.name ?? "Comparable case"),
          similarity: typeof item === "string" ? "See recorded similarities" : String(item.similarity ?? "See recorded similarities"),
          difference: typeof item === "string" ? "See recorded differences" : String(item.difference ?? "See recorded differences"),
        })),
      },
      verification: {
        checked: Number(rawReport.verification?.checked ?? supportedClaims.length),
        supported: Number(rawReport.verification?.supported ?? supportedClaims.length),
        removed: Number(rawReport.verification?.removed ?? 0),
      },
      report: {
        title: String(rawReport.title ?? `${company.legal_name}: evidence-backed decline review`),
        summary: String(rawReport.summary ?? "The completed research run contains only evidence-linked findings."),
        limitations: Array.isArray(rawReport.limitations)
          ? rawReport.limitations.map(String)
          : [String(rawReport.limitations ?? "Public evidence can identify contributors, not prove causation.")],
      },
    };
  } catch (error) {
    throw new Error(`Could not refresh live research: ${error instanceof Error ? error.message : "service unavailable"}`);
  }
}

export async function getEvidence(runId: string, evidenceId: string): Promise<Evidence> {
  const response = await fetch(
    `${apiBase}/api/research/evidence/${encodeURIComponent(evidenceId)}?run_id=${encodeURIComponent(runId)}`,
    { cache: "no-store" },
  );
  const raw = await asJson<any>(response);
  const source = raw.source ?? {};
  const text = String(raw.text ?? "");
  const start = Number(raw.quote_start ?? 0);
  const end = Number(raw.quote_end ?? text.length);
  return {
    id: String(raw.evidence_key ?? raw.id),
    source_id: String(raw.source_id ?? ""),
    title: String(source.title ?? `Evidence ${raw.evidence_key ?? raw.id}`),
    url: String(source.url ?? "#"),
    publisher: String(source.publisher ?? "Source record"),
    published_at: String(source.published_at ?? new Date().toISOString()),
    quote: text.slice(start, end) || text,
    text,
  };
}

export function researchWebSocketUrl(runId: string): string | null {
  if (runId.startsWith("demo-")) return null;
  try {
    const url = new URL(apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = `/ws/research/${encodeURIComponent(runId)}`;
    return url.toString();
  } catch {
    return null;
  }
}

export interface AssistantStreamHandlers {
  onDelta: (text: string) => void;
  onFinal: (result: { messageId: string; citations: AssistantCitation[]; language?: string; conversationId?: string }) => void;
}

/**
 * Reads both the documented SSE contract and a JSON fallback. The replay path is
 * deliberately local so the interface stays useful before credentials exist.
 */
export async function streamAssistantMessage(
  runId: string,
  text: string,
  conversationId: string | undefined,
  handlers: AssistantStreamHandlers,
  language: "auto" | "en" | "hi" = "auto",
): Promise<void> {
  if (runId.startsWith("demo-")) {
    const answer = answerFromReplay(text);
    for (const word of answer.content.split(/(\s+)/)) {
      handlers.onDelta(word);
      await new Promise((resolve) => window.setTimeout(resolve, 12));
    }
    handlers.onFinal({ messageId: `demo-message-${Date.now()}`, citations: answer.citations ?? [], language: answer.language });
    return;
  }

  const response = await fetch(`${apiBase}/api/research/${encodeURIComponent(runId)}/assistant/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ conversation_id: conversationId, text, language }),
  });
  if (!response.ok || !response.body) throw new Error(`Assistant is unavailable (${response.status})`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const messages = buffer.split("\n\n");
    buffer = messages.pop() ?? "";
    for (const message of messages) {
      const dataLine = message.split("\n").find((line) => line.startsWith("data:"));
      const eventLine = message.split("\n").find((line) => line.startsWith("event:"));
      if (!dataLine) continue;
      const valueText = dataLine.replace(/^data:\s?/, "");
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(valueText) as Record<string, unknown>;
      } catch {
        payload = { text: valueText };
      }
      const event = eventLine?.replace(/^event:\s?/, "") ?? "assistant.text.delta";
      if (event.includes("delta")) handlers.onDelta(String(payload.text ?? payload.delta ?? ""));
      if (event.includes("final")) {
        handlers.onFinal({
          messageId: String(payload.message_id ?? payload.id ?? `message-${Date.now()}`),
          citations: Array.isArray(payload.citations)
            ? (payload.citations as Array<AssistantCitation | string>).map((citation) =>
              typeof citation === "string" ? { evidence_id: citation } : citation,
            )
            : [],
          language: payload.language as string | undefined,
          conversationId: payload.conversation_id as string | undefined,
        });
      }
      if (event === "error") throw new Error(String(payload.message ?? "Assistant request failed"));
    }
    if (done) break;
  }
}

export async function transcribeAudio(runId: string, audio: Blob): Promise<{ text: string; language?: string }> {
  const form = new FormData();
  form.append("file", audio, "question.wav");
  const response = await fetch(`${apiBase}/api/research/${encodeURIComponent(runId)}/assistant/transcriptions`, {
    method: "POST",
    body: form,
  });
  return asJson<{ text: string; language?: string }>(response);
}

export async function synthesizeSpeech(runId: string, messageId: string): Promise<Blob> {
  const response = await fetch(`${apiBase}/api/research/${encodeURIComponent(runId)}/assistant/speech`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId }),
  });
  if (!response.ok) throw new Error(`Speech is unavailable (${response.status})`);
  return response.blob();
}

export { apiBase, isReplay };
