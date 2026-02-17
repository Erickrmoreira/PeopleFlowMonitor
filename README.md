# PeopleFlowMonitor

PeopleFlowMonitor is a computer vision ecosystem designed to solve practical reception and security challenges. By combining YOLOv8 detection, multi-object tracking, and directional crossing logic, the system delivers reliable IN/OUT metrics, historical traffic patterns, and actionable insights through a BI dashboard and a dedicated API.

This repository was built with focus on:
- modular architecture
- clean separation of responsibilities
- real-time or near-real-time processing
- production-minded engineering

## Project Goals

- Accurate count of people entering and leaving the monitored area.
- Flow analysis to identify movement patterns.
- Statistical data generation for occupancy and traffic.
- Real-time or near-real-time operation.

## Technical Requirements Implemented

- Python-based solution.
- YOLOv8 used as mandatory detection model.
- Multi-person detection and tracking.
- Zone/line-based IN/OUT counting.
- Event storage and analytics over SQLite.

## Core Features

- YOLOv8 person detection (`class 0`).
- BoT-SORT based tracking with persistent IDs.
- Directional counting (IN/OUT) using configurable crossing line.
- Daily analytics and hourly peak analysis.
- Streamlit BI dashboard with charts and executive PDF export.
- FastAPI endpoints for metrics and health checks.
- Docker and local run scripts.

## Architecture Overview

```text
Video Source
  -> Detection (YOLOv8)
  -> Tracking (BoT-SORT)
  -> Crossing Logic (IN/OUT)
  -> Storage (SQLite, buffered writes)
  -> Analytics Layer
  -> API (FastAPI) + Dashboard (Streamlit)
```

## Repository Structure

```text
app/
  analytics/   # Counting and statistics
  api/         # FastAPI app
  config/      # Settings and zone config
  core/        # Real-time processing pipeline
  detection/   # YOLO wrapper
  services/    # Storage, repository, reporting services
  tracking/    # Tracker abstraction
  ui/          # Streamlit dashboard
  utils/       # Logger and utilities

scripts/
  init_db.py         # creates database schema and indexes
  reset_db.py        # clears stored counting events
  calibrate_zones.py # calibrates the counting line visually
  run_local.py       # starts the local real-time pipeline

tests/
  unit tests for counter, statistics, pipeline fallback, tracker contract,
  detector tracking, storage, repository, and API
```

## Requirements

- Python 3.10+ (3.11 also supported)
- Webcam or video source for real-time pipeline
- `yolov8n.pt` model file in project root (default path in settings)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Local Run

1. Create virtual environment and install dependencies.
2. Initialize database:

```bash
python scripts/init_db.py
```

3. Run full local pipeline:

```bash
python scripts/run_local.py
```

## Video Source Configuration

By default, `scripts/run_local.py` uses local webcam source `0`.

Valid source formats:
- Webcam: `0`
- Video file: `videos/sample.mp4`
- RTSP camera: `rtsp://user:password@camera-ip:554/stream`

To use an RTSP camera, edit the final call in `scripts/run_local.py`:

```python
main("rtsp://user:password@camera-ip:554/stream")
```

Security note: do not hardcode real credentials in public repositories. Use environment variables or local-only config.

Optional launchers:
- Windows: `run_win.bat`
- Linux: `bash run_linux.sh`

Dashboard only:

```bash
python -m streamlit run app/ui/dashboard.py
```

API only:

```bash
python -m uvicorn app.api.main:app
```

## Docker

Build and run services:

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`

Note: direct webcam access can be limited in Docker depending on host OS/runtime.
For camera-based real-time validation, running pipeline on host machine is recommended.

## API Endpoints

- `GET /` basic service status
- `GET /health` health check
- `GET /stats` daily IN/OUT metrics

Swagger docs (when API is running):
- `http://localhost:8000/docs`

## Testing

Run test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Configuration

- `app/config/settings.py` defines paths (DB/model/zones).
- Counting line parameters are loaded from `app/config/zones.yaml`.
- Use `scripts/calibrate_zones.py` to adjust line placement visually.

## Database Maintenance

To clear all stored counting events and reset the auto-increment ID sequence:

```bash
python scripts/reset_db.py
```

Use this for local cleanup, test resets, or demo preparation before a new run.`r`n`r`n## Current Limitations

- API authentication is not enabled by default (project intended for local/demo use).
- Dashboard live updates use periodic polling.
- SQLite is suitable for this scope; larger deployments may require PostgreSQL.

## Roadmap (Possible Next Steps)

- API key/JWT for secured external API usage.
- CI pipeline for lint/test automation.
- Optional migration to PostgreSQL for higher concurrency.
- Extended technical details are documented in `ARCHITECTURE.md`.

## Author

Erick Ribeiro Moreira

Backend Developer Python, Applied AI, Intelligent Systems.
