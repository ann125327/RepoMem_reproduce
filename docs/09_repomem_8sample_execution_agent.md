# 09 - RepoMem 8-Sample Reproduction Execution Plan

## 0. 任务定位

你是执行 agent。你的任务不是重新解释论文，也不是只跑 LocAgent baseline，而是在当前仓库已有工作的基础上，完成一个 **8 个样本规模的 RepoMem 小规模复现**。

最终目标：

1. 将 `repomem/` 中已经实现的 memory 工具正式接入 LocAgent agent 流程。
2. 在相同 8 个 SWE-bench Verified 样本上完成 4 组实验：
   - `LocAgent`
   - `RepoMem-Episodic`
   - `RepoMem-Semantic`
   - `RepoMem-Full`
3. 输出统一评测结果，并比较 repository memory 是否带来收益。

当前状态：

- LocAgent baseline 已经能跑通。
- 最大已有 baseline 结果位于 `LocAgent/results/locagent_batch_fixed/`。
- 已有 8 样本 baseline 指标：
  - `Acc@1 = 4/8 = 50.0%`
  - `Acc@3 = 6/8 = 75.0%`
  - `Acc@5 = 6/8 = 75.0%`
- `repomem/` 已有 memory 原型代码。
- `memory/episodic/astropy_astropy/astropy__astropy-12907.jsonl` 已有 7000 条 commit memory。
- semantic memory 目前只看到 quick test 级别，不能视为完整 RepoMem 实验。

你的工作重点是把这些原型变成可运行、可评测、可对比的 RepoMem agent 实验。

## 1. 样本范围

本阶段固定使用 8 个 astropy 样本，和已有 baseline 保持一致：

```text
astropy__astropy-12907
astropy__astropy-13033
astropy__astropy-13236
astropy__astropy-13398
astropy__astropy-13453
astropy__astropy-13579
astropy__astropy-13977
astropy__astropy-14096
```

数据集：

```text
princeton-nlp/SWE-bench_Verified
split = test
repo = astropy/astropy
```

注意：

- 必须保证所有实验使用同一批 8 个样本。
- 不要把单个样本结果误写成 8 样本结果。
- 不要把 memory 工具单独测试结果误写成 RepoMem agent 结果。

## 2. 总体实验矩阵

需要完成 4 组实验。

| 实验名 | 代码搜索/图工具 | Episodic Memory | Semantic Memory | 输出目录 |
|---|---|---|---|---|
| `LocAgent` | 启用 | 关闭 | 关闭 | `results/locagent_8_baseline/` |
| `RepoMem-Episodic` | 启用 | 启用 | 关闭 | `results/repomem_8_episodic/` |
| `RepoMem-Semantic` | 启用 | 关闭 | 启用 | `results/repomem_8_semantic/` |
| `RepoMem-Full` | 启用 | 启用 | 启用 | `results/repomem_8_full/` |

已有的 `LocAgent/results/locagent_batch_fixed/` 可以作为 baseline 参考，但建议复制或重新规范化到 `results/locagent_8_baseline/`，避免结果分散。

## 3. 必须遵守的数据泄漏规则

RepoMem 的 memory 必须只来自当前样本 `base_commit` 之前的历史。

对于每个 instance：

1. 读取 SWE-bench instance 的 `repo` 和 `base_commit`。
2. 在对应 repo 中使用 `base_commit` 之前的 commits 构建 memory。
3. 不允许使用 `base_commit` 之后的 commits。
4. 不允许从 SWE-bench 的 `patch` 字段向 agent prompt 泄漏答案。
5. 评测脚本可以读取 `patch` 字段作为 ground truth，但 agent 运行阶段不能读取。

检查点：

- `memory/episodic/<repo_name>/<instance_id>.jsonl` 中每条 commit 应来自 `base_commit` 之前。
- semantic summary 应读取 `base_commit` 版本下的文件内容。

## 4. 阶段 A：补齐 8 个样本的 memory

### A1. Episodic memory

目标：

为 8 个样本分别生成 episodic memory 和 BM25 索引。

