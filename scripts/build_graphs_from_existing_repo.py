#!/usr/bin/env python3
"""
从已有的astropy仓库直接构建图索引
不需要重新克隆仓库
"""
import os
import sys
import pickle
from pathlib import Path

# 添加 LocAgent 到路径
sys.path.insert(0, 'LocAgent')

# 应用本地数据补丁
import scripts.local_dataset_patch  # noqa: F401
from datasets import load_dataset
from dependency_graph.build_graph import build_graph

def build_graphs_for_astropy_samples(num_samples=3):
    """为astropy样本构建图索引"""

    # 已有的astropy仓库路径
    existing_repo = Path("LocAgent/playground/2a8ea0d0-94e3-4956-97f1-7edb1e1980a4/astropy_astropy")

    if not existing_repo.exists():
        print(f"Error: Existing repo not found at {existing_repo}")
        return

    print(f"Using existing repo: {existing_repo}")

    # 加载数据集
    print("Loading SWE-bench_Verified dataset...")
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test', trust_remote_code=True)
    samples = list(ds.select(range(num_samples)))

    print(f"Processing {len(samples)} samples...")

    # 图索引输出目录
    index_dir = Path("LocAgent/index_data/SWE-bench_Verified/graph_index_v2.3")
    index_dir.mkdir(parents=True, exist_ok=True)

    for i, sample in enumerate(samples, 1):
        instance_id = sample['instance_id']
        base_commit = sample['base_commit']

        print(f"\n[{i}/{len(samples)}] {instance_id}")
        print(f"  Base commit: {base_commit[:10]}...")

        # 检查是否已存在
        graph_file = index_dir / f"{instance_id}.pkl"
        if graph_file.exists():
            print(f"  [OK] Already exists, skipping")
            continue

        try:
            # 切换到指定commit
            import subprocess
            print(f"  Checking out commit...")
            subprocess.run(
                ['git', 'reset', '--hard', base_commit],
                cwd=existing_repo,
                check=True,
                capture_output=True
            )

            # 构建图
            print(f"  Building graph...")
            G = build_graph(str(existing_repo), global_import=True)

            # 保存图索引
            with open(graph_file, 'wb') as f:
                pickle.dump(G, f)

            print(f"  [OK] Saved to: {graph_file}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            continue

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_samples', type=int, default=3)
    args = parser.parse_args()

    build_graphs_for_astropy_samples(args.num_samples)