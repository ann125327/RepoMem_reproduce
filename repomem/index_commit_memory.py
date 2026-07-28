"""
RepoMem Commit Memory Indexer

This module builds BM25 indexes for commit memory to enable
efficient retrieval based on:
- Commit messages
- Changed files
- Diff summaries
"""

import json
import pickle
import math
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .episodic_memory import CommitMemory, load_memory_from_jsonl


@dataclass
class BM25Index:
    """BM25 index for commit memory."""
    # Inverted index: term -> [(doc_id, term_freq), ...]
    inverted_index: Dict[str, List[Tuple[int, int]]]

    # Document lengths for normalization
    doc_lengths: List[int]

    # Average document length
    avg_doc_length: float

    # Total number of documents
    num_docs: int

    # ID mapping: doc_id -> commit sha
    id_to_sha: Dict[int, str]

    # SHA mapping: commit sha -> doc_id
    sha_to_id: Dict[str, int]

    # Document store: doc_id -> commit memory dict
    doc_store: Dict[int, Dict[str, Any]]

    # Field weights for multi-field search
    field_weights: Dict[str, float]


class CommitMemoryIndexer:
    """Build BM25 index for commit memory."""

    # BM25 parameters
    K1 = 1.5  # Term frequency saturation parameter
    B = 0.75  # Length normalization parameter

    # Field weights for multi-field search
    FIELD_WEIGHTS = {
        'message': 1.0,
        'changed_files': 0.8,
        'diff_summary': 0.6
    }

    def __init__(self, memories: List[CommitMemory]):
        """
        Initialize indexer.

        Args:
            memories: List of commit memories to index
        """
        self.memories = memories
        self.index = None

    def build_index(self) -> BM25Index:
        """
        Build BM25 index from commit memories.

        Returns:
            BM25Index object
        """
        print(f"Building BM25 index for {len(self.memories)} commits...")

        # Initialize data structures
        inverted_index = {}
        doc_lengths = []
        id_to_sha = {}
        sha_to_id = {}
        doc_store = {}

        # Process each commit
        for doc_id, memory in enumerate(self.memories):
            # Create mappings
            id_to_sha[doc_id] = memory.sha
            sha_to_id[memory.sha] = doc_id
            doc_store[doc_id] = memory.to_dict()

            # Combine tokens from all fields with weights
            all_tokens = []

            # Message tokens
            all_tokens.extend(memory.message_tokens)

            # Changed files tokens (path components)
            for file_path in memory.changed_files:
                # Split path into components
                path_tokens = re.findall(r'[a-zA-Z0-9_]+', file_path)
                all_tokens.extend(path_tokens)

            # Diff summary tokens
            all_tokens.extend(memory.diff_tokens)

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
        self.index = BM25Index(
            inverted_index=inverted_index,
            doc_lengths=doc_lengths,
            avg_doc_length=avg_doc_length,
            num_docs=len(self.memories),
            id_to_sha=id_to_sha,
            sha_to_id=sha_to_id,
            doc_store=doc_store,
            field_weights=self.FIELD_WEIGHTS
        )

        print(f"Index built: {self.index.num_docs} docs, {len(inverted_index)} unique terms")
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
        index_file = output_dir / 'commit_index.pkl'
        with open(index_file, 'wb') as f:
            pickle.dump(self.index, f)

        # Save metadata
        metadata = {
            'num_docs': self.index.num_docs,
            'num_terms': len(self.index.inverted_index),
            'avg_doc_length': self.index.avg_doc_length,
            'field_weights': self.index.field_weights
        }
        metadata_file = output_dir / 'index_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"Index saved to {output_dir}")


