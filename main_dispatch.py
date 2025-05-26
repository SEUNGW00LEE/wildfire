"""
Wildfire Helicopter Dispatch Optimization System

This module provides functionality for helicopter dispatch optimization in wildfire scenarios.
It includes both basic deployment logic and advanced optimization using Pyomo.
All data is loaded from CSV files for maximum flexibility.
Configuration is loaded from config.json file.

Dependencies:
- os, sys, csv, random, datetime
- pandas, geopandas, matplotlib
- pyomo.environ
"""

import os
import sys
import csv
import random
import datetime
from typing import List, Dict, Tuple, Any, Optional

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pyomo.environ import *

from utils import config, ConfigManager, GeoUtils, ScenarioGenerator
from data_loader import DataLoader
from pyomo_optimizer import PyomoOptimizer

##############################################################################
# Basic Dispatch Logic
##############################################################################
class BasicDispatcher:
    """Implements a simplified dispatch logic based on proximity."""
    
    def __init__(self):
        """Initialize the basic dispatcher."""
        sim_params = config.get_simulation_params()
        random.seed(sim_params['random_seed'])
        
    def dispatch(self, fire_points: List[Dict[str, Any]]) -> pd.DataFrame:
        """Perform basic helicopter dispatch based on distance."""
        if not fire_points:
            return pd.DataFrame()
            
        # Load helicopter data
        helicopters_df = DataLoader.load_helicopters()
        if helicopters_df.empty:
            print("Cannot perform basic dispatch: No helicopter data available")
            return pd.DataFrame()
            
        # Make a copy and add available column
        heli_copy = helicopters_df.copy()
        heli_copy['available'] = heli_copy['helicopters']
        
        dispatch_log = []
        
        # Get configuration parameters
        max_range = config.get_optimization_params()['max_helicopter_range_km']
        fire_needs = config.get_simulation_params()['fire_helicopter_needs']
        
        # Process each fire
        for fire in fire_points:
            fire_loc = (fire['lat'], fire['lng'])
            
            # Calculate distance to each helipad
            heli_copy['distance'] = heli_copy.apply(
                lambda row: GeoUtils.calculate_distance(fire_loc, (row['lat'], row['lng'])), 
                axis=1
            )
            
            # Filter by maximum range and sort by distance
            near_heli = heli_copy[heli_copy['distance'] <= max_range].sort_values('distance')
            
            # Determine helicopters needed based on fire intensity
            needed = random.choices(fire_needs['options'], weights=fire_needs['weights'])[0]
            
            # Handle case where no helicopter is in range
            if near_heli.empty:
                dispatch_log.append({
                    'Fire Index': fire['name'],
                    'Heli Base': '초기대응불가',
                    'Heli Model': 'N/A',
                    'Heli Count': 0
                })
                continue
            
            # Handle case where not enough helicopters are available
            if near_heli['available'].sum() < needed:
                dispatch_log.append({
                    'Fire Index': fire['name'],
                    'Heli Base': '추가파견불가',
                    'Heli Model': 'N/A',
                    'Heli Count': 0
                })
                continue
            
            # Allocate helicopters
            for _, hp in near_heli.iterrows():
                if needed <= 0:
                    break
                    
                if hp['available'] > 0:
                    to_send = min(needed, hp['available'])
                    needed -= to_send
                    heli_copy.at[hp.name, 'available'] -= to_send
                    
                    dispatch_log.append({
                        'Fire Index': fire['name'],
                        'Heli Base': hp['name'],
                        'Heli Model': hp['model'],
                        'Heli Count': f"{to_send}/{hp['helicopters']}"
                    })
        
        return pd.DataFrame(dispatch_log)

