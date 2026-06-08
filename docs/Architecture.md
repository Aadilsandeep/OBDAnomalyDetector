# AutoAssist System Architecture

## Overview

AutoAssist is an OBD-II Vehicle Health Monitoring and Anomaly Detection Platform designed to transform raw vehicle telemetry into actionable automotive intelligence.

The platform processes historical or live OBD-II sensor data, classifies vehicle operating states, identifies anomalous behavior patterns, and generates vehicle health insights through a modular machine learning pipeline.

The architecture has been designed with a clear separation of responsibilities, allowing each subsystem to evolve independently while supporting future migration from offline batch processing to real-time telemetry streaming.

---

# Architectural Goals

The architecture was designed around the following principles:

* Modular design
* Single responsibility per component
* Explainable analytics
* Future real-time compatibility
* Scalability to larger telemetry datasets
* Easy integration with FastAPI services
* Support for future live OBD-II streaming

---

# High-Level Architecture

```text
Raw OBD-II Data
        │
        ▼
Preprocessing Layer
        │
        ▼
State Intelligence Layer
        │
        ▼
Feature Engineering Layer
        │
        ▼
Anomaly Detection Layer
        │
        ▼
Vehicle Health Engine
        │
        ▼
FastAPI Backend
        │
        ▼
Frontend Dashboard
```

---

# Detailed Processing Pipeline

```text
Raw CSV Sessions
        │
        ▼
Loader
        │
        ▼
Standardizer
        │
        ▼
Cleaner
        │
        ▼
Merger
        │
        ▼
Master Dataset
        │
        ▼
State Classifier
        │
        ▼
State Analyzer
        │
        ▼
Feature Engineering
        │
        ▼
Isolation Forest
        │
        ▼
Health Score Engine
        │
        ▼
REST API
        │
        ▼
Frontend Dashboard
```

---

# Layer 1 — Data Ingestion & Preprocessing

## Purpose

Transform raw OBD-II session files into a clean and standardized master dataset.

---

## Loader

### Responsibilities

* Discover CSV files
* Load individual sessions
* Validate input files
* Handle file-level errors

### Output

```text
Dictionary[str, DataFrame]
```

where each key corresponds to a driving session.

---

## Standardizer

### Responsibilities

Convert raw OBD-II sensor names into a canonical schema.

Example:

```text
Engine RPM [RPM]
        ↓
rpm
```

### Benefits

* Consistent downstream processing
* Dataset independence
* Simplified feature engineering

---

## Cleaner

### Responsibilities

* Remove duplicates
* Handle missing values
* Validate sensor ranges
* Parse timestamps
* Remove invalid observations

### Output

Clean telemetry sessions.

---

## Merger

### Responsibilities

Merge all sessions into a single master dataset.

### Design Decisions

* Preserves session identity using `session_id`
* Uses categorical encoding for memory efficiency
* Maintains full telemetry history

### Output

```text
master_dataset.csv
```

---

## Preprocessor

### Responsibilities

Orchestrate the complete preprocessing workflow.

```text
Load
 ↓
Standardize
 ↓
Clean
 ↓
Merge
 ↓
Master Dataset
```

---

# Layer 2 — State Intelligence

## Purpose

Understand vehicle operating behavior before anomaly detection.

---

## State Classification Engine

The classifier assigns one of five driving states to every telemetry sample.

### Supported States

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

---

### Inputs

* RPM
* Speed
* RPM Delta
* Speed Delta

---

### Design Approach

A deterministic rule-based classifier was selected because:

* No labeled state dataset exists
* Fully explainable
* Easy to validate
* Easy to tune per vehicle

---

### State Distribution

Current dataset distribution:

| State        | Percentage |
| ------------ | ---------- |
| Cruising     | 60.08%     |
| Traffic      | 26.83%     |
| Idle         | 9.66%      |
| Acceleration | 1.74%      |
| Deceleration | 1.69%      |

---

## State Analysis Engine

### Responsibilities

Generate:

* State counts
* State percentages
* Session statistics
* Dominant state
* Aggressive event counts

