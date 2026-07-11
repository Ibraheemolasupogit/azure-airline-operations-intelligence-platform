# Azure Cost Considerations

Cost controls are target-state guidance only.

- Start with dev and test using small SKUs and short retention.
- Use lifecycle management for ADLS zones.
- Keep Log Analytics retention aligned to governance requirements.
- Prefer batch workloads for ML until near-real-time value is proven.
- Size Azure Data Explorer only for telemetry volumes that justify it.
- Keep Fabric and Power BI capacity decisions separate from local dashboard exports.
- Disable unused environments and review private networking cost impacts.

Production cost estimates require workload volumes, retention policies, service tiers, and
approved availability requirements that are outside Milestone 11.