##############################################################################
# Main Dispatcher Class
##############################################################################
class WildfireDispatcher:
    """Main class for wildfire helicopter dispatch."""
    
    def __init__(self):
        """Initialize dispatcher components."""
        sim_params = config.get_simulation_params()
        random.seed(sim_params['random_seed'])
        self.basic_dispatcher = BasicDispatcher()
        self.optimizer = PyomoOptimizer()
        
    def dispatch_basic(self, fire_points: List[Dict[str, Any]]) -> pd.DataFrame:
        """Perform basic dispatch."""
        return self.basic_dispatcher.dispatch(fire_points)
    
    def dispatch_optimized(self, fire_points: List[Dict[str, Any]]) -> pd.DataFrame:
        """Perform optimized dispatch using Pyomo."""
        if not fire_points:
            return pd.DataFrame()
            
        # Check if optimizer is properly initialized
        if self.optimizer.heli_df.empty or not self.optimizer.heli_locs:
            print("Cannot perform optimized dispatch: Missing helicopter data or configuration")
            return pd.DataFrame()
            
        # Group fires into scenarios
        scenario_sets = ScenarioGenerator.group_by_time_proximity(fire_points)
        
        # Load water sources
        water_pts = DataLoader.load_water_sources()
        
        result_df = pd.DataFrame()
        
        # Process each scenario group
        for group in scenario_sets:
            # Extract fire coordinates and intensities
            fire_coords = []
            difficulties = []
            for fidx in group:
                fire_coords.append((fire_points[fidx]['lat'], fire_points[fidx]['lng']))
                difficulties.append(fire_points[fidx]['intensity'])
            
            # Find optimal water sources for each fire-helicopter pair
            d1, d2, d3 = GeoUtils.find_optimal_water_sources(
                fire_coords, water_pts, self.optimizer.heli_locs
            )
            
            # Build and solve model
            model, cost_hf, time_hf = self.optimizer.build_model(
                group, difficulties, d1, d2, d3
            )
            
            if model is None:
                continue
                
            # Parse solution
            solution_df = self.optimizer.parse_solution(
                model, cost_hf, time_hf, d1, d2, d3, offset_index=min(group)
            )
            
            # Handle unassigned fires
            if not solution_df.empty:
                assigned_fires = set(solution_df["Fire Index"].tolist())
                all_fires = set(group)
                unassigned_fires = all_fires - assigned_fires
                
                for fidx in unassigned_fires:
                    solution_df = pd.concat([
                        solution_df, 
                        pd.DataFrame([{
                            "Fire Index": fidx,
                            "Heli Model": "초기대응 불가"
                        }])
                    ], ignore_index=True)
            
            # Append to results
            result_df = pd.concat([result_df, solution_df], ignore_index=True)
        
        # Clean up and finalize results
        if not result_df.empty and "Fire Index" in result_df.columns:
            result_df = result_df.sort_values(by="Fire Index").reset_index(drop=True)
            # Convert to 1-based indices for display
            result_df["Fire Index"] = result_df["Fire Index"] + 1
        
        return result_df
    
    @staticmethod
    def plot_results(result_df: pd.DataFrame, title: str = "Dispatch Results"):
        """Plot dispatch results."""
        if result_df.empty or "Fuel Cost" in result_df.columns:
            print("No data to plot.")
            return
            
        plt.figure(figsize=(10, 6))
        
        df_plot = result_df.groupby("Fire Index")["Fuel Cost"].sum().reset_index()
        plt.bar(df_plot["Fire Index"], df_plot["Fuel Cost"])
        plt.xlabel("Fire Index")
        plt.ylabel("Total Fuel Cost")
        plt.title(title)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
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
    print("\n=== 기본 배치 로직 결과 ===")
    df_basic = dispatcher.dispatch_basic(fire_data)
    if not df_basic.empty:
        print(df_basic)
    else:
        print("기본 배치 결과가 없습니다.")
    
    # Test optimization logic
    print("\n=== 최적화 결과 ===")
    df_opt = dispatcher.dispatch_optimized(fire_data)
    if not df_opt.empty:
        print(df_opt)
    else:
        print("최적화 결과가 없습니다.")
    
    # Visualize results
    if not df_opt.empty and "Fuel Cost" in df_opt.columns:
        WildfireDispatcher.plot_results(df_opt, "Optimized Dispatch Results")
    else:
        print("No optimization results to plot.")
    
    print("\n=== 실행 완료 ===")