目标产物：

```text
memory/episodic/astropy_astropy/<instance_id>.jsonl
memory/indexes/astropy_astropy/<instance_id>/commit_bm25/
```

每个 `jsonl` 至少包含：

- `sha`
- `message`
- `timestamp`
- `changed_files`
- `diff_summary`
- `full_diff`，可截断
- `linked_issue_id`，如果能解析到
- `linked_issue_text`，如果能获得；不能获得时允许为空

建议步骤：

1. 使用或修正 `scripts/build_episodic_memory.py`。
2. 不要只写死 `astropy__astropy-12907`。
3. 增加 8 样本列表。
4. 对每个样本调用：
   - `CommitMemoryBuilder(repo_path, max_commits=7000)`
   - `builder.build_memory(base_commit)`
   - `save_memory_to_jsonl(...)`
   - `CommitMemoryIndexer(...).build_index().save_index(...)`
5. 生成一个 summary 文件：

```text
results/repomem_memory_build/episodic_build_summary.json
```

summary 至少记录：

- instance_id
- commit_count
- memory_file
- index_dir
- build_status
- error，如果失败

验收标准：

- 8 个 instance 都有对应 episodic memory 文件。
- 每个 instance 都有 `commit_bm25` 索引。
- 若某个样本失败，必须在 summary 中说明失败原因。

### A2. Semantic memory

目标：

为 8 个样本分别生成 semantic memory 和 BM25 索引。

目标产物：

```text
memory/semantic/astropy_astropy/<instance_id>_semantic.jsonl
memory/indexes/astropy_astropy/<instance_id>/semantic_bm25/
```

论文设定是 top 200 active files + LLM summary。本阶段的小规模复现允许两级实现：

优先级 1，推荐：

- 使用 LLM 生成 summary。
- 每个样本选 top 200 active files。

优先级 2，资源不足时允许：

- 使用当前 `SummaryGenerator._generate_basic_summary()` 的规则摘要作为 fallback。
- 但必须在结果报告中明确写成 `semantic-basic-summary`，不能声称是完全论文版 LLM semantic memory。

建议步骤：

1. 使用或修正 `scripts/build_semantic_memory.py`。
2. 不要只处理 `astropy__astropy-12907`。
3. 对每个样本：
   - 读取该样本的 episodic memory。
   - 统计 changed files 频率。
   - 选择 top 200 active files。
   - 读取 `base_commit` 下的文件内容。
   - 生成 summary。
   - 建立 semantic BM25 索引。
4. 生成：

```text
results/repomem_memory_build/semantic_build_summary.json
```

summary 至少记录：

- instance_id
- selected_file_count
- summary_count
- summary_mode: `llm` 或 `basic`
- semantic_file
- index_dir
- build_status
- error，如果失败

验收标准：

- 8 个 instance 尽量都有 semantic memory。
- 每个成功 instance 至少有 1 个 summary。
- 如果因为文件不存在或 checkout 问题跳过文件，要记录跳过数量。

## 5. 阶段 B：正式接入 LocAgent agent 流程

当前 `repomem/` 工具是独立模块，不能只停留在脚本测试。必须让 LocAgent 在定位时能调用 memory 工具。

### B1. 增加运行参数

在 `LocAgent/auto_search_main.py` 增加参数：

```text
--repomem_mode
```

取值建议：

```text
none
episodic
semantic
full
```

语义：

- `none`：原始 LocAgent。
- `episodic`：启用 commit memory 工具。
- `semantic`：启用 file summary memory 工具。
- `full`：同时启用两类 memory 工具。

同时建议增加：

```text
--memory_base
```

默认：

```text
../memory
```

### B2. 工具注册接入点

当前 function calling 工具注册位置：

```text
LocAgent/util/runtime/function_calling.py
```

当前工具列表：

```python
ALL_FUNCTIONS = [
    'explore_tree_structure',
    'search_code_snippets',
    'get_entity_contents',
]
```

需要新增 RepoMem 工具名，建议统一使用论文风格名字：

