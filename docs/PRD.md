# Product Requirements Document (PRD)

# AutoAssist – OBD-II Vehicle Health Monitoring & Anomaly Detection Platform

## Version

2.0

## Status

Active Development

---

# Executive Summary

AutoAssist is an automotive analytics platform that transforms raw OBD-II telemetry into actionable vehicle intelligence.

The platform is designed to:

* Understand vehicle behavior
* Classify driving states
* Detect abnormal operating conditions
* Generate vehicle health insights
* Support future real-time vehicle monitoring

The long-term objective is to provide drivers, fleet operators, and automotive technicians with explainable vehicle health assessments derived directly from telemetry data.

---

# Problem Statement

Modern vehicles generate thousands of sensor readings through the OBD-II interface.

However, raw telemetry is difficult to interpret because:

* Sensor values lack behavioral context
* Early degradation may occur before diagnostic trouble codes (DTCs) appear
* Large datasets are difficult to analyze manually
* Existing OBD applications focus primarily on visualization rather than intelligence

There is a need for a system that can transform telemetry into meaningful diagnostics and health insights.

---

# Vision

Create a vehicle intelligence platform capable of:

```text
Telemetry
     ↓
Behavior Understanding
     ↓
Anomaly Detection
     ↓
Health Assessment
     ↓
Actionable Insights
```

The platform should evolve from offline analysis into real-time vehicle monitoring.

---

# Product Goals

## Primary Goals

* Classify driving behavior
* Detect anomalous operating patterns
* Generate vehicle health scores
* Provide explainable analytics
* Support future live OBD-II streaming

---

## Secondary Goals

* Enable dashboard-based monitoring
* Support future predictive maintenance
* Create reusable ML infrastructure
* Support multiple vehicle types

---

# Target Users

## Vehicle Owners

Need:

* Vehicle health visibility
* Driving behavior insights
* Early warning indicators

---

## Automotive Enthusiasts

Need:

* Telemetry exploration
* Performance analysis
* Vehicle behavior understanding

---

## Technicians

Need:

* Diagnostic assistance
* Health indicators
* Behavioral analytics

---

## Fleet Operators

Future target audience.

Need:

* Fleet health monitoring
* Risk detection
* Maintenance prioritization

---

# Dataset

Current development dataset:

| Attribute      | Value     |
| -------------- | --------- |
| Vehicle        | Seat Leon |
| Sessions       | 81        |
| Raw Rows       | 2,693,824 |
| Clean Rows     | 2,693,087 |
| Retention Rate | 99.97%    |

---

## Available Sensors

* RPM
* Speed
* MAF
* MAP
* Coolant Temperature
* Intake Air Temperature
* Ambient Temperature
* Throttle Position
* Pedal Position D
* Pedal Position E

---

# Functional Requirements

---

## FR-1 Data Ingestion

The system shall:

* Load OBD-II CSV datasets
* Validate input files
* Support multiple sessions
* Handle malformed files gracefully

---

## FR-2 Data Standardization

The system shall:

* Convert raw column names into a canonical schema
* Support multiple OBD-II data formats

---

## FR-3 Data Cleaning

The system shall:

* Remove duplicates
* Handle missing values
* Validate sensor ranges
* Parse timestamps

---

## FR-4 Session Management

The system shall:

* Preserve session identity
* Support fleet-level analytics
* Generate a unified master dataset

---

## FR-5 Driving State Classification

The system shall classify every telemetry record into one of:

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

The classifier shall be deterministic and explainable.

---

## FR-6 State Analytics

The system shall generate:

* State counts
* State percentages
* Dominant state
* Aggressive event counts
* Session summaries

---

## FR-7 Feature Engineering

The system shall generate behavioral features including:

```text
speed_delta
rpm_delta
maf_delta
map_delta
throttle_delta
```

These features shall be used by downstream analytics and machine learning components.

---

## FR-8 Anomaly Detection

The system shall identify unusual vehicle behavior patterns.

---

### Research Outcome

Initial project assumptions considered supervised machine learning approaches.

Research demonstrated:

* Reliable anomaly labels do not exist
* Dataset is dominated by normal driving behavior
* Supervised anomaly detection is unsuitable

---

### Selected Approach

The anomaly detection system shall use:

```text
Isolation Forest
```

as the baseline production anomaly detector.

Reasons:

* Unsupervised learning
* No anomaly labels required
* Learns normal vehicle behavior
* Suitable for large telemetry datasets
* Compatible with future streaming systems

---

### Outputs

The anomaly detector shall produce:

```text
anomaly_score

anomaly_flag
```

for every telemetry observation.

---

## FR-9 Vehicle Health Score

The system shall generate a vehicle health score.

---

### Inputs

Future inputs may include:

* Anomaly density
* Aggressive events
* State distributions
* Session statistics

---

### Output

```text
Vehicle Health Score
```

Range:

```text
0–100
```

Where:

```text
100 = Excellent
0 = Critical
```

---

## FR-10 Dashboard Integration

The platform shall support a frontend dashboard providing:

* Vehicle Health Score
* Driving State Analytics
* Health Timeline
* Digital Vehicle Twin
* Anomaly Center
* Sensor Explorer

---

# Non-Functional Requirements

## Performance

The system shall process:

```text
2.6+ million telemetry records
```

without excessive memory usage.

---

## Scalability

The architecture shall support:

* Larger datasets
* Multiple vehicles
* Fleet-scale analytics

---

## Explainability

All major decisions shall be explainable.

Examples:

* State assignments
* Health score calculations
* Anomaly detections

---

## Maintainability

The codebase shall:

* Use modular design
* Follow single responsibility principles
* Use typed interfaces
* Use structured reporting

---

## Future Compatibility

The architecture shall support:

* FastAPI deployment
* Real-time telemetry streams
* ELM327 integration
* Predictive maintenance models

---

# System Architecture

```text
Raw OBD-II Data
        ↓
Preprocessing
        ↓
State Classification
        ↓
State Analysis
        ↓
Feature Engineering
        ↓
Isolation Forest
        ↓
Health Score Engine
        ↓
FastAPI
        ↓
Dashboard
```

---

# Success Criteria

The project will be considered successful if it can:

### Data Layer

* Process raw OBD-II telemetry reliably
* Generate a clean master dataset

### Intelligence Layer

* Classify driving states accurately
* Generate meaningful session analytics

### ML Layer

* Detect unusual behavior patterns
* Produce anomaly scores
* Generate health indicators

### Platform Layer

* Expose functionality through APIs
* Visualize results through the dashboard

---

# Current Status

## Completed

* Dataset Analysis
* Architecture Design
* Preprocessing Pipeline
* State Classification Engine
* State Analysis Engine
* Feature Engineering Research
* Correlation Analysis
* Feature Importance Analysis
* PCA Evaluation
* Isolation Forest Research

---

## In Progress

* Production Feature Engineering Module
* Production Anomaly Detection Module
* Health Score Engine

---

## Planned

* Model Training
* Artifact Generation
* FastAPI Integration
* Dashboard Integration
* Real-Time OBD-II Monitoring

---

# Long-Term Vision

AutoAssist is designed to evolve into a complete automotive intelligence platform capable of monitoring live vehicle telemetry, detecting abnormal behavior, generating explainable health insights, and supporting predictive maintenance through machine learning-driven analytics.
