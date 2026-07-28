"""
RepoMem Semantic Memory Indexer

This module builds BM25 indexes for semantic file summaries.
"""

import json
import pickle
import math
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .semantic_memory import FileSummary, load_semantic_memory


@dataclass
class SemanticBM25Index:
    """BM25 index for semantic file summaries."""
    inverted_index: Dict[str, List[Tuple[int, int]]]
    doc_lengths: List[int]
    avg_doc_length: float
    num_docs: int
    file_path_to_id: Dict[str, int]
    id_to_file_path: Dict[int, str]
    doc_store: Dict[int, Dict[str, Any]]


class SemanticMemoryIndexer:
    """Build BM25 index for semantic file summaries."""

    K1 = 1.5
    B = 0.75

    def __init__(self, summaries: List[FileSummary]):
        """
        Initialize indexer.

        Args:
            summaries: List of file summaries to index
        """
        self.summaries = summaries
        self.index = None

    def build_index(self) -> SemanticBM25Index:
        """
        Build BM25 index from file summaries.

        Returns:
            SemanticBM25Index object
        """
        print(f"Building semantic BM25 index for {len(self.summaries)} files...")

        inverted_index = {}
        doc_lengths = []
        file_path_to_id = {}
        id_to_file_path = {}
        doc_store = {}

        for doc_id, summary in enumerate(self.summaries):
            # Create mappings
            file_path_to_id[summary.file_path] = doc_id
            id_to_file_path[doc_id] = summary.file_path
            doc_store[doc_id] = summary.to_dict()

            # Tokenize summary and entities
            all_tokens = []

            # Summary tokens
            summary_tokens = self._tokenize(summary.summary)
            all_tokens.extend(summary_tokens)
            summary.summary_tokens = summary_tokens

            # File path tokens (for path-based search)
            path_tokens = re.findall(r'[a-zA-Z0-9_]+', summary.file_path)
            all_tokens.extend(path_tokens)

            # Key entities tokens
            for entity in summary.key_entities:
                entity_tokens = self._tokenize(entity)
                all_tokens.extend(entity_tokens)

            # Count term frequencies
            term_freq = Counter(all_tokens)
            doc_lengths.append(len(all_tokens))

            # Update inverted index
            for term, freq in term_freq.items():
                if term not in inverted_index:
                    inverted_index[term] = []
                inverted_index[term].append((doc_id, freq))

        # Calculate average document length
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0

        # Create index object
        self.index = SemanticBM25Index(
            inverted_index=inverted_index,
            doc_lengths=doc_lengths,
            avg_doc_length=avg_doc_length,
            num_docs=len(self.summaries),
            file_path_to_id=file_path_to_id,
            id_to_file_path=id_to_file_path,
            doc_store=doc_store
        )

        print(f"Index built: {self.index.num_docs} files, {len(inverted_index)} unique terms")
        return self.index

    def save_index(self, output_dir: Path):
        """
        Save index to disk.

        Args:
            output_dir: Output directory
        """
        if not self.index:
            raise ValueError("No index to save. Call build_index() first.")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save index data
        index_file = output_dir / 'semantic_index.pkl'
        with open(index_file, 'wb') as f:
            pickle.dump(self.index, f)

        # Save metadata
        metadata = {
            'num_docs': self.index.num_docs,
            'num_terms': len(self.index.inverted_index),
            'avg_doc_length': self.index.avg_doc_length
        }
        metadata_file = output_dir / 'semantic_index_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"Semantic index saved to {output_dir}")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for indexing."""
        if not text:
            return []

        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) > 2]


