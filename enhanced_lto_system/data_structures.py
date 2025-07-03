"""
Core data structures for the Cainiao Parcel Station LTO system.

This module defines the fundamental classes used throughout the simulation:
- Parcel: Represents individual parcels with attributes and predictions
- Shelf: Represents storage locations with capacity and convenience metrics
- ParcelStation: Manages the overall station state
"""

from typing import List, Optional
from datetime import datetime
from enum import Enum
import numpy as np


class ParcelSize(Enum):
    """Enumeration for parcel sizes"""
    SMALL = "S"
    MEDIUM = "M" 
    LARGE = "L"


class ShelfType(Enum):
    """Enumeration for shelf location types"""
    PREMIUM = "premium"    # Easy access, near exit
    STANDARD = "standard"  # Regular access, further from exit


class Parcel:
    """
    Represents a parcel in the station.
    
    Attributes:
        parcel_id (str): Unique identifier for the parcel
        arrival_time (datetime): When the parcel arrived at the station
        size (ParcelSize): Size category of the parcel
        predicted_pickup_probability (float): Predicted probability of pickup (0-1)
        actual_pickup_time (Optional[datetime]): When parcel was actually picked up
        assigned_shelf_id (Optional[str]): ID of the shelf where parcel is stored
    """
    
    def __init__(self, parcel_id: str, arrival_time: datetime, size: ParcelSize):
        self.parcel_id = parcel_id
        self.arrival_time = arrival_time
        self.size = size
        self.predicted_pickup_probability: Optional[float] = None
        self.actual_pickup_time: Optional[datetime] = None
        self.assigned_shelf_id: Optional[str] = None
    
    def __repr__(self):
        prob_str = f"{self.predicted_pickup_probability:.2f}" if self.predicted_pickup_probability is not None else "None"
        return (f"Parcel(id={self.parcel_id}, size={self.size.value}, "
                f"prob={prob_str}, "
                f"shelf={self.assigned_shelf_id})")


class Shelf:
    """
    Represents a storage shelf in the parcel station with matrix-based location.
    
    Attributes:
        shelf_id (str): Unique identifier for the shelf
        location_type (ShelfType): Type of shelf (premium/standard)
        matrix_position (tuple): (row, col) position in the station matrix
        capacity_volume (dict): Maximum capacity for each parcel size
        current_used_volume (dict): Currently used capacity for each size
        distance_to_exit (float): Distance to exit (customer convenience cost)
        distance_from_entrance (float): Distance from entrance (employee workload cost)
        adjacent_shelves (List[str]): List of adjacent shelf IDs
        parcels_stored (List[str]): List of parcel IDs currently stored
    """
    
    def __init__(self, shelf_id: str, location_type: ShelfType, 
                 matrix_position: tuple,
                 capacity_small: int = 10, capacity_medium: int = 5, capacity_large: int = 2,
                 distance_to_exit: float = 1.0, distance_from_entrance: float = 1.0):
        self.shelf_id = shelf_id
        self.location_type = location_type
        self.matrix_position = matrix_position  # (row, col) position
        self.capacity_volume = {
            ParcelSize.SMALL: capacity_small,
            ParcelSize.MEDIUM: capacity_medium,
            ParcelSize.LARGE: capacity_large
        }
        self.current_used_volume = {
            ParcelSize.SMALL: 0,
            ParcelSize.MEDIUM: 0,
            ParcelSize.LARGE: 0
        }
        self.distance_to_exit = distance_to_exit
        self.distance_from_entrance = distance_from_entrance
        self.adjacent_shelves = []  # Will be populated by ParcelStation
        self.parcels_stored: List[str] = []
    
    def can_accommodate(self, parcel_size: ParcelSize) -> bool:
        """
        Check if the shelf can accommodate a parcel of given size.
        
        Args:
            parcel_size: Size of the parcel to check
            
        Returns:
            True if the shelf has capacity for the parcel size
        """
        return (self.current_used_volume[parcel_size] < 
                self.capacity_volume[parcel_size])
    
    def add_parcel(self, parcel: Parcel) -> bool:
        """
        Add a parcel to the shelf if there's capacity.
        
        Args:
            parcel: The parcel to add
            
        Returns:
            True if parcel was successfully added, False otherwise
        """
        if not self.can_accommodate(parcel.size):
            return False
        
        # Add parcel to shelf
        self.parcels_stored.append(parcel.parcel_id)
        self.current_used_volume[parcel.size] += 1
        parcel.assigned_shelf_id = self.shelf_id
        
        return True
    
    def remove_parcel(self, parcel: Parcel) -> bool:
        """
        Remove a parcel from the shelf.
        
        Args:
            parcel: The parcel to remove
            
        Returns:
            True if parcel was successfully removed, False otherwise
        """
        if parcel.parcel_id not in self.parcels_stored:
            return False
        
        # Remove parcel from shelf
        self.parcels_stored.remove(parcel.parcel_id)
        self.current_used_volume[parcel.size] -= 1
        parcel.assigned_shelf_id = None
        
        return True
    
    def calculate_distance_to(self, other_shelf: 'Shelf') -> float:
        """Calculate Manhattan distance to another shelf"""
        return abs(self.matrix_position[0] - other_shelf.matrix_position[0]) + \
               abs(self.matrix_position[1] - other_shelf.matrix_position[1])
    
    def get_adjacent_shelves(self) -> List[str]:
        """Get list of adjacent shelf IDs"""
        return self.adjacent_shelves
    
    def get_utilization_rate(self) -> float:
        """Calculate overall utilization rate of the shelf (0-1)"""
        total_capacity = sum(self.capacity_volume.values())
        total_used = sum(self.current_used_volume.values())
        return total_used / total_capacity if total_capacity > 0 else 0.0
    
    def get_workload_score(self) -> float:
        """Calculate workload score based on current usage and parcel mix"""
        # Higher score means more workload for employees
        size_weights = {
            ParcelSize.SMALL: 1.0,
            ParcelSize.MEDIUM: 1.5,
            ParcelSize.LARGE: 2.0
        }
        workload = sum(self.current_used_volume[size] * weight 
                      for size, weight in size_weights.items())
        return workload / sum(self.capacity_volume.values())
    
    def __repr__(self):
        return (f"Shelf(id={self.shelf_id}, type={self.location_type.value}, "
                f"pos={self.matrix_position}, utilization={self.get_utilization_rate():.2f}, "
                f"distance={self.distance_to_exit})")


