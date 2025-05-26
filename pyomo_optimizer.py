"""
Pyomo-based optimizer for wildfire helicopter dispatch.
"""

from typing import List, Tuple, Optional
import pandas as pd
from pyomo.environ import *

from utils import config
from data_loader import DataLoader

class PyomoOptimizer:
    """Implements optimization-based helicopter dispatch using Pyomo."""
    
    def __init__(self):
        """Initialize the optimizer."""
        self.heli_df = DataLoader.load_detailed_helicopters()
        self.helipads = DataLoader.load_helipads()
        self.opt_params = config.get_optimization_params()
        
        # Initialize model parameters
        self.speed_w1 = []
        self.speed_w2 = []
        self.efficiency = []
        self.load_capa = []
        self.time_limit = []
        self.supp_capa = []
        self.heli_locs = []
        
        # Initialize if data is available
        if not self.heli_df.empty and self.helipads:
            self._init_parameters()
        else:
            print("Warning: Cannot initialize PyomoOptimizer - missing helicopter or helipad data")
            
    def _init_parameters(self):
        """Initialize parameters from helicopter data."""
        self.speed_w1 = list(self.heli_df.speed_w1)
        self.speed_w2 = list(self.heli_df.speed_w2)
        self.efficiency = list(self.heli_df.efficiency)
        self.load_capa = list(self.heli_df.load_capa)
        self.time_limit = list(self.heli_df.time_limit)
        self.supp_capa = list(self.heli_df.supp_capa)
        
        # Map base index to coordinates from loaded helipads
        self.heli_locs = []
        for base_idx in self.heli_df["base"]:
            if 0 <= base_idx < len(self.helipads):
                self.heli_locs.append((self.helipads[base_idx][0], self.helipads[base_idx][1]))
            else:
                print(f"Warning: Invalid base index {base_idx}")
                return  # Stop initialization if invalid base index

    def objective_rule(self, model):
        """Objective function: minimize cost + penalty for unaddressed fires"""
        return (
            sum(model.cost_hf[h, f] * model.AssignFire[h, f] for h in model.H for f in model.F) +
            sum(self.opt_params['big_penalty'] * (1 - model.FireOn[f]) for f in model.F)
        )
    
    def golden_time_rule(self, model, h, f):
        """Constraint 1: Golden time (arrival within configured minutes)"""
        if model.arrival_time_hf[h, f] > self.opt_params['golden_time_minutes']:
            return model.Assign[h, f] == 0
        return Constraint.Skip
    
    def time_limit_rule(self, model, h, f):
        """Constraint 2: Helicopter time limit"""
        if model.time_hf[h, f] > model.TIME_LIMIT[h]:
            return model.Assign[h, f] == 0
        return Constraint.Skip
    
    def suppression_rule(self, model, f):
        """Constraint 3: Fire suppression capacity"""
        return model.difficulties[f] * model.FireOn[f] <= sum(
            model.SUPP_CAPA[h] * model.Assign[h, f] for h in model.H
        )
    
    def one_assignment_rule(self, model, h):
        """Constraint 4: One helicopter can address only one fire"""
        return sum(model.Assign[h, f] for f in model.F) <= 1
        
    def assignfire_upper_bound1(self, model, h, f):
        """Linearization constraint 1"""
        return model.AssignFire[h, f] <= model.Assign[h, f]
    
    def assignfire_upper_bound2(self, model, h, f):
        """Linearization constraint 2"""
        return model.AssignFire[h, f] <= model.FireOn[f]
    
    def assignfire_lower_bound(self, model, h, f):
        """Linearization constraint 3"""
        return model.AssignFire[h, f] >= model.Assign[h, f] + model.FireOn[f] - 1

    def calculate_time_matrices(self, d1, d2, d3, fire_indices):
        """Calculate time and cost matrices"""
        time_hf_list = [[
            (d1[h][f] / self.speed_w1[h]) + 
            (d2[h][f] / self.speed_w2[h]) + 
            (d3[h][f] / self.speed_w1[h])
            for f in range(len(fire_indices))
        ] for h in range(len(self.heli_locs))]
        
        cost_hf_list = [[
            self.opt_params['fuel_rate'] * self.efficiency[h] * time_hf_list[h][f]
            for f in range(len(fire_indices))
        ] for h in range(len(self.heli_locs))]
        
        arrival_time_hf_list = [[
            (d1[h][f] / self.speed_w1[h]) + (d2[h][f] / self.speed_w2[h])
            for f in range(len(fire_indices))
        ] for h in range(len(self.heli_locs))]
        
        return time_hf_list, cost_hf_list, arrival_time_hf_list
        
    def build_model(self, fire_indices: List[int], 
                    difficulties: List[int], 
                    d1: List[List[float]], 
                    d2: List[List[float]], 
                    d3: List[List[float]]) -> Tuple[Optional[ConcreteModel], 
                                                  List[List[float]], 
                                                  List[List[float]]]:
        """Build Pyomo optimization model."""
        if not fire_indices or self.heli_df.empty or not self.heli_locs:
            print("Cannot build optimization model: Missing required data")
            return None, None, None
            
        # Create model
        model = ConcreteModel()
        
        # Define sets
        model.H = RangeSet(0, len(self.heli_locs) - 1)  # Helicopters
        model.F = RangeSet(0, len(fire_indices) - 1)    # Fires
        
        # Define variables
        model.Assign = Var(model.H, model.F, domain=Binary)  # Helicopter h assigned to fire f
        model.FireOn = Var(model.F, domain=Binary)           # Fire f is being addressed
        model.AssignFire = Var(model.H, model.F, domain=Binary)  # Linearization variable
        
        time_hf_list, cost_hf_list, arrival_time_hf_list = self.calculate_time_matrices(d1, d2, d3, fire_indices)

        # Define parameters
        model.time_hf = Param(
            model.H, model.F, 
            initialize={(h, f): time_hf_list[h][f] for h in model.H for f in model.F}
        )
        model.cost_hf = Param(
            model.H, model.F, 
            initialize={(h, f): cost_hf_list[h][f] for h in model.H for f in model.F}
        )
        model.arrival_time_hf = Param(
            model.H, model.F, 
            initialize={(h, f): arrival_time_hf_list[h][f] for h in model.H for f in model.F}
        )
        model.difficulties = Param(
            model.F, 
            initialize={f: difficulties[f] for f in model.F}
        )
        model.SUPP_CAPA = Param(
            model.H, 
            initialize={h: self.supp_capa[h] for h in model.H}
        )
        model.TIME_LIMIT = Param(
            model.H, 
            initialize={h: self.time_limit[h] for h in model.H}
        )
        
        # Linear constraints
        model.AssignFire_ub1 = Constraint(model.H, model.F, rule=self.assignfire_upper_bound1)
        model.AssignFire_ub2 = Constraint(model.H, model.F, rule=self.assignfire_upper_bound2)
        model.AssignFire_lb = Constraint(model.H, model.F, rule=self.assignfire_lower_bound)
        
        # Apply objective function and constraints
        model.objective = Objective(rule=self.objective_rule, sense=minimize)
        model.golden_time_constraint = Constraint(model.H, model.F, rule=self.golden_time_rule)
        model.time_limit_constraint = Constraint(model.H, model.F, rule=self.time_limit_rule)
        model.suppression_constraint = Constraint(model.F, rule=self.suppression_rule)
        model.one_assignment_constraint = Constraint(model.H, rule=self.one_assignment_rule)        
        
        # Solve model
        try:
            solver_config = config.get_solver_config()
            solver = SolverFactory(solver_config['name'], executable=solver_config['executable_path'])
            result = solver.solve(model)
            
            if result.solver.termination_condition != TerminationCondition.optimal:
                print("[Pyomo] Could not find optimal solution.")
                return None, None, None
                
            return model, cost_hf_list, time_hf_list
            
        except Exception as e:
            print(f"Error solving model: {e}")
            return None, None, None
    
    def parse_solution(self, model: ConcreteModel, 
                      cost_hf: List[List[float]], 
                      time_hf: List[List[float]], 
                      d1: List[List[float]], 
                      d2: List[List[float]], 
                      d3: List[List[float]], 
                      offset_index: int = 0) -> pd.DataFrame:
        """Parse Pyomo solution into DataFrame."""
        if model is None:
            return pd.DataFrame()
            
        results = []
        
        # Process assignments
        for h in model.H:
            for f in model.F:
                if model.Assign[h, f].value is not None and model.Assign[h, f].value > 0.5:
                    dist1, dist2, dist3 = d1[h][f], d2[h][f], d3[h][f]
                    t = time_hf[h][f]
                    c = cost_hf[h][f]
                    
                    # Get helicopter info
                    model_name = self.heli_df.loc[h, 'model_nm']
                    base_idx = self.heli_df.loc[h, 'base']
                    base_name = self.helipads[base_idx][2] if 0 <= base_idx < len(self.helipads) else "UnknownBase"
                    
                    results.append({
                        "Fire Index": offset_index + f,
                        "Hel Index": h + 1,
                        "Heli Model": model_name,
                        "Heli Base": base_name,
                        "Dist1 (H2W)": round(dist1, 2),
                        "Dist2 (W2F)": round(dist2, 2),
                        "Dist3 (F2H)": round(dist3, 2),
                        "Travel Time": round(t, 2),
                        "Fuel Cost": round(c, 2),
                    })
        
        # Create and sort DataFrame
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values(by="Fire Index").reset_index(drop=True)
            
        return df