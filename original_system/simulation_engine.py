"""
Simulation engine for the Cainiao Parcel Station LTO system.

This module implements the core simulation logic, including:
1. Station initialization with matrix-based layout
2. Parcel generation and arrival
3. Worker assignment and movement
4. Event processing and state updates
"""

from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
import random
import numpy as np

from data_structures import Parcel, Shelf, ParcelStation, ShelfType, ParcelSize
from learning_module import PickupProbabilityPredictor
from optimization_module import SLAPOptimizer
import config

class SimulationEngine:
    """
    Main simulation engine for the parcel station.
    
    Features:
    1. Matrix-based station layout
    2. Realistic parcel generation
    3. Worker simulation
    4. Event-driven processing
    """
    
    def __init__(self):
        """Initialize the simulation engine"""
        self.station = ParcelStation(rows=config.STATION_ROWS, cols=config.STATION_COLS)
        self.learning_module = PickupProbabilityPredictor()
        self.optimizer = SLAPOptimizer()
        self.current_time = datetime.now()
        self.pending_parcels: List[Parcel] = []
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
        self.logger = logging.getLogger(__name__)
        
        # Initialize station
        self._initialize_shelves()
    
    def _initialize_shelves(self):
        """Initialize the parcel station with matrix-based layout"""
        # Create premium shelves
        for i, pos in enumerate(config.SHELF_POSITIONS['premium']):
            shelf_id = f"P{i+1}"
            shelf_info = config.SHELF_DISTANCES['premium'][i]
            
            shelf = Shelf(
                shelf_id=shelf_id,
                location_type=ShelfType.PREMIUM,
                matrix_position=pos,
                capacity_small=config.SHELF_CAPACITY['premium'][ParcelSize.SMALL],
                capacity_medium=config.SHELF_CAPACITY['premium'][ParcelSize.MEDIUM],
                capacity_large=config.SHELF_CAPACITY['premium'][ParcelSize.LARGE],
                distance_to_exit=shelf_info['distance_to_exit'],
                distance_from_entrance=shelf_info['distance_from_entrance']
            )
            self.station.add_shelf(shelf)
        
        # Create standard shelves
        for i, pos in enumerate(config.SHELF_POSITIONS['standard']):
            shelf_id = f"S{i+1}"
            shelf_info = config.SHELF_DISTANCES['standard'][i]
            
            shelf = Shelf(
                shelf_id=shelf_id,
                location_type=ShelfType.STANDARD,
                matrix_position=pos,
                capacity_small=config.SHELF_CAPACITY['standard'][ParcelSize.SMALL],
                capacity_medium=config.SHELF_CAPACITY['standard'][ParcelSize.MEDIUM],
                capacity_large=config.SHELF_CAPACITY['standard'][ParcelSize.LARGE],
                distance_to_exit=shelf_info['distance_to_exit'],
                distance_from_entrance=shelf_info['distance_from_entrance']
            )
            self.station.add_shelf(shelf)
        
        self.logger.info(f"Initialized station with {len(self.station.shelves)} shelves")
    
    def generate_parcels(self, time_period: str) -> List[Parcel]:
        """
        Generate new parcels for the current time period.
        
        Args:
            time_period: Current time period (e.g., 'peak_morning')
            
        Returns:
            List of generated parcels
        """
        parcels = []
        arrival_rate = config.PARCEL_ARRIVAL_RATES[time_period]
        
        # Generate parcels based on arrival rate
        for _ in range(arrival_rate):
            # Randomly select parcel size
            size = random.choices(
                list(ParcelSize),
                weights=[0.6, 0.3, 0.1]  # 60% small, 30% medium, 10% large
            )[0]
            
            # Create parcel
            parcel = Parcel(
                parcel_id=f"PARCEL_{len(self.station.stored_parcels) + 1}",
                size=size,
                arrival_time=self.current_time
            )
            
            # Predict pickup probability
            parcel.predicted_pickup_probability = self.learning_module.predict_pickup_probability(
                parcel, self.current_time
            )
            
            parcels.append(parcel)
        
        return parcels
    
    def process_time_step(self):
        """Process one time step of the simulation"""
        # 1. Generate new parcels
        time_period = self._get_time_period()
        new_parcels = self.generate_parcels(time_period)
        self.pending_parcels.extend(new_parcels)
        
        # 2. Process parcels in batches
        if len(self.pending_parcels) >= config.BATCH_SIZE:
            batch = self.pending_parcels[:config.BATCH_SIZE]
            self.pending_parcels = self.pending_parcels[config.BATCH_SIZE:]
            
            # Assign parcels using SLAP optimization
            results = self.optimizer.batch_assign_parcels(batch, self.station)
            
            # Log results
            for parcel, shelf in results:
                if shelf:
                    self.logger.info(f"Assigned {parcel.parcel_id} to {shelf.shelf_id}")
                else:
                    self.logger.warning(f"Failed to assign {parcel.parcel_id}")
        
        # 3. Update simulation time
        self.current_time += timedelta(minutes=config.TIME_STEP_MINUTES)
    
    def _get_time_period(self) -> str:
        """Get current time period based on hour"""
        hour = self.current_time.hour
        
        if 8 <= hour < 10:
            return 'peak_morning'
        elif 10 <= hour < 12:
            return 'normal_morning'
        elif 12 <= hour < 14:
            return 'peak_afternoon'
        elif 14 <= hour < 16:
            return 'normal_afternoon'
        elif 16 <= hour < 18:
            return 'peak_evening'
        else:
            return 'low_evening'
    
    def run_simulation(self, hours: int = config.SIMULATION_HOURS):
        """
        Run the simulation for specified number of hours.
        
        Args:
            hours: Number of hours to simulate
        """
        end_time = self.current_time + timedelta(hours=hours)
        
        while self.current_time < end_time:
            self.process_time_step()
            
            # Log station statistics periodically
            if self.current_time.minute == 0:
                self._log_station_statistics()
    
    def _log_station_statistics(self):
        """Log current station statistics"""
        stats = self.station.get_station_statistics()
        
        log_message = (
            f"\nStation Statistics at {self.current_time}:"
            f"\n- Total parcels: {stats['total_parcels']}"
            f"\n- Premium utilization: {stats['premium_utilization']:.2%}"
            f"\n- Standard utilization: {stats['standard_utilization']:.2%}"
            f"\n- Pending parcels: {len(self.pending_parcels)}"
        )
        
        self.logger.info(log_message)


# Example usage and testing
if __name__ == "__main__":
    print("Starting Cainiao Parcel Station LTO Simulation")
    print("=" * 50)
    
    # Create and run simulation
    simulation = SimulationEngine()
    
    # Run the simulation
    simulation.run_simulation()
    
    print("Simulation completed successfully!") 