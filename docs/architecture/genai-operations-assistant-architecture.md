# GenAI Operations Assistant Architecture

Milestone 9 implements a deterministic local GenAI-style airline operations assistant. It uses
governed platform artefacts as evidence, assembles auditable prompts, generates local template
responses, applies guardrails, and writes transcripts, manifests, lineage, and governance reports.

No live LLM, OpenAI, Azure OpenAI, Azure AI Foundry, LangChain, LlamaIndex, vector database,
embedding model, or Azure SDK is used.

## Components

- `genai.config` validates assistant settings, supported intents, retrieval policy, guardrails,
  output paths, and severity policy.
- `genai.discovery` verifies explicit input manifests, checksums, and lineage compatibility.
- `genai.evidence` extracts structured evidence records from validation, monitoring, disruption,
  delay prediction, maintenance, and passenger forecasting artefacts.
- `genai.retrieval` ranks evidence deterministically by entity match, severity, score, domain
  priority, timestamp, and evidence ID.
- `genai.prompts` writes the prompt audit artefact without calling an LLM.
- `genai.templates` creates local deterministic responses.
- `genai.guardrails` records intent, grounding, safety, synthetic-data, no-live-LLM, human-review,
  Azure-claim, and redaction checks.
- `genai.pipeline` writes outputs and reports atomically.

## Outputs

Each run writes to `outputs/genai_assistant/<assistant_run_id>/`:

- `assistant-response.md`
- `assistant-response.json`
- `evidence-pack.json`
- `prompt-audit.json`
- `guardrail-results.json`
- `assistant-transcript.jsonl`
- `assistant-run-manifest.json`

Reports are written to `reports/genai_assistant/<assistant_run_id>/`:

- `assistant-summary.md`
- `assistant-governance-report.md`
- `evidence-report.md`
- `lineage.json`
- `assistant-run-manifest.json`

## Future Azure Mapping

Local evidence extraction maps to a future governed retrieval layer over ADLS, Synapse, Fabric,
or Azure Data Explorer. Prompt assembly maps to Azure AI Foundry prompt flow or an agent workflow.
Local deterministic templates map to a future Azure OpenAI or Azure AI Foundry model call.
Guardrails map to Azure AI Content Safety, prompt shields, policy filters, and human review
workflows. Prompt and response audit maps to Azure Monitor, Log Analytics, Application Insights,
or AI Foundry tracing. Lineage maps to Microsoft Purview. Assistant summaries can feed Power BI
in Milestone 10.
