"""
Configuration parameters for the Cainiao Parcel Station LTO simulation.

This module contains all configurable parameters for the simulation,
including shelf configurations, parcel generation parameters, and simulation settings.
"""

from data_structures import ShelfType, ParcelSize
import numpy as np

# ============================================================================
# STATION LAYOUT CONFIGURATION
# ============================================================================

# Station matrix dimensions
STATION_ROWS = 3
STATION_COLS = 4

# Exit and entrance positions (row, col)
EXIT_POSITION = (0, 0)  # Top-left corner
ENTRANCE_POSITION = (2, 3)  # Bottom-right corner

# Shelf positions in matrix (row, col)
SHELF_POSITIONS = {
    'premium': [
        (0, 1),  # P1
        (0, 2),  # P2
        (1, 0),  # P3
    ],
    'standard': [
        (1, 1),  # S1
        (1, 2),  # S2
        (1, 3),  # S3
        (2, 1),  # S4
        (2, 2),  # S5
    ]
}

# ============================================================================
# SHELF CONFIGURATION
# ============================================================================

# Number of shelves by type
PREMIUM_SHELF_COUNT = len(SHELF_POSITIONS['premium'])
STANDARD_SHELF_COUNT = len(SHELF_POSITIONS['standard'])

# Shelf capacity by parcel size (number of parcels each shelf can hold)
SHELF_CAPACITY = {
    'premium': {
        ParcelSize.SMALL: 8,
        ParcelSize.MEDIUM: 4,
        ParcelSize.LARGE: 2
    },
    'standard': {
        ParcelSize.SMALL: 12,
        ParcelSize.MEDIUM: 6,
        ParcelSize.LARGE: 3
    }
}

# Distance/inconvenience scores for shelves (lower = more convenient)
# These will be used in the cost function: D_j * (1 - p_hat_i)
SHELF_DISTANCE_SCORES = {
    'premium': [1.0, 1.2, 1.5],  # Premium shelves: very convenient
    'standard': [2.0, 2.5, 3.0, 3.5, 4.0]  # Standard shelves: less convenient
}

# ============================================================================
# SLAP OPTIMIZATION PARAMETERS
# ============================================================================

# SLAP optimization weights (multi-objective)
SLAP_OPTIMIZATION_WEIGHTS = {
    'customer_convenience': 0.4,  # Weight for customer distance cost
    'employee_workload': 0.3,     # Weight for employee effort cost  
    'system_efficiency': 0.2,     # Weight for system utilization cost
    'future_flexibility': 0.1     # Weight for future space reservation
}

# Size-based cost factors
SIZE_COST_FACTORS = {
    'customer': {
        ParcelSize.SMALL: 1.0,
        ParcelSize.MEDIUM: 1.2,
        ParcelSize.LARGE: 1.5
    },
    'employee': {
        ParcelSize.SMALL: 1.0,
        ParcelSize.MEDIUM: 1.3,
        ParcelSize.LARGE: 1.8
    }
}

# Probability thresholds for shelf assignment
PROBABILITY_THRESHOLDS = {
    'premium_threshold': 0.7,     # High probability parcels for premium shelves
    'standard_threshold': 0.3     # Low probability parcels for standard shelves
}

# Batch processing parameters
BATCH_PROCESSING = {
    'batch_size': 10,             # Number of parcels per batch (increased for better optimization)
    'time_window_minutes': 30,    # Time window for collecting parcels (30 minutes)
    'reoptimization_interval': 60, # Re-optimize every 60 minutes
    'max_wait_time_minutes': 15   # Maximum time a parcel waits before forced assignment
}

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================

# Simulation time parameters
SIMULATION_HOURS = 8              # Total simulation time
TIME_STEP_MINUTES = 5             # Time step for simulation (5 minutes)

