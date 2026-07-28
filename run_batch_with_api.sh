#!/bin/bash

# Set environment variables
export LOCAL_DATASET_PATCH=true
export GRAPH_INDEX_DIR=index_data/SWE-bench_Verified/graph_index_v2.3
export BM25_INDEX_DIR=index_data/SWE-bench_Verified/BM25_index

# Use existing API key from environment
export ANTHROPIC_API_KEY="${ANTHROPIC_AUTH_TOKEN}"
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL}"

echo "API Key set: ${ANTHROPIC_API_KEY:0:10}..."
echo "Base URL: $ANTHROPIC_BASE_URL"

# Run evaluation
cd LocAgent
../venv_locagent_py311/Scripts/python.exe auto_search_main.py \
  --localize \
  --merge \
  --model anthropic/qwen-max \
  --dataset princeton-nlp/SWE-bench_Verified \
  --num_samples 3 \
  --output_folder results/locagent_batch_fixed \
  --max_attempt_num 1 \
  --num_processes 1 \
  --use_function_calling \
  --simple_desc
