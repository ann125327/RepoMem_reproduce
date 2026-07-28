"""
Test semantic memory functionality.

This script tests the semantic memory module without requiring
LLM API calls (uses fallback basic summaries).
"""

import sys
from pathlib import Path

# Add repomem to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repomem.episodic_memory import load_memory_from_jsonl
from repomem.semantic_memory import (
    SemanticMemoryBuilder,
    save_semantic_memory
)
from repomem.index_semantic_memory import (
    SemanticMemoryIndexer,
    SemanticMemorySearcher
)

# Configuration
repo_path = Path('LocAgent/playground/519e12d6-30ab-4101-a4e0-1ccf054802cd/astropy_astropy')
base_commit = 'd16bfe05a744909de4b27f5875fe0d4ed41ce607'
episodic_memory_file = Path('memory/episodic/astropy_astropy/test_quick.jsonl')
output_base = Path('memory')

print("=" * 70)
print("Testing Semantic Memory Module")
print("=" * 70)

# Step 1: Load existing episodic memory
print("\n[1] Loading episodic memory...")
if not episodic_memory_file.exists():
    print(f"ERROR: Episodic memory file not found: {episodic_memory_file}")
    print("Please run quick_test_episodic.py first")
    sys.exit(1)

memories = load_memory_from_jsonl(episodic_memory_file)
print(f"Loaded {len(memories)} commit memories")

# Step 2: Build semantic memory (top 20 files for quick test)
print("\n[2] Building semantic memory (top 20 active files)...")
builder = SemanticMemoryBuilder(
    str(repo_path),
    memories,
    api_client=None,  # No LLM, use fallback
    top_k=20
)
summaries = builder.build(base_commit)

print(f"\nGenerated {len(summaries)} file summaries")

# Step 3: Display top files
if summaries:
    print("\n" + "=" * 70)
    print("Top Active Files")
    print("=" * 70)

    for i, summary in enumerate(summaries[:10], 1):
        print(f"\n{i}. {summary.file_path}")
        print(f"   Changes: {summary.change_frequency} | Type: {summary.file_type} | Lines: {summary.line_count}")
        print(f"   Summary: {summary.summary[:100]}...")
        if summary.key_entities:
            print(f"   Entities: {', '.join(summary.key_entities[:5])}")

# Step 4: Save semantic memory
print("\n" + "=" * 70)
print("[3] Saving semantic memory...")

semantic_dir = output_base / 'semantic' / 'astropy_astropy'
semantic_file = semantic_dir / 'test_quick_semantic.jsonl'

save_semantic_memory(summaries, semantic_file)

# Step 5: Build index
print("\n[4] Building BM25 index...")
indexer = SemanticMemoryIndexer(summaries)
index = indexer.build_index()

index_dir = output_base / 'indexes' / 'astropy_astropy' / 'test_quick' / 'semantic_bm25'
indexer.save_index(index_dir)

# Step 6: Test search
print("\n" + "=" * 70)
print("[5] Testing search functionality...")

searcher = SemanticMemorySearcher(index_dir)

test_queries = [
    'model',
    'test',
    'coordinate'
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    results = searcher.search(query, top_k=3)

    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['file_path']}")
        print(f"     Score: {result['score']:.2f} | Changes: {result['change_frequency']}")
        print(f"     Summary: {result['summary'][:80]}...")

print("\n" + "=" * 70)
print("[SUCCESS] Semantic memory test completed!")
print("=" * 70)
print(f"\nCreated files:")
print(f"  - Summaries: {semantic_file}")
print(f"  - Index: {index_dir}")