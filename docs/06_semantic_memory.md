# 06 - RepoMem Semantic Memory 实现

## 概述

本文档描述了 RepoMem Semantic Memory 模块的实现，用于为仓库中频繁修改的文件生成语义摘要并建立检索索引。

## 实现背景

根据 RepoMem 论文，semantic memory 用于存储文件的语义级摘要，帮助定位系统快速找到相关文件。实现策略：

1. 基于历史 commit 统计文件修改频率
2. 选择 top 200 active files
3. 用 LLM 为每个文件生成语义摘要
4. 构建 BM25 索引支持检索

## 模块结构

```
repomem/
├── semantic_memory.py      # 文件摘要生成
├── index_semantic_memory.py # BM25 索引构建
└── tools.py               # SearchFile 和 ExamineFile 工具
```

## 核心组件

### 1. FileSummary 数据结构

每个文件的语义摘要包含：

```python
@dataclass
class FileSummary:
    file_path: str              # 文件路径
    summary: str                # 语义摘要
    change_frequency: int       # 修改次数
    last_modified: str          # 最后修改时间
    file_type: str              # 文件类型
    line_count: int             # 行数
    key_entities: List[str]     # 关键实体（类、函数名）
    summary_tokens: List[str]   # 用于索引的tokens
```

### 2. FileActivityAnalyzer

从 commit history 分析文件活跃度：

```python
class FileActivityAnalyzer:
    def __init__(self, memories: List[CommitMemory]):
        """从commit memories初始化"""
        
    def analyze(self) -> Dict[str, Dict[str, Any]]:
        """
        统计每个文件的修改次数
        返回: {
            'file_path': {
                'change_count': int,
                'last_modified': str,
                'commit_shas': List[str]
            }
        }
        """
        
    def get_top_active_files(self, top_k: int = 200) -> List[str]:
        """获取top-k最常修改的文件"""
```

**统计逻辑**：
- 遍历所有 commit 的 changed_files
- 计数每个文件出现的次数
- 按修改频率排序

### 3. FileContentReader

读取特定commit版本的文件内容：

```python
class FileContentReader:
    def read_file_at_commit(self, file_path: str, commit_sha: str) -> Optional[str]:
        """
        使用 git show {commit}:{file} 读取文件内容
        处理编码问题（UTF-8 with error replacement）
        """
```

### 4. SummaryGenerator

生成文件语义摘要：

```python
class SummaryGenerator:
    def __init__(self, api_client=None):
        """
        api_client: LLM客户端（可选）
        如果不提供，使用基础摘要生成
        """
        
    def generate_summary(self, file_path: str, content: str) -> str:
        """
        生成语义摘要：
        1. 如果有LLM，调用API生成高质量摘要
        2. 否则使用基础方法：提取类名、函数名、import等
        """
        
    def _generate_basic_summary(self, file_path: str, content: str) -> str:
        """
        基础摘要（无需LLM）：
        - 提取 class 和 function 定义
        - 统计 import 语句
        - 生成结构化描述
        """
```

**LLM Prompt 示例**：

```
Please provide a concise semantic summary of this code file.

File: {file_path}

Content:
```
{content[:5000]}
```

Provide a 2-3 sentence summary covering:
1. What this file does (purpose/responsibility)
2. Key components (classes, functions, modules)
3. Important dependencies or relationships
```

### 5. SemanticMemoryBuilder

构建完整的 semantic memory：

```python
class SemanticMemoryBuilder:
    def __init__(
        self,
        repo_path: str,
        memories: List[CommitMemory],
        api_client=None,
        top_k: int = 200
    ):
        """初始化构建器"""
        
    def build(self, base_commit: str) -> List[FileSummary]:
        """
        完整构建流程：
        1. 分析文件活跃度
        2. 选择top-k文件
        3. 读取文件内容
        4. 生成语义摘要
        5. 提取关键实体
        """
```

## 工作流程

### 构建 Semantic Memory

```python
# 1. 加载 episodic memory
memories = load_memory_from_jsonl(episodic_memory_file)

# 2. 创建构建器
builder = SemanticMemoryBuilder(
    repo_path=repo_path,
    memories=memories,
    api_client=None,  # 使用基础摘要
    top_k=200
)

# 3. 构建
summaries = builder.build(base_commit)

# 4. 保存
save_semantic_memory(summaries, output_file)

# 5. 建立索引
indexer = SemanticMemoryIndexer(summaries)
index = indexer.build_index()
indexer.save_index(index_dir)
```

### 检索 Semantic Memory

```python
# 1. 加载工具
tools = RepoMemTools(instance_id, repo_name, memory_base)

# 2. 搜索相关文件
results = tools.search_files('coordinate transformation', top_k=10)

# 3. 查看特定文件详情
details = tools.examine_files(['astropy/coordinates/angles.py',
                                'astropy/units/quantity.py'])
```

## BM25 索引策略

### 索引字段

Semantic memory 的 BM25 索引包括多个字段：

1. **Summary tokens** - 语义摘要的tokens（权重最高）
2. **File path tokens** - 文件路径的组成部分
3. **Key entities** - 关键实体名称（类名、函数名）

