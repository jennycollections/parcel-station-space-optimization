"""
Optimization module for the Cainiao Parcel Station LTO system.

This module implements the "Optimization" component of the LTO framework.
It uses the predicted pickup probabilities from the learning module to make
intelligent parcel-to-shelf assignment decisions.

The core objective is to minimize: sum(D_j * (1 - p_hat_i) * x_ij)
where D_j is the distance/inconvenience score of shelf j,
p_hat_i is the predicted pickup probability of parcel i,
and x_ij is 1 if parcel i is assigned to shelf j.
"""

from typing import List, Optional, Tuple
import logging

from data_structures import Parcel, Shelf, ParcelStation, ShelfType
import config


class ParcelAssignmentOptimizer:
    """
    Optimizes parcel-to-shelf assignments based on predicted pickup probabilities.
    
    This is the core "Optimization" component of the LTO system.
    Currently implements a greedy heuristic but can be extended with more
    sophisticated optimization algorithms.
    """
    
    def __init__(self, log_assignments: bool = True):
        """
        Initialize the optimizer.
        
        Args:
            log_assignments: Whether to log assignment decisions
        """
        self.log_assignments = log_assignments
        self.assignment_history = []  # Track assignment decisions for analysis
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
        self.logger = logging.getLogger(__name__)
    
    def assign_parcel_to_shelf(self, parcel: Parcel, station: ParcelStation) -> Optional[Shelf]:
        """
        Assign a parcel to the best available shelf based on LTO strategy.
        
        This is the main optimization function that implements the decision logic:
        - High probability parcels (p_hat > threshold) prefer premium shelves
        - Low probability parcels are assigned to standard shelves
        - Within each category, choose the shelf with lowest cost
        
        Args:
            parcel: The parcel to assign (must have predicted_pickup_probability set)
            station: The parcel station with available shelves
            
        Returns:
            The shelf where the parcel was assigned, or None if assignment failed
        """
        if parcel.predicted_pickup_probability is None:
            raise ValueError(f"Parcel {parcel.parcel_id} must have predicted probability before assignment")
        
        # The optimizer should search across ALL available shelves to find the true minimum cost,
        # aligning with the pure mathematical objective of min(D * (1-p)).
        # The previous hard-coded rule (_determine_preferred_shelf_type) created a conflict.
        available_shelves = station.get_available_shelves(parcel.size)
        
        if not available_shelves:
            self.logger.warning(f"No available shelves for parcel {parcel.parcel_id} (size: {parcel.size.value})")
            return None
        
        # Select the best shelf using cost-based optimization
        best_shelf = self._select_best_shelf(parcel, available_shelves)
        
        # Assign the parcel to the selected shelf
        if best_shelf.add_parcel(parcel):
            station.stored_parcels[parcel.parcel_id] = parcel
            
            # Log the assignment
            if self.log_assignments:
                self._log_assignment(parcel, best_shelf)
            
            # Record assignment for analysis
            self._record_assignment(parcel, best_shelf)
            
            return best_shelf
        else:
            self.logger.error(f"Failed to assign parcel {parcel.parcel_id} to shelf {best_shelf.shelf_id}")
            return None
    
    def _determine_preferred_shelf_type(self, pickup_probability: float) -> ShelfType:
        """
        Determine the preferred shelf type based on pickup probability.
        
        High probability parcels prefer premium (convenient) shelves.
        Low probability parcels are assigned to standard shelves.
        
        Args:
            pickup_probability: Predicted pickup probability (0-1)
            
        Returns:
            Preferred shelf type
        """
        if pickup_probability >= config.HIGH_PROBABILITY_THRESHOLD:
            return ShelfType.PREMIUM
        else:
            return ShelfType.STANDARD
    
    def _select_best_shelf(self, parcel: Parcel, available_shelves: List[Shelf]) -> Shelf:
        """
        Select the best shelf from available options using cost optimization.
        
        Implements the cost function: D_j * (1 - p_hat_i)
        Lower cost is better.
        
        Args:
            parcel: The parcel to assign
            available_shelves: List of shelves that can accommodate the parcel
            
        Returns:
            The shelf with the lowest cost
        """
        best_shelf = None
        best_cost = float('inf')
        
        p_hat = parcel.predicted_pickup_probability
        
        for shelf in available_shelves:
            # Calculate cost: D_j * (1 - p_hat_i)
            cost = shelf.distance_to_exit * (1 - p_hat)
            
            # Add small penalty for utilization to encourage load balancing
            utilization_penalty = shelf.get_utilization_rate() * config.COST_FUNCTION_PARAMS['utilization_penalty']
            total_cost = cost + utilization_penalty
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_shelf = shelf
        
        return best_shelf
    
    def _log_assignment(self, parcel: Parcel, shelf: Shelf):
        """
        Log the assignment decision.
        
        Args:
            parcel: The assigned parcel
            shelf: The shelf where parcel was assigned
        """
        cost = shelf.distance_to_exit * (1 - parcel.predicted_pickup_probability)
        
        log_message = (
            f"ASSIGNMENT: Parcel {parcel.parcel_id} "
            f"(Size: {parcel.size.value}, Prob: {parcel.predicted_pickup_probability:.3f}) "
            f"-> Shelf {shelf.shelf_id} "
            f"(Type: {shelf.location_type.value}, Distance: {shelf.distance_to_exit}, Cost: {cost:.3f})"
        )
        
        if config.LOG_DETAILED_ASSIGNMENTS:
            self.logger.info(log_message)
    
    def _record_assignment(self, parcel: Parcel, shelf: Shelf):
        """
        Record assignment for later analysis.
        
        Args:
            parcel: The assigned parcel
            shelf: The shelf where parcel was assigned
        """
        assignment_record = {
            'parcel_id': parcel.parcel_id,
            'parcel_size': parcel.size.value,
            'predicted_probability': parcel.predicted_pickup_probability,
            'shelf_id': shelf.shelf_id,
            'shelf_type': shelf.location_type.value,
            'shelf_distance': shelf.distance_to_exit,
            'assignment_cost': shelf.distance_to_exit * (1 - parcel.predicted_pickup_probability),
            'shelf_utilization_before': shelf.get_utilization_rate()
        }
        
        self.assignment_history.append(assignment_record)
    
    def get_assignment_statistics(self) -> dict:
        """
        Get statistics about assignment decisions.
        
        Returns:
            Dictionary with assignment statistics
        """
        if not self.assignment_history:
            return {}
        
        # Separate assignments by shelf type
        premium_assignments = [a for a in self.assignment_history if a['shelf_type'] == 'premium']
        standard_assignments = [a for a in self.assignment_history if a['shelf_type'] == 'standard']
        
        # Calculate statistics
        stats = {
            'total_assignments': len(self.assignment_history),
            'premium_assignments': len(premium_assignments),
            'standard_assignments': len(standard_assignments),
            'avg_cost_all': sum(a['assignment_cost'] for a in self.assignment_history) / len(self.assignment_history),
            'avg_probability_premium': sum(a['predicted_probability'] for a in premium_assignments) / len(premium_assignments) if premium_assignments else 0,
            'avg_probability_standard': sum(a['predicted_probability'] for a in standard_assignments) / len(standard_assignments) if standard_assignments else 0,
            'high_prob_to_premium_ratio': len([a for a in premium_assignments if a['predicted_probability'] >= config.HIGH_PROBABILITY_THRESHOLD]) / len(premium_assignments) if premium_assignments else 0,
            'low_prob_to_standard_ratio': len([a for a in standard_assignments if a['predicted_probability'] < config.HIGH_PROBABILITY_THRESHOLD]) / len(standard_assignments) if standard_assignments else 0
        }
        
        return stats
    
    def batch_assign_parcels(self, parcels: List[Parcel], station: ParcelStation) -> List[Tuple[Parcel, Optional[Shelf]]]:
        """
        Assign multiple parcels in batch.
        
        This could be extended to implement more sophisticated batch optimization
        in the future (e.g., solving a small assignment problem).
        
        Args:
            parcels: List of parcels to assign
            station: The parcel station
            
        Returns:
            List of (parcel, assigned_shelf) tuples
        """
        results = []
        
        # Sort parcels by priority (high probability first)
        sorted_parcels = sorted(parcels, key=lambda p: p.predicted_pickup_probability or 0, reverse=True)
        
        for parcel in sorted_parcels:
            assigned_shelf = self.assign_parcel_to_shelf(parcel, station)
            results.append((parcel, assigned_shelf))
        
        return results


