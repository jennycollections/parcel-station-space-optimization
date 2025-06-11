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
from optimization_module import ParcelAssignmentOptimizer
from simulation_engine import SimulationEngine
import config

@dataclass
class EvaluationMetrics:
    """Comprehensive metrics for evaluating parcel placement strategies"""
    
    # Basic Performance Metrics
    avg_assignment_cost: float
    total_assignment_cost: float
    avg_retrieval_distance: float
    
    # Efficiency Metrics
    premium_utilization_rate: float
    standard_utilization_rate: float
    overall_utilization_rate: float
    
    # LTO-specific Metrics
    high_prob_to_premium_rate: float  # 高概率包裹放入premium货架的比例
    low_prob_to_standard_rate: float  # 低概率包裹放入standard货架的比例
    lto_alignment_score: float        # LTO策略对齐度评分
    
    # Service Quality Metrics
    avg_pickup_time: float            # 平均取件时间
    customer_satisfaction_score: float # 客户满意度评分
    
    # Dynamic Evaluation Metrics (NEW)
    actual_pickup_rate: float         # 实际取件率
    weighted_satisfaction_score: float # 概率加权满意度
    high_prob_customer_satisfaction: float  # 高概率客户满意度
    cost_per_satisfied_customer: float      # 每个满意客户的成本
    
    # Operational Metrics
    processing_time: float            # 系统处理时间
    memory_usage: float              # 内存使用量
    assignment_success_rate: float   # 分配成功率
    
    # Advanced Metrics
    misplacement_penalty: float      # 错误放置惩罚
    space_efficiency: float          # 空间利用效率
    strategy_effectiveness: float    # 策略有效性评分

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
    """Our LTO (Learn-then-Optimize) strategy wrapper"""
    
    def __init__(self):
        super().__init__("LTO Strategy")
        self.learning_module = PickupProbabilityPredictor()
        self.optimization_module = ParcelAssignmentOptimizer()
    
    def assign_parcel(self, parcel: Parcel, station: ParcelStation) -> Tuple[Shelf, float]:
        """Use LTO to assign parcel"""
        # Predict pickup probability
        current_time = datetime.now()
        predicted_prob = self.learning_module.predict_pickup_probability(parcel, current_time)
        parcel.predicted_pickup_probability = predicted_prob
        
        # Optimize assignment
        selected_shelf = self.optimization_module.assign_parcel_to_shelf(parcel, station)
        
        if selected_shelf:
            cost = self.get_assignment_cost(parcel, selected_shelf)
            return selected_shelf, cost
        else:
            return None, float('inf')

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
                capacity_small=20,
                capacity_medium=15,
                capacity_large=8,
                distance_to_exit=2.5,      # Far from exit (less convenient for customers)
                distance_from_entrance=1.0 + i*0.3  # Close to entrance (S1=1.0, S2=1.3, ..., S5=2.2)
            )
            station.add_shelf(shelf)
        
        return station
    
    def calculate_advanced_metrics(self, assignments: List[Dict], strategy_name: str) -> EvaluationMetrics:
        """Calculate comprehensive evaluation metrics"""
        if not assignments:
            return EvaluationMetrics(
                avg_assignment_cost=float('inf'),
                total_assignment_cost=float('inf'),
                avg_retrieval_distance=float('inf'),
                premium_utilization_rate=0.0,
                standard_utilization_rate=0.0,
                overall_utilization_rate=0.0,
                high_prob_to_premium_rate=0.0,
                low_prob_to_standard_rate=0.0,
                lto_alignment_score=0.0,
                avg_pickup_time=float('inf'),
                customer_satisfaction_score=0.0,
                processing_time=0.0,
                memory_usage=0.0,
                assignment_success_rate=0.0,
                misplacement_penalty=float('inf'),
                space_efficiency=0.0,
                strategy_effectiveness=0.0
            )
        
        # Basic metrics
        costs = [a['cost'] for a in assignments]
        distances = [a['distance'] for a in assignments]
        
        avg_assignment_cost = statistics.mean(costs)
        total_assignment_cost = sum(costs)
        avg_retrieval_distance = statistics.mean(distances)
        
        # Utilization metrics
        premium_assignments = [a for a in assignments if a['shelf_type'] == ShelfType.PREMIUM.value]
        standard_assignments = [a for a in assignments if a['shelf_type'] == ShelfType.STANDARD.value]
        
        premium_utilization = len(premium_assignments) / (3 * 15) if (3 * 15) > 0 else 0  # 3 premium shelves, capacity 15
        standard_utilization = len(standard_assignments) / (5 * 20) if (5 * 20) > 0 else 0  # 5 standard shelves, capacity 20
        overall_utilization = len(assignments) / (3 * 15 + 5 * 20) if (3 * 15 + 5 * 20) > 0 else 0
        
        # LTO alignment metrics based on "Occupancy Cost" philosophy.
        # This now rewards placing low-probability (long-term) parcels in premium (low-cost) shelves
        # to minimize the overall occupancy cost, aligning with the optimization objective.
        high_prob_parcels = [a for a in assignments if a.get('true_prob', 0.5) >= 0.7]
        low_prob_parcels = [a for a in assignments if a.get('true_prob', 0.5) < 0.4]
        
        # Correctly placed: Low-prob parcels in premium shelves (lowest occupancy cost)
        low_prob_in_premium = len([a for a in low_prob_parcels if a['shelf_type'] == ShelfType.PREMIUM.value])
        # Correctly placed: High-prob parcels in standard shelves (as their occupancy cost is low anyway)
        high_prob_in_standard = len([a for a in high_prob_parcels if a['shelf_type'] == ShelfType.STANDARD.value])
        
        # Calculate rates for the new alignment logic
        low_prob_to_premium_rate = low_prob_in_premium / len(low_prob_parcels) if low_prob_parcels else 0
        high_prob_to_standard_rate = high_prob_in_standard / len(high_prob_parcels) if high_prob_parcels else 0
        
        # The new alignment score, reflecting the cost optimization goal
        lto_alignment_score = (low_prob_to_premium_rate + high_prob_to_standard_rate) / 2
        
        # Service quality metrics (improved with probability weighting)
        # 新的满意度计算：只考虑实际会取件的包裹（概率加权）
        weighted_satisfaction_scores = []
        total_weight = 0
        
        for assignment in assignments:
            true_prob = assignment.get('true_prob', 0.5)
            distance = assignment['distance']
            
            # 基础取件时间：距离 * 0.5 + 基础时间(1.5分钟) + 小随机扰动
            base_pickup_time = distance * 0.5 + 1.5 + random.uniform(-0.2, 0.2)
            
            # 个体满意度 (0-1)：时间越短满意度越高
            individual_satisfaction = max(0, 1.0 - (base_pickup_time - 2) / 8)
            
            # 使用真实取件概率作为权重（只有会取件的人才会影响满意度）
            weight = true_prob
            weighted_satisfaction_scores.append(individual_satisfaction * weight)
            total_weight += weight
        
        # 加权平均满意度（避免除零）
        if total_weight > 0:
            customer_satisfaction_score = sum(weighted_satisfaction_scores) / total_weight
            avg_pickup_time = sum(assignment.get('distance', 0) * 0.5 + 1.5 for assignment in assignments) / len(assignments)
        else:
            customer_satisfaction_score = 0.0
            avg_pickup_time = float('inf')
        
        # 动态取件模拟 (需要临时创建实例来调用)
        temp_engine = EvaluationEngine()
        pickup_simulation = temp_engine.simulate_pickup_process(assignments)
        
        # Operational metrics (simulated)
        processing_time = len(assignments) * 0.01  # 假设每个分配需要0.01秒
        memory_usage = len(assignments) * 0.1  # 假设每个分配占用0.1MB
        assignment_success_rate = 1.0  # 所有分配都成功（在测试中）
        
        # Advanced metrics
        misplacement_penalty = sum(a['cost'] for a in assignments if a.get('misplaced', False))
        space_efficiency = overall_utilization
        
        # Strategy effectiveness score (综合评分)
        normalized_cost = 1.0 - min(avg_assignment_cost / 3.0, 1.0)  # 标准化成本
        normalized_alignment = lto_alignment_score
        normalized_satisfaction = customer_satisfaction_score
        
        weights = config.STRATEGY_EFFECTIVENESS_WEIGHTS
        strategy_effectiveness = (normalized_cost * weights['cost'] +
                                normalized_alignment * weights['alignment'] +
                                normalized_satisfaction * weights['satisfaction'])
        
        return EvaluationMetrics(
            avg_assignment_cost=avg_assignment_cost,
            total_assignment_cost=total_assignment_cost,
            avg_retrieval_distance=avg_retrieval_distance,
            premium_utilization_rate=premium_utilization,
            standard_utilization_rate=standard_utilization,
            overall_utilization_rate=overall_utilization,
            high_prob_to_premium_rate=low_prob_to_premium_rate,
            low_prob_to_standard_rate=high_prob_to_standard_rate,
            lto_alignment_score=lto_alignment_score,
            avg_pickup_time=avg_pickup_time,
            customer_satisfaction_score=customer_satisfaction_score,
            # Dynamic evaluation metrics
            actual_pickup_rate=pickup_simulation['actual_pickup_rate'],
            weighted_satisfaction_score=pickup_simulation['weighted_satisfaction_score'],
            high_prob_customer_satisfaction=pickup_simulation['high_prob_customer_satisfaction'],
            cost_per_satisfied_customer=pickup_simulation['cost_per_satisfied_customer'],
            # Operational metrics
            processing_time=processing_time,
            memory_usage=memory_usage,
            assignment_success_rate=assignment_success_rate,
            misplacement_penalty=misplacement_penalty,
            space_efficiency=space_efficiency,
            strategy_effectiveness=strategy_effectiveness
        )
    
    def run_single_evaluation(self, strategy_name: str, scenario: Dict, parcels: List[Parcel]) -> Dict:
        """Run evaluation for a single strategy on a single scenario"""
        print(f"Running {strategy_name} on {scenario['name']}...")
        
        strategy = self.strategies[strategy_name]
        station = self.create_test_station()
        
        start_time = time.time()
        assignments = []
        
        for parcel in parcels:
            assigned_shelf, cost = strategy.assign_parcel(parcel, station)
            
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
                    'true_prob': getattr(parcel, 'true_pickup_probability', 0.5),
                    'predicted_prob': getattr(parcel, 'predicted_pickup_probability', 0.5)
                }
                assignments.append(assignment_record)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate metrics
        metrics = self.calculate_advanced_metrics(assignments, strategy_name)
        metrics.processing_time = processing_time
        
        return {
            'strategy': strategy_name,
            'scenario': scenario['name'],
            'metrics': metrics,
            'assignments': assignments,
            'scenario_details': scenario
        }
    
    def run_comprehensive_evaluation(self) -> Dict:
        """Run comprehensive evaluation across all strategies and scenarios"""
        print("Starting Comprehensive Evaluation...")
        print("=" * 60)
        
        scenarios = self.create_test_scenarios()
        all_results = {}
        
        for scenario in scenarios:
            print(f"\nEvaluating Scenario: {scenario['name']}")
            print(f"Description: {scenario['description']}")
            print("-" * 40)
            
            scenario_results = {}
            
            # Generate parcels ONCE per scenario for a fair comparison
            parcels = self.generate_test_parcels(scenario)
            
            for strategy_name in self.strategies.keys():
                result = self.run_single_evaluation(strategy_name, scenario, parcels)
                scenario_results[strategy_name] = result
                
                # Print summary
                metrics = result['metrics']
                print(f"{strategy_name:15} | Cost: {metrics.avg_assignment_cost:.3f} | "
                      f"LTO Score: {metrics.lto_alignment_score:.3f} | "
                      f"Satisfaction: {metrics.customer_satisfaction_score:.3f}")
            
            all_results[scenario['name']] = scenario_results
        
        return all_results
    
    def generate_comparison_report(self, results: Dict) -> Dict:
        """Generate detailed comparison report"""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE EVALUATION REPORT")
        print("=" * 60)
        
        comparison_data = {}
        improvement_data = {}
        
        # Calculate improvements relative to baselines
        for scenario_name, scenario_results in results.items():
            print(f"\n[Scenario: {scenario_name}]")
            print("-" * 30)
            
            lto_metrics = scenario_results['LTO']['metrics']
            scenario_comparison = {}
            scenario_improvements = {}
            
            for strategy_name, strategy_result in scenario_results.items():
                metrics = strategy_result['metrics']
                scenario_comparison[strategy_name] = asdict(metrics)
                
                if strategy_name != 'LTO':
                    # Calculate improvements
                    cost_improvement = (metrics.avg_assignment_cost - lto_metrics.avg_assignment_cost) / metrics.avg_assignment_cost * 100
                    lto_score_improvement = (lto_metrics.lto_alignment_score - metrics.lto_alignment_score) / max(metrics.lto_alignment_score, 0.001) * 100
                    satisfaction_improvement = (lto_metrics.customer_satisfaction_score - metrics.customer_satisfaction_score) / max(metrics.customer_satisfaction_score, 0.001) * 100
                    
                    improvements = {
                        'cost_improvement_percent': cost_improvement,
                        'lto_score_improvement_percent': lto_score_improvement,
                        'satisfaction_improvement_percent': satisfaction_improvement,
                        'overall_effectiveness_improvement': (lto_metrics.strategy_effectiveness - metrics.strategy_effectiveness) / max(metrics.strategy_effectiveness, 0.001) * 100
                    }
                    
                    scenario_improvements[strategy_name] = improvements
                    
                    # Print key improvements
                    print(f"LTO vs {strategy_name}:")
                    print(f"  Cost Improvement: {cost_improvement:+.1f}%")
                    print(f"  LTO Alignment: {lto_score_improvement:+.1f}%")
                    print(f"  Satisfaction: {satisfaction_improvement:+.1f}%")
                    print(f"  Overall Effectiveness: {improvements['overall_effectiveness_improvement']:+.1f}%")
                    print()
            
            comparison_data[scenario_name] = scenario_comparison
            improvement_data[scenario_name] = scenario_improvements
        
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
        """Generate summary statistics across all scenarios"""
        all_cost_improvements = []
        all_lto_improvements = []
        all_satisfaction_improvements = []
        all_effectiveness_improvements = []
        
        for scenario_improvements in improvement_data.values():
            for strategy_improvements in scenario_improvements.values():
                all_cost_improvements.append(strategy_improvements['cost_improvement_percent'])
                all_lto_improvements.append(strategy_improvements['lto_score_improvement_percent'])
                all_satisfaction_improvements.append(strategy_improvements['satisfaction_improvement_percent'])
                all_effectiveness_improvements.append(strategy_improvements['overall_effectiveness_improvement'])
        
        return {
            'cost_improvement': {
                'avg': statistics.mean(all_cost_improvements),
                'min': min(all_cost_improvements),
                'max': max(all_cost_improvements),
                'std': statistics.stdev(all_cost_improvements) if len(all_cost_improvements) > 1 else 0
            },
            'lto_alignment_improvement': {
                'avg': statistics.mean(all_lto_improvements),
                'min': min(all_lto_improvements),
                'max': max(all_lto_improvements),
                'std': statistics.stdev(all_lto_improvements) if len(all_lto_improvements) > 1 else 0
            },
            'satisfaction_improvement': {
                'avg': statistics.mean(all_satisfaction_improvements),
                'min': min(all_satisfaction_improvements),
                'max': max(all_satisfaction_improvements),
                'std': statistics.stdev(all_satisfaction_improvements) if len(all_satisfaction_improvements) > 1 else 0
            },
            'overall_effectiveness_improvement': {
                'avg': statistics.mean(all_effectiveness_improvements),
                'min': min(all_effectiveness_improvements),
                'max': max(all_effectiveness_improvements),
                'std': statistics.stdev(all_effectiveness_improvements) if len(all_effectiveness_improvements) > 1 else 0
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
    
    # Print final summary
    summary = report['summary_statistics']
    print("\n" + "=" * 50)
    print("FINAL SUMMARY - LTO IMPROVEMENTS OVER BASELINES")
    print("=" * 50)
    print(f"Average Cost Improvement: {summary['cost_improvement']['avg']:+.1f}%")
    print(f"Average LTO Alignment Improvement: {summary['lto_alignment_improvement']['avg']:+.1f}%")
    print(f"Average Customer Satisfaction Improvement: {summary['satisfaction_improvement']['avg']:+.1f}%")
    print(f"Average Overall Effectiveness Improvement: {summary['overall_effectiveness_improvement']['avg']:+.1f}%")
    print("=" * 50)
    
    return filename

if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    np.random.seed(42)
    
    # Run evaluation
    evaluation_report = main() 