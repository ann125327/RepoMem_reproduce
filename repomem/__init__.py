"""
RepoMem - Repository Memory System

This package implements the RepoMem episodic memory system
for storing and retrieving historical commit information.

Main components:
- episodic_memory: Commit memory data structures and builder
- index_commit_memory: BM25 indexing for commit memory
- tools: SearchCommit and ExamineCommit tools
"""

from .episodic_memory import (
    CommitMemory,
    CommitMemoryBuilder,
    save_memory_to_jsonl,
    load_memory_from_jsonl
)

from .index_commit_memory import (
    BM25Index,
    CommitMemoryIndexer,
    CommitMemorySearcher,
    build_index_for_instance
)

from .tools import (
    SearchCommit,
    ExamineCommit,
    RepoMemTools,
    SearchResult,
    CommitDetail
)

__all__ = [
    # Commit Memory
    'CommitMemory',
    'CommitMemoryBuilder',
    'save_memory_to_jsonl',
    'load_memory_from_jsonl',

    # Indexing
    'BM25Index',
    'CommitMemoryIndexer',
    'CommitMemorySearcher',
    'build_index_for_instance',

    # Tools
    'SearchCommit',
    'ExamineCommit',
    'RepoMemTools',
    'SearchResult',
    'CommitDetail'
]

__version__ = '1.0.0'