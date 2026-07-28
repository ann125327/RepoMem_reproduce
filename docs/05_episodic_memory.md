# 05 - RepoMem Episodic Memory 实现

## 概述

本文档描述了 RepoMem Episodic Memory 模块的实现，用于存储和检索仓库的历史提交信息。

## 实现背景

根据 RepoMem 论文，episodic memory 用于存储仓库的历史提交信息，帮助定位系统理解代码演化的历史上下文。对于每个 SWE-bench instance：

1. 使用 `base_commit` 之前的历史 commits 构建 memory
2. 默认最多使用 7000 个历史 commits
3. 每条 commit memory 包含完整信息

## 模块结构

```
repomem/
├── __init__.py              # 包初始化
├── episodic_memory.py       # Commit memory 数据结构和构建
├── index_commit_memory.py   # BM25 索引构建和检索
└── tools.py                 # SearchCommit 和 ExamineCommit 工具
```

## 核心组件

### 1. CommitMemory 数据结构

每条 commit memory 包含：

```python
@dataclass
class CommitMemory:
    sha: str                          # Commit SHA
    message: str                      # Commit message
    timestamp: str                    # ISO格式时间戳
    changed_files: List[str]          # 修改的文件列表
    diff_summary: str                 # Diff 摘要
    full_diff: Optional[str]          # 完整 diff (可选)
    linked_issue_id: Optional[str]    # 关联的 issue ID
    linked_issue_text: Optional[str]  # Issue 内容 (可选)
    
    # 用于索引的 tokens
    message_tokens: List[str]
    diff_tokens: List[str]
```

### 2. CommitMemoryBuilder

负责从 git 仓库构建 commit memory：

**主要功能**：
- 获取 base_commit 之前的历史提交（最多7000条）
- 解析 commit message
- 提取 changed files
- 生成 diff summary
- 提取 linked issue ID

**关键方法**：

```python
class CommitMemoryBuilder:
    def __init__(self, repo_path: str, max_commits: int = 7000):
        """初始化构建器"""
        
    def build_memory(self, base_commit: Optional[str] = None) -> List[CommitMemory]:
        """构建 commit memory，获取 base_commit 之前的提交"""
        
    def _get_commit_list(self, base_commit: Optional[str]) -> List[str]:
        """使用 git rev-list 获取提交列表"""
        # 使用 git rev-list --max-count=7000 {base_commit}^
        # 获取 base_commit 的父提交及其祖先
        
    def _extract_linked_issue(self, message: str) -> Optional[str]:
        """从 commit message 中提取关联的 issue ID"""
        # 支持: Fixes #id, Closes #id, Resolves #id 等模式
```

**Diff Summary 生成策略**：

```python
def _create_diff_summary(self, diff: str, changed_files: List[str]) -> str:
    """
    生成 diff 摘要，避免完整 diff 过大：
    - 统计 additions/deletions 行数
    - 列出修改的文件（最多10个）
    - 提取修改的函数名
    - 提取修改的类名
    """
```

### 3. CommitMemoryIndexer

构建 BM25 索引以支持高效检索：

**索引策略**：

```python
class CommitMemoryIndexer:
    # BM25 参数
    K1 = 1.5  # Term frequency saturation
    B = 0.75  # Length normalization
    
    # 字段权重（多字段搜索）
    FIELD_WEIGHTS = {
        'message': 1.0,
        'changed_files': 0.8,
        'diff_summary': 0.6
    }
```

**索引构建过程**：

1. 对每个 commit：
   - Tokenize message, changed_files, diff_summary
   - 构建倒排索引：`term -> [(doc_id, term_freq), ...]`
   - 记录文档长度用于归一化

2. 计算 BM25 相关性分数：
   ```
   score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))
   ```
   其中：
   - `IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)`
   - `f(qi, D)` 是词项 qi 在文档 D 中的频率
   - `|D|` 是文档长度
   - `avgdl` 是平均文档长度

### 4. SearchCommit 和 ExamineCommit 工具

#### SearchCommit

搜索相关的历史提交：

```python
class SearchCommit:
    def search(self, query_list: List[str], top_k: int = 10) -> List[SearchResult]:
        """
        多字段搜索：
        - 对 query_list 中的 query 分别检索
        - 结合 message / changed_files / diff_summary
        - 返回 top-k commit，包含 sha、message、score、changed_files、timestamp
        """
```

**使用示例**：

```python
search_tool = SearchCommit(index_dir)

# 搜索与 separability 相关的提交
results = search_tool.search(['separability matrix', 'compound model'], top_k=10)

for result in results:
    print(f"[{result.sha[:8]}] {result.message[:50]}...")
    print(f"  Score: {result.score:.2f}")
    print(f"  Files: {', '.join(result.changed_files[:3])}")
```

#### ExamineCommit

查看特定提交的详细信息：

```python
class ExamineCommit:
    def examine(self, sha_list: List[str], display_issue: bool = True) -> List[CommitDetail]:
        """
        获取提交详细信息：
        - Commit message
        - Changed files
        - Diff summary
        - Linked issue (如果 display_issue=True)
        """
```

**使用示例**：

