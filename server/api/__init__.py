"""
server.api
==========
FastAPI Integration Layer for the AutoAssist OBD-II anomaly detection platform.

This package exposes the completed ML pipeline (preprocessing, state
classification, anomaly detection, health scoring) through a RESTful API
designed for consumption by the TanStack Start frontend via server functions.

Architecture
------------
The browser does **not** call FastAPI directly.  The communication path is::

    Browser → TanStack Server Functions → FastAPI (internal)

All responses use **camelCase** field names to align with frontend conventions.

Package layout
--------------
::

    api/
    ├── main.py           — FastAPI application factory + lifespan
    ├── dependencies.py   — Dependency injection providers
    │
    ├── routes/           — Endpoint definitions
    │   ├── analyze.py    — CSV upload + full pipeline execution
    │   ├── dashboard.py  — Session dashboard data
    │   ├── anomalies.py  — Anomaly list, severity, heatmap
    │   ├── telemetry.py  — Sensor time-series
    │   ├── sensors.py    — Correlation matrix + pairwise
    │   └── report.py     — Executive report + insights
    │
    ├── schemas/          — Pydantic v2 request / response models
    │   ├── analyze.py
    │   ├── dashboard.py
    │   ├── anomalies.py
    │   ├── telemetry.py
    │   ├── sensors.py
    │   └── report.py
    │
    └── services/         — Business logic not belonging to ML layer
        ├── enrichment.py     — anomaly_score → severity mapping
        ├── session_service.py — in-memory session store
        └── report_service.py  — rule-based executive insights
"""
