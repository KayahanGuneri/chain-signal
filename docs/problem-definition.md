# ChainSignal — Problem Definition

## Business problem

Manufacturers and importers depend on overseas suppliers and ports that can be disrupted by earthquakes, floods, conflicts, protests and strikes. Public information about these disruptions is fragmented and source-specific. The operational problem is not discovering that an event happened; it is determining whether the event matters to the company's tracked supply-chain assets, how serious the resulting operational exposure is, why the system reached that conclusion, and whether the situation deserves mitigation review.

## Solution

ChainSignal ingests real public disruption data, preserves the raw source data, normalizes supported records into a canonical Event contract, matches those events against tracked Supplier and Port assets, calculates deterministic and explainable operational risk, stores risk history, and manages alerts for risk conditions that require operational attention. Statistical and ML anomaly outputs are exposed as separate analytical signals and are not treated as operational risk ground truth.

## Primary user

The primary user is the **supply-chain operations / risk team of a manufacturer or importer**.

## Primary operational decision

When disruptive events occur, the user needs to determine **which tracked Supplier or Port assets currently require operational attention, why they are exposed, and whether mitigation actions such as alternate sourcing, inventory review, routing review or escalation should be evaluated**.

ChainSignal supports the decision; it does not automatically execute procurement, sourcing or logistics actions in V1.

## Product boundary: not a news aggregator

A news aggregator stops at "an event happened." ChainSignal must continue through the following decision-support chain:

```text
real-world disruption
  -> canonical Event
  -> relevant SupplyAsset
  -> explainable operational RiskSnapshot
  -> optional Alert
  -> human operational decision
```

An event that is not relevant to a tracked asset may be retained as event data but must not become an operational alert merely because it exists.

## V1 product hypothesis

Public disruption data can be transformed into explainable, asset-specific operational risk signals that help a supply-chain operations/risk team prioritize attention and mitigation review.
