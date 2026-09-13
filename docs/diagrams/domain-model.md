# ChainSignal — Domain Sketch

```mermaid
flowchart LR
    E[Event] --> M[Geospatial / Relevance Matching]
    A[SupplyAsset\nSUPPLIER / PORT] --> M
    M --> RE[Risk Evaluation]
    RE --> RS[RiskSnapshot]
    RS --> RR[RiskReason(s)]
    RS --> AE[Alert Evaluation]
    AE --> AL[Alert\nOPEN / ACKNOWLEDGED / RESOLVED]

    SA[StatisticalAnomaly] -. separate signal .-> A
    MA[MLAnomaly] -. separate signal .-> A
```
