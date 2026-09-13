# Replay Service

Future Go historical replay / stream simulation service.

This component is **gated until Phase 6** and must not be implemented merely to increase technology count.

If the Phase 0-5 batch core is stable, its responsibilities will be:

- read historical canonical events
- rate-controlled replay
- Kafka publishing
- concurrency and graceful shutdown
- replay metrics

It must not reimplement Python normalization or the Java RiskEngine.
