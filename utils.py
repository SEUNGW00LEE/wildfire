import json
import sys
import datetime
import shutil
from typing import Dict, Any, List, Tuple
from geopy.distance import geodesic

class ConfigManager:
    """Manages configuration loaded from JSON file."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize configuration from JSON file."""
        self.config = self._load_config(config_path)
        
        # Set up file paths directly from config
        self.HELINFO_PATH = self.config['paths']['helinfo']
        self.SETHELIS_PATH = self.config['paths']['set_helis']
        self.FIREINFO_PATH = self.config['paths']['fireinfo']
        self.HELIPADS_PATH = self.config['paths']['helipads']
        self.HELI_SPECS_PATH = self.config['paths']['heli_specs']
        self.SHAPEFILE_WATER = self.config['paths']['water_sources']
        
        # Dynamically set solver executable path
        self._set_solver_path()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)
    
    def _set_solver_path(self):
        """Dynamically set the solver executable path using shutil.which."""
        solver_name = self.config['solver'].get('name', 'glpk')  # Default to CBC
        executable_path = self.config['solver'].get('executable_path')
        
        # If executable_path is not provided or invalid, find it dynamically
        if not executable_path or not shutil.which(executable_path):
            # Try to find the solver executable
            solver_executables = {
                'cbc': 'cbc',
                'glpk': 'glpsol'
            }
            
            # First, try the specified solver
            executable = solver_executables.get(solver_name)
            if executable:
                executable_path = shutil.which(executable)
                if executable_path:
                    self.config['solver']['executable_path'] = executable_path
                    return
            
            # If the specified solver isn't found, try alternatives
            for name, exec_name in solver_executables.items():
                executable_path = shutil.which(exec_name)
                if executable_path:
                    print(f"Warning: Solver '{solver_name}' not found. Using '{name}' at {executable_path}")
                    self.config['solver']['name'] = name
                    self.config['solver']['executable_path'] = executable_path
                    return
            
            # If no solver is found, raise an error
            print(f"Error: No solver found (tried {', '.join(solver_executables.values())}). Please install CBC or GLPK.")
            sys.exit(1)
    
    def get_optimization_params(self) -> Dict[str, Any]:
        """Get optimization parameters."""
        return self.config['optimization']
    
    def get_solver_config(self) -> Dict[str, Any]:
        """Get solver configuration."""
        return self.config['solver']
    
    def get_simulation_params(self) -> Dict[str, Any]:
        """Get simulation parameters."""
        return self.config['simulation']

# Global configuration instance
config = ConfigManager()

class GeoUtils:
    """Geographic utility functions."""
    
    @staticmethod
    def calculate_distance(loc1: Tuple[float, float], 
                          loc2: Tuple[float, float]) -> float:
        """Calculate distance between two lat-lng points using geodesic."""
        return geodesic(loc1, loc2).kilometers
    
    @staticmethod
    def find_optimal_water_sources(fire_coords: List[Tuple[float, float]], 
                                  water_pts: List[Tuple[float, float]],
                                  heli_locs: List[Tuple[float, float]]) -> Tuple[List[List[float]], 
                                                                               List[List[float]], 
                                                                               List[List[float]]]:
        """For each fire and helicopter, find the optimal water source."""
        if not fire_coords or not heli_locs:
            return [], [], []
            
        # If no water sources available, use dummy point
        if not water_pts:
            print("Warning: No water sources available. Using dummy water source.")
            water_pts = [(lat + 0.01, lng + 0.01) for lat, lng in fire_coords]
        
        num_heli = len(heli_locs)
        d1 = [[] for _ in range(num_heli)]  # helicopter -> water
        d2 = [[] for _ in range(num_heli)]  # water -> fire
        d3 = [[] for _ in range(num_heli)]  # fire -> helicopter
        
        for fire_loc in fire_coords:
            # Calculate distances to all water sources
            dist_list = []
            for water_loc in water_pts:
                dist_km = GeoUtils.calculate_distance(fire_loc, water_loc)
                dist_list.append((water_loc, dist_km))
                
            # Get 3 nearest water sources
            nearest_3 = sorted(dist_list, key=lambda x: x[1])[:3]
            
            # For each helicopter, find optimal water source
            for h_idx, heli_loc in enumerate(heli_locs):
                best_val = float('inf')
                best_combo = (0, 0, 0)
                
                for water_loc, dist_fw in nearest_3:
                    dist_hw = GeoUtils.calculate_distance(heli_loc, water_loc)  # heli -> water
                    dist_fh = GeoUtils.calculate_distance(fire_loc, heli_loc)  # fire -> heli
                    total_dist = dist_hw + dist_fw + dist_fh
                    
                    if total_dist < best_val:
                        best_val = total_dist
                        best_combo = (dist_hw, dist_fw, dist_fh)
                
                d1[h_idx].append(best_combo[0])
                d2[h_idx].append(best_combo[1])
                d3[h_idx].append(best_combo[2])
        
        return d1, d2, d3

class ScenarioGenerator:
    """Handles scenario generation for wildfire incidents."""
    
    @staticmethod
    def group_by_time_proximity(fire_points: List[Dict[str, Any]]) -> List[List[int]]:
        """Group fires that occur within configured time window into scenarios."""
        if not fire_points:
            return []
            
        time_window = config.get_optimization_params()['scenario_time_window_minutes']
        
        # Convert fires to (index, datetime) pairs
        temp_list = []
        for i, f in enumerate(fire_points):
            dt_str = f['date'] + " " + f['time']  # "YYYY-MM-DD HH:MM"
            dt_fmt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            temp_list.append((i, dt_fmt))

        # Sort by datetime
        temp_list.sort(key=lambda x: x[1])

        # Group fires within time window
        scenario_sets = []
        current_set = []
        for idx, dt in temp_list:
            if not current_set:
                current_set.append((idx, dt))
            else:
                prev_dt = current_set[-1][1]
                diff_mins = (dt - prev_dt).total_seconds() / 60.0
                # Same scenario group if within time window
                if diff_mins <= time_window:
                    current_set.append((idx, dt))
                else:
                    scenario_sets.append([x[0] for x in current_set])
                    current_set = [(idx, dt)]
        
        # Add final group if exists
        if current_set:
            scenario_sets.append([x[0] for x in current_set])

        return scenario_sets