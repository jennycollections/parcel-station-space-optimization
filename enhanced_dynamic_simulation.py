"""
Enhanced Dynamic Simulation Engine for Cainiao LTO System

This module provides a comprehensive simulation environment that models:
1. Realistic temporal patterns and seasonality
2. Dynamic external factors (weather, holidays, traffic)
3. Customer behavior modeling with learning
4. Staff and operational constraints
5. Real-time system stress testing
6. Multi-scenario simulation for robust optimization

Key improvements over basic simulation:
- Event-driven simulation with realistic timing
- Stochastic processes for arrivals and pickups
- Dynamic workload and capacity modeling
- Environmental factor integration
- Performance monitoring and adaptation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random
import json
import math
from collections import defaultdict, deque
import heapq

from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
from optimization_module import SLAPOptimizer
from learning_module import PickupProbabilityPredictor
# Removed unused non_myopic imports


class WeatherCondition(Enum):
    """Weather conditions affecting parcel operations"""
    SUNNY = "sunny"
    RAINY = "rainy"
    SNOWY = "snowy"
    FOGGY = "foggy"
    STORMY = "stormy"


class EventType(Enum):
    """Types of simulation events"""
    PARCEL_ARRIVAL = "parcel_arrival"
    PARCEL_PICKUP = "parcel_pickup"
    STAFF_BREAK = "staff_break"
    STAFF_RETURN = "staff_return"
    SYSTEM_MAINTENANCE = "system_maintenance"
    PEAK_PERIOD_START = "peak_start"
    PEAK_PERIOD_END = "peak_end"
    WEATHER_CHANGE = "weather_change"
    OPTIMIZATION_TRIGGER = "optimization_trigger"


@dataclass
class SimulationEvent:
    """Individual simulation event"""
    timestamp: datetime
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Lower number = higher priority
    
    def __lt__(self, other):
        if self.timestamp == other.timestamp:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


@dataclass
class EnvironmentalFactors:
    """Current environmental conditions"""
    timestamp: datetime
    weather: WeatherCondition = WeatherCondition.SUNNY
    temperature: float = 20.0  # Celsius
    is_holiday: bool = False
    is_weekend: bool = False
    traffic_condition: float = 1.0  # 1.0 = normal, >1.0 = heavy traffic
    special_event: Optional[str] = None  # e.g., "double_11", "chinese_new_year"
    
    def get_impact_factor(self) -> float:
        """Calculate overall environmental impact on operations"""
        factor = 1.0
        
        # Weather impact
        weather_impacts = {
            WeatherCondition.SUNNY: 1.0,
            WeatherCondition.RAINY: 0.8,
            WeatherCondition.SNOWY: 0.6,
            WeatherCondition.FOGGY: 0.9,
            WeatherCondition.STORMY: 0.5
        }
        factor *= weather_impacts[self.weather]
        
        # Holiday impact
        if self.is_holiday:
            factor *= 1.5  # Higher pickup rate during holidays
        
        # Weekend impact
        if self.is_weekend:
            factor *= 1.2  # Slightly higher pickup rate on weekends
        
        # Traffic impact
        factor *= (2.0 - self.traffic_condition)  # Heavy traffic reduces efficiency
        
        return factor


@dataclass
class StaffMember:
    """Individual staff member"""
    staff_id: str
    name: str
    skill_level: float = 1.0  # 0.5-2.0, affects processing speed
    fatigue_level: float = 0.0  # 0.0-1.0, higher = slower
    is_available: bool = True
    break_start: Optional[datetime] = None
    break_duration: timedelta = timedelta(minutes=30)
    shift_start: datetime = datetime.now().replace(hour=8, minute=0)
    shift_end: datetime = datetime.now().replace(hour=18, minute=0)
    
    def get_efficiency(self) -> float:
        """Calculate current efficiency based on skill and fatigue"""
        efficiency = self.skill_level * (1.0 - self.fatigue_level * 0.5)
        return max(0.1, min(2.0, efficiency))
    
    def is_on_shift(self, current_time: datetime) -> bool:
        """Check if staff member is currently on shift"""
        current_time_only = current_time.time()
        return self.shift_start.time() <= current_time_only <= self.shift_end.time()
    
    def accumulate_fatigue(self, hours_worked: float):
        """Accumulate fatigue over time"""
        self.fatigue_level = min(1.0, self.fatigue_level + hours_worked * 0.1)
    
    def rest(self, rest_hours: float):
        """Reduce fatigue through rest"""
        self.fatigue_level = max(0.0, self.fatigue_level - rest_hours * 0.2)


@dataclass 
class CustomerProfile:
    """Customer behavior profile"""
    customer_id: str
    pickup_speed_factor: float = 1.0  # How quickly they pick up parcels
    preferred_times: List[int] = field(default_factory=lambda: [18, 19, 20])  # Preferred hours
    reliability_score: float = 0.8  # 0.0-1.0, higher = more likely to pick up
    location_preference: ShelfType = ShelfType.STANDARD
    historical_pickups: List[datetime] = field(default_factory=list)
    
    def get_pickup_probability_modifier(self, current_time: datetime) -> float:
        """Get probability modifier based on time and history"""
        current_hour = current_time.hour
        
        # Time preference modifier
        if current_hour in self.preferred_times:
            time_modifier = 1.3
        elif abs(current_hour - min(self.preferred_times)) <= 2:
            time_modifier = 1.1
        else:
            time_modifier = 0.8
        
        # Reliability modifier
        reliability_modifier = self.reliability_score
        
        return time_modifier * reliability_modifier


class ArrivalPatternGenerator:
    """Generates realistic parcel arrival patterns"""
    
    def __init__(self):
        # Base hourly patterns (parcels per hour)
        self.base_hourly_rates = {
            0: 0.1, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.1,
            6: 0.3, 7: 0.8, 8: 1.5, 9: 2.5, 10: 2.0, 11: 1.8,
            12: 1.5, 13: 1.2, 14: 1.8, 15: 2.2, 16: 2.8, 17: 3.5,
            18: 3.0, 19: 2.0, 20: 1.5, 21: 1.0, 22: 0.5, 23: 0.2
        }
        
        # Day of week modifiers
        self.daily_modifiers = {
            0: 1.0,  # Monday
            1: 1.1,  # Tuesday
            2: 1.2,  # Wednesday
            3: 1.1,  # Thursday
            4: 1.3,  # Friday
            5: 0.8,  # Saturday
            6: 0.6   # Sunday
        }
        
        # Seasonal modifiers
        self.seasonal_modifiers = {
            1: 1.2,   # January (New Year shopping)
            2: 0.9,   # February
            3: 1.0,   # March
            4: 1.0,   # April
            5: 1.1,   # May
            6: 1.0,   # June
            7: 0.9,   # July
            8: 0.9,   # August
            9: 1.1,   # September
            10: 1.1,  # October
            11: 1.5,  # November (Double 11)
            12: 1.4   # December (Christmas)
        }
        
    def generate_arrival_times(self, start_time: datetime, end_time: datetime,
                             environmental_factors: EnvironmentalFactors) -> List[datetime]:
        """Generate realistic arrival times for the given period"""
        arrivals = []
        current_time = start_time
        
        while current_time < end_time:
            # Calculate expected rate for current hour
            hour = current_time.hour
            day_of_week = current_time.weekday()
            month = current_time.month
            
            base_rate = self.base_hourly_rates[hour]
            daily_mod = self.daily_modifiers[day_of_week]
            seasonal_mod = self.seasonal_modifiers[month]
            env_mod = environmental_factors.get_impact_factor()
            
            effective_rate = base_rate * daily_mod * seasonal_mod * env_mod
            
            # Generate inter-arrival times using exponential distribution
            if effective_rate > 0:
                inter_arrival_time = np.random.exponential(1.0 / effective_rate)
                next_arrival = current_time + timedelta(hours=inter_arrival_time)
                
                if next_arrival < end_time:
                    arrivals.append(next_arrival)
                    current_time = next_arrival
                else:
                    break
            else:
                current_time += timedelta(hours=1)
        
        return sorted(arrivals)
    
    def generate_parcel_properties(self, arrival_time: datetime,
                                 environmental_factors: EnvironmentalFactors) -> Tuple[ParcelSize, str]:
        """Generate parcel size and customer ID based on arrival time"""
        hour = arrival_time.hour
        
        # Size distribution varies by time
        if 6 <= hour <= 10:  # Morning: more small parcels (office deliveries)
            size_probs = [0.7, 0.2, 0.1]
        elif 11 <= hour <= 17:  # Daytime: mixed
            size_probs = [0.5, 0.3, 0.2]
        else:  # Evening/night: more medium/large (personal deliveries)
            size_probs = [0.4, 0.4, 0.2]
        
        size = np.random.choice([ParcelSize.SMALL, ParcelSize.MEDIUM, ParcelSize.LARGE], 
                              p=size_probs)
        
        # Generate customer ID (simplified)
        customer_id = f"CUST_{arrival_time.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        
        return size, customer_id


class DynamicPickupPredictor:
    """Advanced pickup predictor with dynamic learning"""
    
    def __init__(self, base_predictor: PickupProbabilityPredictor):
        self.base_predictor = base_predictor
        self.customer_profiles: Dict[str, CustomerProfile] = {}
        self.historical_patterns = defaultdict(list)
        self.adaptation_rate = 0.1
        
    def get_or_create_customer_profile(self, customer_id: str) -> CustomerProfile:
        """Get existing customer profile or create new one"""
        if customer_id not in self.customer_profiles:
            # Create new profile with some variation
            self.customer_profiles[customer_id] = CustomerProfile(
                customer_id=customer_id,
                pickup_speed_factor=np.random.normal(1.0, 0.2),
                preferred_times=random.sample(range(17, 22), k=random.randint(1, 3)),
                reliability_score=np.random.beta(8, 2),  # Skewed towards high reliability
                location_preference=random.choice([ShelfType.PREMIUM, ShelfType.STANDARD])
            )
        return self.customer_profiles[customer_id]
    
    def predict_pickup_probability(self, parcel: Parcel, current_time: datetime,
                                 environmental_factors: EnvironmentalFactors) -> float:
        """Enhanced pickup probability prediction"""
        # Get base prediction
        base_prob = self.base_predictor.predict_pickup_probability(parcel, current_time)
        
        # Get customer profile if available
        customer_id = getattr(parcel, 'customer_id', None)
        if customer_id:
            profile = self.get_or_create_customer_profile(customer_id)
            customer_modifier = profile.get_pickup_probability_modifier(current_time)
        else:
            customer_modifier = 1.0
        
        # Environmental modifier
        env_modifier = environmental_factors.get_impact_factor()
        
        # Time-since-arrival modifier (more urgent over time)
        wait_time_hours = (current_time - parcel.arrival_time).total_seconds() / 3600
        urgency_modifier = 1.0 + min(wait_time_hours / 24.0, 0.5)  # Up to 50% increase after 24h
        
        # Combine all modifiers
        final_prob = base_prob * customer_modifier * env_modifier * urgency_modifier
        
        # Ensure probability is in valid range
        return max(0.01, min(0.99, final_prob))
    
    def update_with_actual_pickup(self, parcel: Parcel, pickup_time: datetime,
                                environmental_factors: EnvironmentalFactors):
        """Update predictor with actual pickup data"""
        customer_id = getattr(parcel, 'customer_id', None)
        if customer_id:
            profile = self.get_or_create_customer_profile(customer_id)
            profile.historical_pickups.append(pickup_time)
            
            # Update preferred times based on actual pickup
            pickup_hour = pickup_time.hour
            if pickup_hour not in profile.preferred_times:
                # Gradually incorporate new preferred times
                if len(profile.preferred_times) < 5:
                    profile.preferred_times.append(pickup_hour)
                else:
                    # Replace least common time
                    hour_counts = defaultdict(int)
                    for pickup in profile.historical_pickups[-20:]:  # Last 20 pickups
                        hour_counts[pickup.hour] += 1
                    
                    least_common_hour = min(profile.preferred_times, 
                                          key=lambda h: hour_counts[h])
                    profile.preferred_times.remove(least_common_hour)
                    profile.preferred_times.append(pickup_hour)
        
        # Update global patterns
        wait_time = (pickup_time - parcel.arrival_time).total_seconds() / 3600
        pattern_key = (parcel.size, pickup_time.hour, pickup_time.weekday())
        self.historical_patterns[pattern_key].append(wait_time)


class EnhancedDynamicSimulationEngine:
    """Advanced simulation engine with realistic dynamics"""
    
    def __init__(self, station: ParcelStation, optimizer: SLAPOptimizer,
                 base_predictor: PickupProbabilityPredictor):
        self.station = station
        self.optimizer = optimizer
        self.base_predictor = base_predictor
        
        # Enhanced components
        self.pickup_predictor = DynamicPickupPredictor(base_predictor)
        self.arrival_generator = ArrivalPatternGenerator()
        
        # Simulation state
        self.current_time = datetime.now()
        self.event_queue = []  # Priority queue of events
        self.environmental_factors = EnvironmentalFactors(timestamp=self.current_time)
        
        # Staff management
        self.staff_members = self._initialize_staff()
        self.available_staff = len([s for s in self.staff_members if s.is_available])
        
        # Performance tracking
        self.metrics = {
            'total_arrivals': 0,
            'total_pickups': 0,
            'avg_wait_time': 0.0,
            'system_utilization': 0.0,
            'staff_efficiency': 0.0,
            'customer_satisfaction': 0.0
        }
        
        # Event handlers
        self.event_handlers = {
            EventType.PARCEL_ARRIVAL: self._handle_parcel_arrival,
            EventType.PARCEL_PICKUP: self._handle_parcel_pickup,
            EventType.STAFF_BREAK: self._handle_staff_break,
            EventType.STAFF_RETURN: self._handle_staff_return,
            EventType.WEATHER_CHANGE: self._handle_weather_change,
            EventType.OPTIMIZATION_TRIGGER: self._handle_optimization_trigger,
            EventType.PEAK_PERIOD_START: self._handle_peak_start,
            EventType.PEAK_PERIOD_END: self._handle_peak_end
        }
        
        # Dynamic adaptation
        self.adaptation_history = []
        self.stress_test_mode = False
        
    def _initialize_staff(self) -> List[StaffMember]:
        """Initialize staff members with realistic properties"""
        staff = []
        
        # Create staff with different skill levels and shifts
        for i in range(5):  # 5 staff members
            skill_level = np.random.normal(1.0, 0.2)  # Normally distributed skill
            skill_level = max(0.5, min(2.0, skill_level))
            
            # Different shift patterns
            if i < 2:  # Morning shift
                shift_start = datetime.now().replace(hour=6, minute=0)
                shift_end = datetime.now().replace(hour=14, minute=0)
            elif i < 4:  # Day shift
                shift_start = datetime.now().replace(hour=9, minute=0)
                shift_end = datetime.now().replace(hour=17, minute=0)
            else:  # Evening shift
                shift_start = datetime.now().replace(hour=14, minute=0)
                shift_end = datetime.now().replace(hour=22, minute=0)
            
            staff.append(StaffMember(
                staff_id=f"STAFF_{i+1:03d}",
                name=f"Staff Member {i+1}",
                skill_level=skill_level,
                shift_start=shift_start,
                shift_end=shift_end
            ))
        
        return staff
    
    def schedule_event(self, event: SimulationEvent):
        """Schedule an event in the simulation"""
        heapq.heappush(self.event_queue, event)
    
    def run_simulation(self, duration: timedelta, 
                      stress_test: bool = False,
                      scenario_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the enhanced simulation"""
        self.stress_test_mode = stress_test
        start_time = self.current_time
        end_time = start_time + duration
        
        # Apply scenario configuration if provided
        if scenario_config:
            self._apply_scenario_config(scenario_config)
        
        # Initialize simulation with initial events
        self._schedule_initial_events(start_time, end_time)
        
        # Main simulation loop
        while self.event_queue and self.current_time < end_time:
            # Get next event
            event = heapq.heappop(self.event_queue)
            
            # Advance simulation time
            self.current_time = event.timestamp
            
            # Handle event
            if event.event_type in self.event_handlers:
                self.event_handlers[event.event_type](event)
            
            # Update system state
            self._update_system_state()
            
            # Adaptive management
            if len(self.adaptation_history) % 100 == 0:  # Every 100 events
                self._perform_adaptive_management()
        
        # Calculate final metrics
        final_metrics = self._calculate_final_metrics()
        
        return {
            'simulation_duration': duration,
            'events_processed': len(self.adaptation_history),
            'final_metrics': final_metrics,
            'stress_test_mode': stress_test,
            'environmental_impact': self.environmental_factors.get_impact_factor(),
            'staff_performance': self._get_staff_performance_summary()
        }
    
    def _schedule_initial_events(self, start_time: datetime, end_time: datetime):
        """Schedule initial events for the simulation"""
        # Schedule parcel arrivals
        arrival_times = self.arrival_generator.generate_arrival_times(
            start_time, end_time, self.environmental_factors
        )
        
        for arrival_time in arrival_times:
            size, customer_id = self.arrival_generator.generate_parcel_properties(
                arrival_time, self.environmental_factors
            )
            
            self.schedule_event(SimulationEvent(
                timestamp=arrival_time,
                event_type=EventType.PARCEL_ARRIVAL,
                data={'size': size, 'customer_id': customer_id}
            ))
        
        # Schedule staff breaks
        for staff in self.staff_members:
            break_time = start_time + timedelta(hours=4 + random.random() * 2)
            if break_time < end_time:
                self.schedule_event(SimulationEvent(
                    timestamp=break_time,
                    event_type=EventType.STAFF_BREAK,
                    data={'staff_id': staff.staff_id}
                ))
        
        # Schedule weather changes
        current_weather_time = start_time
        while current_weather_time < end_time:
            next_change = current_weather_time + timedelta(hours=random.randint(4, 12))
            if next_change < end_time:
                self.schedule_event(SimulationEvent(
                    timestamp=next_change,
                    event_type=EventType.WEATHER_CHANGE,
                    data={'new_weather': random.choice(list(WeatherCondition))}
                ))
            current_weather_time = next_change
        
        # Schedule optimization triggers
        optimization_time = start_time + timedelta(hours=1)
        while optimization_time < end_time:
            self.schedule_event(SimulationEvent(
                timestamp=optimization_time,
                event_type=EventType.OPTIMIZATION_TRIGGER,
                priority=1  # High priority
            ))
            optimization_time += timedelta(hours=1)
    
    def _handle_parcel_arrival(self, event: SimulationEvent):
        """Handle parcel arrival event"""
        parcel_id = f"P_{self.current_time.strftime('%Y%m%d_%H%M%S')}_{self.metrics['total_arrivals']:04d}"
        
        parcel = Parcel(
            parcel_id=parcel_id,
            arrival_time=event.timestamp,
            size=event.data['size']
        )
        
        # Add customer ID
        setattr(parcel, 'customer_id', event.data['customer_id'])
        
        # Predict pickup probability
        parcel.predicted_pickup_probability = self.pickup_predictor.predict_pickup_probability(
            parcel, self.current_time, self.environmental_factors
        )
        
        # Add to station
        self.station.add_pending_parcel(parcel)
        self.metrics['total_arrivals'] += 1
        
        # Schedule pickup event
        pickup_delay = self._calculate_pickup_delay(parcel)
        pickup_time = event.timestamp + pickup_delay
        
        self.schedule_event(SimulationEvent(
            timestamp=pickup_time,
            event_type=EventType.PARCEL_PICKUP,
            data={'parcel_id': parcel_id}
        ))
        
        # Log event
        self.adaptation_history.append({
            'timestamp': self.current_time,
            'event_type': 'arrival',
            'parcel_id': parcel_id,
            'size': parcel.size.value,
            'predicted_prob': parcel.predicted_pickup_probability
        })
    
    def _handle_parcel_pickup(self, event: SimulationEvent):
        """Handle parcel pickup event"""
        parcel_id = event.data['parcel_id']
        
        # Find parcel
        parcel = self.station.stored_parcels.get(parcel_id)
        if not parcel:
            return  # Parcel not found or already picked up
        
        # Find assigned shelf
        assigned_shelf = None
        for shelf in self.station.shelves:
            if parcel_id in shelf.parcels_stored:
                assigned_shelf = shelf
                break
        
        if assigned_shelf:
            # Remove from shelf
            assigned_shelf.remove_parcel(parcel)
            del self.station.stored_parcels[parcel_id]
            
            # Update metrics
            wait_time = (event.timestamp - parcel.arrival_time).total_seconds() / 3600
            self.metrics['total_pickups'] += 1
            
            # Update predictor with actual pickup
            self.pickup_predictor.update_with_actual_pickup(
                parcel, event.timestamp, self.environmental_factors
            )
            
            # Log event
            self.adaptation_history.append({
                'timestamp': self.current_time,
                'event_type': 'pickup',
                'parcel_id': parcel_id,
                'wait_time_hours': wait_time,
                'shelf_id': assigned_shelf.shelf_id
            })
    
    def _handle_staff_break(self, event: SimulationEvent):
        """Handle staff break event"""
        staff_id = event.data['staff_id']
        staff = next((s for s in self.staff_members if s.staff_id == staff_id), None)
        
        if staff and staff.is_available:
            staff.is_available = False
            staff.break_start = event.timestamp
            
            # Schedule return from break
            return_time = event.timestamp + staff.break_duration
            self.schedule_event(SimulationEvent(
                timestamp=return_time,
                event_type=EventType.STAFF_RETURN,
                data={'staff_id': staff_id}
            ))
            
            # Update available staff count
            self.available_staff = len([s for s in self.staff_members if s.is_available])
    
    def _handle_staff_return(self, event: SimulationEvent):
        """Handle staff return from break"""
        staff_id = event.data['staff_id']
        staff = next((s for s in self.staff_members if s.staff_id == staff_id), None)
        
        if staff and not staff.is_available:
            staff.is_available = True
            staff.break_start = None
            
            # Reduce fatigue from break
            if staff.break_start:
                break_duration_hours = (event.timestamp - staff.break_start).total_seconds() / 3600
                staff.rest(break_duration_hours)
            
            # Update available staff count
            self.available_staff = len([s for s in self.staff_members if s.is_available])
    
    def _handle_weather_change(self, event: SimulationEvent):
        """Handle weather change event"""
        new_weather = event.data['new_weather']
        self.environmental_factors.weather = new_weather
        self.environmental_factors.timestamp = event.timestamp
        
        # Log weather change
        self.adaptation_history.append({
            'timestamp': self.current_time,
            'event_type': 'weather_change',
            'new_weather': new_weather.value,
            'impact_factor': self.environmental_factors.get_impact_factor()
        })
    
    def _handle_optimization_trigger(self, event: SimulationEvent):
        """Handle periodic optimization trigger"""
        if self.station.pending_parcels:
            # Run optimization on pending parcels
            pending_parcels = list(self.station.pending_parcels)
            self.station.pending_parcels.clear()
            
            # Use optimizer to assign parcels
            for parcel in pending_parcels:
                assigned_shelf = self.optimizer.assign_parcel_to_shelf(parcel, self.station)
                if not assigned_shelf:
                    # If assignment failed, put back in pending queue
                    self.station.add_pending_parcel(parcel)
            
            # Log optimization
            self.adaptation_history.append({
                'timestamp': self.current_time,
                'event_type': 'optimization',
                'parcels_processed': len(pending_parcels),
                'successful_assignments': len([p for p in pending_parcels if p.assigned_shelf_id])
            })
    
    def _handle_peak_start(self, event: SimulationEvent):
        """Handle peak period start"""
        # Increase arrival rates
        for hour, rate in self.arrival_generator.base_hourly_rates.items():
            self.arrival_generator.base_hourly_rates[hour] = rate * 1.5
    
    def _handle_peak_end(self, event: SimulationEvent):
        """Handle peak period end"""
        # Reset arrival rates
        for hour, rate in self.arrival_generator.base_hourly_rates.items():
            self.arrival_generator.base_hourly_rates[hour] = rate / 1.5
    
    def _calculate_pickup_delay(self, parcel: Parcel) -> timedelta:
        """Calculate realistic pickup delay based on various factors"""
        base_delay_hours = np.random.exponential(12)  # Average 12 hours
        
        # Adjust based on pickup probability
        prob_factor = 1.0 / max(0.1, parcel.predicted_pickup_probability)
        
        # Adjust based on parcel size
        size_factors = {
            ParcelSize.SMALL: 0.8,
            ParcelSize.MEDIUM: 1.0,
            ParcelSize.LARGE: 1.3
        }
        size_factor = size_factors[parcel.size]
        
        # Environmental factor
        env_factor = 1.0 / self.environmental_factors.get_impact_factor()
        
        # Customer behavior (if available)
        customer_id = getattr(parcel, 'customer_id', None)
        if customer_id and customer_id in self.pickup_predictor.customer_profiles:
            profile = self.pickup_predictor.customer_profiles[customer_id]
            customer_factor = 1.0 / profile.pickup_speed_factor
        else:
            customer_factor = 1.0
        
        total_delay_hours = base_delay_hours * prob_factor * size_factor * env_factor * customer_factor
        total_delay_hours = max(0.5, min(72, total_delay_hours))  # Between 30 min and 3 days
        
        return timedelta(hours=total_delay_hours)
    
    def _update_system_state(self):
        """Update overall system state"""
        # Update staff fatigue
        for staff in self.staff_members:
            if staff.is_available and staff.is_on_shift(self.current_time):
                staff.accumulate_fatigue(0.1)  # Small fatigue accumulation
        
        # Update environmental factors
        self.environmental_factors.timestamp = self.current_time
        self.environmental_factors.is_weekend = self.current_time.weekday() >= 5
        
        # Update metrics
        if self.station.stored_parcels:
            total_wait_time = sum(
                (self.current_time - parcel.arrival_time).total_seconds() / 3600
                for parcel in self.station.stored_parcels.values()
            )
            self.metrics['avg_wait_time'] = total_wait_time / len(self.station.stored_parcels)
        
        # Calculate system utilization
        total_capacity = sum(sum(shelf.capacity_volume.values()) for shelf in self.station.shelves)
        total_used = sum(sum(shelf.current_used_volume.values()) for shelf in self.station.shelves)
        self.metrics['system_utilization'] = total_used / total_capacity if total_capacity > 0 else 0
        
        # Calculate staff efficiency
        if self.staff_members:
            avg_efficiency = np.mean([s.get_efficiency() for s in self.staff_members])
            self.metrics['staff_efficiency'] = avg_efficiency
    
    def _perform_adaptive_management(self):
        """Perform adaptive management based on recent performance"""
        recent_history = self.adaptation_history[-100:]  # Last 100 events
        
        # Analyze patterns and adapt
        arrival_events = [e for e in recent_history if e.get('event_type') == 'arrival']
        pickup_events = [e for e in recent_history if e.get('event_type') == 'pickup']
        
        if arrival_events and pickup_events:
            arrival_rate = len(arrival_events) / len(recent_history)
            pickup_rate = len(pickup_events) / len(recent_history)
            
            # If arrivals are overwhelming pickups, trigger stress response
            if arrival_rate > pickup_rate * 2 and not self.stress_test_mode:
                self._trigger_stress_response()
    
    def _trigger_stress_response(self):
        """Trigger stress response measures"""
        # Add temporary staff
        temp_staff = StaffMember(
            staff_id=f"TEMP_{len(self.staff_members)}",
            name="Temporary Staff",
            skill_level=0.8,
            shift_start=self.current_time,
            shift_end=self.current_time + timedelta(hours=4)
        )
        self.staff_members.append(temp_staff)
        
        # Schedule stress response end
        stress_end_time = self.current_time + timedelta(hours=2)
        self.schedule_event(SimulationEvent(
            timestamp=stress_end_time,
            event_type=EventType.OPTIMIZATION_TRIGGER,
            data={'stress_response': True}
        ))
    
    def _calculate_final_metrics(self) -> Dict[str, float]:
        """Calculate final simulation metrics"""
        if self.metrics['total_arrivals'] > 0:
            pickup_rate = self.metrics['total_pickups'] / self.metrics['total_arrivals']
        else:
            pickup_rate = 0.0
        
        return {
            'pickup_rate': pickup_rate,
            'avg_wait_time_hours': self.metrics['avg_wait_time'],
            'system_utilization': self.metrics['system_utilization'],
            'staff_efficiency': self.metrics['staff_efficiency'],
            'environmental_impact': self.environmental_factors.get_impact_factor(),
            'total_events': len(self.adaptation_history),
            'customer_satisfaction': min(1.0, pickup_rate * (1.0 / max(1.0, self.metrics['avg_wait_time'])))
        }
    
    def _get_staff_performance_summary(self) -> Dict[str, Any]:
        """Get summary of staff performance"""
        return {
            'total_staff': len(self.staff_members),
            'available_staff': self.available_staff,
            'avg_skill_level': np.mean([s.skill_level for s in self.staff_members]),
            'avg_fatigue_level': np.mean([s.fatigue_level for s in self.staff_members]),
            'avg_efficiency': np.mean([s.get_efficiency() for s in self.staff_members])
        }
    
    def _apply_scenario_config(self, config: Dict[str, Any]):
        """Apply scenario-specific configuration"""
        if 'weather' in config:
            self.environmental_factors.weather = WeatherCondition(config['weather'])
        
        if 'is_holiday' in config:
            self.environmental_factors.is_holiday = config['is_holiday']
        
        if 'traffic_factor' in config:
            self.environmental_factors.traffic_condition = config['traffic_factor']
        
        if 'arrival_rate_multiplier' in config:
            multiplier = config['arrival_rate_multiplier']
            for hour in self.arrival_generator.base_hourly_rates:
                self.arrival_generator.base_hourly_rates[hour] *= multiplier


