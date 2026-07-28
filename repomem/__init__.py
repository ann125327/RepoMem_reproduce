"""
RepoMem - Repository Memory System

This package implements the RepoMem episodic and semantic memory system
for storing and retrieving historical commit information and file summaries.

Main components:
- episodic_memory: Commit memory data structures and builder
- semantic_memory: File summary generation and management
- index_commit_memory: BM25 indexing for commit memory
- index_semantic_memory: BM25 indexing for semantic memory
- tools: SearchCommit, ExamineCommit, SearchFile, ExamineFile tools
"""

from .episodic_memory import (
    CommitMemory,
    CommitMemoryBuilder,
    save_memory_to_jsonl,
    load_memory_from_jsonl
)

from .semantic_memory import (
    FileSummary,
    FileActivityAnalyzer,
    FileContentReader,
    SummaryGenerator,
    SemanticMemoryBuilder,
    save_semantic_memory,
    load_semantic_memory
)

from .index_commit_memory import (
    BM25Index,
    CommitMemoryIndexer,
    CommitMemorySearcher,
    build_index_for_instance
)

from .index_semantic_memory import (
    SemanticBM25Index,
    SemanticMemoryIndexer,
    SemanticMemorySearcher,
    build_semantic_index_for_instance
)

from .tools import (
    SearchCommit,
    ExamineCommit,
    SearchFile,
    ExamineFile,
    RepoMemTools,
    SearchResult,
    CommitDetail,
    FileSearchResult
)

__all__ = [
    # Commit Memory
    'CommitMemory',
    'CommitMemoryBuilder',
    'save_memory_to_jsonl',
    'load_memory_from_jsonl',

    # Semantic Memory
    'FileSummary',
    'FileActivityAnalyzer',
    'FileContentReader',
    'SummaryGenerator',
    'SemanticMemoryBuilder',
    'save_semantic_memory',
    'load_semantic_memory',

    # Commit Indexing
    'BM25Index',
    'CommitMemoryIndexer',
    'CommitMemorySearcher',
    'build_index_for_instance',

    # Semantic Indexing
    'SemanticBM25Index',
    'SemanticMemoryIndexer',
    'SemanticMemorySearcher',
    'build_semantic_index_for_instance',

    # Tools
    'SearchCommit',
    'ExamineCommit',
    'SearchFile',
    'ExamineFile',
    'RepoMemTools',
    'SearchResult',
    'CommitDetail',
    'FileSearchResult'
]

__version__ = '1.0.0'