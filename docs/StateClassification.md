# State Classification System

## Overview

The State Classification System is responsible for converting raw OBD-II telemetry into meaningful vehicle operating states.

Rather than analyzing millions of sensor readings directly, AutoAssist first determines the behavioral context of each observation.

This layer provides the foundation for:

* Driving behavior analysis
* Aggressive event detection
* State analytics
* Vehicle health scoring
* Context-aware anomaly detection

---

# Objective

The primary goal of the classifier is to answer:

```text
What is the vehicle doing right now?
```

Every telemetry record is assigned exactly one operating state.

---

# Why State Classification?

Raw telemetry provides sensor values but not behavioral context.

Example:

```text
RPM = 2200
Speed = 60
```

This tells us the vehicle condition but not the driving behavior.

State classification converts sensor data into human-understandable operating modes.

Example:

```text
Cruising
```

This context becomes useful for:

* Driver behavior analysis
* Session summaries
* Anomaly interpretation
* Health score generation

---

# Supported States

The classifier currently supports five operating states.

---

## Idle

### Description

Vehicle is stationary with minimal engine activity.

### Characteristics

```text
Speed ≈ 0
Low RPM
```

### Typical Scenario

* Engine idling
* Vehicle stopped at parking
* Waiting at traffic lights

---

## Traffic

### Description

Default low-speed driving state.

### Characteristics

```text
Moderate RPM
Low speed
No strong acceleration
No strong deceleration
```

### Typical Scenario

* Urban driving
* Stop-and-go traffic
* Congested roads

---

## Cruising

### Description

Vehicle is moving steadily at road speed.

### Characteristics

```text
Stable speed
Stable RPM
Minimal change
```

### Typical Scenario

* Highway driving
* Open roads
* Consistent travel speed

---

## Acceleration

### Description

Vehicle is increasing speed and engine load.

### Characteristics

```text
Positive speed change
Positive RPM change
```

### Typical Scenario

* Overtaking
* Merging into traffic
* Pulling away from a stop

---

## Deceleration

### Description

Vehicle is reducing speed or engine load.

### Characteristics

```text
Negative speed change
Negative RPM change
```

### Typical Scenario

* Braking
* Engine braking
* Approaching a stop

---

# Classification Inputs

The classifier uses both raw and derived telemetry features.

---

## Raw Features

```text
speed
rpm
```

---

## Derived Features

```text
speed_delta
rpm_delta
```

These values are calculated using:

```python
speed.diff()
rpm.diff()
```

within each driving session.

---

# Derived Feature Generation

Before classification begins, the system generates behavioral features.

## Speed Delta

```text
Current Speed
      -
Previous Speed
```

Measures acceleration or deceleration.

---

## RPM Delta

```text
Current RPM
      -
Previous RPM
```

Measures engine load changes.

---

# Classification Strategy

The classifier follows a deterministic rule-based approach.

Machine learning is intentionally not used.

---

## Why Not Machine Learning?

A supervised classifier would require:

```text
Millions of manually labeled rows
```

which do not exist.

A rule-based system provides:

* Full explainability
* Deterministic behavior
* Easy validation
* Easy threshold tuning

---

# State Priority System

States are assigned using a priority hierarchy.

Classification order:

```text
Traffic (default)
        ↓
Cruising
        ↓
Idle
        ↓
Deceleration
        ↓
Acceleration
```

Higher-priority states overwrite lower-priority states.

---

## Why Priority Matters

Some telemetry samples satisfy multiple rules.

Example:

```text
Speed = 0
RPM = 150
RPM Delta = -700
```

This sample may resemble:

* Idle
* Deceleration

Priority ordering ensures a deterministic result.

---

# State Distribution

The classifier was evaluated on the complete dataset.

---

## Dataset Distribution

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

indicating that most telemetry was collected during steady driving conditions.

Acceleration and Deceleration represent a small but important portion of the dataset.

These states often contain the strongest behavioral signals.

---

# Design Decisions

## Decision 1 — Deterministic Rules

Chosen because:

* Explainable
* Reproducible
* No training required

---

## Decision 2 — Delta Features

The classifier relies on:

```text
speed_delta
rpm_delta
```

because driving behavior is defined by change rather than absolute values.

Example:

```text
Speed = 60
```

does not indicate behavior.

Example:

```text
Speed Delta = +8
```

indicates acceleration.

---

## Decision 3 — State Context Before ML

State classification occurs before anomaly detection.

Pipeline:

```text
Telemetry
     ↓
State Classification
     ↓
Anomaly Detection
```

This allows future anomaly models to incorporate behavioral context.

---

# Relationship to Other Components

The classifier feeds directly into:

---

## State Analyzer

Provides:

* State counts
* State percentages
* Dominant state
* Session analytics

---

## Health Score Engine

Future health scores may incorporate:

```text
Aggressive acceleration frequency
Aggressive deceleration frequency
```

---

## Anomaly Detection

Isolation Forest research showed:

```text
Acceleration
```

and

```text
Deceleration
```

contain the highest anomaly rates.

State context therefore improves anomaly interpretation.

---

# Future Enhancements

Potential future states include:

```text
Highway
City Driving
Aggressive Driving
Engine Braking
Coasting
```

The architecture allows new states to be added with minimal changes.

---

# Current Status

| Component                   | Status     |
| --------------------------- | ---------- |
| State Definitions           | ✅ Complete |
| Derived Features            | ✅ Complete |
| State Classifier            | ✅ Complete |
| State Distribution Analysis | ✅ Complete |
| Session Analytics           | ✅ Complete |
| Future State Expansion      | ⏳ Planned  |

---

# Summary

The State Classification System converts raw OBD-II telemetry into interpretable vehicle operating states.

By combining sensor values with behavioral deltas, the system provides the contextual foundation required for downstream analytics, anomaly detection, and vehicle health assessment.

It is one of the core intelligence layers within the AutoAssist platform and serves as the bridge between raw telemetry and higher-level automotive insights.