```python
search_commit
examine_commit
search_summary
view_summary
```

注意：

- `repomem.tools.RepoMemTools` 里当前高层方法叫 `search_commits`、`examine_commits`、`search_files`、`examine_files`。
- 接入时需要做一层 wrapper，让 agent 看到的是论文式工具名。
- 不要直接把 `RepoMemTools` 对象暴露给 LLM。

建议 wrapper 映射：

| agent 工具名 | 内部调用 |
|---|---|
| `search_commit(query_list, top_k)` | `RepoMemTools.search_commits(query_list, top_k)` |
| `examine_commit(sha_list, display_issue)` | `RepoMemTools.examine_commits(sha_list, display_issue)` |
| `search_summary(query, top_k)` | `RepoMemTools.search_files(query, top_k)` |
| `view_summary(file_paths)` | `RepoMemTools.examine_files(file_paths)` |

### B3. 工具运行上下文

关键问题：RepoMemTools 需要知道当前 `instance_id`、`repo_name` 和 `memory_base`。

必须在每个 issue 初始化时设置当前 memory context。

建议实现方式：

1. 新增一个 runtime 模块，例如：

```text
LocAgent/util/runtime/repomem_tools.py
```

2. 提供：

```python
set_repomem_context(instance_id, repo_name, memory_base, mode)
search_commit(...)
examine_commit(...)
search_summary(...)
view_summary(...)
```

3. 在开始处理每个 bug 时调用 `set_repomem_context(...)`。

需要从 `auto_search_main.py` 中找到每个 bug 的处理入口。通常在 localize loop 或 `run_localize()` 中有当前 `bug` 或 `meta_data`。在这里设置 context。

### B4. function calling schema

如果使用 `--use_function_calling`，还需要给 LLM 提供工具 schema。

当前 schema 来自：

```text
LocAgent/util/runtime/content_tools.py
LocAgent/util/runtime/structure_tools.py
LocAgent/util/runtime/finish.py
LocAgent/util/runtime/function_calling.py
```

需要为 4 个 RepoMem 工具增加 schema，字段建议：

`search_commit`：

```json
{
  "query_list": ["string"],
  "top_k": 5
}
```

`examine_commit`：

```json
{
  "sha_list": ["string"],
  "display_issue": true
}
```

`search_summary`：

```json
{
  "query": "string",
  "top_k": 5
}
```

`view_summary`：

```json
{
  "file_paths": ["string"]
}
```

### B5. CodeAct/IPython 模式

LocAgent 也支持非 function calling 的 CodeAct/IPython 工具模式。

如果本阶段只使用 `--use_function_calling`，可以先只保证 function calling 路径可用。

但文档里必须注明：

```text
当前 RepoMem 8-sample reproduction 只验证 function calling 路径。
CodeAct 路径暂不作为验收目标。
```

## 6. 阶段 C：修改 prompt，引导 agent 使用 memory

如果只注册工具，模型可能不主动用。需要在 prompt 中明确告诉它何时使用。

主要 prompt 文件：

```text
LocAgent/util/prompts/pipelines/auto_search_prompt.py
```

建议加入一段 RepoMem instruction，根据 `repomem_mode` 动态拼接。

`episodic` 模式：

```text
Repository memory tools are available.
Use search_commit to find historical commits related to the issue keywords, affected modules, error messages, or suspicious files.
Use examine_commit to inspect relevant commits before deciding final locations.
Do not rely on memory alone; cross-check with current source code using search_code_snippets, get_entity_contents, and explore_tree_structure.
```

`semantic` 模式：

```text
Semantic file summary tools are available.
Use search_summary to find files whose historical responsibility matches the issue.
Use view_summary to inspect relevant file summaries.
Then verify against current code before finalizing locations.
```

`full` 模式：

```text
Both commit memory and semantic summary memory are available.
First use memory tools to get historical and semantic hints, then use current-code tools to verify.
Memory may be noisy, so final answers must be based on current source code evidence.
```

必须强调：

