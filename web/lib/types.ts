export type OutcomeKind =
  | "bankruptcy"
  | "delisted"
  | "wound_down"
  | "going_concern"
  | "distress_without_failure"
  | "unknown";

export type NodeState = "queued" | "running" | "done" | "skipped" | "failed";
export type Confidence = "High" | "Moderate" | "Low" | "Insufficient";

export interface Company {
  id: string;
  legal_name: string;
  ticker?: string;
  cik: string;
  website?: string;
  status?: string;
}

export interface NodeStatus {
  key: string;
  label: string;
  state: NodeState;
  detail?: string;
}

export interface Evidence {
  id: string;
  source_id: string;
  title: string;
  url: string;
  publisher: string;
  published_at: string;
  quote: string;
  text?: string;
}

export interface TimelineEvent {
  id: string;
  date: string;
  date_precision?: "day" | "month" | "quarter" | "year";
  category: string;
  description: string;
  evidence_ids: string[];
  confidence: Confidence;
}

export interface Metric {
  metric: "Revenue" | "Cash" | "Net loss" | "Operating cash flow";
  period: string;
  value: number;
  unit: "USD" | "USD millions";
  kind: "disclosed" | "derived";
  evidence_id?: string;
}

export interface Inflection {
  id: string;
  period: string;
  metric: string;
  size: number;
  explanation: string;
  evidence_ids: string[];
}

export interface OutcomeAssessment {
  kind: OutcomeKind;
  label: string;
  assessed_at: string;
  summary: string;
  evidence_ids: string[];
}

export interface Claim {
  id: string;
  text: string;
  evidence_ids: string[];
  result: "supported" | "unsupported";
  reason?: string;
}

export interface Hypothesis {
  id: string;
  title: string;
  mechanism: string;
  supports: Claim[];
  contradicts: Claim[];
  missing: string[];
  confidence: Confidence;
  critic_notes: string;
}

export interface PatternMatch {
  archetype: string;
  score: number;
  description: string;
  similar_cases: Array<{ name: string; similarity: string; difference: string }>;
}

export interface VerificationReport {
  checked: number;
  supported: number;
  removed: number;
}

export interface ResearchRun {
  id: string;
  company: Company;
  state: "queued" | "running" | "completed" | "completed_with_limits" | "failed";
  started_at: string;
  replay?: boolean;
  /** A built-in synthetic case was explicitly selected; it becomes replay after loading. */
  fixture?: boolean;
  node_status: NodeStatus[];
  evidence: Evidence[];
  events: TimelineEvent[];
  metrics: Metric[];
  inflections: Inflection[];
  outcome: OutcomeAssessment;
  hypotheses: Hypothesis[];
  claims: Claim[];
  patterns: PatternMatch;
  verification: VerificationReport;
  report: { title: string; summary: string; limitations: string[] };
}

export interface AssistantCitation {
  evidence_id: string;
  source_title?: string;
}

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  language?: string;
  citations?: AssistantCitation[];
  created_at: string;
}
