$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Start-Transcript -Path (Join-Path $Root "results/locagent_verified_quick\console.log") -Force | Out-Null

try {
  . .\LocAgent\scripts\env\set_env.ps1

  $env:PYTHONIOENCODING = "utf-8"
  $env:PYTHONPATH = "$Root\LocAgent;$env:PYTHONPATH"
  $env:PYTHONUNBUFFERED = "1"
  $env:GRAPH_INDEX_DIR = "index_data/SWE-bench_Verified/graph_index_v2.3"
  $env:BM25_INDEX_DIR = "index_data/SWE-bench_Verified/BM25_index"

  Set-Location "$Root\LocAgent"

  & "$Root\venv_locagent_py311\Scripts\python.exe" -u run_with_local_data.py `
    --dataset "princeton-nlp/SWE-bench_Verified" `
    --split "test" `
    --model "anthropic/qwen-max" `
    --localize `
    --merge `
    --output_folder "..\results/locagent_verified_quick" `
    --eval_n_limit 1 `
    --num_processes 1 `
    --num_samples 1 `
    --max_attempt_num 1 `
    --use_function_calling `
    --simple_desc `
    --timeout 900
}
finally {
  Stop-Transcript | Out-Null
}