def create_enhanced_simulation(station: ParcelStation, 
                             optimizer: SLAPOptimizer,
                             predictor: PickupProbabilityPredictor) -> EnhancedDynamicSimulationEngine:
    """Factory function to create enhanced simulation engine"""
    return EnhancedDynamicSimulationEngine(station, optimizer, predictor)


# Example usage and testing
if __name__ == "__main__":
    from optimization_module import create_optimizer
    from learning_module import create_predictor
    import config
    
    # Create test setup
    station = ParcelStation()
    
    # Add shelves based on config
    for i in range(config.PREMIUM_SHELF_COUNT):
        shelf = Shelf(
            f"P{i+1}", 
            ShelfType.PREMIUM, 
            matrix_position=(0, i),
            capacity_small=config.SHELF_CAPACITY['premium'][config.ParcelSize.SMALL],
            capacity_medium=config.SHELF_CAPACITY['premium'][config.ParcelSize.MEDIUM],
            capacity_large=config.SHELF_CAPACITY['premium'][config.ParcelSize.LARGE],
            distance_to_exit=config.SHELF_DISTANCE_SCORES['premium'][i]
        )
        station.add_shelf(shelf)
    
    for i in range(config.STANDARD_SHELF_COUNT):
        shelf = Shelf(
            f"S{i+1}", 
            ShelfType.STANDARD,
            matrix_position=(1, i),
            capacity_small=config.SHELF_CAPACITY['standard'][config.ParcelSize.SMALL],
            capacity_medium=config.SHELF_CAPACITY['standard'][config.ParcelSize.MEDIUM],
            capacity_large=config.SHELF_CAPACITY['standard'][config.ParcelSize.LARGE],
            distance_to_exit=config.SHELF_DISTANCE_SCORES['standard'][i]
        )
        station.add_shelf(shelf)
    
    # Create components
    optimizer = create_optimizer("slap")
    predictor = create_predictor("rule_based")
    
    # Create enhanced simulation
    simulation = create_enhanced_simulation(station, optimizer, predictor)
    
    # Run test simulation
    print("Running enhanced dynamic simulation...")
    results = simulation.run_simulation(
        duration=timedelta(hours=24),
        stress_test=False,
        scenario_config={'weather': 'sunny', 'is_holiday': False}
    )
    
    print("Simulation Results:")
    print(f"Events processed: {results['events_processed']}")
    print(f"Final metrics: {results['final_metrics']}")
    print(f"Staff performance: {results['staff_performance']}")
    print("Enhanced simulation completed successfully!")