class CommitMemorySearcher:
    """Search commit memory using BM25 index."""

    # BM25 parameters (same as indexer)
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

    def _load_index(self) -> BM25Index:
        """Load index from disk."""
        index_file = self.index_dir / 'commit_index.pkl'

        if not index_file.exists():
            raise FileNotFoundError(f"Index not found: {index_file}")

        with open(index_file, 'rb') as f:
            index = pickle.load(f)

        print(f"Loaded index: {index.num_docs} commits, {len(index.inverted_index)} terms")
        return index

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for commits matching the query.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of search results with sha, message, score, changed_files, timestamp
        """
        # Tokenize query
        query_tokens = self._tokenize_query(query)

        if not query_tokens:
            return []

        # Calculate BM25 scores for each document
        scores = self._calculate_bm25_scores(query_tokens)

        # Sort by score and get top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Build result list
        results = []
        for doc_id, score in ranked:
            doc = self.index.doc_store[doc_id]
            results.append({
                'sha': doc['sha'],
                'message': doc['message'],
                'score': float(score),
                'changed_files': doc['changed_files'],
                'timestamp': doc['timestamp'],
                'linked_issue_id': doc.get('linked_issue_id')
            })

        return results

    def multi_field_search(
        self,
        query_list: List[str],
        top_k: int = 10,
        field_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Multi-field search with weighted scoring.

        Args:
            query_list: List of queries for different fields
            top_k: Number of top results
            field_weights: Weights for each field (uses default if None)

        Returns:
            List of search results
        """
        # Use provided weights or defaults
        weights = field_weights or self.index.field_weights

        # Aggregate scores from all queries
        all_scores = Counter()

        for query in query_list:
            results = self.search(query, top_k=top_k * 2)  # Get more results for merging
            for result in results:
                sha = result['sha']
                all_scores[sha] += result['score']

        # Get top commits by aggregated score
        top_shas = [sha for sha, _ in all_scores.most_common(top_k)]

        # Build final results
        results = []
        for sha in top_shas:
            doc_id = self.index.sha_to_id.get(sha)
            if doc_id is not None:
                doc = self.index.doc_store[doc_id]
                results.append({
                    'sha': doc['sha'],
                    'message': doc['message'],
                    'score': float(all_scores[sha]),
                    'changed_files': doc['changed_files'],
                    'timestamp': doc['timestamp'],
                    'linked_issue_id': doc.get('linked_issue_id')
                })

        return results

    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize search query."""
        query = query.lower()
        tokens = re.findall(r'\b\w+\b', query)
        return [t for t in tokens if len(t) > 2]

    def _calculate_bm25_scores(self, query_tokens: List[str]) -> Dict[int, float]:
        """
        Calculate BM25 scores for all documents.

        Args:
            query_tokens: List of query terms

        Returns:
            Dictionary mapping doc_id to BM25 score
        """
        scores = {}

        for term in query_tokens:
            if term not in self.index.inverted_index:
                continue

            # Get postings list
            postings = self.index.inverted_index[term]

            # Calculate IDF
            doc_freq = len(postings)
            idf = math.log(
                (self.index.num_docs - doc_freq + 0.5) /
                (doc_freq + 0.5) + 1
            )

            # Accumulate scores for each document
            for doc_id, term_freq in postings:
                # BM25 term score
                doc_length = self.index.doc_lengths[doc_id]
                length_norm = 1 - self.B + self.B * (doc_length / self.index.avg_doc_length)

                term_score = idf * (term_freq * (self.K1 + 1)) / (term_freq + self.K1 * length_norm)

                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += term_score

        return scores


def build_index_for_instance(
    instance_id: str,
    repo_name: str,
    repo_path: Path,
    base_commit: str,
    output_base: Path
):
    """
    Build commit memory and index for a single SWE-bench instance.

    Args:
        instance_id: SWE-bench instance ID
        repo_name: Repository name (e.g., "astropy/astropy")
        repo_path: Path to the repository
        base_commit: Base commit SHA
        output_base: Base output directory
    """
    from .episodic_memory import CommitMemoryBuilder, save_memory_to_jsonl

    # Output paths
    memory_dir = output_base / 'episodic' / repo_name.replace('/', '_')
    index_dir = output_base / 'indexes' / repo_name.replace('/', '_') / instance_id / 'commit_bm25'

    memory_file = memory_dir / f'{instance_id}.jsonl'

    # Check if already exists
    if memory_file.exists() and index_dir.exists():
        print(f"Memory and index already exist for {instance_id}")
        return

    # Build commit memory
    print(f"\n{'='*60}")
    print(f"Building memory for {instance_id}")
    print(f"Repo: {repo_name}")
    print(f"Base commit: {base_commit}")
    print(f"{'='*60}\n")

    builder = CommitMemoryBuilder(str(repo_path))
    memories = builder.build_memory(base_commit)

    # Save memory
    save_memory_to_jsonl(memories, memory_file)

    # Build and save index
    indexer = CommitMemoryIndexer(memories)
    indexer.build_index()
    indexer.save_index(index_dir)

    print(f"\n✅ Completed for {instance_id}")
    print(f"   Memory: {memory_file}")
    print(f"   Index: {index_dir}\n")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python index_commit_memory.py <memory_file.jsonl> <output_dir>")
        sys.exit(1)

    memory_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    # Load memories
    memories = load_memory_from_jsonl(memory_file)

    # Build index
    indexer = CommitMemoryIndexer(memories)
    indexer.build_index()
    indexer.save_index(output_dir)

    print(f"\nIndex saved to {output_dir}")