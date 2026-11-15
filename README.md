# Parcel Station Space Optimization: ML-Enhanced SLAP Framework

## 1. System Architecture

This project explores a machine learning-enhanced approach to the **S ervice Level Agreement Problem (SLAP)** in parcel locker and parcel station operations.

The framework connects parcel arrival simulation, feature engineering, pickup probability prediction, and parcel-to-shelf assignment. Its central mechanism is to use predicted pickup probabilities to adjust the shelf allocation strategy.

The overall data flow is:

```text
Environmental Factors
        |
        v
Parcel Arrival Simulation
        |
        v
Parcel Data Generation
        |
        v
Feature Engineering
        |
        v
Pickup Probability Prediction
        |
        v
Prediction-Driven SLAP Optimization
        |
        v
Parcel-to-Shelf Assignment
        |
        v
Performance Evaluation
        |
        v
Feedback and Model Improvement
```

The system also includes an A/B testing framework to compare the baseline allocation strategy with the ML-enhanced strategy.

## 2. Environment-Driven Parcel Simulation

### 2.1 Environmental Factors

Parcel arrivals are influenced by multiple external factors. The simulation framework considers:

- Weather conditions
- Temperature
- Public holidays
- Weekdays and weekends
- Traffic conditions
- Special events

These factors are used to adjust the expected parcel arrival rate.

### 2.2 Parcel Arrival Model

The arrival rate is determined by the baseline arrival rate and several adjustment factors:

```text
lambda_t =
    lambda_base_t
    * M_daily
    * M_seasonal
    * E_t
```

Where:

| Variable | Description |
|---|---|
| `lambda_t` | Adjusted parcel arrival rate at time t |
| `lambda_base_t` | Baseline arrival rate |
| `M_daily` | Daily pattern adjustment |
| `M_seasonal` | Seasonal adjustment |
| `E_t` | Environmental adjustment factor |

Parcel arrivals follow a Poisson process. Inter-arrival times are modelled using an exponential distribution with the corresponding arrival rate.

Each generated parcel can contain attributes such as parcel size, arrival time, customer information, and environmental context.

## 3. Feature Engineering

Feature engineering transforms raw parcel and operational data into inputs for the pickup probability prediction model.

The data flow analysis describes five feature categories, covering approximately 53 potential features.

| Feature Category | Examples |
|---|---|
| Basic Parcel Features | Parcel size and parcel attributes |
| Temporal Features | Arrival time, hour, weekday, and peak periods |
| Environmental Features | Weather, temperature, holidays, and traffic |
| Historical Statistical Features | Historical pickup patterns and aggregated statistics |
| System-State Features | Shelf availability and current system conditions |

### 3.1 Feature Processing

The feature engineering pipeline includes:

1. Extracting features from parcel, environmental, and system-state data.
2. Handling and transforming input variables.
3. Standardizing numerical features using `StandardScaler`.
4. Analysing feature correlations and importance.
5. Selecting relevant features using a Top-K feature selection approach.

The documented default Top-K setting is 20 features.

## 4. Pickup Probability Prediction

### 4.1 Prediction Objective

The prediction module estimates the probability that a parcel will be collected within the next 24 hours.

The predicted probability is subsequently passed to the SLAP optimization module.

```text
Parcel Features
       |
       v
Feature Processing
       |
       v
ML Prediction Model
       |
       v
Predicted Pickup Probability
       |
       v
Adaptive SLAP Optimization
```

### 4.2 Model Design

The data flow analysis describes several potential model candidates:

- Random Forest
- Gradient Boosting
- XGBoost
- Logistic Regression
- Multi-Layer Perceptron (MLP)

It also describes an ensemble prediction approach.

For the final reported project results, the models are **Random Forest and Logistic Regression**. The broader candidate list represents the documented framework design and should not be interpreted as a claim that every candidate was included in the final evaluation.

### 4.3 Model Training and Evaluation

The documented training workflow includes:

- Batch-based model training
- Five-fold cross-validation
- Hyperparameter tuning
- Feature importance analysis
- Model performance monitoring
- Fallback mechanisms

Prediction performance can be evaluated using accuracy, precision, recall, F1-score, and AUC.

## 5. Prediction-Driven Adaptive SLAP Optimization

This is the central decision-making mechanism of the framework.

The optimization process combines four objectives:

1. Customer convenience
2. Employee workload
3. System efficiency
4. Future flexibility

The predicted pickup probability influences the relative importance of these objectives and adjusts the scores assigned to different shelf types.

### 5.1 Baseline SLAP: Fixed Objective Weights

The baseline strategy uses fixed weights:

| Objective | Weight |
|---|---:|
| Customer Convenience | 0.4 |
| Employee Workload | 0.3 |
| System Efficiency | 0.2 |
| Future Flexibility | 0.1 |
| **Total** | **1.0** |

The combined shelf score is calculated as:

```text
Baseline Score =
    0.4 * Customer Convenience
  + 0.3 * Employee Workload
  + 0.2 * System Efficiency
  + 0.1 * Future Flexibility
```

The available feasible shelves are evaluated, and the shelf with the highest combined score is selected.

### 5.2 Adaptive Objective Weights

In the ML-enhanced strategy, the predicted pickup probability determines the objective weights.

| Predicted Pickup Probability | Customer Convenience | Employee Workload | System Efficiency | Future Flexibility |
|---|---:|---:|---:|---:|
| High: > 0.8 | 0.5 | 0.2 | 0.2 | 0.1 |
| Medium: > 0.5 to 0.8 | 0.4 | 0.3 | 0.2 | 0.1 |
| Low: <= 0.5 | 0.3 | 0.3 | 0.3 | 0.1 |

