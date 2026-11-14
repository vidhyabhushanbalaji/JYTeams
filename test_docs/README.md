# PulseAPI

A lightweight, high-throughput telemetry and event ingestion service built for distributed microservices.

## Features
- **Sub-5ms Ingestion:** Asynchronous event queueing via Redis Streams.
- **Schema Validation:** Automatic JSON schema enforcement at the edge.
- **Multi-Tenant Isolation:** API key scoping with per-tenant rate limiting.

## Quick Start
1. Clone the repository: `git clone https://github.com/example/pulse-api.git`
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env` and set your `REDIS_URL`.
4. Start the server: `npm run dev`

## Documentation
- [System Architecture](./docs/architecture.md)
- [API Reference](./docs/api-reference.md)
- [Deployment Guide](./guides/deployment.md)