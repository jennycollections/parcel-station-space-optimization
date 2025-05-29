"""
Main entry point for the Cainiao Parcel Station LTO system.

This script provides a simple interface to run the complete LTO simulation
and demonstrates the "Learn-then-Optimize" workflow for parcel station management.

Usage:
    python main.py
"""

import sys
import argparse
from datetime import datetime

from simulation_engine import SimulationEngine
import config


def print_welcome():
    """Print welcome message and system information."""
    print("=" * 70)
    print("🏪 CAINIAO PARCEL STATION - LEARN-THEN-OPTIMIZE SYSTEM")
    print("=" * 70)
    print("This system demonstrates the application of LTO algorithms")
    print("to optimize parcel placement in Chinese parcel stations.")
    print()
    print("📦 LTO Process:")
    print("  1. LEARN: Predict parcel pickup probability")
    print("  2. OPTIMIZE: Assign parcels to optimal shelf locations")
    print("  3. ANALYZE: Evaluate system performance")
    print()


def print_configuration():
    """Print current configuration settings."""
    print("⚙️  SIMULATION CONFIGURATION:")
    print("-" * 40)
    print(f"Duration: {config.SIMULATION_HOURS} hours")
    print(f"Time steps: {config.TIME_STEP_MINUTES} minutes each")
    print(f"Premium shelves: {config.PREMIUM_SHELF_COUNT}")
    print(f"Standard shelves: {config.STANDARD_SHELF_COUNT}")
    print(f"High probability threshold: {config.HIGH_PROBABILITY_THRESHOLD}")
    print(f"Random seed: {config.RANDOM_SEED}")
    print()


def run_demo_scenario():
    """Run a quick demo scenario to show LTO in action."""
    print("🎯 QUICK DEMO: LTO Process in Action")
    print("-" * 40)
    
    from datetime import datetime, timedelta
    from data_structures import Parcel, ParcelSize, Shelf, ShelfType, ParcelStation
    from learning_module import create_predictor
    from optimization_module import create_optimizer
    
    # Create a mini station
    station = ParcelStation()
    station.add_shelf(Shelf("P1", ShelfType.PREMIUM, distance_to_exit=1.0))
    station.add_shelf(Shelf("S1", ShelfType.STANDARD, distance_to_exit=3.0))
    
    # Create predictor and optimizer
    predictor = create_predictor("rule_based")
    optimizer = create_optimizer("greedy")
    
    # Create demo parcels
    current_time = datetime(2024, 6, 10, 9, 0)  # 9 AM peak time
    demo_parcels = [
        Parcel("DEMO1", current_time - timedelta(minutes=10), ParcelSize.SMALL),
        Parcel("DEMO2", current_time - timedelta(hours=3), ParcelSize.MEDIUM),  # Off-peak arrival
    ]
    
    print("Processing demo parcels:")
    for i, parcel in enumerate(demo_parcels, 1):
        # LEARN: Predict probability
        prob = predictor.predict_pickup_probability(parcel, current_time)
        parcel.predicted_pickup_probability = prob
        
        # OPTIMIZE: Assign shelf
        shelf = optimizer.assign_parcel_to_shelf(parcel, station)
        
        print(f"  {i}. {parcel.parcel_id}: prob={prob:.2f} → {shelf.shelf_id if shelf else 'FAILED'} "
              f"({shelf.location_type.value if shelf else 'N/A'})")
    
    print()


def main():
    """Main function to run the LTO simulation."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Cainiao Parcel Station LTO Simulation")
    parser.add_argument("--demo", action="store_true", help="Run quick demo only")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    parser.add_argument("--hours", type=int, help="Override simulation duration (hours)")
    args = parser.parse_args()
    
    # Print welcome message
    if not args.quiet:
        print_welcome()
        print_configuration()
    
    # Run demo if requested
    if args.demo:
        run_demo_scenario()
        print("✅ Demo completed! Run without --demo for full simulation.")
        return
    
    # Override configuration if specified
    if args.hours:
        config.SIMULATION_HOURS = args.hours
        print(f"⏱️  Simulation duration overridden to {args.hours} hours")
        print()
    
    try:
        # Create and run simulation
        print("🚀 Starting full LTO simulation...")
        print()
        
        simulation = SimulationEngine(
            predictor_type="rule_based",
            optimizer_type="greedy"
        )
        
        # Run the simulation
        start_time = datetime.now()
        results = simulation.run_simulation()
        end_time = datetime.now()
        
        # Print results
        simulation.print_summary()
        
        # Print execution info
        execution_time = (end_time - start_time).total_seconds()
        print(f"\n⏱️  Execution time: {execution_time:.2f} seconds")
        
        if config.SAVE_RESULTS:
            print(f"💾 Detailed results saved to: {config.RESULTS_FILENAME}")
        
        print("\n✅ Simulation completed successfully!")
        
        # Provide next steps
        print("\n📊 NEXT STEPS:")
        print("- Review the simulation summary above")
        print("- Check the detailed results file for time-series data")
        print("- Experiment with different configurations in config.py")
        print("- Consider implementing ML-based learning for better predictions")
        
    except KeyboardInterrupt:
        print("\n⚠️  Simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during simulation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 