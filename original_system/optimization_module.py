"""
Optimization module for the Cainiao Parcel Station LTO system.

This module implements the Storage Location Assignment Problem (SLAP) optimization
with multiple objectives:
1. Customer convenience (distance to exit)
2. Employee workload (distance from entrance + handling effort)
3. System efficiency (shelf utilization + spatial balance)
4. Future flexibility (reserving space for high-probability parcels)
"""

from typing import List, Optional, Tuple, Dict
import logging
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta

from data_structures import Parcel, Shelf, ParcelStation, ShelfType, ParcelSize
import config

@dataclass
class OptimizationWeights:
    """Weights for different components of the cost function"""
    customer_convenience: float = 0.4  # Weight for customer distance cost
    employee_workload: float = 0.3     # Weight for employee effort cost
    system_efficiency: float = 0.2     # Weight for system utilization cost
    future_flexibility: float = 0.1    # Weight for future space reservation

class SLAPOptimizer:
    """
    Implements Storage Location Assignment Problem (SLAP) optimization.
    
    The optimization considers:
    1. Customer convenience (distance to exit)
    2. Employee workload (distance from entrance + handling effort)
    3. System efficiency (shelf utilization + spatial balance)
    4. Future flexibility (reserving space for high-probability parcels)
    """
    
    def __init__(self, weights: Optional[OptimizationWeights] = None):
        self.weights = weights or OptimizationWeights()
        self.logger = logging.getLogger(__name__)
        
        # Time-based batch processing
        self.current_batch = []
        self.batch_start_time = None
        self.last_reoptimization = None
    
    def add_parcel_to_batch(self, parcel: Parcel, current_time: datetime) -> bool:
        """
        Add parcel to current batch for time-window optimization.
        
        Args:
            parcel: Parcel to add to batch
            current_time: Current simulation time
            
        Returns:
            True if batch is ready for optimization, False otherwise
        """
        # Initialize batch if empty
        if not self.current_batch:
            self.batch_start_time = current_time
        
        self.current_batch.append(parcel)
        
        # Check if batch is ready for optimization
        time_window = timedelta(minutes=config.BATCH_PROCESSING['time_window_minutes'])
        max_wait = timedelta(minutes=config.BATCH_PROCESSING['max_wait_time_minutes'])
        
        batch_full = len(self.current_batch) >= config.BATCH_PROCESSING['batch_size']
        time_window_expired = (current_time - self.batch_start_time) >= time_window
        max_wait_exceeded = any((current_time - p.arrival_time) >= max_wait for p in self.current_batch)
        
        return batch_full or time_window_expired or max_wait_exceeded
    
    def optimize_current_batch(self, station: ParcelStation) -> List[Tuple[Parcel, Optional[Shelf]]]:
        """
        Optimize the current batch using global SLAP optimization.
        
        This implements true multi-objective optimization considering:
        1. All parcels in the batch simultaneously
        2. Current station state
        3. Spatial and temporal constraints
        4. Multi-objective cost minimization
        """
        if not self.current_batch:
            return []
        
        results = []
        
        # Sort parcels by composite priority score
        sorted_parcels = self._prioritize_parcels(self.current_batch)
        
        # Global optimization: consider all parcels together
        assignment_plan = self._create_global_assignment_plan(sorted_parcels, station)
        
        # Execute assignments
        for parcel, shelf in assignment_plan:
            if shelf and shelf.add_parcel(parcel):
                station.stored_parcels[parcel.parcel_id] = parcel
                self._log_assignment(parcel, shelf, 0.0, station)  # Cost will be calculated
                results.append((parcel, shelf))
            else:
                results.append((parcel, None))
        
        # Clear batch
        self.current_batch = []
        self.batch_start_time = None
        
        return results
    
    def _prioritize_parcels(self, parcels: List[Parcel]) -> List[Parcel]:
        """
        Prioritize parcels using multi-criteria scoring.
        
        Priority factors:
        1. Pickup probability (higher = more priority)
        2. Arrival time (earlier = more priority) 
        3. Size (smaller = more priority for flexibility)
        4. Urgency (longer wait = more priority)
        """
        def priority_score(parcel):
            prob_score = parcel.predicted_pickup_probability or 0.5
            
            # Time-based urgency (how long has it been waiting)
            wait_time = (datetime.now() - parcel.arrival_time).total_seconds() / 3600  # hours
            urgency_score = min(wait_time / 24, 1.0)  # Normalize to 0-1 over 24 hours
            
            # Size flexibility (smaller parcels are more flexible)
            size_scores = {ParcelSize.SMALL: 1.0, ParcelSize.MEDIUM: 0.8, ParcelSize.LARGE: 0.6}
            size_score = size_scores[parcel.size]
            
            # Composite score (weighted combination)
            return (0.5 * prob_score + 0.3 * urgency_score + 0.2 * size_score)
        
        return sorted(parcels, key=priority_score, reverse=True)
    
    def _create_global_assignment_plan(self, parcels: List[Parcel], 
                                     station: ParcelStation) -> List[Tuple[Parcel, Optional[Shelf]]]:
        """
        Create a global assignment plan considering all parcels simultaneously.
        
        This is a simplified version of the full SLAP optimization.
        For production, this could be replaced with:
        - Integer Linear Programming (ILP)
        - Constraint Programming (CP)
        - Metaheuristic algorithms (GA, SA, etc.)
        """
        assignment_plan = []
        
        # Create a copy of station state for planning
        available_capacity = {}
        for shelf in station.shelves:
            available_capacity[shelf.shelf_id] = {
                size: shelf.capacity_volume[size] - shelf.current_used_volume[size]
                for size in ParcelSize
            }
        
        # Greedy assignment with global awareness
        for parcel in parcels:
            best_shelf = None
            best_cost = float('inf')
            
            # Consider all available shelves
            for shelf in station.shelves:
                if available_capacity[shelf.shelf_id][parcel.size] > 0:
                    # Calculate comprehensive cost
                    cost = self._calculate_comprehensive_cost(parcel, shelf, station, assignment_plan)
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_shelf = shelf
            
            # Make assignment
            if best_shelf:
                assignment_plan.append((parcel, best_shelf))
                available_capacity[best_shelf.shelf_id][parcel.size] -= 1
            else:
                assignment_plan.append((parcel, None))
        
        return assignment_plan
    
    def _calculate_comprehensive_cost(self, parcel: Parcel, shelf: Shelf, 
                                    station: ParcelStation, 
                                    current_plan: List[Tuple[Parcel, Optional[Shelf]]]) -> float:
        """
        Calculate comprehensive cost considering global state and current assignment plan.
        """
        # Base costs
        customer_cost = self._calculate_customer_cost(parcel, shelf)
        employee_cost = self._calculate_employee_cost(parcel, shelf)
        system_cost = self._calculate_system_cost(shelf, station)
        future_cost = self._calculate_future_cost(parcel, shelf, station)
        
        # Global optimization adjustments
        # Consider impact on other parcels in the current plan
        congestion_penalty = self._calculate_congestion_penalty(shelf, current_plan)
        balance_bonus = self._calculate_balance_bonus(shelf, station, current_plan)
        
        total_cost = (
            self.weights.customer_convenience * customer_cost +
            self.weights.employee_workload * employee_cost +
            self.weights.system_efficiency * (system_cost + congestion_penalty - balance_bonus) +
            self.weights.future_flexibility * future_cost
        )
        
        return total_cost
    
    def _calculate_congestion_penalty(self, shelf: Shelf, 
                                    current_plan: List[Tuple[Parcel, Optional[Shelf]]]) -> float:
        """Calculate penalty for shelf congestion in current assignment plan."""
        shelf_assignments = sum(1 for _, assigned_shelf in current_plan 
                              if assigned_shelf and assigned_shelf.shelf_id == shelf.shelf_id)
        
        # Penalty increases quadratically with assignments to same shelf
        return 0.1 * (shelf_assignments ** 2)
    
    def _calculate_balance_bonus(self, shelf: Shelf, station: ParcelStation,
                               current_plan: List[Tuple[Parcel, Optional[Shelf]]]) -> float:
        """Calculate bonus for maintaining spatial balance."""
        # Count assignments to adjacent shelves in current plan
        adjacent_assignments = 0
        for shelf_id in shelf.adjacent_shelves:
            adjacent_assignments += sum(1 for _, assigned_shelf in current_plan
                                      if assigned_shelf and assigned_shelf.shelf_id == shelf_id)
        
        # Bonus for balanced distribution
        return 0.05 * min(adjacent_assignments, 2)  # Cap bonus at 2 adjacent assignments
    
    def assign_parcel_to_shelf(self, parcel: Parcel, station: ParcelStation) -> Optional[Shelf]:
        """
        Assign a parcel to the optimal shelf using SLAP optimization.
        
        The assignment considers:
        1. Customer convenience (distance to exit)
        2. Employee workload (distance from entrance + handling effort)
        3. System efficiency (shelf utilization + spatial balance)
        4. Future flexibility (reserving space for high-probability parcels)
        
        Args:
            parcel: The parcel to assign
            station: The parcel station
            
        Returns:
            The optimal shelf for assignment, or None if no suitable shelf
        """
        if parcel.predicted_pickup_probability is None:
            raise ValueError(f"Parcel {parcel.parcel_id} must have predicted probability")
        
        available_shelves = station.get_available_shelves(parcel.size)
        if not available_shelves:
            self.logger.warning(f"No available shelves for parcel {parcel.parcel_id}")
            return None
        
        # Calculate costs for each available shelf
        shelf_costs = self._calculate_shelf_costs(parcel, available_shelves, station)
        
        # Select shelf with minimum total cost
        best_shelf = min(shelf_costs.items(), key=lambda x: x[1])[0]
        
        # Assign parcel to selected shelf
        if best_shelf.add_parcel(parcel):
            station.stored_parcels[parcel.parcel_id] = parcel
            self._log_assignment(parcel, best_shelf, shelf_costs[best_shelf], station)
            return best_shelf
        
        return None
    
    def _calculate_shelf_costs(self, parcel: Parcel, 
                             available_shelves: List[Shelf],
                             station: ParcelStation) -> Dict[Shelf, float]:
        """
        Calculate comprehensive costs for each available shelf.
        
        The cost function considers:
        1. Customer convenience cost
        2. Employee workload cost
        3. System efficiency cost
        4. Future flexibility cost
        """
        costs = {}
        
        for shelf in available_shelves:
            # 1. Customer convenience cost
            customer_cost = self._calculate_customer_cost(parcel, shelf)
            
            # 2. Employee workload cost
            employee_cost = self._calculate_employee_cost(parcel, shelf)
            
            # 3. System efficiency cost
            system_cost = self._calculate_system_cost(shelf, station)
            
            # 4. Future flexibility cost
            future_cost = self._calculate_future_cost(parcel, shelf, station)
            
            # Combine costs with weights
            total_cost = (
                self.weights.customer_convenience * customer_cost +
                self.weights.employee_workload * employee_cost +
                self.weights.system_efficiency * system_cost +
                self.weights.future_flexibility * future_cost
            )
            
            costs[shelf] = total_cost
        
        return costs
    
    def _calculate_customer_cost(self, parcel: Parcel, shelf: Shelf) -> float:
        """Calculate customer convenience cost"""
        # Base distance cost
        distance_cost = shelf.distance_to_exit
        
        # Adjust based on parcel size (larger parcels are more inconvenient)
        size_factor = {
            ParcelSize.SMALL: 1.0,
            ParcelSize.MEDIUM: 1.2,
            ParcelSize.LARGE: 1.5
        }[parcel.size]
        
        # Adjust based on pickup probability
        # High probability parcels should be more convenient
        probability_factor = 1.0 - (parcel.predicted_pickup_probability * 0.5)
        
        return distance_cost * size_factor * probability_factor
    
    def _calculate_employee_cost(self, parcel: Parcel, shelf: Shelf) -> float:
        """Calculate employee workload cost"""
        # Base distance cost from entrance
        distance_cost = shelf.distance_from_entrance
        
        # Current workload on the shelf
        workload_cost = shelf.get_workload_score()
        
        # Parcel size factor (larger parcels are more work)
        size_factor = {
            ParcelSize.SMALL: 1.0,
            ParcelSize.MEDIUM: 1.3,
            ParcelSize.LARGE: 1.8
        }[parcel.size]
        
        return (distance_cost + workload_cost) * size_factor
    
    def _calculate_system_cost(self, shelf: Shelf, station: ParcelStation) -> float:
        """Calculate system efficiency cost"""
        # Current utilization
        utilization_cost = shelf.get_utilization_rate()
        
        # Spatial balance cost (penalize uneven distribution)
        # shelf.adjacent_shelves contains shelf_ids, not positions
        adjacent_shelves = []
        for shelf_id in shelf.adjacent_shelves:
            # Find the shelf object by shelf_id
            adjacent_shelf = next((s for s in station.shelves if s.shelf_id == shelf_id), None)
            if adjacent_shelf:
                adjacent_shelves.append(adjacent_shelf)
        
        if adjacent_shelves:
            avg_utilization = np.mean([s.get_utilization_rate() 
                                     for s in adjacent_shelves])
            balance_cost = abs(utilization_cost - avg_utilization)
        else:
            balance_cost = 0
        
        return utilization_cost + balance_cost
    
    def _calculate_future_cost(self, parcel: Parcel, shelf: Shelf, 
                             station: ParcelStation) -> float:
        """Calculate future flexibility cost"""
        # Reserve premium shelves for high probability parcels
        if shelf.location_type == ShelfType.PREMIUM:
            if parcel.predicted_pickup_probability < 0.7:
                return 1.0  # High penalty for using premium shelf for low probability
        
        # Consider shelf's remaining capacity
        remaining_capacity = sum(shelf.capacity_volume.values()) - \
                           sum(shelf.current_used_volume.values())
        capacity_factor = 1.0 - (remaining_capacity / sum(shelf.capacity_volume.values()))
        
        return capacity_factor
    
    def _log_assignment(self, parcel: Parcel, shelf: Shelf, total_cost: float, station: ParcelStation):
        """Log the assignment decision with detailed cost breakdown"""
        if config.LOG_DETAILED_ASSIGNMENTS:
            customer_cost = self._calculate_customer_cost(parcel, shelf)
            employee_cost = self._calculate_employee_cost(parcel, shelf)
            system_cost = self._calculate_system_cost(shelf, station)
            future_cost = self._calculate_future_cost(parcel, shelf, station)
            
            log_message = (
                f"SLAP ASSIGNMENT: Parcel {parcel.parcel_id} "
                f"(Size: {parcel.size.value}, Prob: {parcel.predicted_pickup_probability:.3f}) "
                f"-> Shelf {shelf.shelf_id} "
                f"(Type: {shelf.location_type.value}, "
                f"Customer: {customer_cost:.3f}, Employee: {employee_cost:.3f}, "
                f"System: {system_cost:.3f}, Future: {future_cost:.3f}, "
                f"Total: {total_cost:.3f})"
            )
            self.logger.info(log_message)
    
    def batch_assign_parcels(self, parcels: List[Parcel], 
                            station: ParcelStation) -> List[Tuple[Parcel, Optional[Shelf]]]:
        """
        Assign multiple parcels in batch using SLAP optimization.
        
        This implements a rolling horizon approach:
        1. Sort parcels by priority
        2. Process in small batches
        3. Re-evaluate after each batch
        """
        results = []
        
        # Sort parcels by priority (high probability first)
        sorted_parcels = sorted(parcels, 
                              key=lambda p: p.predicted_pickup_probability or 0, 
                              reverse=True)
        
        # Process in batches of 5
        batch_size = 5
        for i in range(0, len(sorted_parcels), batch_size):
            batch = sorted_parcels[i:i + batch_size]
            
            # Assign each parcel in the batch
            for parcel in batch:
                assigned_shelf = self.assign_parcel_to_shelf(parcel, station)
                results.append((parcel, assigned_shelf))
            
            # Re-evaluate system state after batch
            self._update_system_state(station)
        
        return results
    
    def _update_system_state(self, station: ParcelStation):
        """Update system state after batch assignment"""
        # Update shelf utilization metrics
        for shelf in station.shelves:
            shelf.get_utilization_rate()
            shelf.get_workload_score()
        
        # Update spatial balance metrics
        for shelf in station.shelves:
            station._update_adjacent_shelves(shelf)


