# Milestone 9 - GenAI Operations Assistant

Milestone 9 implements a local deterministic GenAI-style operations assistant over governed
synthetic airline operations artefacts.

## Delivered Scope

- Assistant configuration for development and CI.
- `run-operations-assistant` and `describe-operations-assistant` CLI commands.
- Explicit artefact discovery, checksum verification, and lineage compatibility checks.
- Structured evidence extraction from validation, monitoring, disruption scoring, delay
  prediction, passenger forecasting, and maintenance analytics outputs.
- Deterministic evidence retrieval with entity filtering.
- Prompt audit creation.
- Local deterministic template response generation.
- Guardrail results covering intent, grounding, safety, synthetic-data warning, no-live-LLM
  statement, human review, Azure claims, and redaction.
- Assistant response, transcript, manifest, reports, and lineage.
- CI-sized Makefile and GitHub Actions integration.

## Out Of Scope

Milestone 9 does not implement dashboards, route or schedule optimisation, Azure infrastructure,
live Azure AI Foundry integration, live OpenAI or Azure OpenAI calls, production monitoring, vector
search, embeddings, function-calling tools, web search, or Milestone 10+ functionality.

## Responsible Use

The assistant uses fictional synthetic data and deterministic templates. It is not certified
airline operations-control tooling, not air-traffic-control tooling, not a dispatch authority, not
a safety-critical assistant, and not autonomous operational automation.
