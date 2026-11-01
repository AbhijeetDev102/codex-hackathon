"use client";

import { useEffect, useMemo, useState } from "react";
import AssistantPanel from "../components/AssistantPanel";
import { getEvidence, loadRun, researchWebSocketUrl, searchCompanies, startResearch } from "../lib/api";
import { replayRun, savedCompanies } from "../lib/demo-data";
import type { Company, Evidence, Metric, ResearchRun } from "../lib/types";

type View = "overview" | "analysis" | "report";

const nodeOrder = ["resolve_company", "collect", "extract_events", "compute_financials", "assess_outcome", "detect_inflections", "propose_hypotheses", "critic", "verify_claims", "match_patterns", "write_report"];

function money(value: number): string {
  const absolute = Math.abs(value);
  return `${value < 0 ? "−" : ""}$${absolute.toLocaleString("en-US", { maximumFractionDigits: 0 })}m`;
}

function date(value: string): string {
  return new Intl.DateTimeFormat("en", { year: "numeric", month: "short", day: "numeric" }).format(new Date(value));
}

function stateLabel(state: string): string {
  return state.replaceAll("_", " ");
}

function EvidencePill({ id, onClick }: { id: string; onClick: (id: string) => void }) {
  return <button className="citation" type="button" onClick={() => onClick(id)}>{id}</button>;
}

function StatusIcon({ state }: { state: string }) {
  return <span className={`status-icon ${state}`} aria-label={state}>{state === "done" ? "✓" : state === "running" ? "…" : state === "failed" ? "!" : "○"}</span>;
}

function latestMetricSignal(metrics: Metric[], metricName: Metric["metric"]): { text: string; evidenceId?: string } {
  const series = metrics.filter((metric) => metric.metric === metricName);
  const latest = series.at(-1);
  const previous = series.at(-2);
  if (!latest) return { text: `No verified ${metricName.toLowerCase()} values are available in this run.` };
  if (!previous) return { text: `${metricName} was ${money(latest.value)} in ${latest.period}; there is not yet a prior reported point to compare.`, evidenceId: latest.evidence_id };
  const change = latest.value - previous.value;
  const percentage = previous.value === 0 ? undefined : Math.abs((change / previous.value) * 100);
  const direction = change > 0 ? "increased" : change < 0 ? "decreased" : "was unchanged";
  const percentageText = percentage === undefined ? "" : ` (${percentage.toFixed(0)}%)`;
  return {
    text: `${metricName} ${direction} from ${money(previous.value)} in ${previous.period} to ${money(latest.value)} in ${latest.period}${percentageText}.`,
    evidenceId: latest.evidence_id,
  };
}

