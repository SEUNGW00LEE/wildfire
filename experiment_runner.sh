#!/bin/bash

# Optimization parameter
fuel_rate=0.15
big_penalty=100
golden_time_minutes=15
scenario_time_window_minutes=30
max_helicopter_range_km=120

# Simulation parameter
random_seed=40

# config.json update
python3 -c "
import json

# config.json read
with open('config.json', 'r') as f:
    config = json.load(f)

# 파라미터 업데이트
config['optimization']['fuel_rate'] = $fuel_rate
config['optimization']['big_penalty'] = $big_penalty
config['optimization']['golden_time_minutes'] = $golden_time_minutes
config['optimization']['scenario_time_window_minutes'] = $scenario_time_window_minutes
config['optimization']['max_helicopter_range_km'] = $max_helicopter_range_km
config['simulation']['random_seed'] = $random_seed

# config.json 쓰기
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
"

echo "Running experiment with parameters:"
echo "  fuel_rate: $fuel_rate"
echo "  big_penalty: $big_penalty"
echo "  golden_time_minutes: $golden_time_minutes"
echo "  scenario_time_window_minutes: $scenario_time_window_minutes"
echo "  max_helicopter_range_km: $max_helicopter_range_km"
echo "  random_seed: $random_seed"
echo ""

python main.py