# Parcel arrival rates (parcels per hour) by time period
PARCEL_ARRIVAL_RATES = {
    'peak_morning': 25,    # 8-10 AM: High arrival rate
    'normal_morning': 15,  # 10-12 PM: Normal rate
    'peak_afternoon': 30,  # 12-14 PM: Lunch peak
    'normal_afternoon': 20, # 14-17 PM: Afternoon rate
    'peak_evening': 35,    # 17-19 PM: Evening peak
    'low_evening': 10      # 19-22 PM: Low rate
}

# Time periods definition (hour ranges)
TIME_PERIODS = {
    'peak_morning': (8, 10),
    'normal_morning': (10, 12),
    'peak_afternoon': (12, 14),
    'normal_afternoon': (14, 16),
    'peak_evening': (16, 18),
    'low_evening': (18, 20)
}

# Parcel size distribution (probabilities must sum to 1.0)
PARCEL_SIZE_DISTRIBUTION = {
    ParcelSize.SMALL: 0.6,   # 60% small parcels
    ParcelSize.MEDIUM: 0.3,  # 30% medium parcels
    ParcelSize.LARGE: 0.1    # 10% large parcels
}

# ============================================================================
# LEARNING MODULE PARAMETERS
# ============================================================================

# Base pickup probabilities by time period (for rule-based learning)
BASE_PICKUP_PROBABILITIES = {
    'peak_morning': 0.85,    # High probability during morning peak
    'normal_morning': 0.65,  # Medium-high during normal morning
    'peak_afternoon': 0.75,  # High during lunch peak
    'normal_afternoon': 0.55, # Medium during normal afternoon
    'peak_evening': 0.90,    # Very high during evening peak
    'low_evening': 0.40      # Lower during late evening
}

# Probability modifiers based on parcel size
SIZE_PROBABILITY_MODIFIERS = {
    ParcelSize.SMALL: 1.0,    # No modifier for small parcels
    ParcelSize.MEDIUM: 0.95,  # Slightly lower for medium (harder to carry)
    ParcelSize.LARGE: 0.85    # Lower for large parcels (need planning)
}

# Random noise range for probability prediction (to simulate uncertainty)
PROBABILITY_NOISE_RANGE = 0.1  # ±0.1 random variation

# ============================================================================
# OPTIMIZATION MODULE PARAMETERS
# ============================================================================

# Cost function parameters (for future use in more sophisticated optimization)
COST_FUNCTION_PARAMS = {
    'distance_weight': 1.0,      # Weight for distance component
    'probability_weight': 1.0,   # Weight for probability component
    'utilization_penalty': 0.1   # Penalty for uneven utilization
}

# ============================================================================
# MULTI-OBJECTIVE COST MODEL PARAMETERS
# ============================================================================

# Storage cost parameters
STORAGE_COST_PARAMS = {
    'holding_cost_per_day': 0.1,
    'expected_holding_days': 3,
    'storage_weight': 0.6 
}

# Customer convenience cost parameters  
CONVENIENCE_COST_PARAMS = {
    'inconvenience_weight': 0.5,
    'convenience_weight': 0.4
}

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================

# Starting time for simulation (hour of day)
SIMULATION_START_HOUR = 8

# Random seed for reproducible results (set to None for random)
RANDOM_SEED = 42

# Logging configuration
LOG_LEVEL = 'INFO'  # 'DEBUG', 'INFO', 'WARNING', 'ERROR'
LOG_DETAILED_ASSIGNMENTS = True  # Whether to log each parcel assignment

# Output configuration
SAVE_RESULTS = True
RESULTS_FILENAME = 'simulation_results.json'

# ============================================================================
# EVALUATION WEIGHTS
# ============================================================================
# Weights for the 'strategy_effectiveness' score, reflecting the new focus on occupancy cost.
# These values must sum to 1.0.
STRATEGY_EFFECTIVENESS_WEIGHTS = {
    'cost': 0.6,        # Primary driver: minimize occupancy cost
    'alignment': 0.3,   # Secondary: ensure the cost is minimized via the intended strategy
    'satisfaction': 0.1 # Acknowledge the trade-off with customer-facing metrics
}

