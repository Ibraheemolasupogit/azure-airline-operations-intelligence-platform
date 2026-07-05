# Passenger Forecasting Architecture

Milestone 4 adds deterministic local passenger-demand forecasting from Milestone 3 validated
outputs. It does not implement delay prediction, maintenance analytics, disruption scoring,
optimisation, GenAI, dashboards, monitoring, or Azure deployment.

## Flow

```mermaid
flowchart TD
    validated["Validated passenger-demand data<br/>data/processed/<validation_run_id>"]
    integrity["Input integrity verification<br/>validation manifest and checksums"]
    horizon["Booking-horizon selection<br/>one row per flight at configured horizon"]
    features["Leakage-safe feature engineering<br/>schedule, booking, calendar, historical route features"]
    split["Chronological train, validation, and test split<br/>no flight crosses partitions"]
    train["Baselines and candidate models<br/>historical mean, booking curve, linear regression"]
    validate["Validation evaluation<br/>MAE, RMSE, WAPE, sMAPE, bias"]
    champion["Champion selection<br/>validation metric, bias, simplicity, deterministic tie-breaks"]
    test["Final test evaluation<br/>untouched test partition"]
    intervals["Prediction intervals and constraints<br/>empirical residual intervals, non-negative capacity cap"]
    outputs["Forecast outputs, model artefacts, lineage, reports"]

    validated --> integrity --> horizon --> features --> split --> train --> validate --> champion --> test --> intervals --> outputs

    reproducibility["Reproducibility controls<br/>seed, deterministic ordering, checksums"] -.-> features
    lineage["Feature lineage<br/>availability policy and source checksums"] -.-> outputs
    metadata["Model metadata<br/>features, parameters, metrics, limitations"] -.-> outputs
    status["Validation status gate<br/>reject failed validation runs"] -.-> integrity
    human["Human review<br/>decision-support only"] -.-> outputs

    validated -. future .-> adls["ADLS Gen2 curated zone<br/>or Synapse/Fabric tables"]
    features -. future .-> amlData["Azure ML data assets<br/>or feature engineering jobs"]
    train -. future .-> amlJobs["Azure ML command jobs"]
    champion -. future .-> registry["Azure ML model registry candidate"]
    outputs -. future .-> downstream["ADLS, Synapse, Fabric, or Power BI dataset"]
    metadata -. future .-> monitor["Azure Monitor, Log Analytics, Data Explorer"]
    lineage -. future .-> purview["Azure ML lineage and Microsoft Purview"]
```

## Prediction Design

The principal grain is one forecast per scheduled flight at the configured booking horizon. The
primary target is `expected_final_passengers`, using the booking observation at exactly the
configured horizon when available. If an exact observation is unavailable, the nearest earlier
observation is used; observations closer to departure than the configured horizon are not used.

## Leakage Controls

The feature set excludes actual departure outcomes, delay history outcomes, cancellations,
diversions, target-derived load factor, and future booking observations. Historical route features
are calculated only from earlier flights in deterministic operating-date order.

Preprocessing and model fitting use training rows only. Champion selection uses validation metrics
only, and final test metrics are calculated once for the selected champion.
