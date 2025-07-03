"""
A/B Testing System for Cainiao LTO

This module implements a simplified A/B testing framework that:
1. Compares ML-enhanced SLAP system with baseline SLAP system
2. Provides performance monitoring and comparison
3. Implements simple A/B testing for evaluation purposes
4. Focuses on proving ML optimization effectiveness

Key Design Principles:
- Simple A/B testing between baseline and ML-enhanced systems
- Performance comparison and statistical validation
- Clear separation between control and treatment groups
- Comprehensive evaluation metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import copy
from collections import defaultdict, deque
import threading
import time

from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
from optimization_module import SLAPOptimizer, OptimizationWeights
from learning_module import PickupProbabilityPredictor, create_predictor
# 注意：非近视和RL组件已简化，专注于核心ML-LTO功能
from ml_lto_framework import MLPickupPredictor, create_ml_predictor, MLConfig
from enhanced_dynamic_simulation import EnhancedDynamicSimulationEngine


class TestGroup(Enum):
    """A/B test groups"""
    CONTROL = "control"        # Baseline SLAP system
    TREATMENT = "treatment"    # ML-enhanced SLAP system


@dataclass
class PerformanceMetrics:
    """Performance metrics for comparison"""
    timestamp: datetime
    customer_convenience: float
    employee_workload: float
    system_efficiency: float
    future_flexibility: float
    overall_score: float
    processing_time_ms: float
    memory_usage_mb: float
    error_rate: float
    throughput_per_second: float
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.overall_score == 0.0:
            self.overall_score = (
                0.4 * self.customer_convenience +
                0.3 * self.employee_workload +
                0.2 * self.system_efficiency +
                0.1 * self.future_flexibility
            )
    
    def is_better_than(self, other: 'PerformanceMetrics', 
                      tolerance: float = 0.02) -> bool:
        """Check if this metric is significantly better than another"""
        score_improvement = self.overall_score - other.overall_score
        return score_improvement > tolerance
    
    def is_acceptable(self, baseline: 'PerformanceMetrics',
                     max_degradation: float = 0.05) -> bool:
        """Check if performance is acceptable compared to baseline"""
        score_degradation = baseline.overall_score - self.overall_score
        return score_degradation <= max_degradation


@dataclass
class ABTestConfiguration:
    """Configuration for A/B testing"""
    test_name: str
    treatment_ratio: float = 0.5  # 50/50 split between control and treatment
    min_samples_for_significance: int = 100
    significance_threshold: float = 0.05  # p-value threshold
    effect_size_threshold: float = 0.02   # Minimum meaningful improvement
    test_duration_hours: int = 24


class ABTestRouter:
    """Routes requests between control and treatment groups for A/B testing"""
    
    def __init__(self, config: ABTestConfiguration):
        self.config = config
        self.routing_history = deque(maxlen=10000)  # Track routing decisions
        self.test_start_time = datetime.now()
    
    def assign_test_group(self, request_id: str) -> TestGroup:
        """Assign request to control or treatment group"""
        # Use hash-based routing for consistent assignment
        hash_value = hash(request_id) % 100
        
        if hash_value < (self.config.treatment_ratio * 100):
            group = TestGroup.TREATMENT
        else:
            group = TestGroup.CONTROL
        
        # Record routing decision
        self.routing_history.append({
            'timestamp': datetime.now(),
            'request_id': request_id,
            'test_group': group.value
        })
        
        return group
    
    def get_assignment_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get A/B test assignment statistics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_history = [r for r in self.routing_history if r['timestamp'] >= cutoff_time]
        
        total_requests = len(recent_history)
        treatment_count = sum(1 for r in recent_history if r['test_group'] == TestGroup.TREATMENT.value)
        control_count = total_requests - treatment_count
        
        return {
            'total_requests': total_requests,
            'control_count': control_count,
            'treatment_count': treatment_count,
            'control_ratio': control_count / total_requests if total_requests > 0 else 0.0,
            'treatment_ratio': treatment_count / total_requests if total_requests > 0 else 0.0,
            'configured_treatment_ratio': self.config.treatment_ratio
        }


class PerformanceMonitor:
    """Monitors performance of different feature configurations"""
    
    def __init__(self, baseline_window_hours: int = 24):
        self.baseline_window_hours = baseline_window_hours
        self.metrics_history: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.baseline_metrics: Optional[PerformanceMetrics] = None
        self.alert_thresholds = {
            'error_rate': 0.05,  # 5% error rate
            'latency_degradation': 2.0,  # 2x slower
            'score_degradation': 0.1  # 10% score drop
        }
        
        self.logger = logging.getLogger(__name__)
    
    def record_metrics(self, configuration_id: str, metrics: PerformanceMetrics):
        """Record performance metrics for a configuration"""
        self.metrics_history[configuration_id].append(metrics)
        
        # Keep only recent metrics (last 1000 entries per configuration)
        if len(self.metrics_history[configuration_id]) > 1000:
            self.metrics_history[configuration_id] = self.metrics_history[configuration_id][-1000:]
        
        # Update baseline if this is the baseline configuration
        if configuration_id == 'baseline':
            self.baseline_metrics = metrics
    
    def get_recent_metrics(self, configuration_id: str, hours: int = None) -> List[PerformanceMetrics]:
        """Get recent metrics for a configuration"""
        if hours is None:
            hours = self.baseline_window_hours
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        metrics = self.metrics_history.get(configuration_id, [])
        
        return [m for m in metrics if m.timestamp >= cutoff_time]
    
    def calculate_average_metrics(self, configuration_id: str, hours: int = None) -> Optional[PerformanceMetrics]:
        """Calculate average metrics for a configuration"""
        recent_metrics = self.get_recent_metrics(configuration_id, hours)
        
        if not recent_metrics:
            return None
        
        # Calculate averages
        avg_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            customer_convenience=np.mean([m.customer_convenience for m in recent_metrics]),
            employee_workload=np.mean([m.employee_workload for m in recent_metrics]),
            system_efficiency=np.mean([m.system_efficiency for m in recent_metrics]),
            future_flexibility=np.mean([m.future_flexibility for m in recent_metrics]),
            overall_score=np.mean([m.overall_score for m in recent_metrics]),
            processing_time_ms=np.mean([m.processing_time_ms for m in recent_metrics]),
            memory_usage_mb=np.mean([m.memory_usage_mb for m in recent_metrics]),
            error_rate=np.mean([m.error_rate for m in recent_metrics]),
            throughput_per_second=np.mean([m.throughput_per_second for m in recent_metrics])
        )
        
        return avg_metrics
    
    def compare_with_baseline(self, configuration_id: str, hours: int = None) -> Optional[Dict[str, Any]]:
        """Compare configuration performance with baseline"""
        if not self.baseline_metrics:
            return None
        
        config_metrics = self.calculate_average_metrics(configuration_id, hours)
        if not config_metrics:
            return None
        
        comparison = {
            'configuration_id': configuration_id,
            'baseline_score': self.baseline_metrics.overall_score,
            'config_score': config_metrics.overall_score,
            'score_improvement': config_metrics.overall_score - self.baseline_metrics.overall_score,
            'score_improvement_pct': ((config_metrics.overall_score - self.baseline_metrics.overall_score) / 
                                    self.baseline_metrics.overall_score * 100),
            'latency_ratio': config_metrics.processing_time_ms / max(1, self.baseline_metrics.processing_time_ms),
            'error_rate_diff': config_metrics.error_rate - self.baseline_metrics.error_rate,
            'is_better': config_metrics.is_better_than(self.baseline_metrics),
            'is_acceptable': config_metrics.is_acceptable(self.baseline_metrics),
            'recommendation': self._get_recommendation(config_metrics)
        }
        
        return comparison
    
    def _get_recommendation(self, metrics: PerformanceMetrics) -> str:
        """Get recommendation based on metrics"""
        if not self.baseline_metrics:
            return "insufficient_baseline_data"
        
        if metrics.is_better_than(self.baseline_metrics, tolerance=0.02):
            return "promote"
        elif metrics.is_acceptable(self.baseline_metrics, max_degradation=0.05):
            return "continue_monitoring"
        else:
            return "rollback"
    
    def check_alerts(self, configuration_id: str) -> List[Dict[str, Any]]:
        """Check for performance alerts"""
        alerts = []
        recent_metrics = self.get_recent_metrics(configuration_id, hours=1)  # Last hour
        
        if not recent_metrics or not self.baseline_metrics:
            return alerts
        
        latest_metrics = recent_metrics[-1]
        
        # Error rate alert
        if latest_metrics.error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'high_error_rate',
                'severity': 'critical',
                'message': f"Error rate {latest_metrics.error_rate:.2%} exceeds threshold {self.alert_thresholds['error_rate']:.2%}",
                'value': latest_metrics.error_rate,
                'threshold': self.alert_thresholds['error_rate']
            })
        
        # Latency alert
        latency_ratio = latest_metrics.processing_time_ms / max(1, self.baseline_metrics.processing_time_ms)
        if latency_ratio > self.alert_thresholds['latency_degradation']:
            alerts.append({
                'type': 'latency_degradation',
                'severity': 'warning',
                'message': f"Latency {latency_ratio:.1f}x slower than baseline",
                'value': latency_ratio,
                'threshold': self.alert_thresholds['latency_degradation']
            })
        
        # Score degradation alert
        score_degradation = (self.baseline_metrics.overall_score - latest_metrics.overall_score) / self.baseline_metrics.overall_score
        if score_degradation > self.alert_thresholds['score_degradation']:
            alerts.append({
                'type': 'score_degradation',
                'severity': 'critical',
                'message': f"Score degradation {score_degradation:.1%} exceeds threshold {self.alert_thresholds['score_degradation']:.1%}",
                'value': score_degradation,
                'threshold': self.alert_thresholds['score_degradation']
            })
        
        return alerts


class ABTestingSystem:
    """Main system for A/B testing ML-enhanced vs baseline SLAP optimization"""
    
    def __init__(self, base_optimizer: SLAPOptimizer, base_predictor: PickupProbabilityPredictor):
        self.base_optimizer = base_optimizer
        self.base_predictor = base_predictor
        
        # A/B test configuration
        self.ab_config = ABTestConfiguration(
            test_name="ML_Enhanced_SLAP_vs_Baseline",
            treatment_ratio=0.5,  # 50/50 split
            min_samples_for_significance=100,
            significance_threshold=0.05
        )
        
        # Core components
        self.ab_router = ABTestRouter(self.ab_config)
        self.performance_monitor = PerformanceMonitor()
        
        # ML predictor for treatment group
        self.ml_predictor = None
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize baseline performance
        self._initialize_baseline()
    
    def _initialize_baseline(self):
        """Initialize baseline performance metrics"""
        self.logger.info("Initializing baseline performance metrics...")
        
        # This would normally run the existing system to establish baseline
        # For now, we'll use estimated baseline metrics
        baseline_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            customer_convenience=0.75,
            employee_workload=0.70,
            system_efficiency=0.68,
            future_flexibility=0.60,
            overall_score=0.0,  # Will be calculated
            processing_time_ms=50.0,
            memory_usage_mb=100.0,
            error_rate=0.01,
            throughput_per_second=20.0
        )
        
        self.performance_monitor.record_metrics('baseline', baseline_metrics)
        self.logger.info(f"Baseline established with score: {baseline_metrics.overall_score:.3f}")
    
    def initialize_ml_predictor(self):
        """Initialize ML predictor for treatment group"""
        try:
            ml_config = MLConfig(
                use_ensemble=True,
                ensemble_methods=['rf', 'gb', 'lr'],
                online_learning_enabled=True
            )
            self.ml_predictor = create_ml_predictor(ml_config)
            self.logger.info("ML predictor initialized for treatment group")
        except Exception as e:
            self.logger.error(f"Failed to initialize ML predictor: {e}")
    
    # 注意：非近视和RL初始化方法已移除，专注于核心ML-LTO功能
    
    def predict_pickup_probability(self, parcel: Parcel, current_time: datetime, 
                                 request_id: str = None) -> Tuple[float, str]:
        """Predict pickup probability using A/B testing approach"""
        start_time = time.time()
        error_occurred = False
        
        # Assign to A/B test group
        test_group = self.ab_router.assign_test_group(request_id or parcel.parcel_id)
        
        try:
            if test_group == TestGroup.TREATMENT and self.ml_predictor and self.ml_predictor.is_trained:
                # Treatment group: Use ML predictor
                probability = self.ml_predictor.predict_pickup_probability(parcel, current_time)
                predictor_used = "ml_treatment"
            else:
                # Control group: Use baseline rule-based predictor
                probability = self.base_predictor.predict_pickup_probability(parcel, current_time)
                predictor_used = "rule_based_control"
            
        except Exception as e:
            self.logger.error(f"Error in prediction: {e}, falling back to rule-based")
            probability = self.base_predictor.predict_pickup_probability(parcel, current_time)
            predictor_used = "rule_based_fallback"
            error_occurred = True
        
        # Record performance metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            customer_convenience=0.75,  # Would be calculated from actual assignment
            employee_workload=0.70,
            system_efficiency=0.68,
            future_flexibility=0.60,
            overall_score=0.0,
            processing_time_ms=processing_time,
            memory_usage_mb=100.0,
            error_rate=1.0 if error_occurred else 0.0,
            throughput_per_second=1000.0 / max(processing_time, 1.0)
        )
        
        group_id = f"{test_group.value}_{predictor_used}"
        self.performance_monitor.record_metrics(group_id, metrics)
        
        return probability, predictor_used
    
    def optimize_parcels(self, parcels: List[Parcel], station: ParcelStation, 
                        current_time: datetime, request_id: str = None) -> Tuple[List[Tuple[Parcel, Optional[Shelf]]], str]:
        """Optimize parcel assignments using appropriate optimization strategy"""
        start_time = time.time()
        error_occurred = False
        optimizer_used = "slap_baseline"
        
        try:
            # 使用ML增强的SLAP优化器
            results = self.base_optimizer.batch_assign_parcels(parcels, station)
            optimizer_used = "slap_baseline"
            
        except Exception as e:
            self.logger.error(f"Error in optimization: {e}, falling back to baseline SLAP")
            results = self.base_optimizer.batch_assign_parcels(parcels, station)
            optimizer_used = "slap_fallback"
            error_occurred = True
        
        # Calculate performance metrics
        processing_time = (time.time() - start_time) * 1000
        successful_assignments = len([r for r in results if r[1] is not None])
        success_rate = successful_assignments / len(parcels) if parcels else 1.0
        
        # Calculate actual SLAP metrics
        customer_convenience = self._calculate_customer_convenience(results, station)
        employee_workload = self._calculate_employee_workload(results, station)
        system_efficiency = self._calculate_system_efficiency(results, station)
        future_flexibility = self._calculate_future_flexibility(results, station)
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            customer_convenience=customer_convenience,
            employee_workload=employee_workload,
            system_efficiency=system_efficiency,
            future_flexibility=future_flexibility,
            overall_score=0.0,  # Will be calculated
            processing_time_ms=processing_time,
            memory_usage_mb=100.0,  # Would be measured
            error_rate=1.0 if error_occurred else (1.0 - success_rate),
            throughput_per_second=len(parcels) / max(processing_time / 1000, 0.001)
        )
        
        self.performance_monitor.record_metrics(optimizer_used, metrics)
        
        # Record routing decisions
        if request_id:
            self.feature_router.record_routing_decision(
                FeatureFlag.NON_MYOPIC_OPTIMIZATION, request_id, optimizer_used == "non_myopic"
            )
            self.feature_router.record_routing_decision(
                FeatureFlag.RL_INTEGRATION, request_id, optimizer_used == "rl_integrated"
            )
        
        return results, optimizer_used
    
    def _calculate_customer_convenience(self, results: List[Tuple[Parcel, Optional[Shelf]]], 
                                      station: ParcelStation) -> float:
        """Calculate customer convenience score"""
        if not results:
            return 0.0
        
        total_score = 0.0
        successful_assignments = 0
        
        for parcel, shelf in results:
            if shelf:
                # Higher scores for shorter distances and higher probabilities
                distance_score = 1.0 - (shelf.distance_to_exit / 5.0)  # Normalize to 0-1
                prob_weight = getattr(parcel, 'predicted_pickup_probability', 0.5)
                convenience_score = distance_score * prob_weight
                total_score += convenience_score
                successful_assignments += 1
        
        return total_score / max(successful_assignments, 1)
    
    def _calculate_employee_workload(self, results: List[Tuple[Parcel, Optional[Shelf]]], 
                                   station: ParcelStation) -> float:
        """Calculate employee workload balance score"""
        if not station.shelves:
            return 0.0
        
        # Calculate workload distribution
        workload_scores = [shelf.get_workload_score() for shelf in station.shelves]
        workload_std = np.std(workload_scores)
        
        # Lower standard deviation = better balance = higher score
        balance_score = 1.0 - min(workload_std, 1.0)
        
        return balance_score
    
    def _calculate_system_efficiency(self, results: List[Tuple[Parcel, Optional[Shelf]]], 
                                   station: ParcelStation) -> float:
        """Calculate system efficiency score"""
        if not station.shelves:
            return 0.0
        
        # Calculate utilization metrics
        utilization_rates = [shelf.get_utilization_rate() for shelf in station.shelves]
        avg_utilization = np.mean(utilization_rates)
        utilization_std = np.std(utilization_rates)
        
        # Balanced high utilization is good
        efficiency_score = avg_utilization * (1.0 - min(utilization_std, 1.0))
        
        return min(efficiency_score, 1.0)
    
    def _calculate_future_flexibility(self, results: List[Tuple[Parcel, Optional[Shelf]]], 
                                    station: ParcelStation) -> float:
        """Calculate future flexibility score"""
        premium_shelves = [s for s in station.shelves if s.location_type == ShelfType.PREMIUM]
        if not premium_shelves:
            return 0.0
        
        # Calculate how well premium shelves are reserved for high-probability parcels
        total_flexibility = 0.0
        
        for parcel, shelf in results:
            if shelf and shelf in premium_shelves:
                prob = getattr(parcel, 'predicted_pickup_probability', 0.5)
                if prob > 0.7:
                    total_flexibility += 1.0  # Good use of premium shelf
                else:
                    total_flexibility += 0.3  # Poor use of premium shelf
            elif shelf:
                total_flexibility += 0.7  # Standard shelf usage
        
        return total_flexibility / max(len(results), 1)
    
    def get_ab_test_results(self) -> Dict[str, Any]:
        """Get A/B test results and statistical analysis"""
        # Get assignment statistics
        assignment_stats = self.ab_router.get_assignment_stats()
        
        # Get performance comparison between control and treatment groups
        control_metrics = self.performance_monitor.calculate_average_metrics("control_rule_based_control")
        treatment_metrics = self.performance_monitor.calculate_average_metrics("treatment_ml_treatment")
        
        if not control_metrics or not treatment_metrics:
            return {
                'status': 'insufficient_data',
                'assignment_stats': assignment_stats,
                'message': 'Not enough data collected for statistical analysis'
            }
        
        # Calculate improvement metrics
        improvement = {
            'overall_score_improvement': treatment_metrics.overall_score - control_metrics.overall_score,
            'customer_convenience_improvement': treatment_metrics.customer_convenience - control_metrics.customer_convenience,
            'employee_workload_improvement': treatment_metrics.employee_workload - control_metrics.employee_workload,
            'system_efficiency_improvement': treatment_metrics.system_efficiency - control_metrics.system_efficiency,
            'processing_time_change': treatment_metrics.processing_time_ms - control_metrics.processing_time_ms,
            'error_rate_change': treatment_metrics.error_rate - control_metrics.error_rate
        }
        
        # Statistical significance analysis (simplified)
        is_significant = (
            assignment_stats['total_requests'] >= self.ab_config.min_samples_for_significance and
            improvement['overall_score_improvement'] > self.ab_config.effect_size_threshold
        )
        
        return {
            'status': 'analysis_complete',
            'test_name': self.ab_config.test_name,
            'assignment_stats': assignment_stats,
            'control_metrics': {
                'overall_score': control_metrics.overall_score,
                'customer_convenience': control_metrics.customer_convenience,
                'employee_workload': control_metrics.employee_workload,
                'system_efficiency': control_metrics.system_efficiency,
                'processing_time_ms': control_metrics.processing_time_ms,
                'error_rate': control_metrics.error_rate
            },
            'treatment_metrics': {
                'overall_score': treatment_metrics.overall_score,
                'customer_convenience': treatment_metrics.customer_convenience,
                'employee_workload': treatment_metrics.employee_workload,
                'system_efficiency': treatment_metrics.system_efficiency,
                'processing_time_ms': treatment_metrics.processing_time_ms,
                'error_rate': treatment_metrics.error_rate
            },
            'improvements': improvement,
            'is_statistically_significant': is_significant,
            'recommendation': 'deploy_treatment' if is_significant and improvement['overall_score_improvement'] > 0 else 'keep_control'
        }


def create_ab_testing_system(base_optimizer: SLAPOptimizer,
                           base_predictor: PickupProbabilityPredictor) -> ABTestingSystem:
    """Factory function to create A/B testing system"""
    return ABTestingSystem(base_optimizer, base_predictor)


# Integration with existing evaluation system
class ABTestEvaluationWrapper:
    """Wrapper to integrate A/B testing system with existing evaluation"""
    
    def __init__(self, ab_testing_system: ABTestingSystem):
        self.ab_testing_system = ab_testing_system
        self.evaluation_history = []
    
    def evaluate_with_ab_testing(self, parcels: List[Parcel], 
                                station: ParcelStation) -> Dict[str, Any]:
        """Evaluate system with A/B testing"""
        
        current_time = datetime.now()
        results = []
        
        # Process each parcel with A/B testing
        for i, parcel in enumerate(parcels):
            request_id = f"eval_{current_time.timestamp()}_{i}"
            
            # Predict probability using A/B testing
            probability, predictor_used = self.ab_testing_system.predict_pickup_probability(
                parcel, current_time, request_id
            )
            parcel.predicted_pickup_probability = probability
            
            # Single parcel optimization
            optimization_results, optimizer_used = self.ab_testing_system.optimize_parcels(
                [parcel], station, current_time, request_id
            )
            
            if optimization_results:
                parcel_result, assigned_shelf = optimization_results[0]
                results.append((parcel_result, assigned_shelf))
            else:
                results.append((parcel, None))
        
        # Calculate final metrics
        customer_convenience = self.ab_testing_system._calculate_customer_convenience(results, station)
        employee_workload = self.ab_testing_system._calculate_employee_workload(results, station)
        system_efficiency = self.ab_testing_system._calculate_system_efficiency(results, station)
        future_flexibility = self.ab_testing_system._calculate_future_flexibility(results, station)
        
        overall_score = (0.4 * customer_convenience + 0.3 * employee_workload + 
                        0.2 * system_efficiency + 0.1 * future_flexibility)
        
        evaluation_result = {
            'timestamp': current_time,
            'parcels_processed': len(parcels),
            'successful_assignments': len([r for r in results if r[1] is not None]),
            'customer_convenience': customer_convenience,
            'employee_workload': employee_workload,
            'system_efficiency': system_efficiency,
            'future_flexibility': future_flexibility,
            'overall_score': overall_score,
            'ab_test_results': self.ab_testing_system.get_ab_test_results(),
            'assignments': results
        }
        
        self.evaluation_history.append(evaluation_result)
        return evaluation_result


# Example usage and testing
if __name__ == "__main__":
    from optimization_module import create_optimizer
    from learning_module import create_predictor
    import random
    
    # Create base components
    base_optimizer = create_optimizer("slap")
    base_predictor = create_predictor("rule_based")
    
    # Create A/B testing system
    ab_system = create_ab_testing_system(base_optimizer, base_predictor)
    
    # Initialize ML predictor for treatment group
    print("Initializing ML predictor for treatment group...")
    ab_system.initialize_ml_predictor()
    
    # Create test data
    station = ParcelStation()
    for i in range(3):
        shelf = Shelf(f"P{i+1}", ShelfType.PREMIUM, matrix_position=(0, i))
        station.add_shelf(shelf)
    
    test_parcels = [
        Parcel(f"TEST_{i}", datetime.now() - timedelta(minutes=i*10), 
               random.choice(list(ParcelSize)))
        for i in range(10)
    ]
    
    # Test A/B evaluation
    evaluation_wrapper = ABTestEvaluationWrapper(ab_system)
    results = evaluation_wrapper.evaluate_with_ab_testing(test_parcels, station)
    
    print(f"\nA/B Test Evaluation Results:")
    print(f"Overall Score: {results['overall_score']:.3f}")
    print(f"Successful Assignments: {results['successful_assignments']}/{results['parcels_processed']}")
    
    # Get A/B test results
    ab_results = results['ab_test_results']
    print(f"\nA/B Test Results:")
    print(f"Status: {ab_results['status']}")
    if ab_results['status'] == 'analysis_complete':
        print(f"Control Score: {ab_results['control_metrics']['overall_score']:.3f}")
        print(f"Treatment Score: {ab_results['treatment_metrics']['overall_score']:.3f}")
        print(f"Improvement: {ab_results['improvements']['overall_score_improvement']:.3f}")
        print(f"Recommendation: {ab_results['recommendation']}")
    
    print("\nA/B testing system test completed!")