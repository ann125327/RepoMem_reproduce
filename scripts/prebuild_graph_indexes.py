#!/usr/bin/env python3
"""
预生成 SWE-bench_Verified 样本的图索引
在有稳定网络的环境下运行，避免评估时依赖网络
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datasets import load_dataset
from tqdm import tqdm

# 添加 LocAgent 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'LocAgent'))

# 应用本地数据补丁（避免从 HuggingFace 下载）
import scripts.local_dataset_patch  # noqa: F401

from util.benchmark.git_repo_manager import setup_github_repo
from dependency_graph.build_graph import build_graph

def prebuild_graph_indexes(
    dataset_name: str = "princeton-nlp/SWE-bench_Verified",
    split: str = "test",
    graph_index_dir: str = None,
    eval_n_limit: int = None,
    force_rebuild: bool = False
):
    """
    预生成图索引文件

    Args:
        dataset_name: 数据集名称
        split: 数据集分割
        graph_index_dir: 图索引目录
        eval_n_limit: 限制样本数量（用于测试）
        force_rebuild: 强制重建已有的索引
    """
    # 设置图索引目录
    if not graph_index_dir:
        graph_index_dir = os.path.join(
            "index_data", dataset_name.split("/")[-1], "graph_index_v2.3"
        )

    os.makedirs(graph_index_dir, exist_ok=True)

    # 加载数据集
    print(f"Loading dataset: {dataset_name}/{split}")
    dataset = load_dataset(dataset_name, split=split, trust_remote_code=True)

    if eval_n_limit:
        dataset = dataset.select(range(eval_n_limit))
        print(f"Limited to first {eval_n_limit} samples")

    print(f"Total samples to process: {len(dataset)}")

    # 统计
    success_count = 0
    skip_count = 0
    error_count = 0
    errors = []

    # 处理每个样本
    for idx, instance in enumerate(tqdm(dataset, desc="Building graph indexes")):
        instance_id = instance['instance_id']
        graph_file = os.path.join(graph_index_dir, f"{instance_id}.pkl")

        # 检查是否已存在
        if os.path.exists(graph_file) and not force_rebuild:
            print(f"\n[{idx+1}/{len(dataset)}] Skipping {instance_id} (already exists)")
            skip_count += 1
            continue

        print(f"\n[{idx+1}/{len(dataset)}] Processing {instance_id}")

        # 创建临时目录
        import uuid
        temp_dir = os.path.join("playground", f"prebuild_{uuid.uuid4()}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # 克隆仓库
            print(f"  Cloning {instance['repo']}...")
            repo_dir = setup_github_repo(
                repo=instance['repo'],
                base_commit=instance['base_commit'],
                base_dir=temp_dir
            )
            print(f"  Repo cloned to: {repo_dir}")

            # 构建图
            print(f"  Building graph...")
            G = build_graph(repo_dir, global_import=True)

            # 保存图索引
            import pickle
            with open(graph_file, 'wb') as f:
                pickle.dump(G, f)

            print(f"  ✓ Saved to: {graph_file}")
            success_count += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            error_count += 1
            errors.append({
                'instance_id': instance_id,
                'error': str(e)
            })

        finally:
            # 清理临时目录
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # 打印统计
    print("\n" + "="*60)
    print("Graph Index Prebuild Summary")
    print("="*60)
    print(f"Total samples: {len(dataset)}")
    print(f"Success: {success_count}")
    print(f"Skipped (already exists): {skip_count}")
    print(f"Errors: {error_count}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err['instance_id']}: {err['error']}")

    # 保存错误报告
    if errors:
        error_file = os.path.join(graph_index_dir, "prebuild_errors.json")
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\nError report saved to: {error_file}")

    return success_count, skip_count, error_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prebuild graph indexes for SWE-bench")
    parser.add_argument("--dataset", default="princeton-nlp/SWE-bench_Verified")
    parser.add_argument("--split", default="test")
    parser.add_argument("--graph_index_dir", default=None)
    parser.add_argument("--eval_n_limit", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--force", action="store_true", help="Force rebuild existing indexes")

    args = parser.parse_args()

    prebuild_graph_indexes(
        dataset_name=args.dataset,
        split=args.split,
        graph_index_dir=args.graph_index_dir,
        eval_n_limit=args.eval_n_limit,
        force_rebuild=args.force
    )