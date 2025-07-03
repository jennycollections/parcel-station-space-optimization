#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Evaluation System for Cainiao Parcel Station LTO Optimization

This module implements multiple baseline strategies and comprehensive performance 
metrics to evaluate the effectiveness of the LTO (Learn-then-Optimize) system
compared to traditional parcel placement methods.

Author: Manufacturing Analysis Team
Date: 2024
"""

import json
import time
import random
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import statistics
import os

# Import existing modules
from data_structures import Parcel, Shelf, ParcelStation, ShelfType, ParcelSize
from learning_module import PickupProbabilityPredictor
from optimization_module import SLAPOptimizer
from simulation_engine import SimulationEngine
import config

@dataclass
class CoreEvaluationMetrics:
    """与优化目标函数直接对应的性能指标"""
    
    # 🎯 4个优化目标对应的性能指标 (与权重对应: 40%, 30%, 20%, 10%)
    customer_convenience_cost: float     # 1. 客户便利性成本 (距离×概率×尺寸因子)
    employee_workload_cost: float        # 2. 员工工作负荷成本 (入口距离+工作量×尺寸因子)
    system_efficiency_cost: float        # 3. 系统效率成本 (利用率+空间平衡)
    future_flexibility_cost: float       # 4. 未来灵活性成本 (Premium预留+容量因子)

@dataclass  
class DetailedEvaluationMetrics:
    """详细评估指标 - 用于深入分析"""
    # Core metrics (same as CoreEvaluationMetrics)
    lto_alignment_score: float
    avg_assignment_cost: float
    high_prob_to_premium_rate: float
    customer_satisfaction_score: float
    overall_utilization_rate: float
    
    # Additional detailed metrics
    total_assignment_cost: float
    avg_retrieval_distance: float
    premium_utilization_rate: float
    standard_utilization_rate: float
    low_prob_to_standard_rate: float
    avg_pickup_time: float
    actual_pickup_rate: float
    weighted_satisfaction_score: float
    high_prob_customer_satisfaction: float
    cost_per_satisfied_customer: float
    processing_time: float
    memory_usage: float
    assignment_success_rate: float
    misplacement_penalty: float
    space_efficiency: float

class BaselineStrategy:
    """Base class for baseline placement strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.assignments = []
        self.costs = []
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Assign a parcel to a shelf. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def get_assignment_cost(self, parcel: Parcel, shelf: Shelf) -> float:
        """Calculate assignment cost for evaluation purposes"""
        # Use the same cost function as LTO for fair comparison
        predicted_prob = getattr(parcel, 'predicted_pickup_probability', None)
        if predicted_prob is None:
            # For fair comparison, baseline strategies should also predict
            # Use a default moderate probability
            predicted_prob = 0.5
        return shelf.distance_to_exit * (1 - predicted_prob)

class RandomStrategy(BaselineStrategy):
    """Random parcel placement strategy"""
    
    def __init__(self):
        super().__init__("Random Placement")
        self.predictor = PickupProbabilityPredictor()
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Randomly assign parcel to any available shelf"""
        # Set predicted probability for fair comparison
        if parcel.predicted_pickup_probability is None:
            parcel.predicted_pickup_probability = self.predictor.predict_pickup_probability(parcel, datetime.now())
        
        available_shelves = [shelf for shelf in station.shelves 
                           if shelf.can_accommodate(parcel.size)]
        
        if not available_shelves:
            return None, float('inf')
        
        selected_shelf = random.choice(available_shelves)
        cost = self.get_assignment_cost(parcel, selected_shelf)
        
        return selected_shelf, cost

class FIFOStrategy(BaselineStrategy):
    """First-In-First-Out placement strategy"""
    
    def __init__(self):
        super().__init__("FIFO Placement")
        self.shelf_index = 0
        self.predictor = PickupProbabilityPredictor()
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Assign parcel to the first available shelf in order"""
        # Set predicted probability for fair comparison
        if parcel.predicted_pickup_probability is None:
            parcel.predicted_pickup_probability = self.predictor.predict_pickup_probability(parcel, datetime.now())
        
        for i in range(len(station.shelves)):
            shelf_idx = (self.shelf_index + i) % len(station.shelves)
            shelf = station.shelves[shelf_idx]
            
            if shelf.can_accommodate(parcel.size):
                self.shelf_index = (shelf_idx + 1) % len(station.shelves)
                cost = self.get_assignment_cost(parcel, shelf)
                return shelf, cost
        
        return None, float('inf')

