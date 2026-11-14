# System Architecture

PulseAPI decouples event ingestion from data persistence to prevent traffic spikes from overwhelming the primary database.

## Data Flow
1. **API Gateway:** Authenticates the `X-API-Key` header and validates the JSON payload.
2. **Ingestion Worker:** Pushes valid payloads into a partitioned Redis Stream.
3. **Batch Consumer:** Reads events in batches of 500 and writes them to PostgreSQL (TimescaleDB).

## Core Components
| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| Edge Server | Node.js / Fastify | Request routing, auth, rate limiting |
| Message Broker | Redis Streams | Temporary buffering and backpressure |
| Storage Engine | TimescaleDB | Long-term time-series event storage |