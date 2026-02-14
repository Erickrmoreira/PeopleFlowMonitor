# PeopleFlowMonitor - Architecture

## Goal
Count people IN/OUT in near real time using computer vision, and expose metrics through API and dashboard.

Scope of this document:
- technical design and boundaries
- runtime data flow and persistence strategy
- constraints and engineering tradeoffs

Operational setup and run commands are documented in `README.md`.

## Runtime Flow
```text
Camera/Video
  -> YOLOv8 Detection + Tracking
  -> Crossing Logic (IN/OUT)
  -> Asynchronous Persistence Layer (SQLite)
  -> Analytics
  -> FastAPI + Streamlit Dashboard
```

## Layers
- `app/core`: pipeline orchestration (capture, process cadence, overlay, lifecycle).
- `app/detection`: YOLO wrapper.
- `app/tracking`: tracker contract and configuration.
- `app/analytics`: counting rules and statistics queries.
- `app/services`: persistence, repository, reporting/PDF services.
- `app/api`: HTTP endpoints (`/`, `/health`, `/stats`).
- `app/ui`: dashboard presentation and interaction.

## Data Model
Table: `counts`
- `timestamp`
- `direction` (`IN` / `OUT`)
- `object_id`

Indexes:
- `timestamp`
- `(direction, timestamp)`

## Key Decisions
- SQLite for simple local deployment.
- Asynchronous persistence layer (buffer + worker thread) to keep counting path responsive.
- Read/write responsibilities separated (`statistics`/`repository` vs `storage`).
- Tracker depends on protocol, reducing detector coupling.
- Core-to-storage communication is event-driven (counting events: `IN`/`OUT`).

## Current Constraints
- Designed for local/demo-first usage.
- API auth is not enabled by default.
- Dashboard uses polling for live KPI updates.
- SQLite concurrency is handled at basic level with WAL mode and connection lock.

## Next Step Options
- Add API key/JWT for external exposure.
- Move to PostgreSQL for higher concurrency.
- Add CI quality gates (tests/lint/type checks).
