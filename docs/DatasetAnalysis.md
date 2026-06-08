# Dataset Analysis

## Overview

This document summarizes the structure, quality, characteristics, and research findings derived from the OBD-II telemetry dataset used by AutoAssist.

The dataset forms the foundation for:

* Driving state classification
* Behavioral analysis
* Feature engineering
* Anomaly detection
* Vehicle health scoring

The purpose of this analysis is to understand the dataset before designing machine learning models.

---

# Dataset Summary

| Attribute      | Value     |
| -------------- | --------- |
| Vehicle        | Seat Leon |
| Sessions       | 81        |
| Raw Rows       | 2,693,824 |
| Clean Rows     | 2,693,087 |
| Rows Removed   | 737       |
| Retention Rate | 99.97%    |

---

# Available Sensors

The dataset contains the following OBD-II telemetry parameters.

| Sensor       | Description                  |
| ------------ | ---------------------------- |
| rpm          | Engine Speed                 |
| speed        | Vehicle Speed                |
| maf          | Mass Air Flow                |
| map          | Intake Manifold Pressure     |
| coolant_temp | Engine Coolant Temperature   |
| iat          | Intake Air Temperature       |
| ambient_temp | Ambient Air Temperature      |
| throttle_pos | Throttle Position            |
| pedal_d      | Accelerator Pedal Position D |
| pedal_e      | Accelerator Pedal Position E |
| timestamp    | Session Timestamp            |

Each record also contains:

```text
session_id
```

which identifies the driving session.

---

# Dataset Quality Assessment

## Duplicate Records

Result:

```text
0 duplicates
```

No duplicate telemetry rows were found.

---

## Invalid Sensor Values

Result:

```text
0 invalid records
```

All retained observations passed validation.

---

## Missing Values

Result:

```text
737 missing values
```

Given a dataset containing over 2.6 million observations, this represents a very small percentage of total data.

---

## Data Retention

```text
99.97%
```

of telemetry data was preserved after preprocessing.

This indicates high-quality source data.

---

# Driving State Distribution

The dataset was processed using the rule-based State Classification Engine.

---

## State Breakdown

| State        | Percentage |
| ------------ | ---------- |
| Cruising     | 60.08%     |
| Traffic      | 26.83%     |
| Idle         | 9.66%      |
| Acceleration | 1.74%      |
| Deceleration | 1.69%      |

---

## Interpretation

The dataset is dominated by:

```text
Cruising
```

behavior.

This indicates that most observations represent normal vehicle operation under stable driving conditions.

Acceleration and Deceleration states represent a much smaller portion of the dataset but contain valuable behavioral information.

---

# Feature Engineering Research

To capture behavioral changes, several derived features were created.

---

## Engineered Features

```text
speed_delta
rpm_delta
maf_delta
map_delta
throttle_delta
```

These represent row-to-row changes within a driving session.

---

## Purpose

Raw telemetry describes:

```text
Current vehicle state
```

while engineered features describe:

```text
Vehicle behavior changes
```

Behavioral changes are often more informative for anomaly detection than absolute sensor values.

---

# Correlation Analysis

A correlation study was performed to identify redundant features and relationships between sensors.

---

## Strong Correlations

| Features    | Correlation |
| ----------- | ----------- |
| RPM ↔ Speed | 0.83        |
| MAF ↔ MAP   | 0.87        |
| RPM ↔ MAF   | 0.77        |
| Speed ↔ MAF | 0.70        |
| Speed ↔ MAP | 0.66        |

---

## Interpretation

Several engine-related sensors describe similar physical phenomena.

Example:

```text
Higher Speed
      ↓
Higher RPM
      ↓
Higher Airflow
```

This naturally produces strong correlations.

---

## Design Implication

The dataset contains some feature redundancy.

This motivated PCA evaluation and feature selection research.

---

# Feature Importance Research

A Random Forest model was trained solely for feature importance analysis.

The model was not intended for anomaly detection.

---

## Candidate Features