class SemanticMemorySearcher:
    """Search semantic file summaries using BM25 index."""

    K1 = 1.5
    B = 0.75

    def __init__(self, index_dir: Path):
        """
        Initialize searcher.

        Args:
            index_dir: Directory containing the index files
        """
        self.index_dir = index_dir
        self.index = self._load_index()

    def _load_index(self) -> SemanticBM25Index:
        """Load index from disk."""
        index_file = self.index_dir / 'semantic_index.pkl'

        if not index_file.exists():
            raise FileNotFoundError(f"Index not found: {index_file}")

        with open(index_file, 'rb') as f:
            index = pickle.load(f)

        print(f"Loaded semantic index: {index.num_docs} files, {len(index.inverted_index)} terms")
        return index

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for files matching the query.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of search results with file_path, summary, score, etc.
        """
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # Calculate BM25 scores
        scores = self._calculate_bm25_scores(query_tokens)

        # Sort and get top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Build results
        results = []
        for doc_id, score in ranked:
            doc = self.index.doc_store[doc_id]
            results.append({
                'file_path': doc['file_path'],
                'summary': doc['summary'],
                'score': float(score),
                'change_frequency': doc['change_frequency'],
                'file_type': doc['file_type'],
                'line_count': doc['line_count'],
                'key_entities': doc.get('key_entities', [])
            })

        return results

    def _tokenize(self, query: str) -> List[str]:
        """Tokenize search query."""
        query = query.lower()
        tokens = re.findall(r'\b\w+\b', query)
        return [t for t in tokens if len(t) > 2]

    def _calculate_bm25_scores(self, query_tokens: List[str]) -> Dict[int, float]:
        """Calculate BM25 scores for all documents."""
        scores = {}

        for term in query_tokens:
            if term not in self.index.inverted_index:
                continue

            postings = self.index.inverted_index[term]
            doc_freq = len(postings)

            idf = math.log(
                (self.index.num_docs - doc_freq + 0.5) /
                (doc_freq + 0.5) + 1
            )

            for doc_id, term_freq in postings:
                doc_length = self.index.doc_lengths[doc_id]
                length_norm = 1 - self.B + self.B * (doc_length / self.index.avg_doc_length)

                term_score = idf * (term_freq * (self.K1 + 1)) / (term_freq + self.K1 * length_norm)

                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += term_score

        return scores


def build_semantic_index_for_instance(
    instance_id: str,
    repo_name: str,
    repo_path: Path,
    base_commit: str,
    output_base: Path,
    api_client=None
):
    """
    Build semantic memory and index for a single SWE-bench instance.

    Args:
        instance_id: SWE-bench instance ID
        repo_name: Repository name
        repo_path: Path to the repository
        base_commit: Base commit SHA
        output_base: Base output directory
        api_client: LLM API client (optional)
    """
    from .episodic_memory import load_memory_from_jsonl
    from .semantic_memory import SemanticMemoryBuilder, save_semantic_memory

    # Setup paths
    repo_safe_name = repo_name.replace('/', '_')
    episodic_memory_file = output_base / 'episodic' / repo_safe_name / f'{instance_id}.jsonl'
    semantic_memory_file = output_base / 'semantic' / repo_safe_name / f'{instance_id}_semantic.jsonl'
    semantic_index_dir = output_base / 'indexes' / repo_safe_name / instance_id / 'semantic_bm25'

    # Check if already exists
    if semantic_memory_file.exists() and semantic_index_dir.exists():
        print(f"Semantic memory and index already exist for {instance_id}")
        return

    # Load episodic memory
    if not episodic_memory_file.exists():
        print(f"Episodic memory not found: {episodic_memory_file}")
        return

    print(f"\n{'='*60}")
    print(f"Building semantic memory for {instance_id}")
    print(f"{'='*60}\n")

    memories = load_memory_from_jsonl(episodic_memory_file)

    # Build semantic memory
    builder = SemanticMemoryBuilder(
        str(repo_path),
        memories,
        api_client=api_client,
        top_k=200
    )
    summaries = builder.build(base_commit)

    # Save semantic memory
    save_semantic_memory(summaries, semantic_memory_file)

    # Build and save index
    indexer = SemanticMemoryIndexer(summaries)
    indexer.build_index()
    indexer.save_index(semantic_index_dir)

    print(f"\n✓ Completed semantic memory for {instance_id}")
    print(f"  Summaries: {semantic_memory_file}")
    print(f"  Index: {semantic_index_dir}\n")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python index_semantic_memory.py <summary_file.jsonl> <output_dir>")
        sys.exit(1)

    summary_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    # Load summaries
    summaries = load_semantic_memory(summary_file)

    # Build index
    indexer = SemanticMemoryIndexer(summaries)
    indexer.build_index()
    indexer.save_index(output_dir)

    print(f"\nSemantic index saved to {output_dir}")