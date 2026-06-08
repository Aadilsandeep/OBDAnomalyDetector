# ML Pipeline Report

## Project Overview

AutoAssist is an OBD-II based automotive anomaly detection platform designed to monitor vehicle telemetry, identify abnormal behavior, estimate vehicle health, and provide actionable diagnostics.

The system processes large-scale telemetry data collected from real-world driving sessions and applies machine learning techniques to identify unusual operating conditions.

---

# Dataset Overview

## Dataset Statistics

| Metric         | Value     |
| -------------- | --------- |
| Total Sessions | 81        |
| Raw Records    | 2,693,824 |
| Clean Records  | 2,693,087 |
| Retention Rate | 99.97%    |

## Available Sensors

* RPM
* Speed
* MAP
* MAF
* Coolant Temperature
* Intake Air Temperature
* Ambient Temperature
* Throttle Position
* Pedal Position D
* Pedal Position E
* Timestamp
* Session ID

---

# State Classification Research

## Supported States

* Idle
* Traffic
* Cruising
* Acceleration
* Deceleration

## Rationale

No labeled driving-state dataset was available.

A deterministic rule-based classifier was selected because it:

* Provides explainable classifications.
* Produces consistent outputs.
* Is simple to maintain.
* Can operate in real time.
* Creates useful context for anomaly analysis.

## Final State Distribution

| State        | Percentage |
| ------------ | ---------- |
| Cruising     | 60.08%     |
| Traffic      | 26.83%     |
| Idle         | 9.66%      |
| Acceleration | 1.74%      |
| Deceleration | 1.69%      |

---

# State Analysis Findings

The state analysis module generates:

* State counts
* State percentages
* Dominant state
* Session statistics
* Aggressive event counts

Findings indicate that the dataset is dominated by normal driving behavior, making it suitable for unsupervised anomaly detection.

---

# Feature Engineering Decisions

## Engineered Features

* speed_delta
* rpm_delta
* maf_delta
* map_delta
* throttle_delta

## Rationale

Raw sensor values provide vehicle state information.

Delta features provide behavioral information.

Behavioral changes are often more useful for anomaly detection than absolute values.

---

# Correlation Analysis

## Key Findings

| Feature Pair | Correlation |
| ------------ | ----------- |
| RPM ↔ Speed  | ~0.83       |
| MAF ↔ MAP    | ~0.87       |

These relationships indicate expected physical dependencies between vehicle systems.

No features were removed solely because of correlation.

Interpretability was prioritized over aggressive dimensionality reduction.

---

# Feature Importance Analysis

Random Forest was used strictly as a research tool.

## Key Findings

Most important features:

* speed_delta
* rpm_delta

These features contributed significantly more predictive information than other engineered features.

## Decision

Feature importance results were used for research validation only.

No manual feature elimination was performed.

---

# PCA Evaluation

## Objective

Evaluate whether dimensionality reduction improves the anomaly detection pipeline.

## Results

* Original Features: 10
* Components Required for 95% Variance: 8

## Conclusion

PCA provided limited dimensionality reduction benefits.

Advantages lost:

* Interpretability
* Diagnostic explainability
* Feature traceability

Decision:

PCA was rejected.

Original features will be retained.

---

# Isolation Forest Evaluation

## Objective

Evaluate suitability of Isolation Forest for automotive anomaly detection.

## Findings

Anomaly rate:

Approximately 1%.

State anomaly rates:

* Acceleration: highest
* Deceleration: high
* Traffic: moderate
* Cruising: low
* Idle: lowest

This behavior aligns with expected driving dynamics.

## Conclusion

Isolation Forest successfully identifies unusual operating behavior without requiring labeled anomalies.

---

# Model Selection Rationale

## Supervised Learning Rejected

Reasons:

* No reliable anomaly labels exist.
* Label generation would require extensive domain expertise.
* Label quality would be difficult to validate.

## Isolation Forest Selected

Reasons:

* Unsupervised.
* Scales to large datasets.
* Suitable for telemetry data.
* Compatible with future real-time streaming.
* Produces anomaly scores.

Decision:

Isolation Forest selected as the primary anomaly detection model.

---

# Production ML Pipeline

## Planned Modules

### feature_engineering.py

Responsibilities:

* Feature generation
* Feature validation
* Consistent inference pipeline

### anomaly_detector.py

Responsibilities:

* Model loading
* Anomaly scoring
* Anomaly flag generation

### health_score.py

Responsibilities:

* Health score calculation
* Risk categorization
* Insight generation

---

# Future Work

* Train production Isolation Forest model
* Save model artifacts
* Build FastAPI integration
* Create dashboard visualizations
* Develop explainability layer
* Add health scoring framework
* Support real-time OBD streaming

---

# Lessons Learned

* Behavioral features are highly informative.
* Explainability is critical for automotive diagnostics.
* PCA is not always beneficial.
* Research-driven decisions improve maintainability.
* Isolation Forest is a strong fit for unlabeled vehicle telemetry.