function FindingsBrief({ run, onEvidence }: { run: ResearchRun; onEvidence: (id: string) => void }) {
  const cash = latestMetricSignal(run.metrics, "Cash");
  const revenue = latestMetricSignal(run.metrics, "Revenue");
  const firstEvent = run.events[0];
  const latestEvent = run.events.at(-1);
  return <section className="card findings-card">
    <div className="section-heading"><div><p className="eyebrow">Detailed findings</p><h2>What this run can support</h2></div><span className="muted">Every item links back to a saved receipt.</span></div>
    <div className="findings-grid">
      <article className="finding"><span className="finding-tag">Outcome</span><h3>{run.outcome.label}</h3><p>{run.outcome.summary}</p><div className="citation-row">{run.outcome.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</div></article>
      <article className="finding"><span className="finding-tag">Liquidity signal</span><h3>Cash position</h3><p>{cash.text}</p>{cash.evidenceId && <EvidencePill id={cash.evidenceId} onClick={onEvidence} />}</article>
      <article className="finding"><span className="finding-tag">Operating signal</span><h3>Revenue trend</h3><p>{revenue.text}</p>{revenue.evidenceId && <EvidencePill id={revenue.evidenceId} onClick={onEvidence} />}</article>
      <article className="finding"><span className="finding-tag">Timeline scope</span><h3>{run.events.length} verified events</h3><p>{firstEvent && latestEvent ? `The reviewed record runs from ${date(firstEvent.date)} to ${date(latestEvent.date)}. The latest recorded event is: ${latestEvent.description}` : "The timeline will appear after dated evidence has been verified."}</p><div className="citation-row">{latestEvent?.evidence_ids.slice(0, 2).map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</div></article>
    </div>
    <p className="findings-limit">Interpretation limit: the run identifies documented conditions and possible contributors. It does not claim a single proven cause unless the evidence directly says so.</p>
  </section>;
}

function VerificationLedger({ run, onEvidence }: { run: ResearchRun; onEvidence: (id: string) => void }) {
  const supported = run.claims.filter((claim) => claim.result === "supported");
  const removed = run.claims.filter((claim) => claim.result === "unsupported");
  return <section className="verification-ledger">
    <div className="section-heading"><div><p className="eyebrow">Verification detail</p><h2>What made it into the analysis</h2></div><span className="muted">Unsupported statements are excluded from the report.</span></div>
    <div className="ledger-stats"><article><strong>{run.verification.checked}</strong><span>claims checked</span></article><article><strong>{run.verification.supported}</strong><span>supported claims</span></article><article><strong>{run.verification.removed}</strong><span>claims removed</span></article><article><strong>{run.events.length}</strong><span>verified events</span></article></div>
    {supported.length > 0 ? <div className="claim-ledger"><h3>Supported statements</h3>{supported.slice(0, 6).map((claim) => <article key={claim.id}><p>{claim.text}</p><div className="citation-row">{claim.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</div></article>)}</div> : <p className="ledger-empty">No standalone claim survived verification. The dashboard still shows only the source-linked metrics and events that were collected.</p>}
    {removed.length > 0 && <p className="ledger-note">{removed.length} statement{removed.length === 1 ? " was" : "s were"} rejected because the evidence was missing, invalid, or insufficient.</p>}
  </section>;
}

function MetricChart({ metrics, onEvidence }: { metrics: Metric[]; onEvidence: (id: string) => void }) {
  const [selected, setSelected] = useState<Metric["metric"]>("Cash");
  const selectedMetrics = metrics.filter((metric) => metric.metric === selected);
  const hasData = selectedMetrics.length > 0;
  const width = 700;
  const height = 220;
  const values = selectedMetrics.map((metric) => metric.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const padding = 28;
  const points = selectedMetrics.map((metric, index) => {
    const x = padding + index * ((width - padding * 2) / Math.max(1, selectedMetrics.length - 1));
    const y = height - padding - ((metric.value - min) / Math.max(1, max - min)) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");
  return (
    <section className="card chart-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Financial record</p>
          <h2>Reported numbers, not guesses</h2>
        </div>
        <div className="metric-tabs" role="tablist" aria-label="Choose a financial metric">
          {(["Revenue", "Cash", "Net loss"] as Metric["metric"][]).map((metric) => <button key={metric} type="button" className={selected === metric ? "active" : ""} onClick={() => setSelected(metric)}>{metric}</button>)}
        </div>
      </div>
      {hasData ? <><div className="chart-wrap">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${selected} over time`}>
          {[0.2, 0.5, 0.8].map((offset) => <line key={offset} x1="28" x2={width - 28} y1={height * offset} y2={height * offset} className="grid-line" />)}
          <polyline points={points} className="chart-line" />
          {selectedMetrics.map((metric, index) => {
            const [x, y] = points.split(" ")[index].split(",").map(Number);
            return <g key={`${metric.period}-${metric.value}`}>
              <circle cx={x} cy={y} r="5" className={metric.kind === "derived" ? "derived-point" : "disclosed-point"} />
              <text x={x} y={height - 7} textAnchor="middle" className="chart-label">{metric.period.replace("202", "'")}</text>
            </g>;
          })}
        </svg>
      </div>
      <div className="metric-legend"><span><i className="legend-dot disclosed" /> Disclosed in source</span><span><i className="legend-dot derived" /> Derived calculation</span></div>
      <div className="metric-table">
        {selectedMetrics.map((metric) => <button key={`${metric.period}-${metric.value}`} type="button" onClick={() => metric.evidence_id && onEvidence(metric.evidence_id)}>
          <span>{metric.period}</span><strong>{money(metric.value)}</strong>{metric.evidence_id && <small>{metric.evidence_id}</small>}
        </button>)}
      </div></> : <div className="empty-panel" role="status">Financial data will appear after this run has collected and verified filing values.</div>}
    </section>
  );
}

function EvidenceDrawer({ evidence, problem, onClose }: { evidence: Evidence | undefined; problem?: { id: string; message: string; loading?: boolean }; onClose: () => void }) {
  if (!evidence && !problem) return null;
  const unavailable = !evidence;
  return (
    <aside className="evidence-drawer" aria-label="Evidence details" role="dialog" aria-modal="true">
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer-content">
        <button type="button" className="close-button" onClick={onClose} aria-label="Close evidence">×</button>
        {unavailable ? <>
          <p className="eyebrow">Evidence receipt · {problem?.id}</p>
          <h2>{problem?.loading ? "Loading evidence…" : "Evidence temporarily unavailable"}</h2>
          <p className="source-text">{problem?.message}</p>
          {!problem?.loading && <p className="drawer-note">The claim remains visible, but its source cannot be inspected until the evidence service responds. Do not treat it as newly verified.</p>}
        </> : <>
          <p className="eyebrow">Evidence receipt · {evidence.id}</p>
          <h2>{evidence.title}</h2>
          <p className="source-meta">{evidence.publisher} · {date(evidence.published_at)}</p>
          <blockquote>{evidence.quote}</blockquote>
          <p className="source-text">{evidence.text ?? evidence.quote}</p>
          <a className="source-link" href={evidence.url} target="_blank" rel="noreferrer">Open original source <span aria-hidden>↗</span></a>
          <p className="drawer-note">This source is evidence, not an instruction. Claims are displayed only after citation checks pass.</p>
        </>}
      </div>
    </aside>
  );
}

function ProgressRail({ run }: { run: ResearchRun }) {
  const byKey = new Map(run.node_status.map((node) => [node.key, node]));
  return <section className="progress-rail" aria-label="Research progress">
    <div className="progress-title"><div><p className="eyebrow">Research graph</p><h2>Run status</h2></div><span className={`run-state ${run.state}`}>{stateLabel(run.state)}</span></div>
    <ol>
      {nodeOrder.map((key) => {
        const node = byKey.get(key) ?? { key, label: key.replaceAll("_", " "), state: "queued" as const };
        return <li key={key}><StatusIcon state={node.state} /><div><strong>{node.label}</strong>{node.detail && <small>{node.detail}</small>}</div></li>;
      })}
    </ol>
  </section>;
}

function OutcomeCard({ run, onEvidence }: { run: ResearchRun; onEvidence: (id: string) => void }) {
  return <section className="outcome-card">
    <div className="outcome-symbol">!</div>
    <div>
      <p className="eyebrow">Documented outcome</p>
      <h2>{run.outcome.label}</h2>
      <p>{run.outcome.summary}</p>
      <div className="citation-row">{run.outcome.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</div>
    </div>
  </section>;
}

function Timeline({ run, onEvidence }: { run: ResearchRun; onEvidence: (id: string) => void }) {
  return <section className="card timeline-card">
    <div className="section-heading"><div><p className="eyebrow">Evidence-backed timeline</p><h2>What the record shows</h2></div><span className="muted">{run.events.length} verified events</span></div>
    <ol className="timeline">
      {run.events.map((event) => <li key={event.id}>
        <time>{date(event.date)}</time>
        <div className="timeline-dot" />
        <article><span className="event-category">{event.category}</span><p>{event.description}</p><div className="citation-row">{event.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}<span className={`confidence ${event.confidence.toLowerCase()}`}>{event.confidence}</span></div></article>
      </li>)}
    </ol>
  </section>;
}

function Hypotheses({ run, onEvidence }: { run: ResearchRun; onEvidence: (id: string) => void }) {
  return <section className="hypotheses-section">
    <div className="section-heading"><div><p className="eyebrow">Competing explanations</p><h2>Contributors, not a single story</h2></div><span className="muted">The evidence can support uncertainty.</span></div>
    <div className="hypothesis-grid">
      {run.hypotheses.map((hypothesis) => <article className="hypothesis-card" key={hypothesis.id}>
        <div className="hypothesis-header"><h3>{hypothesis.title}</h3><span className={`confidence ${hypothesis.confidence.toLowerCase()}`}>{hypothesis.confidence}</span></div>
        <p>{hypothesis.mechanism}</p>
        <div className="claim-group"><strong>Evidence for</strong>{hypothesis.supports.map((claim) => <div className="claim" key={claim.id}><span>{claim.text}</span>{claim.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</div>)}</div>
        {hypothesis.contradicts.length > 0 && <div className="claim-group"><strong>Evidence against</strong>{hypothesis.contradicts.map((claim) => <div className="claim" key={claim.id}><span>{claim.text}</span>{claim.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</div>)}</div>}
        <div className="missing"><strong>Still unknown</strong><p>{hypothesis.missing.join(" ")}</p></div>
        <footer>Critic: {hypothesis.critic_notes}</footer>
      </article>)}
    </div>
  </section>;
}

function Report({ run, onEvidence }: { run: ResearchRun; onEvidence: (id: string) => void }) {
  return <section className="report-page">
    <header className="report-header"><p className="eyebrow">Evidence-first report</p><h1>{run.report.title}</h1><p>{run.company.legal_name} · Run {run.id}</p></header>
    <h2>Summary</h2><p>{run.report.summary}</p>
    <h2>Documented outcome</h2><p>{run.outcome.summary} {run.outcome.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={onEvidence} />)}</p>
    <h2>Verified explanations</h2>
    {run.hypotheses.map((hypothesis) => <article key={hypothesis.id}><h3>{hypothesis.title}</h3><p>{hypothesis.mechanism}</p></article>)}
    <h2>Limits</h2><ul>{run.report.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul>
  </section>;
}

export default function HomePage() {
  const [run, setRun] = useState<ResearchRun>(replayRun);
  const [view, setView] = useState<View>("overview");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>(savedCompanies);
  const [loading, setLoading] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence>();
  const [evidenceProblem, setEvidenceProblem] = useState<{ id: string; message: string; loading?: boolean }>();
  const [dataError, setDataError] = useState<string>();
  const [connection, setConnection] = useState<"replay" | "live" | "connecting" | "polling">("replay");

  useEffect(() => {
    let active = true;
    const lookup = window.setTimeout(() => {
      void searchCompanies(query).then((next) => active && setResults(next));
    }, 160);
    return () => { active = false; window.clearTimeout(lookup); };
  }, [query]);

  useEffect(() => {
    const url = researchWebSocketUrl(run.id);
    if (!url || run.replay) { setConnection("replay"); return; }
    setConnection("connecting");
    const socket = new WebSocket(url);
    let closedByEffect = false;
    socket.onopen = () => setConnection("live");
    socket.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data) as { type?: string; data?: unknown };
        const update = (envelope.data ?? envelope) as {
          node?: string;
          state?: string;
          detail?: string;
          node_status?: Record<string, string | { state?: string; detail?: string }> | ResearchRun["node_status"];
          run?: Partial<ResearchRun>;
        };
        setRun((current) => {
          if (update.run) return { ...current, ...update.run };
          if (update.node_status) {
            const statuses = Array.isArray(update.node_status)
              ? update.node_status
              : Object.entries(update.node_status).map(([key, value]) => ({
                key,
                label: key.replaceAll("_", " "),
                state: (typeof value === "string" ? value : value.state ?? "queued") as ResearchRun["node_status"][number]["state"],
                detail: typeof value === "string" ? undefined : value.detail,
              }));
            return { ...current, state: (update.state as ResearchRun["state"] | undefined) ?? current.state, node_status: statuses };
          }
          if (!update.node || !update.state) return current;
          return { ...current, node_status: current.node_status.map((node) => node.key === update.node ? { ...node, state: update.state as typeof node.state, detail: update.detail ?? node.detail } : node) };
        });
      } catch { /* Ignore malformed status messages; polling/API remains the source of truth. */ }
    };
    socket.onerror = () => setConnection("polling");
    socket.onclose = () => { if (!closedByEffect) setConnection("polling"); };
    return () => { closedByEffect = true; socket.close(); };
  }, [run.id, run.replay]);

  useEffect(() => {
    if (run.replay) return;
    let active = true;
    let timer: number | undefined;
    const refresh = async () => {
      try {
        const next = await loadRun(run.id, run.company, Boolean(run.fixture));
        if (active) {
          setRun(next);
          setDataError(undefined);
          if (["completed", "completed_with_limits", "failed"].includes(next.state) && timer !== undefined) {
            window.clearInterval(timer);
          }
        }
      } catch (error) {
        if (active) setDataError(error instanceof Error ? error.message : "Could not refresh live research. Showing the last verified view.");
      }
    };
    timer = window.setInterval(() => void refresh(), 1_000);
    void refresh();
    return () => { active = false; window.clearInterval(timer); };
  }, [run.company, run.id, run.replay]);

  const evidenceById = useMemo(() => new Map(run.evidence.map((item) => [item.id, item])), [run.evidence]);
  const showEvidence = (id: string) => {
    const local = evidenceById.get(id);
    if (local) {
      setEvidenceProblem(undefined);
      setSelectedEvidence(local);
      return;
    }
    setSelectedEvidence(undefined);
    setEvidenceProblem({ id, loading: true, message: "Requesting the saved source excerpt…" });
    void getEvidence(run.id, id)
      .then((evidence) => {
        setSelectedEvidence(evidence);
        setEvidenceProblem(undefined);
      })
      .catch(() => setEvidenceProblem({ id, message: "The evidence service did not return this source. Please retry or inspect the run later." }));
  };
  const chooseCompany = async (company: Company) => {
    setLoading(true);
    setView("overview");
    setDataError(undefined);
    try {
      // The four built-in cards are explicitly labelled synthetic demos. Keep
      // their reliable, cited replay fixtures separate from a live SEC search.
      const useReplayFixture = savedCompanies.some((saved) => saved.id === company.id);
      const started = await startResearch(company, useReplayFixture);
      setRun(started);
      if (!started.replay) {
        const refreshed = await loadRun(started.id, company, useReplayFixture);
        setRun(refreshed);
      }
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Could not start research. The existing view was preserved.");
    } finally { setLoading(false); }
  };
  const printReport = () => {
    if (view !== "report") setView("report");
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => window.print()));
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Failure Investigator home"><span className="brand-mark">ƒ</span><span>Failure <b>Investigator</b></span></a>
        <div className="topbar-status"><span className={`connection ${connection}`} />{connection === "live" ? "Live research connection" : connection === "connecting" ? "Connecting…" : connection === "polling" ? "Live connection lost · polling status" : "Replay-ready demo"}</div>
        <button className="outline-button print-hidden" type="button" onClick={printReport}>Print report</button>
      </header>

      <div className="workspace" id="top">
        <aside className="sidebar print-hidden">
          <p className="sidebar-label">Research run</p>
          <div className="current-company"><span>{run.company.legal_name.slice(0, 1)}</span><div><strong>{run.company.legal_name}</strong><small>{run.company.ticker} · CIK {run.company.cik}</small></div></div>
          <nav aria-label="Research views">
            {([ ["overview", "Overview"], ["analysis", "Failure analysis"], ["report", "Final report"] ] as Array<[View, string]>).map(([key, label]) => <button key={key} type="button" className={view === key ? "active" : ""} onClick={() => setView(key)}>{label}</button>)}
          </nav>
          <div className="sidebar-foot"><span className="trust-badge">Evidence-first</span><p>Likely contributors, not proven causes.</p></div>
        </aside>

        <div className="content">
          <section className="hero print-hidden">
            <div><p className="eyebrow">Public-company due diligence</p><h1>Find the evidence behind a business failure.</h1><p>Trace the timeline, financial pressure, and competing explanations—without pretending public data can prove one cause.</p></div>
            <div className="company-picker">
              <label htmlFor="company-search">Start a research run</label>
              <input id="company-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a U.S. company, ticker, or CIK" />
              <div className="search-results">
                {results.slice(0, 4).map((company) => <button key={company.id} type="button" onClick={() => void chooseCompany(company)} disabled={loading}><span><b>{company.legal_name}</b><small>{company.ticker ?? "—"} · CIK {company.cik}</small></span><em>{company.status}</em></button>)}
              </div>
              {query.trim() && !loading && results.length === 0 && <p className="search-empty">No SEC-listed company matched that name, ticker, or CIK.</p>}
              {!query.trim() && <p className="search-hint">Search beyond the demo list with a U.S. public-company name, ticker, or CIK.</p>}
              {loading && <p className="search-loading">Starting research…</p>}
            </div>
          </section>
          {dataError && <section className="data-error" role="alert"><strong>Live data unavailable.</strong> {dataError}</section>}

          {view === "overview" && <>
            <section className="overview-grid">
              <OutcomeCard run={run} onEvidence={showEvidence} />
              <section className="verification-card"><p className="eyebrow">Verification gate</p><strong>{run.verification.supported}<small> / {run.verification.checked} claims supported</small></strong><div className="verification-bar"><span style={{ width: `${run.verification.checked > 0 ? (run.verification.supported / run.verification.checked) * 100 : 0}%` }} /></div><p>{run.verification.removed} unsupported claims removed before the report.</p></section>
              <ProgressRail run={run} />
            </section>
            <FindingsBrief run={run} onEvidence={showEvidence} />
            <MetricChart metrics={run.metrics} onEvidence={showEvidence} />
            <section className="inflection-strip"><p className="eyebrow">Turning points</p>{run.inflections.map((point) => <article key={point.id}><strong>{point.period} · {point.metric}</strong><p>{point.explanation}</p><div>{point.evidence_ids.map((id) => <EvidencePill key={id} id={id} onClick={showEvidence} />)}</div></article>)}</section>
            <Timeline run={run} onEvidence={showEvidence} />
          </>}

          {view === "analysis" && <>
            <VerificationLedger run={run} onEvidence={showEvidence} />
            <Hypotheses run={run} onEvidence={showEvidence} />
            <section className="pattern-card"><p className="eyebrow">Pattern match · {Math.round(run.patterns.score * 100)}% similarity</p><h2>{run.patterns.archetype}</h2><p>{run.patterns.description}</p><div className="case-comparisons">{run.patterns.similar_cases.map((item) => <article key={item.name}><strong>{item.name}</strong><p><b>Similar:</b> {item.similarity}</p><p><b>Different:</b> {item.difference}</p></article>)}</div></section>
            <AssistantPanel run={run} onEvidence={showEvidence} />
          </>}

          {view === "report" && <Report run={run} onEvidence={showEvidence} />}
        </div>
      </div>
      <EvidenceDrawer evidence={selectedEvidence} problem={evidenceProblem} onClose={() => { setSelectedEvidence(undefined); setEvidenceProblem(undefined); }} />
    </main>
  );
}
