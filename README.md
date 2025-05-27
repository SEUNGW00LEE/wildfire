# Wildfire Helicopter Dispatch Optimization

This project provides an optimization-based system for efficiently dispatching helicopters in response to wildfires. It simulates both basic proximity-based dispatch and mathematical optimization using Pyomo.

## Project Structure

- `main.py` : Entry point for execution
- `dispatcher.py` : Implements basic and optimized dispatch logic
- `pyomo_optimizer.py` : Pyomo-based optimization model
- `data_loader.py` : Loads CSV and Shapefile data
- `utils.py` : Configuration management and utilities
- `experiment_runner.sh` : Automates experiment parameter setting and runs the simulation
- `config.json` : Project configuration file
- `environment.yaml` : Conda environment definition

---

## Installation

### 1. Create Conda Environment

Make sure Anaconda or Miniconda is installed.

```bash
conda env create -f environment.yaml
conda activate wildfire-env
```

> The environment includes Pyomo and both GLPK and CBC solvers, so no additional solver installation is required.

---

## Data File Structure

All input paths are defined in `config.json` under the `paths` section:

```json
"paths": {
  "helinfo": "static/helinfo.csv",
  "set_helis": "static/set_helis.csv",
  "fireinfo": "static/fireinfo.csv",
  "helipads": "static/helipads.csv",
  "heli_specs": "static/heli_specs.csv",
  "water_sources": "static/shp/waters.shp"
}
```

### ✅ Example Project Directory Structure

```
wildfire_project/
├── main.py
├── dispatcher.py
├── pyomo_optimizer.py
├── data_loader.py
├── utils.py
├── config.json
├── environment.yaml
├── experiment_runner.sh
├── static/
│   ├── helinfo.csv
│   ├── set_helis.csv
│   ├── fireinfo.csv
│   ├── helipads.csv
│   ├── heli_specs.csv
│   └── shp/
│       ├── waters.shp
│       ├── waters.dbf
│       ├── waters.shx
│       ├── waters.prj
│       └── waters.cpg
```

> The Shapefile should include all related files (e.g., `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`) for successful loading.

---

## How to Run

### Basic Run

```bash
python main.py
```

- Loads wildfire data and prints both basic and optimized dispatch results.

### Experiment Script (Automated Run)

```bash
chmod +x experiment_runner.sh
./experiment_runner.sh
```

- Updates parameters in `config.json` and runs `main.py`.
- Parameters set in the script include:
  - `fuel_rate`
  - `big_penalty` (penalty for unaddressed fires)
  - `golden_time_minutes`
  - `scenario_time_window_minutes`
  - `max_helicopter_range_km`
  - `random_seed`

---

## Output Example

```
=== Basic Dispatch Result ===
Fire Index  |  Heli Base  |  Heli Model  |  Heli Count
-------------------------------------------------------
A001        |  Station1   |  HH-60       |  2/4
...

=== Optimization Result ===
Fire Index  |  Hel Index  |  Heli Model  |  Heli Base  |  Travel Time  |  Fuel Cost
------------------------------------------------------------------------------------
1           |  2          |  HH-60       |  Base A     |  12.6         |  33.2
...
```

---

## Notes

- All input files must exist at the paths defined in `config.json`.
- The Shapefile must be complete and encoded properly (e.g., EUC-KR) for GeoPandas to load.
- Essential CSVs include:
  - `set_helis.csv`
  - `heli_specs.csv`
  - `fireinfo.csv`
- Fires that cannot be addressed may appear as `"Unreachable"` in the output.

---

## License

This project is intended for research and educational use. For commercial use, please contact the authors.
