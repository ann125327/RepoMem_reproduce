"""
Build episodic memory for SWE-bench instances.

This script builds commit memory and BM25 indexes for SWE-bench instances.
"""

import json
import sys
from pathlib import Path

# Add repomem to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repomem.episodic_memory import CommitMemoryBuilder, save_memory_to_jsonl
from repomem.index_commit_memory import CommitMemoryIndexer


def build_memory_for_instance(instance_data: dict, repo_base: Path, output_base: Path):
    """
    Build commit memory for a single instance.

    Args:
        instance_data: Instance metadata with repo, base_commit, etc.
        repo_base: Base directory containing cloned repositories
        output_base: Base directory for output files
    """
    instance_id = instance_data['instance_id']
    repo_name = instance_data['repo']
    base_commit = instance_data['base_commit']

    print(f"\n{'='*70}")
    print(f"Building memory for {instance_id}")
    print(f"Repository: {repo_name}")
    print(f"Base commit: {base_commit}")
    print(f"{'='*70}\n")

    # Setup paths
    repo_safe_name = repo_name.replace('/', '_')

    # Use the specific playground directory that has the correct repo
    # This should be the one with the base_commit we need
    repo_path = None

    # Try specific known working directory first
    specific_dir = repo_base / '519e12d6-30ab-4101-a4e0-1ccf054802cd' / repo_safe_name
    if specific_dir.exists() and (specific_dir / '.git').exists():
        repo_path = specific_dir
        print(f"Using repository: {repo_path}")
    else:
        # Find any existing repo directory in playground
        for playground_dir in repo_base.iterdir():
            potential_repo = playground_dir / repo_safe_name
            if potential_repo.exists() and (potential_repo / '.git').exists():
                repo_path = potential_repo
                print(f"Using repository: {repo_path}")
                break

    if not repo_path:
        print(f"[ERROR] Repository not found in playground: {repo_name}")
        return

    memory_dir = output_base / 'episodic' / repo_safe_name
    index_dir = output_base / 'indexes' / repo_safe_name / instance_id / 'commit_bm25'

    memory_file = memory_dir / f'{instance_id}.jsonl'

    # Check if already exists
    if memory_file.exists() and index_dir.exists():
        print(f"[OK] Memory and index already exist for {instance_id}")
        return

    # Build commit memory
    try:
        builder = CommitMemoryBuilder(str(repo_path))
        memories = builder.build_memory(base_commit)

        # Save memory
        save_memory_to_jsonl(memories, memory_file)

        # Build and save index
        indexer = CommitMemoryIndexer(memories)
        indexer.build_index()
        indexer.save_index(index_dir)

        print(f"\n[OK] Successfully built memory for {instance_id}")
        print(f"   Memory file: {memory_file}")
        print(f"   Index dir: {index_dir}")
        print(f"   Total commits: {len(memories)}")

    except Exception as e:
        print(f"\n[ERROR] Error building memory for {instance_id}: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to build memory for test instances."""

    # Configuration
    project_root = Path(__file__).parent.parent
    repo_base = project_root / 'LocAgent' / 'playground'
    output_base = project_root / 'memory'

    # Test instances from our evaluation results
    test_instances = [
        {
            'instance_id': 'astropy__astropy-12907',
            'repo': 'astropy/astropy',
            'base_commit': 'd16bfe05a744909de4b27f5875fe0d4ed41ce607',
            'problem_statement': 'Modeling separability_matrix issue'
        }
    ]

    print("=" * 70)
    print("Building Episodic Memory for SWE-bench Instances")
    print("=" * 70)

    for instance_data in test_instances:
        build_memory_for_instance(instance_data, repo_base, output_base)

    print("\n" + "=" * 70)
    print("Memory building complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()