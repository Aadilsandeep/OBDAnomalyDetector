# OBD-II Vehicle Health Monitoring & Anomaly Detection Platform

AutoAssist is an automotive analytics platform designed to transform raw OBD-II telemetry into actionable vehicle intelligence.

The system processes vehicle sensor data, classifies driving behavior, detects anomalous operating conditions, and generates vehicle health insights. The architecture is designed to evolve from offline analysis of historical datasets to real-time monitoring using live OBD-II data streams.

---

# Project Goal

Modern vehicles continuously generate large volumes of sensor data through the OBD-II interface.

AutoAssist aims to:

* Understand driving behavior
* Classify vehicle operating states
* Detect abnormal vehicle behavior
* Generate vehicle health indicators
* Support future real-time vehicle monitoring
* Provide explainable analytics for diagnostics and maintenance

---

# Current Project Status

## Phase 1 — Foundation & Data Platform ✅

Completed:

* Product Requirements Definition (PRD)
* System Architecture Design
* Dataset Analysis
* Frontend Dashboard Design
* Data Preprocessing Pipeline
* Session Merging Pipeline

---

## Phase 2 — Vehicle State Intelligence ✅

Completed:

* State Definitions
* Rule-Based State Classification Engine
* State Analysis Engine
* Session-Level State Analytics
* Aggressive Event Detection

Supported driving states:

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

---

## Phase 3 — ML Research & Model Selection ✅

Completed:

* Correlation Analysis
* Feature Engineering Research
* Feature Importance Analysis
* PCA Evaluation
* Isolation Forest Evaluation
* Model Selection

Key outcome:

* Isolation Forest selected as the production anomaly detection model.

---

## Phase 4 — Production ML Pipeline 🚧

Currently in progress:

* Production Feature Engineering Module
* Production Anomaly Detection Module
* Health Score Engine

---

# Dataset Information

| Attribute         | Value     |
| ----------------- | --------- |
| Vehicle           | Seat Leon |
| Sessions          | 81        |
| Raw Rows          | 2,693,824 |
| Clean Rows        | 2,693,087 |
| Retention Rate    | 99.97%    |
| Sensor Parameters | 11        |

---

# Available Sensors

The dataset contains the following OBD-II telemetry parameters:

* Engine RPM
* Vehicle Speed
* Mass Air Flow (MAF)
* Intake Manifold Pressure (MAP)
* Intake Air Temperature (IAT)
* Coolant Temperature
* Ambient Temperature
* Throttle Position
* Accelerator Pedal Position D
* Accelerator Pedal Position E
* Timestamp

Each record is associated with a driving session through:

```text
session_id
```

---

# System Architecture

```text
Raw OBD-II Data
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
FastAPI Backend
        │
        ▼
Frontend Dashboard
```

---

# Project Structure

```text
OBDAnomalyDetector
│
├── client/
│
├── server/
│   │
│   ├── preprocessing/
│   │   ├── loader.py
│   │   ├── standardizer.py
│   │   ├── cleaner.py
│   │   ├── merger.py
│   │   └── preprocess.py
│   │
│   ├── analytics/
│   │   ├── state_definitions.py
│   │   ├── state_classifier.py
│   │   └── state_analyzer.py
│   │
│   └── ml/
│       ├── feature_engineering.py
│       ├── anomaly_detector.py
│       └── health_score.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│
├── models/
│
├── docs/
│
└── README.md
```

---

# Data Processing Pipeline

The preprocessing layer transforms raw OBD-II logs into a unified master dataset.

### Loader

Responsibilities:

* CSV ingestion
* Dataset discovery
* Validation
* Error handling

### Standardizer

Converts raw sensor names into a canonical schema.

Example:

```text
Engine RPM [RPM]
        ↓
rpm
```

### Cleaner

Performs:

* Duplicate removal
* Missing value handling
* Timestamp validation
* Sensor range validation

### Merger

Combines all driving sessions into a single dataset while preserving session identity.

### Preprocessor

Orchestrates the complete preprocessing workflow.

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

# Driving State Classification

The platform uses a deterministic rule-based state machine to label vehicle behavior.

States:

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

The classifier currently uses:

* Speed
* RPM
* Speed Delta
* RPM Delta

to classify each telemetry sample.

Current state distribution:

| State        | Percentage |
| ------------ | ---------- |
| Cruising     | 60.08%     |
| Traffic      | 26.83%     |
| Idle         | 9.66%      |
| Acceleration | 1.74%      |
| Deceleration | 1.69%      |

---

# State Analysis

The state analysis engine generates:

* State counts
* State percentages
* Session-level statistics
* Dominant driving state
* Aggressive event counts

Example outputs:

* Dominant state across dataset
* Driving style characterization
* Session behavior summaries

---

# Feature Engineering

Current engineered features:

```text
speed_delta
rpm_delta
maf_delta
map_delta
throttle_delta
```

These features capture vehicle dynamics and behavioral changes between consecutive telemetry readings.

---

# Research Findings

## Correlation Analysis

Strong relationships identified:

```text
RPM ↔ Speed ≈ 0.83
MAF ↔ MAP ≈ 0.87
```

---

## Feature Importance Analysis

Most informative behavioral features:

```text
speed_delta
rpm_delta
```

These features consistently dominated feature importance rankings.

---

## PCA Evaluation

Principal Component Analysis was evaluated to determine whether dimensionality reduction was beneficial.

Results:

* 95% variance retained with 8 principal components
* Original feature space contained 10 features

Conclusion:

```text
PCA was not adopted.
```

The dimensionality reduction benefit did not justify the loss of interpretability.

---

# Anomaly Detection Research

Several approaches were evaluated.

## Why Not Supervised Learning?

The dataset primarily contains normal driving behavior.

Reliable anomaly labels do not exist.

Therefore:

```text
Supervised anomaly detection
was rejected.
```

---

## Selected Model

```text
Isolation Forest
```

Reasons:

* Unsupervised learning
* No anomaly labels required
* Effective on large telemetry datasets
* Learns normal driving behavior
* Suitable for real-world deployment

Research findings showed:

* Acceleration and Deceleration states exhibit the highest anomaly rates.
* Idle exhibits the lowest anomaly rate.
* Isolation Forest captures behavioral deviations rather than simple statistical outliers.

---

# Frontend Dashboard

Planned dashboard components include:

### Vehicle Health Score

Overall vehicle condition indicator.

### Digital Vehicle Twin

Subsystem health visualization.

### Health Timeline

Historical vehicle health trends.

### Driving State Analytics

State distribution and behavior analysis.

### Anomaly Center

Anomaly investigation dashboard.

### Sensor Explorer

Sensor correlation and telemetry analysis tools.

---

# Technology Stack

## Data Processing

* Python
* Pandas
* NumPy

## Machine Learning

* Scikit-Learn
* Isolation Forest
* PCA
* Random Forest (Research Only)

## Backend

* FastAPI

## Frontend

* React
* TypeScript
* Tailwind CSS
* Lovable

## Visualization

* Matplotlib
* Recharts

---

# Current Progress

| Module                      | Status         |
| --------------------------- | -------------- |
| Documentation               | ✅ Complete     |
| Dataset Analysis            | ✅ Complete     |
| Preprocessing Pipeline      | ✅ Complete     |
| Master Dataset Generation   | ✅ Complete     |
| State Classification Engine | ✅ Complete     |
| State Analysis Engine       | ✅ Complete     |
| Correlation Analysis        | ✅ Complete     |
| Feature Importance Analysis | ✅ Complete     |
| PCA Evaluation              | ✅ Complete     |
| Isolation Forest Research   | ✅ Complete     |
| Feature Engineering Module  | 🚧 In Progress |
| Anomaly Detection Module    | 🚧 In Progress |
| Health Score Engine         | 🚧 In Progress |
| FastAPI Integration         | ⏳ Planned      |
| Frontend Integration        | ⏳ Planned      |

---

# Future Roadmap

## Short-Term

* Production Feature Engineering Module
* Production Isolation Forest Pipeline
* Vehicle Health Score Engine

## Mid-Term

* FastAPI Backend
* Health APIs
* Session Analysis APIs

## Long-Term

* Live OBD-II Streaming
* ELM327 Integration
* Real-Time Vehicle Monitoring
* Predictive Maintenance
* Fleet Analytics

---

# Vision

AutoAssist is designed to evolve into a complete vehicle intelligence platform capable of transforming raw OBD-II telemetry into meaningful, explainable, and actionable automotive insights.

The long-term goal is to provide real-time vehicle monitoring, anomaly detection, health scoring, and predictive maintenance support through a scalable ML-powered architecture.