### Purpose

Provide behavioral context for anomaly detection and health scoring.

---

# Layer 3 — Feature Engineering

## Purpose

Create behavioral features that capture changes in vehicle operation.

---

## Engineered Features

```text
speed_delta
rpm_delta
maf_delta
map_delta
throttle_delta
```

---

## Design Rationale

Raw sensors describe:

```text
Current vehicle condition
```

Delta features describe:

```text
Vehicle behavior changes
```

These behavioral features proved valuable during feature importance research.

---

# Layer 4 — Anomaly Detection

## Purpose

Identify unusual vehicle behavior patterns.

---

## Research Findings

The dataset contains predominantly normal driving behavior.

Reliable anomaly labels do not exist.

Therefore:

```text
Supervised anomaly detection
was rejected.
```

---

## Candidate Models Evaluated

### Random Forest

Used for:

* Feature importance analysis

Not selected as the production anomaly detector because anomaly labels were unavailable.

---

### PCA

Evaluated as a dimensionality reduction technique.

Findings:

```text
10 Features
      ↓
8 Principal Components
      ↓
95% Variance Retained
```

Decision:

```text
Rejected for production use.
```

Reason:

The reduction benefit did not justify the loss of interpretability.

---

## Selected Model

### Isolation Forest

Chosen because:

* Unsupervised learning
* No anomaly labels required
* Scales well to large telemetry datasets
* Learns normal behavior patterns
* Supports future real-time monitoring

---

### Outputs

```text
anomaly_score

anomaly_flag
```

---

# Layer 5 — Vehicle Health Engine

## Purpose

Convert anomaly signals into a human-readable vehicle health score.

---

## Planned Inputs

* Anomaly density
* Aggressive driving events
* Session statistics
* State distributions

---

## Planned Output

```text
Vehicle Health Score
```

Range:

```text
0 – 100
```

Where:

```text
100 = Excellent
0 = Critical
```

---

# Layer 6 — Backend Services

## Technology

```text
FastAPI
```

---

## Responsibilities

Expose REST endpoints for:

* Health Score
* Anomaly Detection
* Session Analytics
* Sensor Statistics
* Dashboard Data

---

## Future API Examples

```text
POST /analyze

GET /health

GET /anomalies

GET /sessions

GET /states
```

---

# Layer 7 — Frontend Dashboard

## Purpose

Present vehicle insights through a modern automotive dashboard.

---

## Planned Components

### Vehicle Health Score

Overall condition indicator.

---

### Digital Vehicle Twin

Visual subsystem representation.

---

### Driving State Analytics

Behavior analysis and state distribution.

---

### Health Timeline

Historical health trends.

---

### Anomaly Center

Investigation and root-cause analysis.

---

### Sensor Explorer

Telemetry relationships and correlations.

---

# Current Implementation Status

| Layer                          | Status         |
| ------------------------------ | -------------- |
| Preprocessing                  | ✅ Complete     |
| State Classification           | ✅ Complete     |
| State Analysis                 | ✅ Complete     |
| Feature Engineering Research   | ✅ Complete     |
| Correlation Analysis           | ✅ Complete     |
| Feature Importance Analysis    | ✅ Complete     |
| PCA Evaluation                 | ✅ Complete     |
| Isolation Forest Research      | ✅ Complete     |
| Production Feature Engineering | 🚧 In Progress |
| Production Anomaly Detector    | 🚧 In Progress |
| Health Score Engine            | 🚧 In Progress |
| FastAPI Integration            | ⏳ Planned      |
| Frontend Integration           | ⏳ Planned      |

---

# Future Evolution

The architecture has been intentionally designed so that offline batch processing and live streaming share the same pipeline.

Future architecture:

```text
ELM327
     │
     ▼
Live OBD-II Stream
     │
     ▼
Feature Engineering
     │
     ▼
Isolation Forest
     │
     ▼
Health Engine
     │
     ▼
Dashboard
```

This ensures that research performed on historical datasets can be reused directly in real-time vehicle monitoring deployments.