class GreedyCapacityStrategy(BaselineStrategy):
    """Greedy strategy prioritizing shelf capacity utilization"""
    
    def __init__(self):
        super().__init__("Greedy Capacity")
        self.predictor = PickupProbabilityPredictor()
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Assign to shelf with highest remaining capacity"""
        # Set predicted probability for fair comparison
        if parcel.predicted_pickup_probability is None:
            parcel.predicted_pickup_probability = self.predictor.predict_pickup_probability(parcel, datetime.now())
        
        available_shelves = [shelf for shelf in station.shelves 
                           if shelf.can_accommodate(parcel.size)]
        
        if not available_shelves:
            return None, float('inf')
        
        # Sort by remaining capacity (descending) - need to calculate remaining capacity properly
        def get_remaining_capacity(shelf):
            return shelf.capacity_volume[parcel.size] - shelf.current_used_volume[parcel.size]
        
        available_shelves.sort(key=get_remaining_capacity, reverse=True)
        selected_shelf = available_shelves[0]
        cost = self.get_assignment_cost(parcel, selected_shelf)
        
        return selected_shelf, cost

class DistanceOnlyStrategy(BaselineStrategy):
    """Strategy based only on shelf distance (ignoring predictions)"""
    
    def __init__(self):
        super().__init__("Distance Only")
        self.predictor = PickupProbabilityPredictor()
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Assign to the nearest available shelf"""
        # Set predicted probability for fair comparison
        if parcel.predicted_pickup_probability is None:
            parcel.predicted_pickup_probability = self.predictor.predict_pickup_probability(parcel, datetime.now())
        
        available_shelves = [shelf for shelf in station.shelves 
                           if shelf.can_accommodate(parcel.size)]
        
        if not available_shelves:
            return None, float('inf')
        
        # Sort by distance (ascending)
        available_shelves.sort(key=lambda s: s.distance_to_exit)
        selected_shelf = available_shelves[0]
        cost = self.get_assignment_cost(parcel, selected_shelf)
        
        return selected_shelf, cost

class LTOStrategy(BaselineStrategy):
    """LTO strategy using SLAP batch optimization"""
    
    def __init__(self):
        super().__init__("LTO Strategy")
        self.learning_module = PickupProbabilityPredictor()
        self.optimization_module = SLAPOptimizer()
        self.batch_assignments = {}  # Store batch assignment results
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Use LTO to assign parcel - this is called by evaluation but we'll batch process"""
        # Predict pickup probability
        current_time = datetime.now()
        predicted_prob = self.learning_module.predict_pickup_probability(parcel, current_time)
        parcel.predicted_pickup_probability = predicted_prob
        
        # Check if we have a pre-computed assignment from batch optimization
        if parcel.parcel_id in self.batch_assignments:
            shelf, cost = self.batch_assignments[parcel.parcel_id]
            return shelf, cost
        
        # Fallback to individual assignment if not in batch
        selected_shelf = self.optimization_module.assign_parcel_to_shelf(parcel, station)
        
        if selected_shelf:
            cost = self.get_assignment_cost(parcel, selected_shelf)
            return selected_shelf, cost
        else:
            return None, float('inf')
    
    def batch_optimize_parcels(self, parcels: List[Parcel], station: ParcelStation) -> Dict[str, Tuple[Shelf, float]]:
        """
        Perform batch optimization for all parcels using SLAP global optimization.
        This is the main method that implements our new optimization strategy.
        """
        # Clear previous batch assignments
        self.batch_assignments = {}
        
        # Predict probabilities for all parcels
        current_time = datetime.now()
        for parcel in parcels:
            if parcel.predicted_pickup_probability is None:
                predicted_prob = self.learning_module.predict_pickup_probability(parcel, current_time)
                parcel.predicted_pickup_probability = predicted_prob
        
        # Add all parcels to optimizer batch
        for parcel in parcels:
            self.optimization_module.add_parcel_to_batch(parcel, current_time)
        
        # Perform global batch optimization
        optimization_results = self.optimization_module.optimize_current_batch(station)
        
        # Store results for later retrieval
        for parcel, shelf in optimization_results:
            if shelf:
                cost = self.get_assignment_cost(parcel, shelf)
                self.batch_assignments[parcel.parcel_id] = (shelf, cost)
            else:
                self.batch_assignments[parcel.parcel_id] = (None, float('inf'))
        
        return self.batch_assignments

