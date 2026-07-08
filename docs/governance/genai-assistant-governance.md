# GenAI Assistant Governance

Milestone 9 is a governed local assistant simulation over synthetic evidence. It demonstrates
retrieval, prompt assembly, response grounding, guardrails, audit, and lineage patterns without
using any live LLM or cloud service.

## Controls

- Inputs are explicit; latest-run selection is not allowed.
- Manifests and available artefact checksums are verified before evidence extraction.
- Optional inputs must share the same validation lineage.
- Unsupported intents are rejected.
- Evidence references are required for substantive findings.
- The response states that it is synthetic, local, deterministic, and not live LLM output.
- Human review is required for interpretation.
- Conservative redaction is applied to personal-looking fields.
- Prompt, evidence, response, transcript, guardrail results, lineage, and checksums are auditable.

## Prohibited Use

The assistant must not autonomously cancel, delay, divert, reroute, ground, rebook, or reassign
flights. It must not evaluate real passengers, crew, engineers, operators, aircraft, or airline
performance. It is not certified operations-control tooling, air-traffic-control tooling, a
dispatch authority, or a safety-critical assistant.

## Future Mapping

Future milestones may map this pattern to Azure AI Foundry, Azure OpenAI, Prompt Flow, Azure AI
Content Safety, Azure Monitor, Log Analytics, Microsoft Purview, and Power BI. Milestone 9 does
not introduce SDK clients, endpoints, credentials, deployment names, or live model calls.
