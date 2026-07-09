# Dashboard Output Architecture

Milestone 10 adds a local dashboard-output layer that converts verified synthetic platform
artefacts into Power BI-ready analytical exports.

The layer consumes explicit validation, disruption scoring, and monitoring report directories.
Optional passenger forecasting, delay prediction, maintenance analytics, generation, and assistant
report directories can be supplied, but the workflow never selects the latest run implicitly.

## Flow

1. Read explicit source report directories.
2. Verify manifest schema versions and checksums where available.
3. Reject sources that do not share the same validation lineage.
4. Build deterministic dimension and fact tables.
5. Build KPI and summary tables.
6. Write a semantic model specification, measure catalogue, page specs, data dictionary, quality
   evidence, manifest, lineage, and reports.

Outputs are local CSV and JSON documentation artefacts only. This milestone does not create
`.pbix` files, publish semantic models, call Power BI APIs, call Fabric APIs, or use Azure SDK
clients.

## Future Microsoft Mapping

Local dashboard CSV outputs can map to an ADLS Gen2 curated dashboard zone or Fabric Lakehouse
tables in a future milestone. The semantic-model JSON can inform a Power BI semantic model or
Tabular model definition. The measure catalogue can inform DAX implementation. The lineage JSON
can map to Microsoft Purview.