class EvaluationEngine:
    """Main evaluation engine to compare different strategies"""
    
    def __init__(self):
        self.strategies = {
            'LTO': LTOStrategy(),
            'Random': RandomStrategy(),
            'FIFO': FIFOStrategy(),
            'GreedyCapacity': GreedyCapacityStrategy(),
            'DistanceOnly': DistanceOnlyStrategy()
        }
        self.results = {}
        
    def create_test_scenarios(self) -> List[Dict]:
        """Create different test scenarios for evaluation"""
        scenarios = []
        
        # Scenario 1: Light Load (正常工作日)
        scenarios.append({
            'name': 'Light_Load',
            'description': '正常工作日，包裹流量较少',
            'parcel_count': 50,
            'high_prob_ratio': 0.3,  # 30% 高概率包裹
            'size_distribution': {'S': 0.5, 'M': 0.3, 'L': 0.2}
        })
        
        # Scenario 2: Medium Load (周末或促销期间)
        scenarios.append({
            'name': 'Medium_Load',
            'description': '周末或小型促销，包裹流量中等',
            'parcel_count': 100,
            'high_prob_ratio': 0.4,  # 40% 高概率包裹
            'size_distribution': {'S': 0.4, 'M': 0.4, 'L': 0.2}
        })
        
        # Scenario 3: Heavy Load (双11等大促)
        scenarios.append({
            'name': 'Heavy_Load',
            'description': '双11等大促期间，包裹流量大',
            'parcel_count': 200,
            'high_prob_ratio': 0.6,  # 60% 高概率包裹
            'size_distribution': {'S': 0.3, 'M': 0.5, 'L': 0.2}
        })
        
        # Scenario 4: Extreme Load (压力测试)
        scenarios.append({
            'name': 'Extreme_Load',
            'description': '极端情况压力测试',
            'parcel_count': 300,
            'high_prob_ratio': 0.5,  # 50% 高概率包裹
            'size_distribution': {'S': 0.4, 'M': 0.3, 'L': 0.3}
        })
        
        return scenarios
    
    def generate_test_parcels(self, scenario: Dict) -> List[Parcel]:
        """Generate test parcels for a scenario"""
        parcels = []
        parcel_count = scenario['parcel_count']
        high_prob_ratio = scenario['high_prob_ratio']
        size_dist = scenario['size_distribution']
        
        for i in range(parcel_count):
            # Determine size
            rand = random.random()
            if rand < size_dist['S']:
                size = ParcelSize.SMALL
            elif rand < size_dist['S'] + size_dist['M']:
                size = ParcelSize.MEDIUM
            else:
                size = ParcelSize.LARGE
            
            # Create parcel
            parcel = Parcel(
                parcel_id=f"TEST_{i:04d}",
                arrival_time=datetime.now() + timedelta(minutes=i*5),
                size=size
            )
            
            # Simulate true pickup probability for evaluation
            if random.random() < high_prob_ratio:
                parcel.true_pickup_probability = random.uniform(0.7, 1.0)  # 高概率
            else:
                parcel.true_pickup_probability = random.uniform(0.0, 0.4)  # 低概率
            
            parcels.append(parcel)
        
        return parcels
    
    def create_test_station(self) -> ParcelStation:
        """Create a standardized test station with comprehensive distance modeling"""
        station = ParcelStation()
        
        # Add premium shelves (close to exit, moderate distance from entrance)
        for i in range(3):
            shelf = Shelf(
                shelf_id=f"P{i+1}",
                location_type=ShelfType.PREMIUM,
                matrix_position=config.SHELF_POSITIONS['premium'][i],
                capacity_small=15,
                capacity_medium=10,
                capacity_large=5,
                distance_to_exit=1.0,      # Close to exit (good for customers)
                distance_from_entrance=2.0 + i*0.5  # Moderate from entrance (P1=2.0, P2=2.5, P3=3.0)
            )
            station.add_shelf(shelf)
        
        # Add standard shelves (far from exit, close to entrance)
        for i in range(5):
            shelf = Shelf(
                shelf_id=f"S{i+1}",
                location_type=ShelfType.STANDARD,
                matrix_position=config.SHELF_POSITIONS['standard'][i],
                capacity_small=20,
                capacity_medium=15,
                capacity_large=8,
                distance_to_exit=2.5,      # Far from exit (less convenient for customers)
                distance_from_entrance=1.0 + i*0.3  # Close to entrance (S1=1.0, S2=1.3, ..., S5=2.2)
            )
            station.add_shelf(shelf)
        
        return station
    
    def calculate_advanced_metrics(self, assignments: List[Dict], strategy_name: str) -> CoreEvaluationMetrics:
        """计算与优化目标函数直接对应的4个成本指标"""
        if not assignments:
            return CoreEvaluationMetrics(
                customer_convenience_cost=float('inf'),
                employee_workload_cost=float('inf'),
                system_efficiency_cost=float('inf'),
                future_flexibility_cost=float('inf')
            )

        # 计算四个优化目标的平均成本
        customer_costs = []
        employee_costs = []
        system_costs = []
        future_costs = []
        
        # 为了计算系统成本，我们需要重建货架利用率信息
        shelf_utilizations = {}
        shelf_assignments_count = {}
        
        for assignment in assignments:
            shelf_id = assignment['shelf_id']
            distance = assignment['distance']
            predicted_prob = assignment.get('predicted_prob', 0.5)
            
            # 统计货架分配数量
            shelf_assignments_count[shelf_id] = shelf_assignments_count.get(shelf_id, 0) + 1
            
            # 1. Customer Convenience Cost (客户便利性成本)
            # 基于优化函数: distance_cost * size_factor * probability_factor
            size_factor = 1.2  # 假设平均尺寸因子 (Small:1.0, Medium:1.2, Large:1.5)
            probability_factor = 1.0 - (predicted_prob * 0.5)
            customer_cost = distance * size_factor * probability_factor
            customer_costs.append(customer_cost)
            
            # 2. Employee Workload Cost (员工工作负荷成本)
            # 基于优化函数: (distance_from_entrance + workload_cost) * size_factor
            # 假设distance_from_entrance约等于distance_to_exit的0.8倍
            distance_from_entrance = distance * 0.8
            workload_cost = 0.1  # 基础工作负荷
            employee_cost = (distance_from_entrance + workload_cost) * size_factor
            employee_costs.append(employee_cost)
            
            # 4. Future Flexibility Cost (未来灵活性成本)
            # 基于优化函数: Premium货架惩罚 + 容量因子
            if shelf_id.startswith('P'):  # Premium货架
                if predicted_prob < 0.7:
                    future_cost = 1.0  # 高惩罚
                else:
                    future_cost = 0.1  # 低惩罚
            else:
                future_cost = 0.3  # Standard货架的基础成本
            
            # 容量因子 (假设平均容量使用率)
            capacity_factor = 0.5  # 假设平均50%容量使用
            future_cost += capacity_factor
            future_costs.append(future_cost)
        
        # 3. System Efficiency Cost (系统效率成本)
        # 基于优化函数: utilization_cost + balance_cost
        premium_capacity = 14  # 每个Premium货架容量
        standard_capacity = 35  # 每个Standard货架容量
        
        utilization_rates = []
        for shelf_id, count in shelf_assignments_count.items():
            if shelf_id.startswith('P'):  # Premium货架
                utilization_rate = count / premium_capacity
            else:  # Standard货架
                utilization_rate = count / standard_capacity
            utilization_rates.append(utilization_rate)
            shelf_utilizations[shelf_id] = utilization_rate
        
        # 计算每个分配的系统成本
        for assignment in assignments:
            shelf_id = assignment['shelf_id']
            current_utilization = shelf_utilizations[shelf_id]
            
            # 空间平衡成本 (相邻货架利用率差异)
            # 简化计算：使用所有货架的平均利用率作为参考
            avg_utilization = sum(utilization_rates) / len(utilization_rates) if utilization_rates else 0
            balance_cost = abs(current_utilization - avg_utilization)
            
            system_cost = current_utilization + balance_cost
            system_costs.append(system_cost)
        
        # 计算平均成本
        avg_customer_cost = sum(customer_costs) / len(customer_costs)
        avg_employee_cost = sum(employee_costs) / len(employee_costs)
        avg_system_cost = sum(system_costs) / len(system_costs)
        avg_future_cost = sum(future_costs) / len(future_costs)

        return CoreEvaluationMetrics(
            customer_convenience_cost=avg_customer_cost,
            employee_workload_cost=avg_employee_cost,
            system_efficiency_cost=avg_system_cost,
            future_flexibility_cost=avg_future_cost
        )
    
    def run_single_evaluation(self, strategy_name: str, scenario: Dict, parcels: List[Parcel]) -> Dict:
        """Run evaluation for a single strategy on a single scenario"""
        print(f"Running {strategy_name} on {scenario['name']}...")
        
        strategy = self.strategies[strategy_name]
        station = self.create_test_station()
        
        start_time = time.time()
        assignments = []
        
        # Special handling for LTO strategy - use batch optimization
        if strategy_name == 'LTO' and hasattr(strategy, 'batch_optimize_parcels'):
            # Use batch optimization for LTO strategy
            batch_results = strategy.batch_optimize_parcels(parcels, station)
            
            # Calculate processing time after optimization completes
            end_time = time.time()
            processing_time = end_time - start_time
            per_parcel_processing_time = processing_time / len(parcels) if parcels else 0
            
            # Process batch results
            for parcel in parcels:
                if parcel.parcel_id in batch_results:
                    assigned_shelf, cost = batch_results[parcel.parcel_id]
                    
                    if assigned_shelf:
                        # Record assignment
                        assignment_record = {
                            'parcel_id': parcel.parcel_id,
                            'shelf_id': assigned_shelf.shelf_id,
                            'shelf_type': assigned_shelf.location_type.value,
                            'cost': cost,
                            'distance': assigned_shelf.distance_to_exit,
                            'processing_time': per_parcel_processing_time,
                            'true_prob': getattr(parcel, 'true_pickup_probability', 0.5),
                            'predicted_prob': getattr(parcel, 'predicted_pickup_probability', 0.5)
                        }
                        assignments.append(assignment_record)
        else:
            # Use individual assignment for other strategies
            for parcel in parcels:
                parcel_start_time = time.time()
                assigned_shelf, cost = strategy.assign_parcel(parcel, station)
                parcel_end_time = time.time()
                parcel_processing_time = parcel_end_time - parcel_start_time
                
                if assigned_shelf:
                    # Store the parcel
                    assigned_shelf.add_parcel(parcel)
                    
                    # Record assignment
                    assignment_record = {
                        'parcel_id': parcel.parcel_id,
                        'shelf_id': assigned_shelf.shelf_id,
                        'shelf_type': assigned_shelf.location_type.value,
                        'cost': cost,
                        'distance': assigned_shelf.distance_to_exit,
                        'processing_time': parcel_processing_time,
                        'true_prob': getattr(parcel, 'true_pickup_probability', 0.5),
                        'predicted_prob': getattr(parcel, 'predicted_pickup_probability', 0.5)
                    }
                    assignments.append(assignment_record)
            
            # Calculate total processing time for non-LTO strategies
            end_time = time.time()
            processing_time = end_time - start_time
        
        # Calculate metrics
        metrics = self.calculate_advanced_metrics(assignments, strategy_name)
        
        return {
            'strategy': strategy_name,
            'scenario': scenario['name'],
            'metrics': metrics,
            'assignments': assignments,
            'scenario_details': scenario
        }
    
    def run_comprehensive_evaluation(self) -> Dict:
        """Run comprehensive evaluation across all strategies and scenarios"""
        print("Cainiao LTO Evaluation - 4 Optimization Objective Costs")
        print("=" * 70)
        
        scenarios = self.create_test_scenarios()
        all_results = {}
        
        for scenario in scenarios:
            scenario_results = {}
            
            # Generate parcels ONCE per scenario for a fair comparison
            parcels = self.generate_test_parcels(scenario)
            
            for strategy_name in self.strategies.keys():
                result = self.run_single_evaluation(strategy_name, scenario, parcels)
                scenario_results[strategy_name] = result
            
            all_results[scenario['name']] = scenario_results
        
        return all_results
    
    def generate_comparison_report(self, results: Dict) -> Dict:
        """Generate focused report for 4 optimization objective costs"""
        
        comparison_data = {}
        improvement_data = {}
        
        # Calculate improvements relative to baselines
        for scenario_name, scenario_results in results.items():
            lto_metrics = scenario_results['LTO']['metrics']
            scenario_comparison = {}
            scenario_improvements = {}
            
            for strategy_name, strategy_result in scenario_results.items():
                metrics = strategy_result['metrics']
                scenario_comparison[strategy_name] = asdict(metrics)
                
                if strategy_name != 'LTO':
                    # Calculate improvements for 4 optimization objectives with proper bounds
                    # 所有成本都是越低越好，所以LTO成本更低为正向改进
                    
                    # 客户便利性改进：LTO成本更低为正向改进
                    customer_improvement = (metrics.customer_convenience_cost - lto_metrics.customer_convenience_cost) / max(metrics.customer_convenience_cost, 0.01) * 100
                    customer_improvement = max(-99.9, min(99.9, customer_improvement))
                    
                    # 员工工作负荷改进：LTO成本更低为正向改进
                    employee_improvement = (metrics.employee_workload_cost - lto_metrics.employee_workload_cost) / max(metrics.employee_workload_cost, 0.01) * 100
                    employee_improvement = max(-99.9, min(99.9, employee_improvement))
                    
                    # 系统效率改进：LTO成本更低为正向改进
                    system_improvement = (metrics.system_efficiency_cost - lto_metrics.system_efficiency_cost) / max(metrics.system_efficiency_cost, 0.01) * 100
                    system_improvement = max(-99.9, min(99.9, system_improvement))
                    
                    # 未来灵活性改进：LTO成本更低为正向改进
                    future_improvement = (metrics.future_flexibility_cost - lto_metrics.future_flexibility_cost) / max(metrics.future_flexibility_cost, 0.01) * 100
                    future_improvement = max(-99.9, min(99.9, future_improvement))
                    
                    improvements = {
                        'customer_improvement_percent': customer_improvement,
                        'employee_improvement_percent': employee_improvement,
                        'system_improvement_percent': system_improvement,
                        'future_improvement_percent': future_improvement
                    }
                    
                    scenario_improvements[strategy_name] = improvements
            
            comparison_data[scenario_name] = scenario_comparison
            improvement_data[scenario_name] = scenario_improvements
        
        # Print focused summary with actual results
        print("\n" + "=" * 70)
        print("📊 LTO PERFORMANCE SUMMARY - 4 OPTIMIZATION OBJECTIVE COSTS")
        print("=" * 70)
        
        # Calculate and display actual performance metrics
        for scenario_name, scenario_results in results.items():
            lto_metrics = scenario_results['LTO']['metrics']
            print(f"\n[{scenario_name}]")
            print(f"1. Customer Convenience Cost: {lto_metrics.customer_convenience_cost:.3f}")
            print(f"2. Employee Workload Cost: {lto_metrics.employee_workload_cost:.3f}")
            print(f"3. System Efficiency Cost: {lto_metrics.system_efficiency_cost:.3f}")
            print(f"4. Future Flexibility Cost: {lto_metrics.future_flexibility_cost:.3f}")
            
            # Show improvements vs baselines
            if scenario_name in improvement_data:
                print("   Cost Reductions vs Baselines:")
                for baseline_name, improvements in improvement_data[scenario_name].items():
                    print(f"   vs {baseline_name}:")
                    print(f"     Customer: {improvements['customer_improvement_percent']:+.1f}%")
                    print(f"     Employee: {improvements['employee_improvement_percent']:+.1f}%")
                    print(f"     System: {improvements['system_improvement_percent']:+.1f}%")
                    print(f"     Future: {improvements['future_improvement_percent']:+.1f}%")
        
        print("\n" + "=" * 70)
        
        # Generate summary statistics
        summary_stats = self._generate_summary_statistics(improvement_data)
        
        return {
            'detailed_results': results,
            'comparison_data': comparison_data,
            'improvement_data': improvement_data,
            'summary_statistics': summary_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_summary_statistics(self, improvement_data: Dict) -> Dict:
        """Generate summary statistics for 4 optimization objective cost reductions"""
        all_customer_improvements = []
        all_employee_improvements = []
        all_system_improvements = []
        all_future_improvements = []
        
        for scenario_improvements in improvement_data.values():
            for strategy_improvements in scenario_improvements.values():
                all_customer_improvements.append(strategy_improvements['customer_improvement_percent'])
                all_employee_improvements.append(strategy_improvements['employee_improvement_percent'])
                all_system_improvements.append(strategy_improvements['system_improvement_percent'])
                all_future_improvements.append(strategy_improvements['future_improvement_percent'])
        
        return {
            'customer_improvement': {
                'avg': statistics.mean(all_customer_improvements),
                'min': min(all_customer_improvements),
                'max': max(all_customer_improvements),
                'std': statistics.stdev(all_customer_improvements) if len(all_customer_improvements) > 1 else 0
            },
            'employee_improvement': {
                'avg': statistics.mean(all_employee_improvements),
                'min': min(all_employee_improvements),
                'max': max(all_employee_improvements),
                'std': statistics.stdev(all_employee_improvements) if len(all_employee_improvements) > 1 else 0
            },
            'system_improvement': {
                'avg': statistics.mean(all_system_improvements),
                'min': min(all_system_improvements),
                'max': max(all_system_improvements),
                'std': statistics.stdev(all_system_improvements) if len(all_system_improvements) > 1 else 0
            },
            'future_improvement': {
                'avg': statistics.mean(all_future_improvements),
                'min': min(all_future_improvements),
                'max': max(all_future_improvements),
                'std': statistics.stdev(all_future_improvements) if len(all_future_improvements) > 1 else 0
            }
        }
    
    def save_results(self, report: Dict, filename: str = None):
        """Save evaluation results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
        
        # Ensure the file is saved inside the 'Cainiao system' directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(script_dir, filename)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nEvaluation results saved to: {save_path}")
        return filename

    def simulate_pickup_process(self, assignments: List[Dict], simulation_days: int = 7) -> Dict:
        """
        模拟实际取件过程，基于真实概率进行动态评估
        
        Args:
            assignments: 分配记录列表
            simulation_days: 模拟天数
            
        Returns:
            模拟结果字典
        """
        pickup_events = []
        total_actual_pickups = 0
        total_satisfaction_weighted = 0
        total_cost_for_picked_up = 0
        high_prob_satisfactions = []
        
        for assignment in assignments:
            true_prob = assignment.get('true_prob', 0.5)
            distance = assignment['distance']
            cost = assignment['cost']
            
            # 模拟是否实际取件（基于真实概率）
            will_pickup = random.random() < true_prob
            
            if will_pickup:
                total_actual_pickups += 1
                total_cost_for_picked_up += cost
                
                # 计算实际取件时间和满意度
                pickup_time = distance * 0.5 + 1.5 + random.uniform(-0.1, 0.1)  # 减少随机性
                satisfaction = max(0, 1.0 - (pickup_time - 2) / 8)
                
                # 概率加权满意度
                weighted_satisfaction = satisfaction * true_prob
                total_satisfaction_weighted += weighted_satisfaction
                
                # 记录高概率客户的满意度
                if true_prob >= 0.7:
                    high_prob_satisfactions.append(satisfaction)
                
                pickup_events.append({
                    'parcel_id': assignment['parcel_id'],
                    'pickup_time': pickup_time,
                    'satisfaction': satisfaction,
                    'true_prob': true_prob,
                    'cost': cost
                })
        
        # 计算动态指标
        actual_pickup_rate = total_actual_pickups / len(assignments) if assignments else 0
        avg_weighted_satisfaction = total_satisfaction_weighted / len(assignments) if assignments else 0
        high_prob_satisfaction = statistics.mean(high_prob_satisfactions) if high_prob_satisfactions else 0
        cost_per_satisfied = total_cost_for_picked_up / max(total_actual_pickups, 1)
        
        return {
            'pickup_events': pickup_events,
            'actual_pickup_rate': actual_pickup_rate,
            'weighted_satisfaction_score': avg_weighted_satisfaction,
            'high_prob_customer_satisfaction': high_prob_satisfaction,
            'cost_per_satisfied_customer': cost_per_satisfied,
            'total_actual_pickups': total_actual_pickups
        }

def main():
    """Main evaluation function"""
    print("Cainiao Parcel Station LTO Evaluation System")
    print("=" * 50)
    
    # Initialize evaluation engine
    evaluation_engine = EvaluationEngine()
    
    # Run comprehensive evaluation
    results = evaluation_engine.run_comprehensive_evaluation()
    
    # Generate comparison report
    report = evaluation_engine.generate_comparison_report(results)
    
    # Save results
    filename = evaluation_engine.save_results(report)
    
    print(f"\n✅ Results saved to: {filename}")
    print("✅ Evaluation completed successfully!")
    
    return filename

if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    np.random.seed(42)
    
    # Run evaluation
    evaluation_report = main() 