"""
Build semantic memory for SWE-bench instances.

This script builds semantic file summaries and BM25 indexes.
"""

import sys
from pathlib import Path

# Add repomem to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repomem.episodic_memory import load_memory_from_jsonl
from repomem.semantic_memory import SemanticMemoryBuilder, save_semantic_memory
from repomem.index_semantic_memory import SemanticMemoryIndexer


def build_semantic_for_instance(
    instance_id: str,
    repo_name: str,
    repo_path: Path,
    base_commit: str,
    output_base: Path,
    top_k: int = 200,
    api_client=None
):
    """
    Build semantic memory for a single instance.

    Args:
        instance_id: SWE-bench instance ID
        repo_name: Repository name
        repo_path: Path to repository
        base_commit: Base commit SHA
        output_base: Base output directory
        top_k: Number of top active files to process
        api_client: LLM API client (optional)
    """
    # Setup paths
    repo_safe_name = repo_name.replace('/', '_')
    episodic_memory_file = output_base / 'episodic' / repo_safe_name / f'{instance_id}.jsonl'
    semantic_memory_file = output_base / 'semantic' / repo_safe_name / f'{instance_id}_semantic.jsonl'
    semantic_index_dir = output_base / 'indexes' / repo_safe_name / instance_id / 'semantic_bm25'

    # Check if already exists
    if semantic_memory_file.exists() and semantic_index_dir.exists():
        print(f"[OK] Semantic memory already exists for {instance_id}")
        return

    # Load episodic memory
    if not episodic_memory_file.exists():
        print(f"[ERROR] Episodic memory not found: {episodic_memory_file}")
        return

    print(f"\n{'='*70}")
    print(f"Building semantic memory for {instance_id}")
    print(f"Repository: {repo_name}")
    print(f"Base commit: {base_commit}")
    print(f"Top files: {top_k}")
    print(f"{'='*70}\n")

    # Load memories
    memories = load_memory_from_jsonl(episodic_memory_file)
    print(f"Loaded {len(memories)} commits")

    # Build semantic memory
    print(f"\nBuilding semantic summaries...")
    builder = SemanticMemoryBuilder(
        str(repo_path),
        memories,
        api_client=api_client,
        top_k=top_k
    )
    summaries = builder.build(base_commit)

    # Save
    save_semantic_memory(summaries, semantic_memory_file)

    # Build and save index
    print(f"\nBuilding BM25 index...")
    indexer = SemanticMemoryIndexer(summaries)
    indexer.build_index()
    indexer.save_index(semantic_index_dir)

    print(f"\n[SUCCESS] Semantic memory built for {instance_id}")
    print(f"  Summaries: {semantic_memory_file}")
    print(f"  Index: {semantic_index_dir}")
    print(f"  Files processed: {len(summaries)}")


def main():
    """Main function to build semantic memory."""
    project_root = Path(__file__).parent.parent
    repo_base = project_root / 'LocAgent' / 'playground'
    output_base = project_root / 'memory'

    # Test instances
    test_instances = [
        {
            'instance_id': 'test_quick',  # Use existing test file
            'repo': 'astropy/astropy',
            'base_commit': 'd16bfe05a744909de4b27f5875fe0d4ed41ce607',
        }
    ]

    print("=" * 70)
    print("Building Semantic Memory for SWE-bench Instances")
    print("=" * 70)

    for instance_data in test_instances:
        instance_id = instance_data['instance_id']
        repo_name = instance_data['repo']
        base_commit = instance_data['base_commit']

        # Find repo path
        repo_safe_name = repo_name.replace('/', '_')
        repo_path = None

        # Try specific known working directory first
        specific_dir = repo_base / '519e12d6-30ab-4101-a4e0-1ccf054802cd' / repo_safe_name
        if specific_dir.exists() and (specific_dir / '.git').exists():
            repo_path = specific_dir
        else:
            # Find any existing repo directory in playground
            for playground_dir in repo_base.iterdir():
                potential_repo = playground_dir / repo_safe_name
                if potential_repo.exists() and (potential_repo / '.git').exists():
                    repo_path = potential_repo
                    break

        if not repo_path:
            print(f"[ERROR] Repository not found: {repo_name}")
            continue

        build_semantic_for_instance(
            instance_id,
            repo_name,
            repo_path,
            base_commit,
            output_base,
            top_k=200,
            api_client=None  # Use basic summaries
        )

    print("\n" + "=" * 70)
    print("Semantic memory building complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()