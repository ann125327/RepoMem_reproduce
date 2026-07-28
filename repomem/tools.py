"""
RepoMem Episodic Memory Tools

This module provides tools for agents to interact with
the episodic memory (commit history):

- SearchCommit: Search for relevant commits
- ExamineCommit: Get detailed information about specific commits
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .index_commit_memory import CommitMemorySearcher


@dataclass
class SearchResult:
    """Result from SearchCommit tool."""
    sha: str
    message: str
    score: float
    changed_files: List[str]
    timestamp: str
    linked_issue_id: Optional[str] = None


@dataclass
class CommitDetail:
    """Detailed commit information from ExamineCommit tool."""
    sha: str
    message: str
    changed_files: List[str]
    diff_summary: str
    timestamp: str
    linked_issue_id: Optional[str] = None
    linked_issue_text: Optional[str] = None
    full_diff: Optional[str] = None


class SearchCommit:
    """
    Tool to search for relevant commits in episodic memory.

    This tool searches commit messages, changed files, and diff summaries
    using BM25 ranking to find the most relevant historical commits.
    """

    def __init__(self, index_dir: Path):
        """
        Initialize SearchCommit tool.

        Args:
            index_dir: Directory containing the BM25 index
        """
        self.index_dir = index_dir
        self.searcher = None

    def _ensure_searcher(self):
        """Lazy load the searcher."""
        if not self.searcher:
            self.searcher = CommitMemorySearcher(self.index_dir)

    def search(
        self,
        query_list: List[str],
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Search for commits matching the queries.

        Args:
            query_list: List of search queries (will be combined)
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects
        """
        self._ensure_searcher()

        # Perform multi-field search
        raw_results = self.searcher.multi_field_search(query_list, top_k=top_k)

        # Convert to SearchResult objects
        results = []
        for r in raw_results:
            results.append(SearchResult(
                sha=r['sha'],
                message=r['message'],
                score=r['score'],
                changed_files=r['changed_files'],
                timestamp=r['timestamp'],
                linked_issue_id=r.get('linked_issue_id')
            ))

        return results

    def search_by_message(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search commits by message content.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of SearchResult objects
        """
        return self.search([query], top_k=top_k)

    def search_by_file(self, file_pattern: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search commits that changed specific files.

        Args:
            file_pattern: File path pattern to search
            top_k: Number of results

        Returns:
            List of SearchResult objects
        """
        return self.search([file_pattern], top_k=top_k)

    def format_results(self, results: List[SearchResult]) -> str:
        """
        Format search results for display.

        Args:
            results: List of search results

        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"Found {len(results)} relevant commits:\n")

        for i, result in enumerate(results, 1):
            lines.append(f"{i}. [{result.sha[:8]}] (score: {result.score:.2f})")
            lines.append(f"   Message: {result.message[:100]}...")

            if result.changed_files:
                files_str = ', '.join(result.changed_files[:3])
                if len(result.changed_files) > 3:
                    files_str += f" ... ({len(result.changed_files)} files)"
                lines.append(f"   Files: {files_str}")

            if result.linked_issue_id:
                lines.append(f"   Issue: #{result.linked_issue_id}")

            lines.append(f"   Time: {result.timestamp}")
            lines.append("")

        return '\n'.join(lines)


class ExamineCommit:
    """
    Tool to examine specific commits in detail.

    This tool retrieves full commit information including:
    - Commit message
    - Changed files
    - Diff summary
    - Linked issue (if available)
    """

    def __init__(self, memory_file: Path, index_dir: Path):
        """
        Initialize ExamineCommit tool.

        Args:
            memory_file: JSONL file containing commit memories
            index_dir: Directory containing the BM25 index
        """
        self.memory_file = memory_file
        self.index_dir = index_dir
        self._memory_cache = None

    def _load_memory(self) -> Dict[str, Any]:
        """Load commit memory into cache."""
        if not self._memory_cache:
            self._memory_cache = {}
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    commit = json.loads(line.strip())
                    self._memory_cache[commit['sha']] = commit
        return self._memory_cache

    def examine(
        self,
        sha_list: List[str],
        display_issue: bool = True,
        include_diff: bool = False
    ) -> List[CommitDetail]:
        """
        Examine specific commits in detail.

        Args:
            sha_list: List of commit SHAs to examine
            display_issue: Whether to fetch linked issue content
            include_diff: Whether to include full diff

        Returns:
            List of CommitDetail objects
        """
        memory = self._load_memory()
        details = []

        for sha in sha_list:
            # Normalize SHA to full length
            full_sha = self._find_full_sha(sha, memory)

            if not full_sha:
                print(f"Warning: Commit not found: {sha}")
                continue

            commit_data = memory[full_sha]

            # Build detail object
            detail = CommitDetail(
                sha=full_sha,
                message=commit_data['message'],
                changed_files=commit_data['changed_files'],
                diff_summary=commit_data['diff_summary'],
                timestamp=commit_data['timestamp'],
                linked_issue_id=commit_data.get('linked_issue_id'),
                linked_issue_text=None,
                full_diff=commit_data.get('full_diff') if include_diff else None
            )

            # Fetch issue content if requested
            if display_issue and commit_data.get('linked_issue_id'):
                detail.linked_issue_text = self._fetch_issue_content(
                    commit_data['linked_issue_id']
                )

            details.append(detail)

        return details

    def _find_full_sha(self, short_sha: str, memory: Dict[str, Any]) -> Optional[str]:
        """Find full SHA from short version."""
        # If already full SHA
        if short_sha in memory:
            return short_sha

        # Search for matching short SHA
        for full_sha in memory.keys():
            if full_sha.startswith(short_sha):
                return full_sha

        return None

    def _fetch_issue_content(self, issue_id: str) -> Optional[str]:
        """
        Fetch linked issue content from GitHub.

        Note: This is a placeholder. In production, this would use
        GitHub API to fetch the actual issue content.

        Args:
            issue_id: Issue ID (number or full reference)

        Returns:
            Issue text or None if not available
        """
        # Placeholder implementation
        # In production, this would:
        # 1. Parse repository from context
        # 2. Call GitHub API: GET /repos/{owner}/{repo}/issues/{issue_number}
        # 3. Return issue title and body

        return f"[Issue #{issue_id} - content would be fetched from GitHub API]"

    def format_details(self, details: List[CommitDetail]) -> str:
        """
        Format commit details for display.

        Args:
            details: List of commit details

        Returns:
            Formatted string
        """
        lines = []

        for i, detail in enumerate(details, 1):
            lines.append(f"{'='*70}")
            lines.append(f"Commit {i}: {detail.sha}")
            lines.append(f"{'='*70}")
            lines.append(f"\nTimestamp: {detail.timestamp}\n")
            lines.append("Message:")
            lines.append("-" * 70)
            lines.append(detail.message)
            lines.append("")

            lines.append("Changed Files:")
            lines.append("-" * 70)
            for file in detail.changed_files:
                lines.append(f"  - {file}")
            lines.append("")

            lines.append("Diff Summary:")
            lines.append("-" * 70)
            lines.append(detail.diff_summary)
            lines.append("")

            if detail.linked_issue_id:
                lines.append(f"Linked Issue: #{detail.linked_issue_id}")
                if detail.linked_issue_text:
                    lines.append("-" * 70)
                    lines.append(detail.linked_issue_text)
                lines.append("")

            if detail.full_diff:
                lines.append("Full Diff:")
                lines.append("-" * 70)
                lines.append(detail.full_diff[:2000])  # Limit output
                if len(detail.full_diff) > 2000:
                    lines.append("\n... [diff truncated]")
                lines.append("")

        return '\n'.join(lines)


class RepoMemTools:
    """
    Unified interface for RepoMem episodic memory tools.

    This class provides a high-level interface that combines
    SearchCommit and ExamineCommit tools for easy use.
    """

    def __init__(self, instance_id: str, repo_name: str, memory_base: Path):
        """
        Initialize RepoMem tools.

        Args:
            instance_id: SWE-bench instance ID
            repo_name: Repository name
            memory_base: Base directory for memory storage
        """
        self.instance_id = instance_id
        self.repo_name = repo_name

        # Setup paths
        repo_safe_name = repo_name.replace('/', '_')
        self.memory_file = memory_base / 'episodic' / repo_safe_name / f'{instance_id}.jsonl'
        self.index_dir = memory_base / 'indexes' / repo_safe_name / instance_id / 'commit_bm25'

        # Initialize tools
        self.search_tool = None
        self.examine_tool = None

        # Verify paths exist
        if not self.memory_file.exists():
            raise FileNotFoundError(f"Memory file not found: {self.memory_file}")
        if not self.index_dir.exists():
            raise FileNotFoundError(f"Index directory not found: {self.index_dir}")

    def _get_search_tool(self) -> SearchCommit:
        """Get or create search tool."""
        if not self.search_tool:
            self.search_tool = SearchCommit(self.index_dir)
        return self.search_tool

    def _get_examine_tool(self) -> ExamineCommit:
        """Get or create examine tool."""
        if not self.examine_tool:
            self.examine_tool = ExamineCommit(self.memory_file, self.index_dir)
        return self.examine_tool

    def search_commits(self, query_list: List[str], top_k: int = 10) -> str:
        """
        Search for relevant commits.

        Args:
            query_list: List of search queries
            top_k: Number of results

        Returns:
            Formatted search results
        """
        tool = self._get_search_tool()
        results = tool.search(query_list, top_k=top_k)
        return tool.format_results(results)

    def examine_commits(
        self,
        sha_list: List[str],
        display_issue: bool = True,
        include_diff: bool = False
    ) -> str:
        """
        Examine specific commits in detail.

        Args:
            sha_list: List of commit SHAs
            display_issue: Whether to show linked issues
            include_diff: Whether to include full diff

        Returns:
            Formatted commit details
        """
        tool = self._get_examine_tool()
        details = tool.examine(sha_list, display_issue, include_diff)
        return tool.format_details(details)


# Tool function signatures for agent integration
def search_commit_tool(query_list: List[str], top_k: int = 10) -> str:
    """
    Agent tool: Search for relevant commits in episodic memory.

    Searches commit messages, changed files, and diff summaries
    to find historically relevant commits.

    Args:
        query_list: List of search queries (keywords or phrases)
        top_k: Number of top results to return (default: 10)

    Returns:
        Formatted list of matching commits with sha, message, score,
        changed files, and timestamp.
    """
    # This will be called with proper context from RepoMemTools
    raise NotImplementedError("Tool must be called with RepoMem context")


def examine_commit_tool(sha_list: List[str], display_issue: bool = True) -> str:
    """
    Agent tool: Examine specific commits in detail.

    Retrieves detailed information about commits including
    message, changed files, diff summary, and linked issues.

    Args:
        sha_list: List of commit SHAs to examine (short or full)
        display_issue: Whether to fetch linked issue content (default: True)

    Returns:
        Detailed information for each commit including:
        - Full commit message
        - List of changed files
        - Diff summary
        - Linked issue content (if available)
    """
    # This will be called with proper context from RepoMemTools
    raise NotImplementedError("Tool must be called with RepoMem context")


if __name__ == '__main__':
    import sys

    # Example usage
    print("RepoMem Episodic Memory Tools")
    print("=" * 70)
    print("\nAvailable tools:")
    print("1. SearchCommit - Search for relevant commits")
    print("2. ExamineCommit - Examine specific commits in detail")
    print("\nUsage:")
    print("  tools = RepoMemTools(instance_id, repo_name, memory_base)")
    print("  results = tools.search_commits(['bug fix', 'separability'])")
    print("  details = tools.examine_commits(['abc123', 'def456'])")