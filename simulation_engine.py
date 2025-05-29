"""
Simulation engine for the Cainiao Parcel Station LTO system.

This module orchestrates the entire LTO simulation by:
1. Generating parcel arrivals over time
2. Using the learning module to predict pickup probabilities
3. Using the optimization module to assign parcels to shelves
4. Collecting and analyzing results

This demonstrates the complete "Learn-then-Optimize" workflow.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
from learning_module import create_predictor
from optimization_module import create_optimizer
import config


class ParcelGenerator:
    """
    Generates realistic parcel arrivals for simulation.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize the parcel generator.
        
        Args:
            seed: Random seed for reproducible results
        """
        if seed is not None:
            random.seed(seed)
        self.parcel_counter = 0
    
    def generate_parcels_for_time_step(self, current_time: datetime, time_step_minutes: int) -> List[Parcel]:
        """
        Generate parcels that arrive during a specific time step.
        
        Args:
            current_time: Current simulation time
            time_step_minutes: Duration of the time step in minutes
            
        Returns:
            List of parcels that arrived during this time step
        """
        # Determine time period and arrival rate
        hour = current_time.hour
        time_period = config.get_time_period(hour)
        arrival_rate = config.PARCEL_ARRIVAL_RATES.get(time_period, 5)  # parcels per hour
        
        # Calculate expected arrivals for this time step
        expected_arrivals = arrival_rate * (time_step_minutes / 60.0)
        
        # Use Poisson distribution for realistic arrival patterns
        num_arrivals = max(0, int(random.normalvariate(expected_arrivals, expected_arrivals * 0.3)))
        
        parcels = []
        for _ in range(num_arrivals):
            # Generate random arrival time within the time step
            arrival_offset = random.uniform(0, time_step_minutes)
            arrival_time = current_time + timedelta(minutes=arrival_offset)
            
            # Generate parcel size based on distribution
            size = self._generate_parcel_size()
            
            # Create parcel
            self.parcel_counter += 1
            parcel_id = f"P{self.parcel_counter:04d}"
            parcel = Parcel(parcel_id, arrival_time, size)
            parcels.append(parcel)
        
        return parcels
    
    def _generate_parcel_size(self) -> ParcelSize:
        """
        Generate a random parcel size based on configured distribution.
        
        Returns:
            Random parcel size
        """
        rand = random.random()
        cumulative = 0.0
        
        for size, probability in config.PARCEL_SIZE_DISTRIBUTION.items():
            cumulative += probability
            if rand <= cumulative:
                return size
        
        # Fallback to small if something goes wrong
        return ParcelSize.SMALL


class SimulationEngine:
    """
    Main simulation engine that orchestrates the LTO process.
    """
    
    def __init__(self, predictor_type: str = "rule_based", optimizer_type: str = "greedy"):
        """
        Initialize the simulation engine.
        
        Args:
            predictor_type: Type of learning predictor to use
            optimizer_type: Type of optimizer to use
        """
        # Initialize components
        self.station = ParcelStation()
        self.parcel_generator = ParcelGenerator(config.RANDOM_SEED)
        self.predictor = create_predictor(predictor_type)
        self.optimizer = create_optimizer(optimizer_type)
        
        # Simulation state
        self.current_time = None
        self.simulation_results = {
            'assignments': [],
            'time_steps': [],
            'final_statistics': {}
        }
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
        self.logger = logging.getLogger(__name__)
        
        # Initialize shelves (after logger is set up)
        self._initialize_shelves()
    
    def _initialize_shelves(self):
        """
        Initialize the parcel station with configured shelves.
        """
        # Create premium shelves
        for i in range(config.PREMIUM_SHELF_COUNT):
            shelf_id = f"P{i+1}"
            distance = config.SHELF_DISTANCE_SCORES['premium'][i]
            capacity = config.SHELF_CAPACITY['premium']
            
            shelf = Shelf(
                shelf_id=shelf_id,
                location_type=ShelfType.PREMIUM,
                capacity_small=capacity[ParcelSize.SMALL],
                capacity_medium=capacity[ParcelSize.MEDIUM],
                capacity_large=capacity[ParcelSize.LARGE],
                distance_to_exit=distance
            )
            self.station.add_shelf(shelf)
        
        # Create standard shelves
        for i in range(config.STANDARD_SHELF_COUNT):
            shelf_id = f"S{i+1}"
            distance = config.SHELF_DISTANCE_SCORES['standard'][i]
            capacity = config.SHELF_CAPACITY['standard']
            
            shelf = Shelf(
                shelf_id=shelf_id,
                location_type=ShelfType.STANDARD,
                capacity_small=capacity[ParcelSize.SMALL],
                capacity_medium=capacity[ParcelSize.MEDIUM],
                capacity_large=capacity[ParcelSize.LARGE],
                distance_to_exit=distance
            )
            self.station.add_shelf(shelf)
        
        self.logger.info(f"Initialized station with {len(self.station.shelves)} shelves")
    
    def run_simulation(self) -> Dict[str, Any]:
        """
        Run the complete LTO simulation.
        
        Returns:
            Dictionary containing simulation results
        """
        self.logger.info("Starting LTO simulation")
        
        # Initialize simulation time
        start_date = datetime(2024, 6, 10, config.SIMULATION_START_HOUR, 0)
        self.current_time = start_date
        
        # Calculate total time steps
        total_minutes = config.SIMULATION_HOURS * 60
        time_step_minutes = config.TIME_STEP_MINUTES
        num_time_steps = total_minutes // time_step_minutes
        
        self.logger.info(f"Simulation: {config.SIMULATION_HOURS} hours, {num_time_steps} time steps")
        
        # Main simulation loop
        for step in range(num_time_steps):
            self._simulate_time_step(step, time_step_minutes)
            
            # Advance time
            self.current_time += timedelta(minutes=time_step_minutes)
        
        # Finalize results
        self._finalize_simulation()
        
        self.logger.info("Simulation completed")
        return self.simulation_results
    
    def _simulate_time_step(self, step: int, time_step_minutes: int):
        """
        Simulate a single time step of the LTO process.
        
        Args:
            step: Current time step number
            time_step_minutes: Duration of time step in minutes
        """
        step_start_time = self.current_time
        
        # 1. Generate new parcel arrivals
        new_parcels = self.parcel_generator.generate_parcels_for_time_step(
            self.current_time, time_step_minutes
        )
        
        if new_parcels:
            self.logger.info(f"Step {step}: {len(new_parcels)} new parcels arrived")
        
        # 2. Process each new parcel through the LTO pipeline
        step_assignments = []
        for parcel in new_parcels:
            # LEARN: Predict pickup probability
            parcel.predicted_pickup_probability = self.predictor.predict_pickup_probability(
                parcel, self.current_time
            )
            
            # OPTIMIZE: Assign to best shelf
            assigned_shelf = self.optimizer.assign_parcel_to_shelf(parcel, self.station)
            
            if assigned_shelf:
                step_assignments.append({
                    'parcel_id': parcel.parcel_id,
                    'predicted_probability': parcel.predicted_pickup_probability,
                    'assigned_shelf': assigned_shelf.shelf_id,
                    'shelf_type': assigned_shelf.location_type.value,
                    'assignment_cost': assigned_shelf.distance_to_exit * (1 - parcel.predicted_pickup_probability)
                })
            else:
                self.logger.warning(f"Failed to assign parcel {parcel.parcel_id}")
        
        # 3. Record time step results
        time_step_result = {
            'step': step,
            'time': step_start_time.isoformat(),
            'new_parcels': len(new_parcels),
            'successful_assignments': len(step_assignments),
            'station_stats': self.station.get_station_statistics(),
            'assignments': step_assignments
        }
        
        self.simulation_results['time_steps'].append(time_step_result)
        self.simulation_results['assignments'].extend(step_assignments)
        
        # Log progress
        if step % 5 == 0 or len(new_parcels) > 0:
            stats = self.station.get_station_statistics()
            self.logger.info(
                f"Step {step} ({self.current_time.strftime('%H:%M')}): "
                f"{stats['total_stored_parcels']} parcels stored, "
                f"Premium util: {stats['avg_premium_utilization']:.2f}, "
                f"Standard util: {stats['avg_standard_utilization']:.2f}"
            )
    
    def _finalize_simulation(self):
        """
        Finalize simulation and compute final statistics.
        """
        # Get final station statistics
        final_station_stats = self.station.get_station_statistics()
        
        # Get optimizer statistics
        optimizer_stats = self.optimizer.get_assignment_statistics()
        
        # Compute additional metrics
        total_assignments = len(self.simulation_results['assignments'])
        if total_assignments > 0:
            avg_cost = sum(a['assignment_cost'] for a in self.simulation_results['assignments']) / total_assignments
            premium_ratio = len([a for a in self.simulation_results['assignments'] if a['shelf_type'] == 'premium']) / total_assignments
        else:
            avg_cost = 0
            premium_ratio = 0
        
        # Compile final statistics
        self.simulation_results['final_statistics'] = {
            'simulation_duration_hours': config.SIMULATION_HOURS,
            'total_parcels_processed': total_assignments,
            'avg_assignment_cost': avg_cost,
            'premium_assignment_ratio': premium_ratio,
            'final_station_stats': final_station_stats,
            'optimizer_stats': optimizer_stats,
            'lto_effectiveness': self._calculate_lto_effectiveness()
        }
        
        # Save results if configured
        if config.SAVE_RESULTS:
            self._save_results()
    
    def _calculate_lto_effectiveness(self) -> Dict[str, float]:
        """
        Calculate metrics to evaluate LTO effectiveness.
        
        Returns:
            Dictionary with effectiveness metrics
        """
        assignments = self.simulation_results['assignments']
        if not assignments:
            return {}
        
        # Calculate how well high-probability parcels got premium shelves
        high_prob_assignments = [a for a in assignments if a['predicted_probability'] >= config.HIGH_PROBABILITY_THRESHOLD]
        high_prob_to_premium = len([a for a in high_prob_assignments if a['shelf_type'] == 'premium'])
        high_prob_premium_rate = high_prob_to_premium / len(high_prob_assignments) if high_prob_assignments else 0
        
        # Calculate how well low-probability parcels avoided premium shelves
        low_prob_assignments = [a for a in assignments if a['predicted_probability'] < config.HIGH_PROBABILITY_THRESHOLD]
        low_prob_to_standard = len([a for a in low_prob_assignments if a['shelf_type'] == 'standard'])
        low_prob_standard_rate = low_prob_to_standard / len(low_prob_assignments) if low_prob_assignments else 0
        
        # Overall LTO alignment score
        lto_alignment = (high_prob_premium_rate + low_prob_standard_rate) / 2
        
        return {
            'high_prob_to_premium_rate': high_prob_premium_rate,
            'low_prob_to_standard_rate': low_prob_standard_rate,
            'lto_alignment_score': lto_alignment,
            'avg_premium_probability': sum(a['predicted_probability'] for a in assignments if a['shelf_type'] == 'premium') / len([a for a in assignments if a['shelf_type'] == 'premium']) if any(a['shelf_type'] == 'premium' for a in assignments) else 0,
            'avg_standard_probability': sum(a['predicted_probability'] for a in assignments if a['shelf_type'] == 'standard') / len([a for a in assignments if a['shelf_type'] == 'standard']) if any(a['shelf_type'] == 'standard' for a in assignments) else 0
        }
    
    def _save_results(self):
        """
        Save simulation results to file.
        """
        try:
            with open(config.RESULTS_FILENAME, 'w') as f:
                json.dump(self.simulation_results, f, indent=2, default=str)
            self.logger.info(f"Results saved to {config.RESULTS_FILENAME}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
    
    def print_summary(self):
        """
        Print a summary of simulation results.
        """
        stats = self.simulation_results['final_statistics']
        
        print("\n" + "="*60)
        print("CAINIAO PARCEL STATION LTO SIMULATION SUMMARY")
        print("="*60)
        
        print(f"Simulation Duration: {stats['simulation_duration_hours']} hours")
        print(f"Total Parcels Processed: {stats['total_parcels_processed']}")
        print(f"Average Assignment Cost: {stats['avg_assignment_cost']:.3f}")
        print(f"Premium Shelf Usage: {stats['premium_assignment_ratio']:.1%}")
        
        print("\nLTO Effectiveness Metrics:")
        print("-" * 30)
        effectiveness = stats['lto_effectiveness']
        print(f"High-prob → Premium Rate: {effectiveness.get('high_prob_to_premium_rate', 0):.1%}")
        print(f"Low-prob → Standard Rate: {effectiveness.get('low_prob_to_standard_rate', 0):.1%}")
        print(f"Overall LTO Alignment: {effectiveness.get('lto_alignment_score', 0):.1%}")
        
        print("\nFinal Station Status:")
        print("-" * 30)
        station_stats = stats['final_station_stats']
        print(f"Premium Shelves Utilization: {station_stats['avg_premium_utilization']:.1%}")
        print(f"Standard Shelves Utilization: {station_stats['avg_standard_utilization']:.1%}")
        print(f"Total Stored Parcels: {station_stats['total_stored_parcels']}")
        
        print("\n" + "="*60)


# Example usage and testing
if __name__ == "__main__":
    print("Starting Cainiao Parcel Station LTO Simulation")
    print("=" * 50)
    
    # Create and run simulation
    simulation = SimulationEngine(
        predictor_type="rule_based",
        optimizer_type="greedy"
    )
    
    # Run the simulation
    results = simulation.run_simulation()
    
    # Print summary
    simulation.print_summary()
    
    print(f"\nDetailed results saved to: {config.RESULTS_FILENAME}")
    print("Simulation completed successfully!") 