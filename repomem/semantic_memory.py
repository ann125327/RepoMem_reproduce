"""
RepoMem Semantic Memory Module

This module implements the semantic memory component of RepoMem,
which generates and indexes semantic summaries for active files.

Workflow:
1. Analyze commit history to find frequently modified files
2. Select top 200 active files
3. Read file content at base_commit version
4. Generate semantic summary using LLM
5. Build BM25 index for retrieval
"""

import json
import subprocess
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from .episodic_memory import load_memory_from_jsonl, CommitMemory


@dataclass
class FileSummary:
    """Semantic summary for a single file."""
    file_path: str
    summary: str
    change_frequency: int
    last_modified: str
    file_type: str
    line_count: int
    key_entities: List[str]  # Classes, functions, imports

    # For indexing
    summary_tokens: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileSummary':
        """Create from dictionary."""
        return cls(**data)


class FileActivityAnalyzer:
    """Analyze file modification frequency from commit history."""

    def __init__(self, memories: List[CommitMemory]):
        """
        Initialize analyzer.

        Args:
            memories: List of commit memories
        """
        self.memories = memories
        self.file_stats = None

    def analyze(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze file modification statistics.

        Returns:
            Dictionary mapping file_path to stats:
            {
                'file_path': {
                    'change_count': int,
                    'last_modified': str,
                    'commit_shas': List[str]
                }
            }
        """
        file_stats = {}

        for memory in self.memories:
            for file_path in memory.changed_files:
                if file_path not in file_stats:
                    file_stats[file_path] = {
                        'change_count': 0,
                        'last_modified': memory.timestamp,
                        'commit_shas': []
                    }

                file_stats[file_path]['change_count'] += 1
                file_stats[file_path]['commit_shas'].append(memory.sha)

                # Update last modified if newer
                if memory.timestamp > file_stats[file_path]['last_modified']:
                    file_stats[file_path]['last_modified'] = memory.timestamp

        self.file_stats = file_stats
        return file_stats

    def get_top_active_files(self, top_k: int = 200) -> List[str]:
        """
        Get top-k most frequently modified files.

        Args:
            top_k: Number of top files to return

        Returns:
            List of file paths sorted by modification frequency
        """
        if not self.file_stats:
            self.analyze()

        # Sort by change count
        sorted_files = sorted(
            self.file_stats.items(),
            key=lambda x: x[1]['change_count'],
            reverse=True
        )

        return [file_path for file_path, _ in sorted_files[:top_k]]


class FileContentReader:
    """Read file content at specific commit."""

    def __init__(self, repo_path: str):
        """
        Initialize reader.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path)

    def read_file_at_commit(self, file_path: str, commit_sha: str) -> Optional[str]:
        """
        Read file content at specific commit.

        Args:
            file_path: Relative path to file
            commit_sha: Commit SHA

        Returns:
            File content or None if not found
        """
        try:
            cmd = [
                'git', '-C', str(self.repo_path),
                'show', f'{commit_sha}:{file_path}'
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error reading {file_path} at {commit_sha}: {e}")
            return None

    def get_file_info(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Get basic file information.

        Args:
            file_path: File path
            content: File content

        Returns:
            Dictionary with file info
        """
        lines = content.split('\n') if content else []

        # Detect file type
        file_type = 'unknown'
        if file_path.endswith('.py'):
            file_type = 'python'
        elif file_path.endswith('.js'):
            file_type = 'javascript'
        elif file_path.endswith('.ts'):
            file_type = 'typescript'
        elif file_path.endswith('.java'):
            file_type = 'java'
        elif file_path.endswith('.cpp') or file_path.endswith('.c'):
            file_type = 'c/c++'
        elif file_path.endswith('.md'):
            file_type = 'markdown'
        elif file_path.endswith('.json'):
            file_type = 'json'

        return {
            'file_type': file_type,
            'line_count': len(lines)
        }


class SummaryGenerator:
    """Generate semantic summary for files using LLM."""

    def __init__(self, api_client=None):
        """
        Initialize generator.

        Args:
            api_client: LLM API client (e.g., OpenAI, Anthropic)
        """
        self.api_client = api_client

    def generate_summary(self, file_path: str, content: str) -> str:
        """
        Generate semantic summary for a file.

        Args:
            file_path: File path
            content: File content

        Returns:
            Semantic summary string
        """
        if not self.api_client:
            # Fallback: generate basic summary without LLM
            return self._generate_basic_summary(file_path, content)

        # Use LLM to generate summary
        prompt = self._build_summary_prompt(file_path, content)

        try:
            response = self.api_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"LLM error for {file_path}: {e}")
            return self._generate_basic_summary(file_path, content)

    def _build_summary_prompt(self, file_path: str, content: str) -> str:
        """Build prompt for summary generation."""
        return f"""Please provide a concise semantic summary of this code file.

File: {file_path}

Content:
```
{content[:5000]}  # Limit to avoid token limits
```

Provide a 2-3 sentence summary covering:
1. What this file does (purpose/responsibility)
2. Key components (classes, functions, modules)
3. Important dependencies or relationships

Keep it concise and informative for code search and understanding."""

    def _generate_basic_summary(self, file_path: str, content: str) -> str:
        """Generate basic summary without LLM."""
        if not content:
            return f"Empty file: {file_path}"

        # Extract key information
        lines = content.split('\n')

        # Find classes and functions (Python-specific)
        classes = []
        functions = []
        imports = []

        for line in lines:
            line = line.strip()
            if line.startswith('class '):
                class_name = line.split('(')[0].replace('class ', '')
                classes.append(class_name)
            elif line.startswith('def '):
                func_name = line.split('(')[0].replace('def ', '')
                functions.append(func_name)
            elif line.startswith('import ') or line.startswith('from '):
                imports.append(line)

        # Build summary
        parts = [f"File: {file_path}"]

        if classes:
            parts.append(f"Classes: {', '.join(classes[:5])}")
        if functions:
            parts.append(f"Functions: {', '.join(functions[:10])}")
        if imports:
            parts.append(f"Key imports: {len(imports)} modules")

        parts.append(f"Total lines: {len(lines)}")

        return ' | '.join(parts)

    def extract_key_entities(self, content: str) -> List[str]:
        """
        Extract key entities (classes, functions) from content.

        Args:
            content: File content

        Returns:
            List of entity names
        """
        entities = []

        if not content:
            return entities

        lines = content.split('\n')
        for line in lines:
            line = line.strip()

            # Python: class and function definitions
            if line.startswith('class '):
                class_name = line.split('(')[0].replace('class ', '').strip()
                if class_name:
                    entities.append(class_name)
            elif line.startswith('def '):
                func_name = line.split('(')[0].replace('def ', '').strip()
                if func_name and not func_name.startswith('_'):
                    entities.append(func_name)

        return entities[:20]  # Limit to top 20


class SemanticMemoryBuilder:
    """Build semantic memory for a repository."""

    def __init__(
        self,
        repo_path: str,
        memories: List[CommitMemory],
        api_client=None,
        top_k: int = 200
    ):
        """
        Initialize builder.

        Args:
            repo_path: Path to git repository
            memories: List of commit memories
            api_client: LLM API client
            top_k: Number of top active files to process
        """
        self.repo_path = repo_path
        self.memories = memories
        self.api_client = api_client
        self.top_k = top_k

        self.analyzer = FileActivityAnalyzer(memories)
        self.reader = FileContentReader(repo_path)
        self.generator = SummaryGenerator(api_client)

    def build(self, base_commit: str) -> List[FileSummary]:
        """
        Build semantic memory.

        Args:
            base_commit: Base commit SHA

        Returns:
            List of FileSummary objects
        """
        print(f"\nBuilding semantic memory for top {self.top_k} active files...")

        # 1. Analyze file activity
        print("  1. Analyzing file modification frequency...")
        self.analyzer.analyze()
        top_files = self.analyzer.get_top_active_files(self.top_k)

        print(f"     Found {len(top_files)} active files")

        # 2. Generate summaries
        print("  2. Generating semantic summaries...")
        summaries = []

        for i, file_path in enumerate(top_files):
            if i % 20 == 0:
                print(f"     Processing {i}/{len(top_files)} files...")

            summary = self._generate_file_summary(
                file_path,
                base_commit
            )

            if summary:
                summaries.append(summary)

        print(f"     Generated {len(summaries)} summaries")
        return summaries

    def _generate_file_summary(
        self,
        file_path: str,
        base_commit: str
    ) -> Optional[FileSummary]:
        """Generate summary for a single file."""
        # Get file stats
        stats = self.analyzer.file_stats.get(file_path, {})

        # Read file content
        content = self.reader.read_file_at_commit(file_path, base_commit)

        if content is None:
            return None

        # Get file info
        info = self.reader.get_file_info(file_path, content)

        # Generate summary
        summary_text = self.generator.generate_summary(file_path, content)

        # Extract key entities
        key_entities = self.generator.extract_key_entities(content)

        # Create summary object
        return FileSummary(
            file_path=file_path,
            summary=summary_text,
            change_frequency=stats.get('change_count', 0),
            last_modified=stats.get('last_modified', ''),
            file_type=info['file_type'],
            line_count=info['line_count'],
            key_entities=key_entities,
            summary_tokens=[]  # Will be filled during indexing
        )


def save_semantic_memory(summaries: List[FileSummary], output_path: Path):
    """
    Save semantic memory to JSONL file.

    Args:
        summaries: List of file summaries
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for summary in summaries:
            f.write(json.dumps(summary.to_dict()) + '\n')

    print(f"Saved {len(summaries)} file summaries to {output_path}")


def load_semantic_memory(input_path: Path) -> List[FileSummary]:
    """
    Load semantic memory from JSONL file.

    Args:
        input_path: Input file path

    Returns:
        List of FileSummary objects
    """
    summaries = []

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            summaries.append(FileSummary.from_dict(data))

    print(f"Loaded {len(summaries)} file summaries from {input_path}")
    return summaries


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 4:
        print("Usage: python semantic_memory.py <repo_path> <memory_file.jsonl> <base_commit>")
        sys.exit(1)

    repo_path = sys.argv[1]
    memory_file = Path(sys.argv[2])
    base_commit = sys.argv[3]

    # Load commit memory
    memories = load_memory_from_jsonl(memory_file)

    # Build semantic memory
    builder = SemanticMemoryBuilder(repo_path, memories)
    summaries = builder.build(base_commit)

    # Save
    output_file = memory_file.parent.parent / 'semantic' / f'{memory_file.stem}_semantic.jsonl'
    save_semantic_memory(summaries, output_file)