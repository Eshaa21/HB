# Smart Water Distribution & Leak Detection System

## Problem Statement
Cities need a centralized way to monitor water flow, pressure, and consumption across multiple areas and detect leak patterns early using telemetry from virtual sensors.

## Project Objective
This FastAPI project uses SQLite, Pandas, logging, APScheduler, and rule-based leak detection to monitor Pune water distribution areas and their pipelines.

## Default Areas And Pipelines

| Area | Pipelines |
| --- | --- |
| Kothrud | KOTH_P1, KOTH_P2 |
| Hinjewadi | HINJ_P1, HINJ_P2 |
| Baner | BAN_P1, BAN_P2 |
| Wakad | WAK_P1, WAK_P2 |

The default data is inserted automatically when `water.db` is created or initialized.

## Project Flow
1. FastAPI starts and initializes SQLite.
2. Tables are created: `areas`, `pipelines`, `telemetry`, and `alerts`.
3. Default Pune areas and 8 pipelines are seeded.
4. APScheduler starts a background job.
5. Every 2 minutes, telemetry is generated for every registered pipeline.
6. The leak detector checks pressure, flow, and pressure-drop rules.
7. Alerts are stored and logged when leak rules are triggered.
8. Analytics are calculated from SQLite using Pandas.

## Database Design

### areas
- `id INTEGER PRIMARY KEY`
- `area_name TEXT`
- `created_at TEXT`

### pipelines
- `id INTEGER PRIMARY KEY`
- `area_name TEXT`
- `pipeline_name TEXT`
- `created_at TEXT`

### telemetry
- `id INTEGER PRIMARY KEY`
- `area_name TEXT`
- `pipeline_name TEXT`
- `flow_rate REAL`
- `pressure REAL`
- `consumption REAL`
- `timestamp TEXT`

### alerts
- `id INTEGER PRIMARY KEY`
- `area_name TEXT`
- `pipeline_name TEXT`
- `alert_type TEXT`
- `severity TEXT`
- `message TEXT`
- `timestamp TEXT`

## Leak Detection Logic
The system keeps the original three rules:

1. Pressure is below 40 PSI.
2. Flow rate is more than consumption by 30.
3. Pressure drop is greater than 20% compared with the previous reading for the same pipeline.

If any rule is triggered, an alert is stored in SQLite and written to `logs/system_logs.log`.

## APIs

### `GET /`
Returns basic service health.

### `POST /generate-data`
Manually generates one telemetry reading. Request body can be empty or:

```json
{
  "area_name": "Kothrud",
  "pipeline_name": "KOTH_P1"
}
```

If the area/pipeline does not already exist, it is registered automatically before the telemetry row is stored.

### `GET /areas`
Returns registered areas.

### `GET /pipelines`
Returns registered pipelines. Optional filter: `?area=Kothrud`

### `GET /water-data`
Returns telemetry rows. Optional filters:

```text
?area=Kothrud&pipeline=KOTH_P1
```

### `GET /alerts`
Returns leak alerts.

### `GET /analytics`
Returns totals, water loss, leak count, area-wise statistics, and pipeline statistics.

### `GET /logs`
Returns recent log entries.

## How To Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server from inside `smart_water_system`:

```bash
uvicorn main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```bash
pytest
```