class ParcelStation:
    """
    Represents the overall parcel station with matrix-based layout.
    
    Attributes:
        shelves (List[Shelf]): All shelves in the station
        matrix_layout (numpy.ndarray): 2D matrix representing shelf layout
        pending_parcels (List[Parcel]): Parcels waiting to be assigned
        stored_parcels (dict): Mapping of parcel_id to Parcel objects
    """
    
    def __init__(self, rows: int = 3, cols: int = 4):
        self.shelves: List[Shelf] = []
        self.matrix_layout = np.full((rows, cols), None, dtype=object)  # Will store shelf objects
        self.pending_parcels: List[Parcel] = []
        self.stored_parcels: dict[str, Parcel] = {}
    
    def add_shelf(self, shelf: Shelf):
        """Add a shelf to the station and update matrix layout"""
        self.shelves.append(shelf)
        row, col = shelf.matrix_position
        self.matrix_layout[row, col] = shelf
        self._update_adjacent_shelves(shelf)
    
    def _update_adjacent_shelves(self, shelf: Shelf):
        """Update adjacent shelves list for a given shelf"""
        row, col = shelf.matrix_position
        adjacent = []
        
        # Check all 4 directions
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            new_row, new_col = row + dr, col + dc
            if (0 <= new_row < self.matrix_layout.shape[0] and 
                0 <= new_col < self.matrix_layout.shape[1] and 
                self.matrix_layout[new_row, new_col] is not None):
                adjacent.append(self.matrix_layout[new_row, new_col].shelf_id)
        
        shelf.adjacent_shelves = adjacent
    
    def get_shelf_by_position(self, row: int, col: int) -> Optional[Shelf]:
        """Get shelf at specific matrix position"""
        if 0 <= row < self.matrix_layout.shape[0] and 0 <= col < self.matrix_layout.shape[1]:
            return self.matrix_layout[row, col]
        return None
    
    def get_available_shelves(self, parcel_size: ParcelSize, 
                            preferred_type: Optional[ShelfType] = None) -> List[Shelf]:
        """
        Get list of shelves that can accommodate a parcel of given size.
        Considers both capacity and spatial constraints.
        """
        available = [shelf for shelf in self.shelves 
                    if shelf.can_accommodate(parcel_size)]
        
        if preferred_type:
            # Sort by preference: preferred type first, then by distance
            available.sort(key=lambda s: (
                s.location_type != preferred_type,  # False (0) for preferred type
                s.distance_to_exit
            ))
        else:
            # Sort by distance only
            available.sort(key=lambda s: s.distance_to_exit)
        
        return available
    
    def add_pending_parcel(self, parcel: Parcel):
        """Add a parcel to the pending queue"""
        self.pending_parcels.append(parcel)
    
    def get_station_statistics(self) -> dict:
        """Get overall station statistics"""
        total_shelves = len(self.shelves)
        premium_shelves = [s for s in self.shelves if s.location_type == ShelfType.PREMIUM]
        standard_shelves = [s for s in self.shelves if s.location_type == ShelfType.STANDARD]
        
        return {
            'total_shelves': total_shelves,
            'premium_shelves': len(premium_shelves),
            'standard_shelves': len(standard_shelves),
            'avg_premium_utilization': sum(s.get_utilization_rate() for s in premium_shelves) / len(premium_shelves) if premium_shelves else 0,
            'avg_standard_utilization': sum(s.get_utilization_rate() for s in standard_shelves) / len(standard_shelves) if standard_shelves else 0,
            'total_stored_parcels': len(self.stored_parcels),
            'pending_parcels': len(self.pending_parcels)
        }
    
    def __repr__(self):
        stats = self.get_station_statistics()
        return (f"ParcelStation(shelves={stats['total_shelves']}, "
                f"stored={stats['total_stored_parcels']}, "
                f"pending={stats['pending_parcels']})") 