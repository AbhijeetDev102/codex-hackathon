# ADR-006: Configure the Cerebras extraction model

**Status:** accepted

## Decision

The Cerebras event-extraction adapter reads its model name from `CEREBRAS_MODEL`. The default is `gpt-oss-120b`; deployments may set it to another model listed by their Cerebras account.

## Why

Model access is account-specific. The previous hard-coded `llama-3.3-70b` was unavailable to the configured account, which made live extraction fail even with a valid API key. A setting keeps the provider boundary stable and makes the selected model visible in local configuration.

## Evidence

On 2026-11-01, the configured account listed `gpt-oss-120b` and `qwen-3.8-27b`. A minimal `gpt-oss-120b` request returned valid structured event JSON, and a full live Peloton run completed all graph stages.

## Consequences

- Keep model IDs in `.env`, never in request-handling code.
- If a Cerebras request returns `model_not_found` or `model_archived_error`, call the account's model-list endpoint and update only `CEREBRAS_MODEL`.
- Replay mode does not need Cerebras credentials or a live model.
