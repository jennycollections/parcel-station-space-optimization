"""
Test script for the Cainiao Parcel Station LTO system.

This script runs comprehensive tests to verify that all components
of the LTO system are working correctly.
"""

import sys
from datetime import datetime, timedelta

def test_data_structures():
    """Test the core data structures."""
    print("🧪 Testing Data Structures...")
    
    from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
    
    # Test Parcel
    parcel = Parcel("TEST001", datetime.now(), ParcelSize.SMALL)
    assert parcel.parcel_id == "TEST001"
    assert parcel.size == ParcelSize.SMALL
    assert parcel.predicted_pickup_probability is None
    
    # Test Shelf
    shelf = Shelf("S1", ShelfType.PREMIUM, distance_to_exit=1.5)
    assert shelf.shelf_id == "S1"
    assert shelf.location_type == ShelfType.PREMIUM
    assert shelf.can_accommodate(ParcelSize.SMALL)
    
    # Test adding parcel to shelf
    success = shelf.add_parcel(parcel)
    assert success
    assert parcel.assigned_shelf_id == "S1"
    assert len(shelf.parcels_stored) == 1
    
    # Test ParcelStation
    station = ParcelStation()
    station.add_shelf(shelf)
    assert len(station.shelves) == 1
    
    print("✅ Data structures test passed!")


def test_learning_module():
    """Test the learning module."""
    print("🧪 Testing Learning Module...")
    
    from learning_module import create_predictor
    from data_structures import Parcel, ParcelSize
    
    predictor = create_predictor("rule_based")
    
    # Test prediction
    current_time = datetime(2024, 6, 10, 9, 0)  # Peak morning
    parcel = Parcel("TEST002", current_time - timedelta(minutes=30), ParcelSize.SMALL)
    
    prob = predictor.predict_pickup_probability(parcel, current_time)
    assert 0.0 <= prob <= 1.0
    assert prob > 0.5  # Should be high during peak time
    
    # Test explanation
    explanation = predictor.get_prediction_explanation(parcel, current_time)
    assert "TEST002" in explanation
    assert "peak_morning" in explanation
    
    print("✅ Learning module test passed!")


def test_optimization_module():
    """Test the optimization module."""
    print("🧪 Testing Optimization Module...")
    
    from optimization_module import create_optimizer
    from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
    
    # Setup test environment
    station = ParcelStation()
    premium_shelf = Shelf("P1", ShelfType.PREMIUM, distance_to_exit=1.0)
    standard_shelf = Shelf("S1", ShelfType.STANDARD, distance_to_exit=3.0)
    station.add_shelf(premium_shelf)
    station.add_shelf(standard_shelf)
    
    optimizer = create_optimizer("greedy")
    
    # Test high probability parcel (should go to premium)
    high_prob_parcel = Parcel("HIGH", datetime.now(), ParcelSize.SMALL)
    high_prob_parcel.predicted_pickup_probability = 0.9
    
    assigned_shelf = optimizer.assign_parcel_to_shelf(high_prob_parcel, station)
    assert assigned_shelf is not None
    assert assigned_shelf.location_type == ShelfType.PREMIUM
    
    # Test low probability parcel (should prefer standard, but may go to premium if available)
    low_prob_parcel = Parcel("LOW", datetime.now(), ParcelSize.SMALL)
    low_prob_parcel.predicted_pickup_probability = 0.3
    
    assigned_shelf = optimizer.assign_parcel_to_shelf(low_prob_parcel, station)
    assert assigned_shelf is not None
    # Note: Low prob parcel may still go to premium if it's the best available option
    
    # Test statistics
    stats = optimizer.get_assignment_statistics()
    assert stats['total_assignments'] == 2
    assert stats['premium_assignments'] >= 1  # At least the high prob parcel
    assert stats['total_assignments'] == stats['premium_assignments'] + stats['standard_assignments']
    
    print("✅ Optimization module test passed!")


def test_simulation_engine():
    """Test the simulation engine."""
    print("🧪 Testing Simulation Engine...")
    
    from simulation_engine import SimulationEngine
    import config
    
    # Override config for quick test
    original_hours = config.SIMULATION_HOURS
    config.SIMULATION_HOURS = 1  # Just 1 hour for testing
    
    try:
        simulation = SimulationEngine("rule_based", "greedy")
        
        # Test initialization
        assert len(simulation.station.shelves) > 0
        assert simulation.predictor is not None
        assert simulation.optimizer is not None
        
        # Run short simulation
        results = simulation.run_simulation()
        
        # Verify results structure
        assert 'assignments' in results
        assert 'time_steps' in results
        assert 'final_statistics' in results
        
        # Check that some parcels were processed
        total_parcels = results['final_statistics']['total_parcels_processed']
        assert total_parcels >= 0  # Could be 0 if no arrivals in 1 hour
        
        print("✅ Simulation engine test passed!")
        
    finally:
        # Restore original config
        config.SIMULATION_HOURS = original_hours


def test_lto_integration():
    """Test the complete LTO integration."""
    print("🧪 Testing LTO Integration...")
    
    from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
    from learning_module import create_predictor
    from optimization_module import create_optimizer
    
    # Create mini LTO system
    station = ParcelStation()
    station.add_shelf(Shelf("P1", ShelfType.PREMIUM, distance_to_exit=1.0))
    station.add_shelf(Shelf("S1", ShelfType.STANDARD, distance_to_exit=3.0))
    
    predictor = create_predictor("rule_based")
    optimizer = create_optimizer("greedy")
    
    # Test LTO workflow
    current_time = datetime(2024, 6, 10, 9, 0)  # Peak time
    test_parcels = [
        Parcel("LTO1", current_time - timedelta(minutes=10), ParcelSize.SMALL),
        Parcel("LTO2", current_time - timedelta(hours=5), ParcelSize.MEDIUM),  # Off-peak
    ]
    
    assignments = []
    for parcel in test_parcels:
        # LEARN
        prob = predictor.predict_pickup_probability(parcel, current_time)
        parcel.predicted_pickup_probability = prob
        
        # OPTIMIZE
        shelf = optimizer.assign_parcel_to_shelf(parcel, station)
        assignments.append((parcel, shelf))
    
    # Verify LTO logic
    peak_parcel, peak_shelf = assignments[0]
    off_peak_parcel, off_peak_shelf = assignments[1]
    
    # Peak time parcel should have higher probability
    assert peak_parcel.predicted_pickup_probability > off_peak_parcel.predicted_pickup_probability
    
    # Both should be assigned successfully
    assert peak_shelf is not None
    assert off_peak_shelf is not None
    
    print("✅ LTO integration test passed!")


def test_configuration():
    """Test configuration validation."""
    print("🧪 Testing Configuration...")
    
    import config
    
    # Test configuration validation
    try:
        config.validate_config()
        print("✅ Configuration validation passed!")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    return True


def run_all_tests():
    """Run all tests."""
    print("🚀 Running Cainiao LTO System Tests")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_data_structures,
        test_learning_module,
        test_optimization_module,
        test_simulation_engine,
        test_lto_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result is not False:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with error: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The LTO system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 