```text
rpm
speed
maf
map
throttle_pos

rpm_delta
speed_delta
maf_delta
map_delta
throttle_delta
```

---

## Results

Most important features:

```text
speed_delta
rpm_delta
```

These features dominated feature importance rankings.

---

## Interpretation

Driving behavior is more strongly associated with:

```text
Change
```

than with:

```text
Absolute sensor values
```

This validates the use of behavioral features within the anomaly detection pipeline.

---

# PCA Evaluation

Principal Component Analysis was evaluated as a dimensionality reduction technique.

---

## Objective

Determine whether a lower-dimensional representation could preserve most information while reducing model complexity.

---

## Results

```text
10 Features
      ↓
8 Principal Components
      ↓
95% Variance Retained
```

---

## Interpretation

PCA successfully captured most variance.

However:

```text
10 → 8
```

represents only a modest reduction.

---

## Decision

PCA was not adopted for the production anomaly detector.

Reasons:

* Limited dimensionality reduction benefit
* Reduced interpretability
* Automotive diagnostics benefit from sensor-level explanations

---

# Anomaly Detection Research

The primary challenge of this dataset is the absence of anomaly labels.

---

## Problem

The dataset contains:

```text
Normal driving telemetry
```

but does not contain reliable labels for:

```text
Sensor failures
Mechanical faults
Engine problems
Vehicle anomalies
```

---

## Consequence

Traditional supervised models cannot be trained reliably.

---

# Model Selection Study

Several approaches were evaluated.

---

## Random Forest

Used for:

```text
Feature importance analysis
```

Not selected as the final anomaly detector.

---

## PCA

Used for:

```text
Dimensionality reduction evaluation
```

Not selected for production deployment.

---

## Isolation Forest

Selected as the production anomaly detection model.

---

## Why Isolation Forest?

Advantages:

* Unsupervised learning
* No anomaly labels required
* Effective on large datasets
* Learns normal operating behavior
* Suitable for future real-time monitoring

---

# Isolation Forest Findings

The model was trained on:

```text
rpm
speed
maf
map
throttle_pos

rpm_delta
speed_delta
maf_delta
map_delta
throttle_delta
```

---

## Research Findings

Anomaly rates by state:

| State        | Anomaly Rate |
| ------------ | ------------ |
| Acceleration | 5.53%        |
| Deceleration | 4.95%        |
| Traffic      | 1.11%        |
| Cruising     | 0.81%        |
| Idle         | 0.35%        |

---

## Interpretation

Acceleration and Deceleration exhibit the highest anomaly rates.

This suggests that unusual behavior is more likely to occur during dynamic vehicle operation than during steady-state driving.

---

# Key Conclusions

## Dataset Characteristics

* Large telemetry dataset
* High data quality
* Predominantly normal driving behavior

---

## Feature Findings

Most informative behavioral features:

```text
speed_delta
rpm_delta
```

---

## PCA Findings

PCA was evaluated but rejected due to limited reduction benefits.

---

## Model Findings

Isolation Forest was selected because:

* No anomaly labels exist
* Normal behavior dominates the dataset
* Unsupervised learning is more appropriate

---

# Impact on Project Architecture

The findings from this analysis directly influenced the final system design:

```text
Telemetry
      ↓
State Classification
      ↓
Feature Engineering
      ↓
Isolation Forest
      ↓
Health Score Engine
```

This architecture provides a scalable and explainable approach to automotive anomaly detection without requiring manually labeled fault data.

---

# Current Status

| Analysis                     | Status     |
| ---------------------------- | ---------- |
| Dataset Profiling            | ✅ Complete |
| Data Quality Assessment      | ✅ Complete |
| Correlation Analysis         | ✅ Complete |
| Feature Engineering Research | ✅ Complete |
| Feature Importance Study     | ✅ Complete |
| PCA Evaluation               | ✅ Complete |
| Isolation Forest Evaluation  | ✅ Complete |
| Model Selection              | ✅ Complete |
