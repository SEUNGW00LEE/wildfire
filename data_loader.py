"""
DataManager class for loading and processing data files for wildfire helicopter dispatch.
"""

import pandas as pd
import geopandas as gpd
from typing import List, Dict, Tuple, Any

from utils import config

class DataLoader:
    """Handles loading and processing of data files."""

    @staticmethod
    def load_helicopters() -> pd.DataFrame:
        """Load helicopter data from CSV file."""
        try:
            return pd.read_csv(config.HELINFO_PATH)
        except FileNotFoundError:
            print(f"Error: Helicopter data file not found at {config.HELINFO_PATH}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error loading helicopter data: {e}")
            return pd.DataFrame()

    @staticmethod
    def load_helicopter_specs() -> pd.DataFrame:
        """Load helicopter specifications from CSV file."""
        try:
            return pd.read_csv(config.HELI_SPECS_PATH)
        except FileNotFoundError:
            print(f"Error: Helicopter specs file not found at {config.HELI_SPECS_PATH}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error loading helicopter specs: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load_helipads() -> List[Tuple[float, float, str]]:
        """Load helipad data from CSV file."""
        try:
            df = pd.read_csv(config.HELIPADS_PATH)
            return [(row['lat'], row['lng'], row['name']) for _, row in df.iterrows()]
        except FileNotFoundError:
            print(f"Error: Helipads data file not found at {config.HELIPADS_PATH}")
            return []
        except Exception as e:
            print(f"Error loading helipads data: {e}")
            return []
    
    @staticmethod
    def load_fires() -> List[Dict[str, Any]]:
        """Load fire data from CSV file."""
        try:
            df = pd.read_csv(config.FIREINFO_PATH)
            fires = []
            for _, row in df.iterrows():
                fires.append({
                    'name': row['name'],
                    'lat': float(row['lat']),
                    'lng': float(row['lng']),
                    'date': str(row['date']),
                    'time': str(row['time']),
                    'intensity': int(row['intensity'])
                })
            return fires
        except FileNotFoundError:
            print(f"Error: Fire data file not found at {config.FIREINFO_PATH}")
            return []
        except Exception as e:
            print(f"Error loading fire data: {e}")
            return []
    
    @staticmethod
    def load_detailed_helicopters() -> pd.DataFrame:
        """Load detailed helicopter configuration."""
        try:
            helis_df = pd.read_csv(config.SETHELIS_PATH)
            spec_matrix = DataLoader.load_helicopter_specs()
            # Merge heli data with specs
            if not helis_df.empty and not spec_matrix.empty:
                return helis_df.merge(spec_matrix, left_on='model', right_on='model_id', how='left')
            return pd.DataFrame()
        except FileNotFoundError:
            print(f"Error: Detailed helicopter data file not found at {config.SETHELIS_PATH}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error loading detailed helicopter data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load_water_sources() -> List[Tuple[float, float]]:
        """Load water sources from shapefile."""
        try:
            gdf = gpd.read_file(config.SHAPEFILE_WATER, encoding='euc-kr').to_crs(epsg=4326)
            return [(geom.y, geom.x) for geom in gdf.geometry]  # (lat, lng)
        except FileNotFoundError:
            print(f"Warning: Water sources shapefile not found at {config.SHAPEFILE_WATER}")
            return []
        except Exception as e:
            print(f"Warning: Failed to load water sources shapefile: {e}")
            return []