class AdvancedOptimizer(ParcelAssignmentOptimizer):
    """
    Placeholder for more advanced optimization algorithms.
    
    This could implement:
    - Integer Linear Programming (ILP) for exact optimization
    - Large Neighborhood Search (LNS) for iterative improvement
    - Multi-objective optimization considering multiple criteria
    """
    
    def __init__(self):
        super().__init__()
        self.logger.info("Advanced optimizer initialized (placeholder)")
    
    def solve_assignment_problem(self, parcels: List[Parcel], station: ParcelStation) -> dict:
        """
        Placeholder for exact optimization using mathematical programming.
        
        This would formulate and solve the assignment problem:
        minimize: sum(D_j * (1 - p_hat_i) * x_ij)
        subject to: assignment constraints
        
        Args:
            parcels: Parcels to assign
            station: Station with available shelves
            
        Returns:
            Optimization results
        """
        # Placeholder for future implementation
        # In reality, this would use libraries like PuLP, Gurobi, or CPLEX
        self.logger.info("Exact optimization not yet implemented, falling back to greedy")
        return self.batch_assign_parcels(parcels, station)


def create_optimizer(optimizer_type: str = "greedy") -> ParcelAssignmentOptimizer:
    """
    Factory function to create the appropriate optimizer.
    
    Args:
        optimizer_type: Type of optimizer ("greedy" or "advanced")
        
    Returns:
        Configured optimizer instance
    """
    if optimizer_type == "greedy":
        return ParcelAssignmentOptimizer()
    elif optimizer_type == "advanced":
        return AdvancedOptimizer()
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")


# Example usage and testing
if __name__ == "__main__":
    from datetime import datetime, timedelta
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
    optimizer = create_optimizer("greedy")
    
    print("Testing Optimization Module:")
    print("=" * 50)
    
    for parcel in test_parcels:
        assigned_shelf = optimizer.assign_parcel_to_shelf(parcel, station)
        if assigned_shelf:
            print(f"✓ {parcel} -> {assigned_shelf}")
        else:
            print(f"✗ Failed to assign {parcel}")
    
    print("\nAssignment Statistics:")
    print("-" * 30)
    stats = optimizer.get_assignment_statistics()
    for key, value in stats.items():
        print(f"{key}: {value:.3f}" if isinstance(value, float) else f"{key}: {value}")
    
    print("\nOptimization module test completed!") 