The resulting objective weights are used to calculate the base shelf score:

```text
Adaptive Base Score =
    w_customer * Customer Convenience
  + w_employee * Employee Workload
  + w_efficiency * System Efficiency
  + w_flexibility * Future Flexibility
```

Here, each weight is selected according to the predicted pickup probability.

### 5.3 ML-Based Shelf Score Adjustment

In addition to adjusting objective weights, the framework applies a further score adjustment based on the parcel's predicted pickup probability and the shelf type.

**Premium shelves**

For parcels with a high predicted pickup probability:

```text
ML Bonus = 2.0 * Pickup Probability

Adjusted Score = Base Score + ML Bonus
```

For parcels with a predicted pickup probability of 0.8 or below:

```text
ML Penalty = -1.5 * (1 - Pickup Probability)

Adjusted Score = Base Score + ML Penalty
```

**Standard shelves**

```text
ML Adjustment = 0.5 * Pickup Probability

Adjusted Score = Base Score + ML Adjustment
```

This mechanism gives higher priority to premium shelf locations for parcels expected to be collected quickly, while reducing their attractiveness for parcels with lower predicted pickup probabilities.

### 5.4 Shelf Assignment

After calculating the adjusted scores:

1. Identify shelves that are compatible with the parcel size.
2. Exclude unavailable or infeasible shelves.
3. Calculate the adjusted score for each feasible shelf.
4. Select the shelf with the highest score.
5. Assign the parcel to the selected shelf.

The documented allocation approach uses a greedy selection heuristic.

## 6. A/B Testing Framework

The A/B testing framework compares two allocation strategies under the same general evaluation structure.

### 6.1 Control and Treatment Groups

| Component | Control Group | Treatment Group |
|---|---|---|
| Pickup Prediction | Rule-based prediction | ML-based prediction |
| SLAP Strategy | Fixed objective weights | Prediction-driven adaptive weights |
| Shelf Scoring | Baseline scoring | ML-adjusted scoring |
| Allocation | Baseline SLAP | ML-enhanced SLAP |

The control group represents the baseline SLAP strategy, while the treatment group uses ML predictions to influence the allocation decisions.

### 6.2 Group Assignment

The documented design uses a 50/50 traffic split.

Requests are assigned to a test group using a hash-based routing mechanism.

```text
Incoming Parcel
       |
       v
A/B Test Router
       |
       +----------------------+
       |                      |
       v                      v
Control Group           Treatment Group
       |                      |
       v                      v
Baseline SLAP           ML-Enhanced SLAP
       |                      |
       +----------+-----------+
                  |
                  v
          Performance Evaluation
```

### 6.3 Evaluation Metrics

The framework evaluates performance across several dimensions:

| Evaluation Dimension | Example Metrics |
|---|---|
| Prediction Performance | Accuracy, precision, recall, F1-score, AUC |
| Optimization Performance | Four-objective combined score |
| Operational Performance | Processing time and throughput |
| Business Performance | Customer convenience and operational efficiency |

Statistical validation can include:

- Sample size assessment
- Confidence level
- P-value
- Effect size
- Comparison of control and treatment group results

## 7. Feedback and Continuous Improvement

The framework also describes a feedback loop connecting actual parcel pickup outcomes with previous predictions.

```text
Predicted Pickup Probability
           |
           v
      Parcel Assignment
           |
           v
    Actual Pickup Outcome
           |
           v
   Prediction Comparison
           |
           v
      Feedback Data
           |
           v
      Model Update
           |
           +------> Updated Prediction Model
```

The purpose of this process is to use observed outcomes to improve future predictions.

The documented design includes batch-based updates, model monitoring, and mechanisms for handling changes in prediction performance.

## 8. Performance Monitoring

The monitoring framework covers four main areas:

| Area | Indicators |
|---|---|
| Prediction | Accuracy, recall, F1-score, AUC |
| Optimization | Objective scores and allocation performance |
| System | Throughput, response time, and stability |
| Business | Customer convenience and operational efficiency |

The monitoring workflow is:

```text
System Execution
       |
       v
Metric Calculation
       |
       v
Performance Monitoring
       |
       v
Alerting and Diagnosis
       |
       v
Potential System Adjustment
```

## 9. Core Module Reference

The following modules are associated with the documented data flow and system design.

| Module | Main Responsibility |
|---|---|
| `start.py` | Application entry point and execution modes |
| `config.py` | System and model configuration |
| `data_structures.py` | Core data structures, including parcels, shelves, and stations |
| `learning_module.py` | Machine learning functionality |
| `ml_lto_framework.py` | ML prediction and ML-enhanced optimization framework |
| `optimization_module.py` | Baseline SLAP optimization |
| `progressive_improvement_system.py` | A/B testing and progressive improvement mechanisms |
| `enhanced_dynamic_simulation.py` | Dynamic simulation |
| `performance_comparison.py` | Performance comparison and evaluation |
| `cost_analysis_tool.py` | Cost analysis |
| `simple_visualizer.py` | Visualization support |

The module descriptions above indicate their documented roles. The actual execution path and dependencies should be confirmed against the current source code.

- The documented A/B testing architecture distinguishes the baseline control group from the ML-enhanced treatment group.
- Numerical examples in the design document should not automatically be treated as independently validated experimental results.
- Reported performance improvements should be interpreted according to the corresponding experimental setup and evaluation results.
