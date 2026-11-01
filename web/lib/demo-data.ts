import type { AssistantMessage, Company, ResearchRun } from "./types";

export const savedCompanies: Company[] = [
  { id: "wework", legal_name: "WeWork Inc.", ticker: "WE", cik: "1533523", status: "Bankruptcy" },
  { id: "bbby", legal_name: "Bed Bath & Beyond Inc.", ticker: "BBBYQ", cik: "886158", status: "Bankruptcy" },
  { id: "bird", legal_name: "Bird Global, Inc.", ticker: "BRDS", cik: "1577967", status: "Bankruptcy" },
  { id: "carvana", legal_name: "Carvana Co.", ticker: "CVNA", cik: "1690820", status: "Survivor control" },
];

export const replayRun: ResearchRun = {
  id: "demo-wework",
  replay: true,
  state: "completed",
  started_at: "2023-11-07T12:00:00Z",
  company: savedCompanies[0],
  node_status: [
    { key: "resolve_company", label: "Confirm company", state: "done", detail: "CIK 1533523" },
    { key: "collect", label: "Collect primary sources", state: "done", detail: "18 sources" },
    { key: "extract_events", label: "Extract dated events", state: "done", detail: "14 verified events" },
    { key: "compute_financials", label: "Compute financials", state: "done", detail: "24 reported values" },
    { key: "assess_outcome", label: "Assess outcome", state: "done", detail: "Bankruptcy filing found" },
    { key: "detect_inflections", label: "Detect inflections", state: "done", detail: "3 candidate turns" },
    { key: "propose_hypotheses", label: "Propose hypotheses", state: "done", detail: "3 competing explanations" },
    { key: "critic", label: "Critique explanations", state: "done", detail: "1 revision round" },
    { key: "verify_claims", label: "Verify claims", state: "done", detail: "38 supported / 3 removed" },
    { key: "match_patterns", label: "Match patterns", state: "done", detail: "Premature scaling" },
    { key: "write_report", label: "Write evidence report", state: "done", detail: "Ready" },
  ],
  evidence: [
    {
      id: "E-001",
      source_id: "src-1",
      title: "WeWork 2022 Form 10-K",
      url: "https://www.sec.gov/Archives/edgar/data/1533523/",
      publisher: "SEC EDGAR",
      published_at: "2023-03-17",
      quote: "The Company has incurred operating losses and negative cash flows from operating activities.",
      text: "The Company has incurred operating losses and negative cash flows from operating activities. Management evaluated conditions and events that raised substantial doubt about its ability to continue as a going concern.",
    },
    {
      id: "E-002",
      source_id: "src-2",
      title: "WeWork November 2023 Form 8-K",
      url: "https://www.sec.gov/Archives/edgar/data/1533523/",
      publisher: "SEC EDGAR",
      published_at: "2023-11-07",
      quote: "WeWork Inc. and certain of its subsidiaries filed voluntary petitions for relief under chapter 11.",
      text: "WeWork Inc. and certain of its subsidiaries filed voluntary petitions for relief under chapter 11 of the United States Bankruptcy Code.",
    },
    {
      id: "E-003",
      source_id: "src-3",
      title: "WeWork Q2 2023 Form 10-Q",
      url: "https://www.sec.gov/Archives/edgar/data/1533523/",
      publisher: "SEC EDGAR",
      published_at: "2023-08-08",
      quote: "Substantial doubt exists about the Company's ability to continue as a going concern.",
      text: "Substantial doubt exists about the Company's ability to continue as a going concern. The Company continues to evaluate strategic actions to improve liquidity.",
    },
    {
      id: "E-004",
      source_id: "src-4",
      title: "WeWork 2023 Form 8-K: restructuring",
      url: "https://www.sec.gov/Archives/edgar/data/1533523/",
      publisher: "SEC EDGAR",
      published_at: "2023-08-09",
      quote: "The Company is taking actions to significantly reduce its real estate portfolio.",
      text: "The Company is taking actions to significantly reduce its real estate portfolio and improve liquidity.",
    },
  ],
  events: [
    { id: "event-1", date: "2022-12-31", category: "Financial warning", description: "Annual filing reports operating losses and negative operating cash flows.", evidence_ids: ["E-001"], confidence: "High" },
    { id: "event-2", date: "2023-08-08", category: "Going concern", description: "Quarterly filing says substantial doubt exists about continued operations.", evidence_ids: ["E-003"], confidence: "High" },
    { id: "event-3", date: "2023-08-09", category: "Restructuring", description: "Company announces a plan to reduce its real-estate portfolio.", evidence_ids: ["E-004"], confidence: "High" },
    { id: "event-4", date: "2023-11-07", category: "Bankruptcy", description: "Company files voluntary Chapter 11 petitions.", evidence_ids: ["E-002"], confidence: "High" },
  ],
  metrics: [
    { metric: "Revenue", period: "2022 Q1", value: 765, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Revenue", period: "2022 Q2", value: 815, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Revenue", period: "2022 Q3", value: 817, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Revenue", period: "2022 Q4", value: 849, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Revenue", period: "2023 Q1", value: 849, unit: "USD millions", kind: "disclosed", evidence_id: "E-003" },
    { metric: "Revenue", period: "2023 Q2", value: 844, unit: "USD millions", kind: "disclosed", evidence_id: "E-003" },
    { metric: "Cash", period: "2022 Q1", value: 1006, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Cash", period: "2022 Q2", value: 743, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Cash", period: "2022 Q3", value: 635, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Cash", period: "2022 Q4", value: 517, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Cash", period: "2023 Q1", value: 487, unit: "USD millions", kind: "disclosed", evidence_id: "E-003" },
    { metric: "Cash", period: "2023 Q2", value: 205, unit: "USD millions", kind: "disclosed", evidence_id: "E-003" },
    { metric: "Net loss", period: "2022 Q1", value: -435, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Net loss", period: "2022 Q2", value: -635, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Net loss", period: "2022 Q3", value: -629, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Net loss", period: "2022 Q4", value: -527, unit: "USD millions", kind: "disclosed", evidence_id: "E-001" },
    { metric: "Net loss", period: "2023 Q1", value: -264, unit: "USD millions", kind: "disclosed", evidence_id: "E-003" },
    { metric: "Net loss", period: "2023 Q2", value: -397, unit: "USD millions", kind: "disclosed", evidence_id: "E-003" },
  ],
  inflections: [
    { id: "inflection-1", period: "2022 Q2", metric: "Cash", size: -26, explanation: "Cash declined sharply quarter over quarter. This marks a timing signal, not proof of cause.", evidence_ids: ["E-001"] },
    { id: "inflection-2", period: "2023 Q2", metric: "Cash", size: -58, explanation: "Liquidity declined before the disclosed going-concern warning.", evidence_ids: ["E-003"] },
    { id: "inflection-3", period: "2023 Q3", metric: "Outcome", size: 0, explanation: "Portfolio-reduction actions followed the liquidity warning; the record does not prove one caused the other.", evidence_ids: ["E-003", "E-004"] },
  ],
  outcome: {
    kind: "bankruptcy",
    label: "Bankruptcy filing",
    assessed_at: "2023-11-07",
    summary: "A voluntary Chapter 11 filing is documented in the November 2023 filing.",
    evidence_ids: ["E-002"],
  },
  hypotheses: [
    {
      id: "hyp-1",
      title: "Liquidity pressure constrained the company",
      mechanism: "Declining available cash and disclosed negative operating cash flows may have narrowed the company’s ability to absorb obligations and fund restructuring.",
      supports: [{ id: "c-1", text: "The annual filing reports negative operating cash flows and operating losses.", evidence_ids: ["E-001"], result: "supported" }],
      contradicts: [{ id: "c-2", text: "Revenue remained broadly stable across the shown quarters.", evidence_ids: ["E-003"], result: "supported" }],
      missing: ["Detailed liquidity covenants and counterparty decisions are not established by the reviewed record."],
      confidence: "Moderate",
      critic_notes: "Liquidity evidence is strong; the evidence does not establish it as the sole cause.",
    },
    {
      id: "hyp-2",
      title: "Real-estate commitments amplified stress",
      mechanism: "A large fixed real-estate portfolio may have made cost reduction slower than the deterioration in liquidity.",
      supports: [{ id: "c-3", text: "The company announced plans to significantly reduce its real-estate portfolio.", evidence_ids: ["E-004"], result: "supported" }],
      contradicts: [],
      missing: ["This run does not establish the full portfolio-level economics or individual lease negotiations."],
      confidence: "Moderate",
      critic_notes: "The restructuring action supports relevance, but causal weight remains uncertain.",
    },
    {
      id: "hyp-3",
      title: "Going-concern risk became acute",
      mechanism: "The disclosed going-concern warning indicates material uncertainty about continued operations before the filing.",
      supports: [{ id: "c-4", text: "The Q2 filing states that substantial doubt existed about continuing as a going concern.", evidence_ids: ["E-003"], result: "supported" }],
      contradicts: [],
      missing: ["The warning does not identify one decisive management decision."],
      confidence: "High",
      critic_notes: "This describes documented distress, not a complete causal explanation.",
    },
  ],
  claims: [],
  patterns: {
    archetype: "Premature scaling / fixed-cost overhang",
    score: 0.78,
    description: "The case resembles businesses where fixed commitments become difficult to support when liquidity tightens.",
    similar_cases: [
      { name: "Comparable case A", similarity: "Liquidity pressure and costly footprint", difference: "Different sector and capital structure" },
      { name: "Comparable case B", similarity: "Restructuring before insolvency", difference: "Recovered rather than filed" },
    ],
  },
  verification: { checked: 41, supported: 38, removed: 3 },
  report: {
    title: "WeWork: evidence-backed decline review",
    summary: "Public filings document liquidity pressure, a going-concern warning, portfolio reduction actions, and a later Chapter 11 filing. The evidence supports contributing factors, not one proven cause.",
    limitations: ["Public records cannot prove a single cause.", "This replay contains a bounded set of filings and sources.", "This is not investment or financial advice."],
  },
};

export function answerFromReplay(question: string): Pick<AssistantMessage, "content" | "citations" | "language"> {
  const q = question.toLowerCase();
  if (/(cash|liquidity|money|पैसा|कैश)/.test(q)) {
    return {
      content: "The reviewed filings show cash declining from $517m at 2022 year-end to $205m in 2023 Q2. The filing also disclosed substantial doubt about continuing as a going concern. This is evidence of liquidity stress, not proof of a single cause.",
      citations: [{ evidence_id: "E-001" }, { evidence_id: "E-003" }],
      language: /[\u0900-\u097F]/.test(question) ? "hi" : "en",
    };
  }
  if (/(bankrupt|chapter|fail|दिवालिया)/.test(q)) {
    return {
      content: "The reviewed November 2023 filing states that WeWork and certain subsidiaries filed voluntary Chapter 11 petitions. The record supports the outcome label, while the report deliberately avoids claiming one proven cause.",
      citations: [{ evidence_id: "E-002" }],
      language: /[\u0900-\u097F]/.test(question) ? "hi" : "en",
    };
  }
  return {
    content: "I cannot confirm that from this approved research run. I can explain the verified timeline, financial metrics, outcome assessment, or the evidence behind a listed hypothesis.",
    citations: [],
    language: /[\u0900-\u097F]/.test(question) ? "hi" : "en",
  };
}
