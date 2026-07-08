# GenAI Operations Assistant Operations

Run the local deterministic assistant against explicit completed artefacts:

```bash
python3 -m airline_operations_intelligence.cli run-operations-assistant \
  --validation-report-dir reports/validation/<validation_run_id> \
  --monitoring-report-dir reports/monitoring/<monitoring_run_id> \
  --disruption-report-dir reports/disruption_scoring/<disruption_run_id> \
  --config configs/genai_assistant.yaml \
  --intent executive_operations_brief
```

Optional inputs can add generation, passenger forecast, delay prediction, and maintenance
evidence. Entity-specific intents can use `--flight-id`, `--route-id`, `--aircraft-id`, or
`--airport-code`.

Describe a completed run:

```bash
python3 -m airline_operations_intelligence.cli describe-operations-assistant \
  --assistant-report-dir reports/genai_assistant/<assistant_run_id>
```

Run the CI-sized assistant workflow:

```bash
make run-operations-assistant-ci
make describe-operations-assistant-ci
```

## Supported Intents

- `executive_operations_brief`
- `delay_investigation`
- `disruption_summary`
- `maintenance_review_brief`
- `forecast_demand_summary`
- `data_quality_brief`
- `monitoring_health_brief`
- `route_risk_brief`
- `flight_risk_brief`

Unsupported intents are rejected with a non-zero exit.

## Review Order

Review `assistant-response.md`, then `evidence-pack.json`, `prompt-audit.json`,
`guardrail-results.json`, `assistant-transcript.jsonl`, and `lineage.json`. Treat every response as
synthetic portfolio evidence requiring human review.
