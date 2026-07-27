#!/usr/bin/env python3
"""
快速验证脚本：只评估已有图索引的样本
"""
import os
import sys
import subprocess

def check_existing_indexes(graph_index_dir="LocAgent/index_data/SWE-bench_Verified/graph_index_v2.3"):
    """检查已有的图索引"""
    if not os.path.exists(graph_index_dir):
        print(f"Error: Graph index directory not found: {graph_index_dir}")
        return []

    pkl_files = [f for f in os.listdir(graph_index_dir) if f.endswith('.pkl')]
    instance_ids = [f.replace('.pkl', '') for f in pkl_files]

    print(f"Found {len(instance_ids)} existing graph indexes:")
    for i, instance_id in enumerate(instance_ids, 1):
        print(f"  {i}. {instance_id}")

    return instance_ids


def create_custom_dataset(instance_ids, output_file="data/custom_verified_samples.json"):
    """创建自定义样本列表"""
    import json

    data = {
        "instance_ids": instance_ids,
        "count": len(instance_ids),
        "created_at": "2026-07-27T22:40:00Z"
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nCustom dataset saved to: {output_file}")
    print(f"You can use --eval_n_limit {len(instance_ids)} to run all available samples")

    return output_file


def run_quick_verification(graph_index_dir, output_folder="results/locagent_verified_quick"):
    """运行快速验证"""
    instance_ids = check_existing_indexes(graph_index_dir)

    if not instance_ids:
        print("No existing graph indexes found!")
        return

    print(f"\n{'='*60}")
    print(f"Quick Verification with {len(instance_ids)} available samples")
    print(f"{'='*60}")

    # 创建运行命令
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "scripts/run_locagent_verified_10.ps1"
    ]

    # 修改参数
    print("\nYou can run:")
    print(f"  .\\LocAgent\\venv_locagent_py311\\Scripts\\python.exe \\")
    print(f"    -u LocAgent/run_with_local_data.py \\")
    print(f"    --dataset princeton-nlp/SWE-bench_Verified \\")
    print(f"    --split test \\")
    print(f"    --model anthropic/qwen-max \\")
    print(f"    --localize --merge \\")
    print(f"    --output_folder {output_folder} \\")
    print(f"    --eval_n_limit {len(instance_ids)} \\")
    print(f"    --num_processes 1 \\")
    print(f"    --num_samples 1 \\")
    print(f"    --max_attempt_num 1 \\")
    print(f"    --use_function_calling \\")
    print(f"    --simple_desc \\")
    print(f"    --timeout 900")

    print("\nOr create a custom PowerShell script:")
    ps_script = f"""$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Start-Transcript -Path (Join-Path $Root "{output_folder}\\console.log") -Force | Out-Null

try {{
  . .\\LocAgent\\scripts\\env\\set_env.ps1

  $env:PYTHONIOENCODING = "utf-8"
  $env:PYTHONPATH = "$Root\\LocAgent;$env:PYTHONPATH"
  $env:PYTHONUNBUFFERED = "1"
  $env:GRAPH_INDEX_DIR = "index_data/SWE-bench_Verified/graph_index_v2.3"
  $env:BM25_INDEX_DIR = "index_data/SWE-bench_Verified/BM25_index"

  Set-Location "$Root\\LocAgent"

  & "$Root\\venv_locagent_py311\\Scripts\\python.exe" -u run_with_local_data.py `
    --dataset "princeton-nlp/SWE-bench_Verified" `
    --split "test" `
    --model "anthropic/qwen-max" `
    --localize `
    --merge `
    --output_folder "..\\{output_folder}" `
    --eval_n_limit {len(instance_ids)} `
    --num_processes 1 `
    --num_samples 1 `
    --max_attempt_num 1 `
    --use_function_calling `
    --simple_desc `
    --timeout 900
}}
finally {{
  Stop-Transcript | Out-Null
}}
"""

    script_path = f"scripts/run_locagent_verified_quick.ps1"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(ps_script)

    print(f"\nPowerShell script created: {script_path}")
    print(f"Run it with: powershell -File {script_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--graph_index_dir", default="LocAgent/index_data/SWE-bench_Verified/graph_index_v2.3")
    parser.add_argument("--output_folder", default="results/locagent_verified_quick")
    parser.add_argument("--create_script", action="store_true")

    args = parser.parse_args()

    if args.create_script:
        run_quick_verification(args.graph_index_dir, args.output_folder)
    else:
        check_existing_indexes(args.graph_index_dir)