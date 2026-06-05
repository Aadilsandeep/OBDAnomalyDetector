# OBD-II Vehicle Health Monitoring & Anomaly Detection Platform

AutoAssist is an automotive analytics platform that processes OBD-II telemetry data to understand vehicle behavior, classify driving states, detect anomalies, and generate vehicle health insights.

The project is being developed as a modular pipeline that can evolve from offline dataset analysis to real-time vehicle monitoring using live OBD-II data streams.

---

# 🎯 Project Goal

Modern vehicles generate thousands of sensor readings every minute through the OBD-II interface.

AutoAssist aims to transform raw telemetry into meaningful insights by:

* Understanding driving behavior
* Detecting abnormal operating conditions
* Generating vehicle health indicators
* Providing intuitive visual analytics
* Supporting future real-time OBD-II monitoring

---

# 🏗 Current Project Status

## Phase 0 – Foundation & Data Platform ✅

Completed:

* Project Planning
* Product Requirements Definition (PRD)
* System Architecture Design
* Dataset Analysis
* Frontend Dashboard Design
* Data Preprocessing Pipeline
* Session Merging Pipeline
* State Classification Design

---

# 📊 Dataset Information

| Attribute      | Value                |
| -------------- | -------------------- |
| Vehicle        | Seat Leon            |
| Files          | 81 CSV Sessions      |
| Total Rows     | 2,693,824            |
| Clean Rows     | 2,693,087            |
| Retention Rate | 99.97%               |
| Sensors        | 11 OBD-II Parameters |

### Available Sensors

* Engine Coolant Temperature
* Intake Manifold Pressure (MAP)
* Engine RPM
* Vehicle Speed
* Intake Air Temperature
* Mass Air Flow (MAF)
* Throttle Position
* Ambient Air Temperature
* Accelerator Pedal Position D
* Accelerator Pedal Position E

---

# ⚙️ System Architecture

```text
Raw OBD-II Data
        │
        ▼
Preprocessing Layer
        │
        ▼
State Classification Layer
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

# 📂 Project Structure

```text
OBDAnomalyDetector
│
├── client/
│   └── Frontend Dashboard (Lovable)
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
│   └── analytics/
│       ├── state_definitions.py
│       ├── state_classifier.py
│       └── state_analyzer.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── docs/
│
├── notebooks/
│
├── models/
│
└── README.md
```

---

# 🔄 Data Processing Pipeline

The preprocessing system transforms raw OBD-II logs into a clean master dataset.

### Loader

Responsible for:

* Loading individual CSV files
* Loading complete datasets
* Error handling and validation

### Standardizer

Converts raw OBD-II column names into a canonical schema.

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
* Timestamp parsing
* Sensor range validation

### Merger

Combines all driving sessions into a single master dataset while preserving session identity using:

```text
session_id
```

### Preprocessor

Orchestrates the entire pipeline:

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

# 🚦 Driving State Classification

AutoAssist uses a rule-based state machine to classify vehicle operation.

Current states:

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

The classifier uses:

* Speed
* RPM
* Speed Delta
* RPM Delta

to determine the operating state of each telemetry record.

---

# 🎨 Frontend Dashboard

The frontend has been designed as a modern automotive analytics platform.

Key dashboard components:

### Vehicle Health Score

Overall vehicle condition indicator.

### Vehicle Digital Twin

Blueprint-style vehicle visualization showing subsystem health.

### Health Timeline

Historical health trend visualization.

### Driving State Visualization

Distribution of:

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

### Anomaly Center

Future anomaly investigation dashboard.

### Sensor Explorer

Interactive sensor relationship and correlation analysis.

---

# 🚀 Planned Features

## Phase 1

Vehicle Intelligence Layer

* State Classification Engine
* Driving Pattern Analysis
* State Analytics

## Phase 2

Feature Engineering Layer

* Rolling Statistics
* Temporal Features
* Engine Behavior Indicators
* PCA Evaluation
* Feature Selection

## Phase 3

Machine Learning Layer

* Isolation Forest
* Anomaly Detection
* Explainable Insights

## Phase 4

Vehicle Health Engine

* Health Score Generation
* Risk Assessment
* Health Timeline

## Phase 5

Backend Integration

* FastAPI
* Analysis Endpoints
* Report Generation

## Phase 6

Frontend Integration

* Real Data Visualization
* Interactive Analytics
* Dashboard Integration

## Phase 7

Future Expansion

* Live OBD-II Streaming
* ELM327 Integration
* Real-Time Monitoring
* Predictive Maintenance

---

# 🛠 Technology Stack

### Data Processing

* Python
* Pandas
* NumPy

### Machine Learning (Planned)

* Scikit-Learn
* Isolation Forest
* PCA
* Random Forest

### Backend (Planned)

* FastAPI

### Frontend

* React
* TypeScript
* Tailwind CSS
* Lovable

### Visualization

* Recharts
* Interactive Dashboards

---

# 📈 Current Progress

| Module                      | Status         |
| --------------------------- | -------------- |
| Documentation               | ✅ Complete     |
| Dataset Analysis            | ✅ Complete     |
| Frontend Design             | ✅ Complete     |
| Preprocessing Pipeline      | ✅ Complete     |
| Master Dataset Generation   | ✅ Complete     |
| State Classification Design | ✅ Complete     |
| State Classification Engine | 🚧 In Progress |
| Feature Engineering         | ⏳ Planned      |
| Machine Learning            | ⏳ Planned      |
| FastAPI Integration         | ⏳ Planned      |
| Frontend Integration        | ⏳ Planned      |

---

# 📌 Vision

AutoAssist is designed to evolve from an offline OBD-II analytics platform into a real-time vehicle intelligence system capable of monitoring live telemetry streams, detecting anomalies, and providing actionable vehicle health insights.