# ============================================================================
# VALIDATION PARAMETERS
# ============================================================================

# Minimum and maximum values for validation
MIN_PROBABILITY = 0.0
MAX_PROBABILITY = 1.0
MIN_DISTANCE_SCORE = 0.1
MAX_DISTANCE_SCORE = 10.0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_manhattan_distance(pos1: tuple, pos2: tuple) -> float:
    """Calculate Manhattan distance between two positions"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def get_shelf_distances():
    """Calculate distances for all shelves"""
    distances = {
        'premium': [],
        'standard': []
    }
    
    # Calculate distances for premium shelves
    for pos in SHELF_POSITIONS['premium']:
        exit_dist = calculate_manhattan_distance(pos, EXIT_POSITION)
        entrance_dist = calculate_manhattan_distance(pos, ENTRANCE_POSITION)
        distances['premium'].append({
            'position': pos,
            'distance_to_exit': exit_dist,
            'distance_from_entrance': entrance_dist
        })
    
    # Calculate distances for standard shelves
    for pos in SHELF_POSITIONS['standard']:
        exit_dist = calculate_manhattan_distance(pos, EXIT_POSITION)
        entrance_dist = calculate_manhattan_distance(pos, ENTRANCE_POSITION)
        distances['standard'].append({
            'position': pos,
            'distance_to_exit': exit_dist,
            'distance_from_entrance': entrance_dist
        })
    
    return distances

# Initialize shelf distances
SHELF_DISTANCES = get_shelf_distances()

def get_time_period(hour: int) -> str:
    """
    Get the time period name for a given hour.
    
    Args:
        hour: Hour of day (0-23)
        
    Returns:
        Time period name
    """
    for period, (start, end) in TIME_PERIODS.items():
        if start <= hour < end:
            return period
    return 'low_evening'  # Default for hours outside defined periods

def validate_config():
    """
    Validate configuration parameters.
    
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate parcel size distribution
    total_prob = sum(PARCEL_SIZE_DISTRIBUTION.values())
    if abs(total_prob - 1.0) > 0.001:
        raise ValueError(f"Parcel size distribution probabilities must sum to 1.0, got {total_prob}")
    
    # Validate strategy effectiveness weights
    total_weight = sum(STRATEGY_EFFECTIVENESS_WEIGHTS.values())
    if abs(total_weight - 1.0) > 0.001:
        raise ValueError(f"Strategy effectiveness weights must sum to 1.0, got {total_weight}")

    # Validate shelf counts match distance scores
    if len(SHELF_DISTANCE_SCORES['premium']) != PREMIUM_SHELF_COUNT:
        raise ValueError("Number of premium distance scores must match PREMIUM_SHELF_COUNT")
    
    if len(SHELF_DISTANCE_SCORES['standard']) != STANDARD_SHELF_COUNT:
        raise ValueError("Number of standard distance scores must match STANDARD_SHELF_COUNT")
    
    # Validate probability values
    for prob in BASE_PICKUP_PROBABILITIES.values():
        if not (MIN_PROBABILITY <= prob <= MAX_PROBABILITY):
            raise ValueError(f"Base pickup probability {prob} out of valid range")
    
    print("Configuration validation passed!")

# Validate configuration on import
if __name__ == "__main__":
    validate_config()

# ============================================================================
# COMPREHENSIVE OBJECTIVE FUNCTION PARAMETERS (NEW)
# ============================================================================

# NEW COMPREHENSIVE COST MODEL: min ∑ x_ij · [α · D_j + β · W_j + γ · (1 - p̂_i)]
COMPREHENSIVE_COST_PARAMS = {
    'alpha': 0.4,   # α: Customer convenience weight
    'beta': 0.3,    # β: Employee workload weight 
    'gamma': 0.3    # γ: LTO priority weight
}

# Note: α + β + γ = 1.0 for interpretability, but can be adjusted independently 