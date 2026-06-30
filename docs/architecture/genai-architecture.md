# GenAI Architecture

Future GenAI capabilities will be grounded in governed platform outputs and will not operate
as autonomous aviation decision-makers.

## Candidate Capabilities

- Operations Copilot.
- Delay Investigation Assistant.
- Flight Disruption Summariser.
- Executive Operations Brief.
- Schedule Recommendation Assistant.

## Required Controls

- Ground responses in governed datasets, reports, scores, or model evidence.
- Cite the underlying evidence or data artefacts used for each material claim.
- Distinguish facts, analysis, assumptions, and recommendations.
- Avoid fabricating operational events, passengers, aircraft defects, or disruption causes.
- Avoid autonomous schedule, maintenance, crew, or safety-critical actions.
- Require human review for consequential decisions.
- Audit prompts, responses, retrieved context, model configuration, and user intent.
- Exclude personal passenger information from prompts.

The target Azure mapping is Azure AI Foundry with identity, secrets, monitoring, lineage, and
prompt-governance controls integrated from the broader platform architecture.
