import { describe, expect, it } from "vitest";
import { answerFromReplay, replayRun } from "./demo-data";

describe("replay research run", () => {
  it("keeps all displayed timeline evidence resolvable", () => {
    const evidence = new Set(replayRun.evidence.map((item) => item.id));
    for (const event of replayRun.events) {
      for (const id of event.evidence_ids) expect(evidence.has(id)).toBe(true);
    }
  });

  it("does not fabricate an answer for unsupported questions", () => {
    expect(answerFromReplay("Who was responsible?").content).toContain("cannot confirm");
    expect(answerFromReplay("What happened to cash?").citations).toEqual(expect.arrayContaining([{ evidence_id: "E-001" }]));
  });
});
