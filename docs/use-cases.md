# ChainSignal — V1 Use Cases

## UC-01 — Earthquake near Supplier

**Actor:** Supply-chain operations / risk analyst  
**Trigger:** A supported public source reports an earthquake near a tracked supplier.  
**System behavior:** The event is normalized, spatial relevance to the supplier is evaluated, operational risk is recalculated, an explainable RiskSnapshot is stored, and alert rules are evaluated.  
**Decision supported:** Review inventory exposure, alternate sourcing or operational escalation.

## UC-02 — Flood affecting Port

**Actor:** Supply-chain operations / risk analyst  
**Trigger:** A flood is reported near a tracked port.  
**System behavior:** The event is normalized, spatial relevance is evaluated, the port risk state is recalculated, reasons are persisted and alert rules are evaluated.  
**Decision supported:** Review alternate port or shipment-routing options.

## UC-03 — Strike affecting Port

**Actor:** Supply-chain operations / risk analyst  
**Trigger:** A strike is reported at or near a tracked port.  
**System behavior:** The strike is normalized, matched to the port, and incorporated into the deterministic risk calculation.  
**Decision supported:** Determine whether expected delay exposure requires routing or logistics-plan review.

## UC-04 — Conflict near Supplier

**Actor:** Supply-chain risk analyst  
**Trigger:** Conflict activity is reported near a tracked supplier.  
**System behavior:** The event is normalized, relevance is evaluated and the supplier's operational risk state is recalculated with persisted reasons.  
**Decision supported:** Decide whether supplier-continuity escalation or alternate-sourcing review is required.

## UC-05 — Protest near Supplier or Port

**Actor:** Supply-chain operations / risk analyst  
**Trigger:** A protest is reported near a tracked Supplier or Port.  
**System behavior:** The event is normalized and evaluated for asset relevance. If it changes meaningful risk state or reasons, a new RiskSnapshot can be recorded and alert rules are evaluated.  
**Decision supported:** Determine whether monitoring remains sufficient or escalation is needed.

## Common end-to-end pattern

```text
Event
  -> normalization
  -> asset relevance / geospatial matching
  -> deterministic operational risk
  -> explainable RiskSnapshot
  -> optional Alert
  -> human operational decision
```
