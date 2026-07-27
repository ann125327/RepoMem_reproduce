你是一名严谨的科研复现 Agent。我要复现论文：

Title: Improving Code Localization with Repository Memory
Baseline/核心方法：RepoMem，基于 LocAgent 改进代码定位任务
目标：完成一个课程/科研复现项目，最终交付 LaTeX 实验报告，包括实验设定、实验结果、实验分析、失败原因分析、改进方法和局限性分析。

请你严格按阶段执行，不要跳步。每个阶段完成后都要产出明确文件、日志或中间结论。

====================
阶段 0：项目理解与复现目标确认
====================

任务：
1. 阅读论文 Improving Code Localization with Repository Memory。
2. 总结论文的核心问题、方法、实验设定和主要结论。
3. 明确该论文和 LocAgent 的关系：
   - LocAgent 是直接 baseline。
   - RepoMem 是在 LocAgent 基础上加入 repository memory。
4. 明确本次复现的最小可行目标和扩展目标。

请输出：
- docs/00_paper_summary.md
- docs/01_reproduction_plan.md

要求：
00_paper_summary.md 至少包含：
- 论文解决什么问题
- 为什么 code localization 很重要
- LocAgent 的做法
- LocAgent 的局限
- RepoMem 的核心 motivation
- RepoMem 的两个 memory：
  - episodic memory
  - semantic memory
- RepoMem 新增了哪些工具
- 论文使用的数据集
- 评价指标
- 主要实验结果
- 消融实验结论
- 论文承认的局限性

01_reproduction_plan.md 至少包含：
- 本次复现目标
- 最小复现范围
- 完整复现范围
- 预计成本
- 预计风险
- 每阶段交付物

注意：
如果官方 RepoMem 代码不可用，请不要停止。你需要基于 LocAgent 官方代码实现一个 faithful reproduction，即尽量按照论文描述复现核心机制。

====================
阶段 1：环境准备与 LocAgent 跑通
====================

任务：
1. 克隆并检查 LocAgent 官方代码库。
2. 阅读 README、requirements、主要入口文件。
3. 建立 Python 环境。
4. 安装依赖。
5. 跑通 LocAgent 在 SWE-bench-verified 上的小规模样本。
6. 保存运行日志、配置和输出。

推荐命令参考：

git clone https://github.com/gersteinlab/LocAgent.git
cd LocAgent
conda create -n locagent python=3.12
conda activate locagent
pip install -r requirements.txt

构建 dependency graph：

python dependency_graph/batch_build_graph.py \
  --dataset 'princeton-nlp/SWE-bench_Verified' \
  --split 'test' \
  --num_processes 4 \
  --download_repo

小规模运行：

python auto_search_main.py \
  --dataset 'princeton-nlp/SWE-bench_Verified' \
  --split 'test' \
  --model '<your_model_name>' \
  --localize \
  --merge \
  --output_folder results/locagent_verified_small \
  --eval_n_limit 30 \
  --num_processes 4 \
  --use_function_calling \
  --simple_desc

请根据实际代码库参数修正命令，不要机械照抄。如果参数不兼容，先阅读源码并修改命令。

请输出：
- docs/02_locagent_code_reading.md
- docs/03_environment_setup.md
- results/locagent_verified_small/
- logs/locagent_small_run.log

要求：
02_locagent_code_reading.md 包含：
- LocAgent 的主入口文件
- 数据加载流程
- dependency graph 构建流程
- agent 可用工具
- localization 输出格式
- evaluation 脚本位置

03_environment_setup.md 包含：
- 操作系统
- Python 版本
- 依赖安装方式
- 使用模型
- API 配置方式，注意不要泄露 key
- 成功运行的命令
- 遇到的问题和解决办法

====================
阶段 2：建立评估脚本
====================

任务：
1. 找到 LocAgent 的 evaluation 代码。
2. 确认 file-level localization 的 ground truth 文件来源。
3. 实现或整理一个统一评估脚本。
4. 输出每个样本的：
   - instance_id
   - repo
   - problem_statement
   - ground_truth_files
   - predicted_files_top1
   - predicted_files_top3
   - predicted_files_top5
   - acc@1
   - acc@3
   - acc@5
   - tool_calls
   - token usage
   - cost，如果可得
   - failure_type，初始可为空

评价指标定义：
对于每个 issue，如果 top-k predicted files 覆盖所有 ground-truth modified files，则 Acc@k = 1，否则为 0。

请输出：
- scripts/evaluate_localization.py
- results/locagent_verified_small/eval_summary.json
- results/locagent_verified_small/eval_instances.csv
- docs/04_evaluation_protocol.md

要求：
04_evaluation_protocol.md 包含：
- Acc@1 / Acc@3 / Acc@5 的定义
- 为什么使用 file-level localization
- 与论文评价方式是否一致
- 如果不一致，说明差异

====================
阶段 3：复现 RepoMem 的 Episodic Memory
====================

任务：
实现 RepoMem 的 episodic memory。

论文思路：
对于每个 benchmark instance，使用 base_commit 之前的历史 commits 构建 memory。默认最多使用 7000 个历史 commits。每条 commit memory 至少包含：
- commit sha
- commit message
- commit timestamp
- changed files
- diff summary 或完整 diff
- linked issue id，如果 commit message 包含 Fixes #id / Closes #id 等模式
- linked issue text，如果可以获得

实现步骤：
1. 从 SWE-bench instance 中读取 repo 和 base_commit。
2. 确保对应 repo 已经下载。
3. 使用 git log 获取 base_commit 之前的 commits。
4. 最多截取最近 7000 条。
5. 解析 commit message。
6. 提取 changed files。
7. 提取 diff 或 diff summary。
8. 建立 BM25 检索索引。
9. 实现两个工具：
   - SearchCommit(query_list, top_k)
   - ExamineCommit(sha_list, display_issue)

请输出：
- repomem/episodic_memory.py
- repomem/index_commit_memory.py
- repomem/tools.py
- memory/episodic/<repo_name>/<instance_id>.jsonl
- memory/indexes/<repo_name>/<instance_id>/commit_bm25/
- docs/05_episodic_memory.md

要求：
SearchCommit：
- 输入 query_list 和 top_k
- 对 query_list 中的 query 分别检索 commit message / changed files / diff summary
- 返回 top-k commit sha、message、score、changed files、timestamp

ExamineCommit：
- 输入 sha_list 和 display_issue
- 返回 commit message、changed files、diff summary
- 如果 display_issue=True 且能找到 linked issue，则返回 issue 内容

注意：
如果无法访问 GitHub issue API，则先只保留 linked issue id，不强制抓 issue text。
如果完整 diff 太大，保存 diff summary 或限制 token 长度。

====================
阶段 4：复现 RepoMem 的 Semantic Memory
====================

任务：
实现 RepoMem 的 semantic memory。

论文思路：
对每个 repo，根据历史 commit 修改频率选择 top 200 active files，然后用 LLM 为每个文件生成 semantic summary。之后通过 BM25 检索 summary，并提供查看工具。

实现步骤：
1. 基于 episodic memory 统计每个文件被修改次数。
2. 选出 top 200 active files。
3. 读取这些文件在 base_commit 版本下