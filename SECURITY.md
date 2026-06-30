# Security Policy

## Current Scope

This repository currently contains a local Milestone 1 foundation. It does not contain real
airline data, personal data, credentials, deployed Azure resources, models, or generated
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
system, flight-control system, safety-management system, or certified aviation operational
system.
