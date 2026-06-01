# Dataset Analysis

## 1. Dataset Overview

### Vehicle Information

* **Vehicle Model:** Seat Leon
* **Dataset Type:** OBD-II Vehicle Telemetry Dataset
* **Data Format:** CSV
* **Total Files:** 81
* **Telemetry Nature:** Time-series sensor recordings collected during real-world driving sessions

### Sample Dataset Statistics

| Metric         | Value                    |
| -------------- | ------------------------ |
| Rows           | 46,349                   |
| Columns        | 11                       |
| Data Type      | Multivariate Time-Series |
| Missing Values | Less than 0.02%          |

### Objective of Analysis

The purpose of this analysis is to evaluate the suitability of the dataset for:

* Vehicle operational state classification
* Anomaly detection
* Vehicle health scoring
* Sensor relationship analysis
* Future predictive maintenance applications

---

## 2. Available Sensors

The dataset contains the following OBD-II telemetry parameters:

| Sensor                                  | Description                                   |
| --------------------------------------- | --------------------------------------------- |
| Time                                    | Timestamp of sensor reading                   |
| Engine Coolant Temperature              | Engine cooling system temperature             |
| Intake Manifold Absolute Pressure (MAP) | Intake manifold pressure                      |
| Engine RPM                              | Engine rotational speed                       |
| Vehicle Speed Sensor                    | Vehicle speed                                 |
| Intake Air Temperature                  | Temperature of incoming air                   |
| Mass Air Flow (MAF)                     | Air entering the engine                       |
| Absolute Throttle Position              | Throttle opening percentage                   |
| Ambient Air Temperature                 | External air temperature                      |
| Accelerator Pedal Position D            | Accelerator pedal position                    |
| Accelerator Pedal Position E            | Accelerator pedal position (redundant sensor) |

---

## 3. Data Quality Assessment

### Missing Value Analysis

The dataset exhibits exceptionally low missing data percentages.

| Sensor            | Missing Percentage |
| ----------------- | ------------------ |
| Engine RPM        | 0.004%             |
| Vehicle Speed     | 0.006%             |
| MAF               | 0.011%             |
| Throttle Position | 0.013%             |
| Pedal Position D  | 0.017%             |
| Pedal Position E  | 0.019%             |

### Assessment

* Missing values are negligible.
* No advanced imputation strategy is required.
* Rows containing missing values can be safely removed or forward-filled during preprocessing.
* Dataset quality is suitable for machine learning applications.

---

## 4. Sensor Variability Analysis

Sensor variability indicates the amount of information each feature contributes.

| Sensor                   | Unique Values |
| ------------------------ | ------------- |
| Engine RPM               | 1221          |
| Mass Air Flow (MAF)      | 1208          |
| Intake Manifold Pressure | 147           |
| Vehicle Speed            | 127           |
| Pedal Position D         | 122           |
| Pedal Position E         | 124           |
| Coolant Temperature      | 66            |

### Assessment

The dataset contains high-resolution telemetry with significant variation across major engine and driving parameters. This provides sufficient information for feature engineering and anomaly detection.

---

## 5. Driving Behaviour Analysis

### Vehicle Speed Characteristics

Observed speed range:

```text
0 km/h to 126 km/h
```

The speed profile indicates multiple driving environments:

* Vehicle idle periods
* Stop-and-go traffic conditions
* Urban driving
* Moderate-speed cruising
* Highway driving
* Acceleration and deceleration events

### Engine RPM Characteristics

Observed RPM range:

```text
0 RPM to 2689 RPM
```

RPM behaviour demonstrates:

* Idle operation around 800–1000 RPM
* Stable cruising between 1400–1800 RPM
* Multiple acceleration events above 2200 RPM
* Engine-off or logging-transition periods represented by 0 RPM values

### Assessment

The dataset captures realistic driving behaviour and contains sufficient diversity for operational state classification.

---

## 6. Sensor Relationship Analysis

Correlation analysis was performed to understand relationships between key vehicle parameters.

### Strong Positive Correlations

| Sensor Pair       | Correlation |
| ----------------- | ----------- |
| MAP ↔ MAF         | 0.863       |
| RPM ↔ Speed       | 0.742       |
| RPM ↔ MAF         | 0.741       |
| Speed ↔ MAF       | 0.649       |
| Pedal D ↔ Pedal E | 0.983       |

### Key Observations

#### MAP and MAF

A strong relationship exists between intake manifold pressure and airflow, indicating realistic engine breathing characteristics.

#### RPM and Speed

Engine RPM and vehicle speed move together as expected during driving operations.

#### RPM and MAF

Higher engine speeds correspond to increased airflow through the engine.

#### Pedal Position Sensors

Accelerator Pedal Position D and E are nearly identical and may be treated as redundant features during model development.

#### Throttle Position

Throttle Position exhibits weak correlation with most other sensors and requires further investigation during feature engineering.

### Assessment

The dataset demonstrates realistic automotive sensor relationships and provides a strong foundation for anomaly detection and health assessment.

---

## 7. Suitability for Project Objectives

### Operational State Classification

**Status:** Suitable

Available sensors support classification of:

* Idle
* Cruising
* Acceleration
* Deceleration
* Stop-and-go traffic

---

### Anomaly Detection

**Status:** Suitable

Available telemetry contains sufficient variability and inter-sensor relationships to support unsupervised anomaly detection techniques such as Isolation Forest.

---

### Vehicle Health Scoring

**Status:** Suitable

Health scoring can be derived using:

* Anomaly frequency
* Anomaly severity
* Sensor stability
* Driving behaviour consistency

---

### Sensor Relationship Explorer

**Status:** Suitable

Strong correlations between major sensors enable development of interactive relationship visualizations.

---

### Vehicle Digital Twin

**Status:** Partially Suitable

The dataset supports representation of:

* Engine subsystem
* Airflow subsystem
* Cooling subsystem

However, additional sensors such as fuel trim, battery voltage, and oil temperature would improve digital twin fidelity.

---

## 8. Limitations

The dataset does not contain:

* Diagnostic Trouble Codes (DTCs)
* Fuel Trim Data
* Battery Voltage
* Oil Temperature
* Fuel Pressure
* Emissions System Data

As a result, the system focuses primarily on behavioural and telemetry-based health assessment rather than fault-code diagnostics.

---

## 9. Final Assessment

### Dataset Quality

**9/10**

### Sensor Coverage

**8.5/10**

### Anomaly Detection Suitability

**9/10**

### Health Scoring Suitability

**8/10**

### Educational and Engineering Value

**10/10**

### Overall Conclusion

The dataset is well-suited for the AutoAssist project. It provides high-quality multivariate OBD-II telemetry with realistic driving behaviour, strong inter-sensor relationships, minimal missing data, and sufficient variability to support operational state classification, anomaly detection, vehicle health scoring, and future predictive maintenance extensions.