- memory 是辅助线索，不是最终答案。
- 最终输出仍然是需要修改的文件/函数位置。
- 不要输出 test files 作为最终修改位置，除非原任务明确是测试问题。

## 7. 阶段 D：运行 4 组实验

建议新建 PowerShell 脚本：

```text
scripts/run_repomem_8_baseline.ps1
scripts/run_repomem_8_episodic.ps1
scripts/run_repomem_8_semantic.ps1
scripts/run_repomem_8_full.ps1
```

公共参数建议：

```powershell
--dataset "princeton-nlp/SWE-bench_Verified"
--split "test"
--model "anthropic/qwen-max"
--localize
--merge
--eval_n_limit 8
--num_processes 1
--num_samples 1
--max_attempt_num 1
--use_function_calling
--simple_desc
--timeout 900
```

不同实验只变：

```powershell
--repomem_mode "none"
--output_folder "..\results\locagent_8_baseline"
```

```powershell
--repomem_mode "episodic"
--memory_base "..\memory"
--output_folder "..\results\repomem_8_episodic"
```

```powershell
--repomem_mode "semantic"
--memory_base "..\memory"
--output_folder "..\results\repomem_8_semantic"
```

```powershell
--repomem_mode "full"
--memory_base "..\memory"
--output_folder "..\results\repomem_8_full"
```

每组实验必须保留：

```text
args.json
localize.log
loc_outputs.jsonl
loc_trajs.jsonl
merged_loc_outputs_mrr.jsonl
```

如果某组失败，不要覆盖已有结果。新建带时间戳的输出目录或保存失败日志。

## 8. 阶段 E：统一评测

使用或扩展：

```text
scripts/evaluate_localization.py
```

对 4 个输出目录分别评测。

每组产物：

```text
results/<experiment>/eval_summary.json
results/<experiment>/eval_instances.csv
```

评测字段至少包含：

- `instance_id`
- `repo`
- `ground_truth_files`
- `predicted_files_top1`
- `predicted_files_top3`
- `predicted_files_top5`
- `acc@1`
- `acc@3`
- `acc@5`
- `tool_calls`
- `memory_tool_calls`
- `token_usage`
- `cost`
- `failure_type`

需要新增或补充 `memory_tool_calls` 统计：

统计以下工具调用次数：

```text
search_commit
examine_commit
search_summary
view_summary
```

如果从 `loc_trajs.jsonl` 中无法稳定解析 token/cost，可以留空，但要在报告里说明。

## 9. 阶段 F：对比报告

新建：

```text
docs/10_repomem_8sample_results.md
```

报告结构：

1. 实验设置
2. 8 样本列表
3. memory 构建情况
4. 四组结果总表
5. 每个样本的逐例对比
6. memory 工具调用分析
7. 成功案例分析
8. 失败案例分析
9. 与原论文差距
10. 下一步改进

四组结果总表模板：

| Method | Acc@1 | Acc@3 | Acc@5 | Avg memory calls | Notes |
|---|---:|---:|---:|---:|---|
| LocAgent | | | | 0 | baseline |
| RepoMem-Episodic | | | | | commit memory only |
| RepoMem-Semantic | | | | | summary memory only |
| RepoMem-Full | | | | | both memories |

逐例对比模板：

| Instance | GT files | LocAgent top5 | Episodic top5 | Semantic top5 | Full top5 | Best method | Notes |
|---|---|---|---|---|---|---|---|

必须诚实写清楚：

- 如果 semantic summary 是 basic fallback，不要称为论文级 LLM summary。
- 如果只在 astropy 8 样本上跑，不要泛化到完整 SWE-bench Verified。
- 如果 RepoMem 没有提升，也要如实报告，并分析 memory 噪声、工具调用不足、prompt 不够强、样本太少等原因。

## 10. 验收标准

本任务只有在以下条件全部满足时，才算完成。

代码层面：

- `auto_search_main.py` 支持 `--repomem_mode`。
- function calling 路径能识别并执行 RepoMem 工具。
- 每个 issue 都能正确设置当前 memory context。
- `repomem_mode=none` 时行为与原始 LocAgent 一致。
- `repomem_mode=episodic/semantic/full` 时对应工具可用。