def create_optimizer(optimizer_type: str = "slap") -> SLAPOptimizer:
    """
    Factory function to create the appropriate optimizer.
    
    Args:
        optimizer_type: Type of optimizer ("slap")
        
    Returns:
        Configured optimizer instance
    """
    if optimizer_type == "slap":
        return SLAPOptimizer()
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")


# Example usage and testing
if __name__ == "__main__":
    from learning_module import create_predictor
    from data_structures import ParcelSize
    
    # Create test setup
    station = ParcelStation()
    
    # Add some shelves
    premium_shelves = [
        Shelf(f"P{i+1}", ShelfType.PREMIUM, distance_to_exit=config.SHELF_DISTANCE_SCORES['premium'][i])
        for i in range(config.PREMIUM_SHELF_COUNT)
    ]
    
    standard_shelves = [
        Shelf(f"S{i+1}", ShelfType.STANDARD, distance_to_exit=config.SHELF_DISTANCE_SCORES['standard'][i])
        for i in range(config.STANDARD_SHELF_COUNT)
    ]
    
    for shelf in premium_shelves + standard_shelves:
        station.add_shelf(shelf)
    
    # Create test parcels
    current_time = datetime(2024, 6, 10, 9, 0)
    test_parcels = [
        Parcel("P001", current_time - timedelta(minutes=30), ParcelSize.SMALL),
        Parcel("P002", current_time - timedelta(minutes=15), ParcelSize.MEDIUM),
        Parcel("P003", current_time - timedelta(minutes=45), ParcelSize.LARGE),
        Parcel("P004", current_time - timedelta(minutes=10), ParcelSize.SMALL),
    ]
    
    # Predict probabilities
    predictor = create_predictor("rule_based")
    for parcel in test_parcels:
        parcel.predicted_pickup_probability = predictor.predict_pickup_probability(parcel, current_time)
    
    # Test optimization
    optimizer = create_optimizer("slap")
    
    print("Testing Optimization Module:")
    print("=" * 50)
    
    for parcel in test_parcels:
        assigned_shelf = optimizer.assign_parcel_to_shelf(parcel, station)
        if assigned_shelf:
            print(f"✓ {parcel} -> {assigned_shelf}")
        else:
            print(f"✗ Failed to assign {parcel}")
    
    print("\nOptimization module test completed!") 