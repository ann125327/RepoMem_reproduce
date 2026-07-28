"""
Quick test for episodic memory with limited commits.
"""

import sys
from pathlib import Path

# Add repomem to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repomem.episodic_memory import CommitMemoryBuilder, save_memory_to_jsonl
from repomem.index_commit_memory import CommitMemoryIndexer

# Test configuration
repo_path = Path('LocAgent/playground/519e12d6-30ab-4101-a4e0-1ccf054802cd/astropy_astropy')
base_commit = 'd16bfe05a744909de4b27f5875fe0d4ed41ce607'
output_base = Path('memory')

print("=" * 70)
print("Quick Test: Building Episodic Memory (100 commits)")
print("=" * 70)

# Build with limited commits
print(f"\nBuilding memory for {repo_path}")
print(f"Base commit: {base_commit}")
print(f"Limit: 100 commits\n")

builder = CommitMemoryBuilder(str(repo_path), max_commits=100)
memories = builder.build_memory(base_commit)

print(f"\nBuilt {len(memories)} commit memories")

if len(memories) > 0:
    # Save memory
    memory_file = output_base / 'episodic' / 'astropy_astropy' / 'test_quick.jsonl'
    save_memory_to_jsonl(memories, memory_file)

    # Build index
    indexer = CommitMemoryIndexer(memories)
    index = indexer.build_index()

    index_dir = output_base / 'indexes' / 'astropy_astropy' / 'test_quick' / 'commit_bm25'
    indexer.save_index(index_dir)

    # Test search
    print("\n" + "=" * 70)
    print("Testing Search")
    print("=" * 70)

    from repomem.tools import SearchCommit

    search_tool = SearchCommit(index_dir)
    results = search_tool.search(['separability', 'model'], top_k=5)

    print(f"\nSearch for 'separability model' returned {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. [{result.sha[:8]}] Score: {result.score:.2f}")
        print(f"   Message: {result.message[:80]}...")
        print(f"   Files: {', '.join(result.changed_files[:3])}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Quick test completed!")
    print("=" * 70)

else:
    print("\n[ERROR] No commits were processed")