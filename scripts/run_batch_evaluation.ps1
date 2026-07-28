#!/usr/bin/env powershell
# 运行3个样本的批量评估（使用已有图索引）

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 创建输出目录
$OutputDir = "results\locagent_verified_batch_final"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# 开始转录
Start-Transcript -Path (Join-Path $Root "$OutputDir\console.log") -Force | Out-Null

try {
  # 加载环境变量
  . .\LocAgent\scripts\env\set_env.ps1

  # 设置必要的环境变量
  $env:PYTHONIOENCODING = "utf-8"
  $env:PYTHONPATH = "$Root\LocAgent;$env:PYTHONPATH"
  $env:PYTHONUNBUFFERED = "1"

  # 图索引和BM25索引路径
  $env:GRAPH_INDEX_DIR = "index_data/SWE-bench_Verified/graph_index_v2.3"
  $env:BM25_INDEX_DIR = "index_data/SWE-bench_Verified/BM25_index"

  Write-Host "Environment variables set:"
  Write-Host "  GRAPH_INDEX_DIR: $($env:GRAPH_INDEX_DIR)"
  Write-Host "  BM25_INDEX_DIR: $($env:BM25_INDEX_DIR)"
  Write-Host "  ANTHROPIC_API_KEY: $(if($env:ANTHROPIC_API_KEY){'set'}else{'NOT SET'})"

  Set-Location "$Root\LocAgent"

  # 运行LocAgent
  & "$Root\venv_locagent_py311\Scripts\python.exe" -u run_with_local_data.py `
    --dataset "princeton-nlp/SWE-bench_Verified" `
    --split "test" `
    --model "anthropic/qwen-max" `
    --localize `
    --merge `
    --output_folder "..\$OutputDir" `
    --eval_n_limit 3 `
    --num_processes 1 `
    --num_samples 1 `
    --max_attempt_num 1 `
    --use_function_calling `
    --simple_desc `
    --timeout 900

  Write-Host "`nEvaluation completed successfully!"
}
catch {
  Write-Host "`nError occurred: $_"
  Write-Host $_.ScriptStackTrace
  throw
}
finally {
  Stop-Transcript | Out-Null
}