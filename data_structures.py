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
    Represents a storage shelf in the parcel station.
    
    Attributes:
        shelf_id (str): Unique identifier for the shelf
        location_type (ShelfType): Type of shelf (premium/standard)
        capacity_volume (dict): Maximum capacity for each parcel size
        current_used_volume (dict): Currently used capacity for each size
        distance_to_exit (float): Distance/inconvenience score (lower = more convenient)
        distance_from_entrance (float): Distance from entrance (NEW: Employee workload cost)
        parcels_stored (List[str]): List of parcel IDs currently stored
    """
    
    def __init__(self, shelf_id: str, location_type: ShelfType, 
                 capacity_small: int = 10, capacity_medium: int = 5, capacity_large: int = 2,
                 distance_to_exit: float = 1.0, distance_from_entrance: float = 1.0):
        self.shelf_id = shelf_id
        self.location_type = location_type
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
        self.distance_from_entrance = distance_from_entrance  # NEW: Employee workload cost
        self.parcels_stored: List[str] = []
    
    def can_accommodate(self, parcel_size: ParcelSize) -> bool:
        """Check if shelf can accommodate a parcel of given size"""
        return self.current_used_volume[parcel_size] < self.capacity_volume[parcel_size]
    
    def add_parcel(self, parcel: Parcel) -> bool:
        """
        Add a parcel to this shelf.
        
        Returns:
            bool: True if successfully added, False if no capacity
        """
        if not self.can_accommodate(parcel.size):
            return False
        
        self.current_used_volume[parcel.size] += 1
        self.parcels_stored.append(parcel.parcel_id)
        parcel.assigned_shelf_id = self.shelf_id
        return True
    
    def remove_parcel(self, parcel: Parcel) -> bool:
        """
        Remove a parcel from this shelf.
        
        Returns:
            bool: True if successfully removed, False if parcel not found
        """
        if parcel.parcel_id not in self.parcels_stored:
            return False
        
        self.current_used_volume[parcel.size] -= 1
        self.parcels_stored.remove(parcel.parcel_id)
        parcel.assigned_shelf_id = None
        return True
    
    def get_utilization_rate(self) -> float:
        """Calculate overall utilization rate of the shelf (0-1)"""
        total_capacity = sum(self.capacity_volume.values())
        total_used = sum(self.current_used_volume.values())
        return total_used / total_capacity if total_capacity > 0 else 0.0
    
    def __repr__(self):
        return (f"Shelf(id={self.shelf_id}, type={self.location_type.value}, "
                f"utilization={self.get_utilization_rate():.2f}, "
                f"distance={self.distance_to_exit})")


class ParcelStation:
    """
    Represents the overall parcel station managing shelves and parcels.
    
    Attributes:
        shelves (List[Shelf]): All shelves in the station
        pending_parcels (List[Parcel]): Parcels waiting to be assigned
        stored_parcels (dict): Mapping of parcel_id to Parcel objects for stored parcels
    """
    
    def __init__(self):
        self.shelves: List[Shelf] = []
        self.pending_parcels: List[Parcel] = []
        self.stored_parcels: dict[str, Parcel] = {}
    
    def add_shelf(self, shelf: Shelf):
        """Add a shelf to the station"""
        self.shelves.append(shelf)
    
    def add_pending_parcel(self, parcel: Parcel):
        """Add a parcel to the pending queue"""
        self.pending_parcels.append(parcel)
    
    def get_available_shelves(self, parcel_size: ParcelSize, 
                            preferred_type: Optional[ShelfType] = None) -> List[Shelf]:
        """
        Get list of shelves that can accommodate a parcel of given size.
        
        Args:
            parcel_size: Size of parcel to accommodate
            preferred_type: Preferred shelf type (premium/standard)
            
        Returns:
            List of available shelves, sorted by preference
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