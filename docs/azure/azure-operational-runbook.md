# Azure Architecture Review Runbook

This runbook describes how to review the target Azure architecture without deploying anything.

1. Run `make validate-azure-architecture`.
2. Review `configs/azure_mapping.yaml` for reference-only policy flags.
3. Review `docs/azure/` for service, environment, data-zone, security, governance, ML, GenAI,
   monitoring, dashboard, and cost mappings.
4. Review `infra/` skeletons for placeholder-only values and non-deploying disclaimers.
5. Confirm GitHub Actions contains no Azure login or deployment step.
6. Confirm generated runtime data, credentials, and local state files are absent.

The runbook is a review workflow, not a cloud operations procedure.
