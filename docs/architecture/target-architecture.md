# Target Architecture

The target state is a local-first implementation with clean deployment boundaries for Azure.
Local folders, producers, configuration, ingestion, and validation interfaces represent Azure
services until later milestones introduce cloud deployments.

```mermaid
flowchart TB
  subgraph Sources["Synthetic aviation sources"]
    Schedule["flight_schedule.csv"]
    Demand["passenger_demand.csv"]
    Weather["weather_events.csv"]
    Health["aircraft_health.jsonl"]
    Crew["crew_operations.csv"]
    Delay["delay_history.csv"]
    Airport["airport_events.jsonl"]
  end

  subgraph Ingestion["Local producers and validation / Azure mapping"]
    BatchProducer["Batch file producers"]
    EventProducer["Operational event producers"]
    Validator["Governed validation CLI"]
    EventHub["Azure Event Hubs boundary"]
  end

  subgraph Lake["Raw landing zone / ADLS Gen2 mapping"]
    Raw["data/raw"]
    Interim["data/interim"]
    Processed["data/processed"]
  end

  subgraph Quality["Validation and data-quality controls"]
    Schema["Schema contracts"]
    Completeness["Completeness checks"]
    Freshness["Freshness checks"]
    Lineage["Dataset lineage"]
  end

  subgraph Curated["Curated operational datasets"]
    FlightOps["Flight operations facts"]
    RouteDemand["Route demand features"]
    AircraftHealth["Aircraft health features"]
    DisruptionFeatures["Disruption features"]
  end

  subgraph Analytics["Forecasting, prediction, anomaly and disruption services"]
    Forecasting["Passenger forecasting"]
    DelayPrediction["Delay prediction"]
    Maintenance["Maintenance risk"]
    Anomaly["Anomaly detection"]
    Disruption["Disruption scoring"]
    Optimisation["Schedule optimisation research"]
  end

  subgraph Outputs["Operational outputs and model evidence"]
    Scores["Risk scores"]
    Forecasts["Demand forecasts"]
    Evidence["Model evidence and metadata"]
    Decisions["Recovery decision support"]
  end

  subgraph Consumption["Power BI, reports and GenAI operations assistant"]
    PowerBI["Microsoft Power BI"]
    Reports["Operational reports"]
    GenAI["Azure AI Foundry operations assistant"]
  end

  subgraph Controls["Cross-cutting controls"]
    Entra["Microsoft Entra ID"]
    KeyVault["Azure Key Vault"]
    Purview["Microsoft Purview"]
    Monitor["Azure Monitor and Application Insights"]
    CICD["CI/CD quality gate"]
    ModelGov["Model governance"]
  end

  Schedule --> BatchProducer
  Demand --> BatchProducer
  Delay --> BatchProducer
  Crew --> BatchProducer
  Weather --> EventProducer
  Health --> EventProducer
  Airport --> EventProducer
  BatchProducer --> Raw
  EventProducer --> EventHub --> Raw
  Raw --> Validator --> Schema --> Interim
  Interim --> Completeness --> Freshness --> Lineage --> Processed
  Processed --> FlightOps
  Processed --> RouteDemand
  Processed --> AircraftHealth
  Processed --> DisruptionFeatures
  RouteDemand --> Forecasting
  FlightOps --> DelayPrediction
  AircraftHealth --> Maintenance
  FlightOps --> Anomaly
  DisruptionFeatures --> Disruption
  FlightOps --> Optimisation
  Forecasting --> Forecasts
  DelayPrediction --> Scores
  Maintenance --> Scores
  Anomaly --> Evidence
  Disruption --> Decisions
  Scores --> PowerBI
  Forecasts --> PowerBI
  Evidence --> Reports
  Decisions --> GenAI
  Evidence --> GenAI
  Entra -. identity .- Ingestion
  KeyVault -. secrets .- Ingestion
  Purview -. lineage .- Lake
  Monitor -. telemetry .- Analytics
  CICD -. validation .- Quality
  ModelGov -. approvals .- Analytics
```

## Cross-Cutting Concerns

- Microsoft Entra ID will provide identity and access control in the Azure target state.
- Azure Key Vault will manage secrets; no credentials belong in repository configuration.
- Microsoft Purview will support data cataloguing, lineage, classification, and retention.
- Azure Monitor and Application Insights will capture telemetry and operational health.
- CI/CD will enforce linting, formatting, type checks, tests, documentation checks, YAML checks,
  and repository validation.
- Data-quality controls will guard schema, completeness, timeliness, referential integrity, and
  sensitivity expectations.
- Model governance will track features, training windows, evaluation results, metadata, approval
  status, and operational limitations.
