# Demo replay fixtures

`demo_cases.json` is the deterministic source used by replay mode. It contains four
small, hand-curated demo cases:

- WeWork, Bed Bath & Beyond, and Bird Global as failure cases.
- Carvana as the survivor control.

The fixture excerpts, financial values, claim wording, and summaries are deliberately
short **synthetic demo material**. They are not substitutes for an SEC filing or other
primary source. Each item retains a public-style source URL and evidence key so that
the application can demonstrate traceability without storing complete third-party
documents.

Live or record mode must replace these excerpts with fetched source text and must run
the normal quote, date, and numeric verification checks. Replay mode must never present
fixture content as newly fetched data.
