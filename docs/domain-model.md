# ChainSignal — Domain Model

## Ubiquitous language

### SupplyAsset

A tracked supply-chain location that may be exposed to disruption. V1 supports exactly two asset types:

- `SUPPLIER`
- `PORT`

A SupplyAsset is **not** a shipment, container, purchase order, product or cargo type.

### Event

A real-world disruptive occurrence from the controlled V1 taxonomy. An Event is a domain/data concept and is **not** a Kafka message.

Events exist independently from SupplyAssets. Geospatial/relevance matching determines which assets are operationally relevant to an Event.

### RiskSnapshot

An immutable representation of a SupplyAsset's calculated operational risk state at a meaningful calculation point.

A RiskSnapshot is not created merely because a fixed timer elapsed. A meaningful recalculation may be triggered by relevant event changes, asset changes, risk-rule changes, event aging/expiry or similar risk inputs.

A new RiskSnapshot can be meaningful even when `riskLevel` is unchanged if the risk reasons/evidence changed.

### RiskReason

The minimal persisted explanation/evidence needed to explain why a RiskSnapshot received its result. It should reference relevant events/rules without duplicating complete raw provider payloads.

### Alert

A lifecycle entity representing a continuing risk condition that requires operational attention.

Initial lifecycle:

```text
OPEN -> ACKNOWLEDGED -> RESOLVED
```

`ACKNOWLEDGED` means a user has reviewed/owned the alert; it does not mean the underlying risk is gone.

The same continuing risk condition must not generate duplicate active alerts merely because additional events or recalculations occur. Alert state must never feed back into the RiskEngine as a risk input.

### StatisticalAnomaly

An analytical signal showing that current observations materially deviate from a historical statistical baseline.

It is not operational risk.

### MLAnomaly

An unsupervised ML analytical signal indicating that current observations look unusual relative to learned historical patterns.

It is not a forecast and it is not operational risk.

## Key relationships

```text
Event + SupplyAsset
    -> geospatial/relevance matching
    -> deterministic RiskEngine
    -> RiskSnapshot + RiskReason(s)
    -> Alert evaluation
    -> Alert lifecycle

StatisticalAnomaly = separate analytical signal
MLAnomaly          = separate analytical signal
```

Multiple relevant Events may contribute reasons to a single RiskSnapshot.

## Important invariants

- `Event` does not belong to a specific SupplyAsset at ingestion time.
- `RiskSnapshot` belongs to one SupplyAsset.
- operational risk is deterministic and explainable in V1.
- StatisticalAnomaly and MLAnomaly do not directly determine RiskSnapshot in V1.
- Alert is downstream of risk evaluation and has an independent lifecycle.
- no `Alert -> RiskEngine -> Alert` feedback loop is allowed.

## Model separation

### Domain model
Business concepts and their semantics: SupplyAsset, Event, RiskSnapshot, Alert and anomaly signals.

### Canonical data model
The normalized cross-source Event representation used by the system after source-specific normalization.

### Persistence model
How domain/canonical data is physically stored in PostgreSQL/PostGIS. Persistence details such as `JSONB` or PostGIS geometry are not themselves the domain model.

### API model
The representations exposed to the frontend/clients. API responses may combine or reshape domain data and are not required to mirror persistence rows one-to-one.
