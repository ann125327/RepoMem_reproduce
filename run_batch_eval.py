#!/usr/bin/env python3
"""
Batch evaluation script for LocAgent
"""
import os
import sys
import subprocess
import json
from datetime import datetime

# Configuration
NUM_SAMPLES = 3
OUTPUT_DIR = "results/locagent_verified_batch_continue"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Use virtual environment Python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, "venv_locagent_py311", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    print(f"Error: Virtual environment Python not found at {VENV_PYTHON}")
    sys.exit(1)

# Set environment variables
os.environ['GRAPH_INDEX_DIR'] = 'index_data/SWE-bench_Verified/graph_index_v2.3'
os.environ['BM25_INDEX_DIR'] = 'index_data/SWE-bench_Verified/BM25_index'
os.environ['LOCAL_DATASET_PATCH'] = 'true'

print(f"Starting batch evaluation at {datetime.now()}")
print(f"Output directory: {OUTPUT_DIR}")
print(f"Number of samples: {NUM_SAMPLES}")

# Run evaluation
cmd = [
    VENV_PYTHON,
    "auto_search_main.py",
    "--model_name", "anthropic/qwen-max",
    "--dataset", "SWE-bench_Verified",
    "--num_samples", str(NUM_SAMPLES),
    "--output_dir", OUTPUT_DIR,
    "--max_attempts", "1",
    "--max_workers", "1"
]

print(f"Command: {' '.join(cmd)}")

try:
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=False,
        text=True
    )
    print(f"\nEvaluation completed successfully at {datetime.now()}")
except subprocess.CalledProcessError as e:
    print(f"\nEvaluation failed with error: {e}")
    sys.exit(1)

# Check results
output_file = os.path.join(OUTPUT_DIR, "loc_outputs.jsonl")
if os.path.exists(output_file):
    with open(output_file, 'r') as f:
        lines = f.readlines()
    print(f"\nResults: {len(lines)} samples processed")

    # Show summary
    for line in lines:
        data = json.loads(line)
        print(f"Instance: {data['instance_id']}")
        print(f"  Files found: {len(data.get('found_files', [[]])[0])}")
        print(f"  Modules found: {len(data.get('found_modules', [[]])[0])}")
else:
    print(f"\nWarning: Output file not found: {output_file}")