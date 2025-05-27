"""
Wildfire Helicopter Dispatch Optimization System

Main execution script for helicopter dispatch optimization in wildfire scenarios.
Uses dispatcher classes for both basic deployment logic and advanced optimization.
All data is loaded from CSV files for maximum flexibility.
Configuration is loaded from config.json file.

Dependencies:
- pandas, geopandas, matplotlib
- pyomo.environ
"""

import sys
from data_loader import DataLoader
from dispatcher import WildfireDispatcher


def main():
    """Main execution function."""
    # Check if required CSV files exist
    print("Checking required CSV files...")
    
    # Load fire data from CSV
    fire_data = DataLoader.load_fires()
    
    if not fire_data:
        print("No fire data loaded. Please check the fireinfo.csv file.")
        sys.exit(1)
    
    print(f"\nLoaded {len(fire_data)} fires from CSV file")
    
    # Create WildfireDispatcher instance
    dispatcher = WildfireDispatcher()
    
    # Test basic dispatch logic
    print("\n=== Basic Dispatch Result ===")
    df_basic = dispatcher.dispatch_basic(fire_data)
    if not df_basic.empty:
        print(df_basic)
    else:
        print("No Basic Dispatch Result")
    
    # Test optimization logic
    print("\n=== Optimization Result ===")
    df_opt = dispatcher.dispatch_optimized(fire_data)
    if not df_opt.empty:
        print(df_opt)
    else:
        print("No Optimization Result")
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()