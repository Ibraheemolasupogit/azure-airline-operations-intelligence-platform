# GenAI Architecture

Milestone 9 implements a deterministic local GenAI-style assistant simulation. It is grounded in
governed platform outputs and does not operate as an autonomous aviation decision-maker.

## Candidate Capabilities

- Executive operations brief.
- Delay investigation.
- Disruption summary.
- Maintenance review brief.
- Forecast demand summary.
- Data-quality brief.
- Monitoring health brief.
- Route risk brief.
- Flight risk brief.

## Required Controls

- Ground responses in governed datasets, reports, scores, or model evidence.
- Cite the underlying evidence or data artefacts used for each material claim.
- Distinguish facts, analysis, assumptions, and recommendations.
- Avoid fabricating operational events, passengers, aircraft defects, or disruption causes.
- Avoid autonomous schedule, maintenance, crew, or safety-critical actions.
- Require human review for consequential decisions.
- Audit prompts, responses, retrieved context, model configuration, and user intent.
- Exclude personal passenger information from prompts.

The current implementation uses deterministic local templates only. The target Azure mapping is
Azure AI Foundry or Azure OpenAI with identity, secrets, monitoring, lineage, and prompt-governance
controls integrated from the broader platform architecture in a later milestone.