```python
examine_tool = ExamineCommit(memory_file, index_dir)

# 查看特定提交
details = examine_tool.examine(['a4f25a2', '95f3d4da'], display_issue=True)

for detail in details:
    print(f"\n{'='*70}")
    print(f"Commit: {detail.sha}")
    print(f"Message: {detail.message}")
    print(f"Files: {', '.join(detail.changed_files)}")
    print(f"Diff Summary: {detail.diff_summary}")
    if detail.linked_issue_id:
        print(f"Issue: #{detail.linked_issue_id}")
        print(f"Issue Text: {detail.linked_issue_text}")
```

## 数据存储格式

### Memory 文件格式 (JSONL)

```
memory/episodic/<repo_name>/<instance_id>.jsonl
```

每行一个 JSON 对象：

```json
{
  "sha": "a4f25a2ced5d7bb5cfe539071c36f30ae35b0b42",
  "message": "Merge pull request #12864...",
  "timestamp": "2022-03-15T10:30:00+00:00",
  "changed_files": ["astropy/modeling/core.py", "astropy/modeling/separable.py"],
  "diff_summary": "+45/-12 lines | Files: astropy/modeling/core.py...",
  "linked_issue_id": "12864",
  "message_tokens": ["merge", "pull", "request", ...],
  "diff_tokens": ["lines", "files", "astropy", ...]
}
```

### Index 文件格式

```
memory/indexes/<repo_name>/<instance_id>/commit_bm25/
├── commit_index.pkl       # 序列化的 BM25 索引
└── index_metadata.json    # 索引元数据
```

**index_metadata.json**:

```json
{
  "num_docs": 7000,
  "num_terms": 15234,
  "avg_doc_length": 125.5,
  "field_weights": {
    "message": 1.0,
    "changed_files": 0.8,
    "diff_summary": 0.6
  }
}
```

## 工作流程

### 构建 Commit Memory

```python
# 1. 创建构建器
builder = CommitMemoryBuilder(repo_path, max_commits=7000)

# 2. 构建 memory（获取 base_commit 之前的提交）
memories = builder.build_memory(base_commit)

# 3. 保存到 JSONL
save_memory_to_jsonl(memories, output_file)

# 4. 构建索引
indexer = CommitMemoryIndexer(memories)
index = indexer.build_index()
indexer.save_index(index_dir)
```

### 检索 Commit Memory

```python
# 1. 加载工具
tools = RepoMemTools(instance_id, repo_name, memory_base)

# 2. 搜索相关提交
search_results = tools.search_commits(['bug fix', 'separability'], top_k=10)

# 3. 查看特定提交详情
commit_details = tools.examine_commits(['a4f25a2', '95f3d4da'], display_issue=True)
```

## 关键设计决策

### 1. Git 历史获取策略

使用 `git rev-list --max-count=7000 {base_commit}^` 获取 base_commit 的父提交及其祖先：

- `{base_commit}^` 表示 base_commit 的父提交
- `--max-count=7000` 限制最多7000个提交
- 结果按时间倒序排列（最新的在前）

### 2. Diff Summary vs Full Diff

为避免内存占用过大：
- 默认生成 diff summary（统计信息 + 关键函数/类名）
- 可选保存 full diff（限制50KB）
- 根据任务需求选择合适的存储策略

### 3. Linked Issue 提取

支持常见的 issue 引用模式：
- `Fixes #id`
- `Closes #id`
- `Resolves #id`
- `issue #id`
- `PR #id`

如果无法访问 GitHub API，则只保存 issue ID，不强制抓取内容。

### 4. BM25 参数调优

基于常见实践选择参数：
- `K1 = 1.5`：适中的 term frequency 饱和度
- `B = 0.75`：较强的文档长度归一化
- 字段权重：message > changed_files > diff_summary

## 性能考虑

### 内存使用

- 单个 commit memory 约 1-5KB
- 7000 个提交约需 7-35MB 内存
- BM25 索引约需额外 10-20MB

### 构建时间

- Git 命令执行：每100次提交约1秒
- 总构建时间：约70-100秒（7000个提交）

### 检索性能

- BM25 检索：<100ms（7000文档）
- 多字段加权检索：<200ms

## 局限性与改进方向

### 当前局限

1. **Issue 内容获取**：需要 GitHub API 访问权限
2. **编码处理**：Windows 下 git 输出的编码问题
3. **大 diff 处理**：截断可能丢失关键信息

### 改进方向

1. **GitHub API 集成**：自动抓取 linked issue 内容
2. **增量更新**：支持增量添加新提交
3. **语义检索**：结合 embedding 进行语义搜索
4. **Commit 分组**：按功能/模块对提交进行聚类

## 测试示例

参见 `scripts/build_episodic_memory.py`：

```python
# 测试实例
test_instances = [
    {
        'instance_id': 'astropy__astropy-12907',
        'repo': 'astropy/astropy',
        'base_commit': 'd16bfe05a744909de4b27f5875fe0d4ed41ce607',
        'problem_statement': 'Modeling separability_matrix issue'
    }
]

# 构建 memory
build_memory_for_instance(instance_data, repo_base, output_base)
```

## 相关文档

- [04_evaluation_protocol.md](04_evaluation_protocol.md) - LocAgent 评估协议
- [08_final_evaluation_results.md](08_final_evaluation_results.md) - 评估结果

## 参考文献

- RepoMem: Repository-Level Memory for Software Engineering (论文)
- SWE-bench: Can Language Models Resolve Real-World GitHub Issues?
- BM25: Best Matching 25 算法