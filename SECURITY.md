# Security Policy

## Current Scope

This repository currently contains local synthetic data generation, governed local ingestion and
validation, passenger-demand forecasting, flight-delay prediction, aircraft-health maintenance
analytics, operational disruption scoring, and local monitoring evidence. It does not contain real
airline data, personal data, credentials, deployed Azure resources, or committed generated
operational outputs.

## Reporting Security Issues

Report suspected security issues through the repository maintainers rather than public issue
threads. Include the affected files, expected impact, and reproduction steps where possible.

## Secret Handling

- Never commit Azure keys, connection strings, tenant IDs, subscription IDs, certificates,
  service principal credentials, or personal tokens.
- Use `.env.example` only for placeholder variable names and comments.
- Future Azure implementations must use Microsoft Entra ID, managed identities where possible,
  and Azure Key Vault for secrets.

## Aviation Boundary

The platform is an analytics and decision-support demonstration. It is not an airworthiness
system, flight-control system, safety-management system, certified aviation operational system, or
live production monitoring system. Forecasts, predictions, maintenance scores, disruption scores,
and monitoring alerts are synthetic evaluation artefacts and are not autonomous operational
instructions.