### 参数设置

```python
K1 = 1.5  # Term frequency saturation
B = 0.75  # Length normalization
```

与 Episodic memory 相同的参数设置，适合代码检索场景。

## 数据存储格式

### Memory 文件格式 (JSONL)

```
memory/semantic/<repo_name>/<instance_id>_semantic.jsonl
```

每行一个JSON对象：

```json
{
  "file_path": "astropy/modeling/core.py",
  "summary": "Core modeling classes including Model, CompoundModel...",
  "change_frequency": 156,
  "last_modified": "2022-03-15T10:30:00+00:00",
  "file_type": "python",
  "line_count": 2345,
  "key_entities": ["Model", "CompoundModel", "Parameter"],
  "summary_tokens": ["core", "modeling", "classes", ...]
}
```

### Index 文件格式

```
memory/indexes/<repo_name>/<instance_id>/semantic_bm25/
├── semantic_index.pkl       # BM25索引
└── semantic_index_metadata.json  # 元数据
```

## SearchFile 和 ExamineFile 工具

### SearchFile

搜索相关文件：

```python
class SearchFile:
    def search(self, query: str, top_k: int = 10) -> List[FileSearchResult]:
        """
        基于语义摘要搜索文件
        返回: file_path, summary, score, change_frequency, key_entities
        """
```

**使用示例**：

```python
search_tool = SearchFile(index_dir)
results = search_tool.search('separability matrix calculation', top_k=10)

for result in results:
    print(f"{result.file_path} (score: {result.score:.2f})")
    print(f"  Summary: {result.summary[:100]}...")
    print(f"  Key entities: {', '.join(result.key_entities[:5])}")
```

### ExamineFile

查看文件详情：

```python
class ExamineFile:
    def examine(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        获取文件详细信息：
        - 完整摘要
        - 修改历史
        - 关键实体
        """
```

## 与 Episodic Memory 的关系

Semantic Memory 依赖于 Episodic Memory：

```
Episodic Memory (commits)
    ↓
FileActivityAnalyzer (统计文件活跃度)
    ↓
Top 200 Active Files
    ↓
File Content Reading
    ↓
Summary Generation
    ↓
Semantic Memory (file summaries)
```

### 依赖关系

1. **输入依赖**：需要 episodic memory 提供历史commit信息
2. **构建顺序**：必须先构建episodic memory，再构建semantic memory
3. **数据流**：commit histories → file statistics → file summaries

## 性能考虑

### 时间估算（单个instance）

| 步骤 | 时间（200文件） |
|------|----------------|
| 文件活跃度分析 | ~1秒 |
| 读取文件内容 | ~10-20秒 |
| 基础摘要生成 | ~5-10秒 |
| LLM摘要生成 | ~2-5分钟（如果使用）|
| 建立BM25索引 | ~1秒 |
| **总计（无LLM）** | **~15-30秒** |
| **总计（有LLM）** | **~3-6分钟** |

### 资源使用

- **内存**：~50MB（200个文件摘要）
- **磁盘**：~1MB JSONL + ~1MB索引
- **API调用**：如果使用LLM，200次API调用

## 关键设计决策

### 1. Top 200 Active Files

选择策略：
- 基于修改频率而非文件大小
- 活跃文件更有可能包含bug或需要修改
- 平衡覆盖范围和构建成本

### 2. 基础摘要 vs LLM摘要

**基础摘要优点**：
- 无需API调用
- 快速、确定
- 成本为零

**LLM摘要优点**：
- 语义理解更深入
- 能捕捉文件间关系
- 检索效果更好

**推荐**：
- 开发测试：使用基础摘要
- 生产环境：使用LLM摘要

### 3. Key Entities 提取

提取策略（Python）：
```python
# 识别类定义
if line.startswith('class '):
    class_name = line.split('(')[0].replace('class ', '')
    
# 识别函数定义
if line.startswith('def '):
    func_name = line.split('(')[0].replace('def ', '')
```

为其他语言可扩展类似规则。

## 测试示例

参见 `scripts/test_semantic_memory.py`：

```python
# 使用基础摘要测试
builder = SemanticMemoryBuilder(
    repo_path,
    memories,
    api_client=None,  # 不使用LLM
    top_k=20  # 测试用20个文件
)

summaries = builder.build(base_commit)
```

## 局限性与改进方向

### 当前局限

1. **Key Entities 提取**：仅支持Python语法
2. **文件类型检测**：基于扩展名，不够智能
3. **跨文件关系**：未捕捉文件间依赖

### 改进方向

1. **多语言支持**：添加Java/JavaScript等的实体提取
2. **Import分析**：构建文件依赖图
3. **增量更新**：支持只处理新修改的文件
4. **Embedding检索**：结合语义embedding提升检索效果

## 相关文档

- [05_episodic_memory.md](05_episodic_memory.md) - Episodic Memory实现
- [08_final_evaluation_results.md](08_final_evaluation_results.md) - 评估结果

## 参考文献

- RepoMem: Repository-Level Memory for Software Engineering
- SWE-bench: Can Language Models Resolve Real-World GitHub Issues?