memory 层面：

- 8 个样本均尝试构建 episodic memory。
- 8 个样本均尝试构建 semantic memory。
- 构建失败要有明确日志和 summary。

实验层面：

- 完成 4 组实验，或明确说明某组失败原因。
- 每组都有 `loc_outputs.jsonl` 和评测结果。
- 不能只提供工具单测结果。

报告层面：

- `docs/10_repomem_8sample_results.md` 完成。
- 明确说明当前复现规模和原论文差距。
- 明确说明 RepoMem 是否相对 LocAgent 有提升。

## 11. 建议执行顺序

不要一上来就跑 4 组完整实验。按下面顺序推进：

1. 跑通一个样本的 `repomem_mode=episodic`。
2. 检查日志中是否真的出现 `search_commit` 或 `examine_commit`。
3. 跑通一个样本的 `repomem_mode=semantic`。
4. 检查日志中是否真的出现 `search_summary` 或 `view_summary`。
5. 跑通一个样本的 `repomem_mode=full`。
6. 确认三个 RepoMem 模式都能输出定位结果。
7. 扩展到 8 个样本。
8. 跑 4 组完整实验。
9. 统一评测。
10. 写对比报告。

## 12. 常见失败点和处理方式

### 12.1 工具注册了但模型不用

处理：

- 加强 prompt。
- 在任务开头明确建议先使用 memory。
- 对 `RepoMem-Full` 模式要求至少尝试一次 memory search。

但不要强迫最终答案依赖 memory。memory 只是辅助。

### 12.2 memory 文件缺失

处理：

- 工具调用时返回清楚错误，而不是让主流程崩溃。
- 在实验 summary 中记录该 instance memory unavailable。

### 12.3 semantic summary 质量低

处理：

- 先记录为 `basic summary`。
- 不要和论文 LLM summary 直接等价。
- 如果时间允许，再接入 LLM 生成。

### 12.4 多文件样本仍失败

重点关注：

```text
astropy__astropy-13398
```

这是多文件 ground truth。分析 RepoMem 是否能通过历史 co-change 或 semantic summary 提醒更多相关文件。

### 12.5 WCS 样本仍失败

重点关注：

```text
astropy__astropy-13579
```

检查 memory 是否能找到 `astropy/wcs/wcsapi/wrappers/sliced_wcs.py` 相关历史。

## 13. 最终交付清单

代码：

```text
LocAgent/auto_search_main.py
LocAgent/util/runtime/function_calling.py
LocAgent/util/runtime/repomem_tools.py
LocAgent/util/prompts/pipelines/auto_search_prompt.py
repomem/*.py
scripts/build_episodic_memory.py
scripts/build_semantic_memory.py
scripts/run_repomem_8_*.ps1
scripts/evaluate_localization.py
```

memory：

```text
memory/episodic/astropy_astropy/
memory/semantic/astropy_astropy/
memory/indexes/astropy_astropy/
```

结果：

```text
results/locagent_8_baseline/
results/repomem_8_episodic/
results/repomem_8_semantic/
results/repomem_8_full/
results/repomem_memory_build/
```

文档：

```text
docs/10_repomem_8sample_results.md
```

## 14. 组会汇报口径

如果完成本计划，可以这样汇报：

```text
我在已有 LocAgent baseline 的基础上，完成了 8 个 astropy 样本的小规模 RepoMem 复现。
具体做法是为每个样本构建 base_commit 之前的 episodic commit memory 和 semantic file memory，
然后把 SearchCommit、ExamineCommit、SearchSummary、ViewSummary 四个 memory 工具接入 LocAgent agent 流程。
最后我分别跑了 LocAgent、RepoMem-Episodic、RepoMem-Semantic 和 RepoMem-Full 四组实验，
用统一的 Acc@1、Acc@3、Acc@5 指标做对比。
当前实验规模仍小于论文的完整 SWE-bench Verified 500 样本，因此结论主要用于验证机制和观察趋势。
```
