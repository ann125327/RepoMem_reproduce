"""
RepoMem Episodic Memory Module

This module implements the episodic memory component of RepoMem,
which stores and indexes historical commits for a repository.

Each commit memory entry contains:
- commit sha
- commit message
- commit timestamp
- changed files
- diff summary or full diff
- linked issue id (if found)
- linked issue text (if available)
"""

import json
import re
import subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib


@dataclass
class CommitMemory:
    """Single commit memory entry."""
    sha: str
    message: str
    timestamp: str
    changed_files: List[str]
    diff_summary: str
    full_diff: Optional[str] = None
    linked_issue_id: Optional[str] = None
    linked_issue_text: Optional[str] = None

    # Metadata for indexing
    message_tokens: List[str] = field(default_factory=list)
    diff_tokens: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommitMemory':
        """Create from dictionary."""
        return cls(**data)


class CommitMemoryBuilder:
    """Build commit memory from a git repository."""

    # Patterns to extract linked issues from commit messages
    ISSUE_PATTERNS = [
        r'(?:Fixes|Closes|Resolves|References|See)\s+#(\d+)',
        r'(?:Fixes|Closes|Resolves|References|See)\s+(\S+/\S+#\d+)',
        r'issue\s+#?(\d+)',
        r'PR\s+#(\d+)',
    ]

    def __init__(self, repo_path: str, max_commits: int = 7000):
        """
        Initialize builder.

        Args:
            repo_path: Path to the git repository
            max_commits: Maximum number of commits to process
        """
        self.repo_path = Path(repo_path)
        self.max_commits = max_commits
        self._validate_repo()

    def _validate_repo(self):
        """Validate that the path is a git repository."""
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")

        git_dir = self.repo_path / '.git'
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def build_memory(self, base_commit: Optional[str] = None) -> List[CommitMemory]:
        """
        Build commit memory up to base_commit.

        Args:
            base_commit: Base commit SHA (exclusive). If None, uses all commits.

        Returns:
            List of CommitMemory objects
        """
        # Get commit list
        commits = self._get_commit_list(base_commit)

        print(f"Building memory for {len(commits)} commits...")

        memories = []
        for i, sha in enumerate(commits[:self.max_commits]):
            if i % 100 == 0:
                print(f"  Processing commit {i}/{min(len(commits), self.max_commits)}")

            memory = self._build_single_memory(sha)
            if memory:
                memories.append(memory)

        print(f"Built {len(memories)} commit memories")
        return memories

    def _get_commit_list(self, base_commit: Optional[str]) -> List[str]:
        """
        Get list of commit SHAs before base_commit.

        Args:
            base_commit: Base commit SHA (exclusive, we want commits BEFORE this one)

        Returns:
            List of commit SHAs in reverse chronological order (newest first)
        """
        try:
            if base_commit:
                # Get all commits BEFORE base_commit (not including base_commit itself)
                # base_commit^ means the parent of base_commit, so base_commit^..HEAD would give
                # commits from parent to HEAD. We want commits BEFORE base_commit.
                # Use base_commit^@ to get all ancestors of base_commit
                cmd = ['git', '-C', str(self.repo_path), 'rev-list', '--max-count=7000', f'{base_commit}^']
            else:
                # Get all commits
                cmd = ['git', '-C', str(self.repo_path), 'rev-list', '--max-count=7000', '--all']

            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            commits = result.stdout.strip().split('\n')
            commits = [c.strip() for c in commits if c.strip()]

            # commits are already in reverse chronological order (newest first)
            return commits
        except subprocess.CalledProcessError as e:
            print(f"Error getting commit list: {e}")
            print(f"Git stderr: {e.stderr}")
            return []

    def _build_single_memory(self, sha: str) -> Optional[CommitMemory]:
        """
        Build memory for a single commit.

        Args:
            sha: Commit SHA

        Returns:
            CommitMemory object or None if failed
        """
        try:
            # Get commit info
            message = self._get_commit_message(sha)
            timestamp = self._get_commit_timestamp(sha)
            changed_files = self._get_changed_files(sha)
            diff = self._get_commit_diff(sha)

            # Extract linked issue
            issue_id = self._extract_linked_issue(message)

            # Create diff summary
            diff_summary = self._create_diff_summary(diff, changed_files)

            # Tokenize for indexing
            message_tokens = self._tokenize(message)
            diff_tokens = self._tokenize(diff_summary)

            return CommitMemory(
                sha=sha,
                message=message,
                timestamp=timestamp,
                changed_files=changed_files,
                diff_summary=diff_summary,
                full_diff=diff,
                linked_issue_id=issue_id,
                message_tokens=message_tokens,
                diff_tokens=diff_tokens
            )
        except Exception as e:
            print(f"Error processing commit {sha}: {e}")
            return None

    def _get_commit_message(self, sha: str) -> str:
        """Get commit message for a given SHA."""
        cmd = ['git', '-C', str(self.repo_path), 'log', '-1', '--pretty=format:%B', sha]
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', check=True)
        return result.stdout.strip()

    def _get_commit_timestamp(self, sha: str) -> str:
        """Get commit timestamp in ISO format."""
        cmd = ['git', '-C', str(self.repo_path), 'log', '-1', '--pretty=format:%aI', sha]
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', check=True)
        return result.stdout.strip()

    def _get_changed_files(self, sha: str) -> List[str]:
        """Get list of files changed in a commit."""
        cmd = ['git', '-C', str(self.repo_path), 'diff-tree', '--no-commit-id', '--name-only', '-r', sha]
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', check=True)
        files = result.stdout.strip().split('\n')
        return [f.strip() for f in files if f.strip()]

    def _get_commit_diff(self, sha: str) -> str:
        """Get full diff for a commit."""
        cmd = ['git', '-C', str(self.repo_path), 'show', '--format=', sha]
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', check=True)

        # Limit diff size to avoid memory issues
        diff = result.stdout.strip()
        if len(diff) > 50000:  # ~50KB limit
            diff = diff[:50000] + "\n... [truncated due to size]"

        return diff

    def _extract_linked_issue(self, message: str) -> Optional[str]:
        """
        Extract linked issue ID from commit message.

        Args:
            message: Commit message

        Returns:
            Issue ID string or None
        """
        for pattern in self.ISSUE_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _create_diff_summary(self, diff: str, changed_files: List[str]) -> str:
        """
        Create a summary of the diff.

        This extracts key information without the full diff content.
        """
        if not diff:
            return f"Changed {len(changed_files)} files: {', '.join(changed_files[:5])}"

        # Extract function/class changes
        summary_parts = []

        # Count additions/deletions
        additions = len([line for line in diff.split('\n') if line.startswith('+')])
        deletions = len([line for line in diff.split('\n') if line.startswith('-')])
        summary_parts.append(f"+{additions}/-{deletions} lines")

        # List changed files (up to 10)
        if changed_files:
            files_str = ', '.join(changed_files[:10])
            if len(changed_files) > 10:
                files_str += f" ... and {len(changed_files) - 10} more"
            summary_parts.append(f"Files: {files_str}")

        # Extract function definitions changed
        func_changes = re.findall(r'@@.*def\s+(\w+)', diff)
        if func_changes:
            summary_parts.append(f"Functions: {', '.join(func_changes[:5])}")

        # Extract class definitions changed
        class_changes = re.findall(r'@@.*class\s+(\w+)', diff)
        if class_changes:
            summary_parts.append(f"Classes: {', '.join(class_changes[:3])}")

        return ' | '.join(summary_parts)

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for indexing.

        Converts to lowercase and splits on non-alphanumeric characters.
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Split on non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text)

        # Filter short tokens
        tokens = [t for t in tokens if len(t) > 2]

        return tokens


def save_memory_to_jsonl(memories: List[CommitMemory], output_path: Path):
    """
    Save commit memories to JSONL file.

    Args:
        memories: List of commit memories
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for memory in memories:
            f.write(json.dumps(memory.to_dict()) + '\n')

    print(f"Saved {len(memories)} commit memories to {output_path}")


def load_memory_from_jsonl(input_path: Path) -> List[CommitMemory]:
    """
    Load commit memories from JSONL file.

    Args:
        input_path: Input file path

    Returns:
        List of CommitMemory objects
    """
    memories = []

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            memories.append(CommitMemory.from_dict(data))

    print(f"Loaded {len(memories)} commit memories from {input_path}")
    return memories


if __name__ == '__main__':
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python episodic_memory.py <repo_path> [base_commit] [output_file]")
        sys.exit(1)

    repo_path = sys.argv[1]
    base_commit = sys.argv[2] if len(sys.argv) > 2 else None
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'commit_memory.jsonl'

    builder = CommitMemoryBuilder(repo_path)
    memories = builder.build_memory(base_commit)

    save_memory_to_jsonl(memories, Path(output_file))