# RepoMem Reproduction Plan

## 1. 本次复现目标
在 LocAgent 官方代码基础上，复现论文 **Improving Code Localization with Repository Memory** 的核心机制与主要实验结论；如果官方 RepoMem 代码不可用，则实现一个 faithful reproduction：保留 LocAgent 的定位流程，只补上论文描述的 episodic memory 和 semantic memory 工具。

## 2. 最小复现范围
1. 跑通 LocAgent baseline。
2. 构建 episodic memory。
3. 构建 semantic memory。
4. 接入 `SearchCommit / ExamineCommit / ViewSummary / SearchSummary`。
5. 在一个小规模 SWE-bench-verified 子集上完成 Acc@1/3/5 评估。

## 3. 完整复现范围
1. 在 SWE-bench-verified 上复现实验。
2. 在 SWE-bench-live 上做对照验证。
3. 复现三种记忆设置：only episodic、only semantic、full RepoMem。
4. 复现仓库分组分析、检索方式分析、下游 resolve rate 与 token cost 分析。
5. 在失败样本上做原因分析，并提出改进方法。

## 4. 预计成本
主要成本来自：

- 仓库拉取与图构建。
- 历史提交扫描与 memory 索引构建。
- LLM 调用，尤其是摘要生成、检索决策和定位推理。

若只做小规模验证，成本可控；若跑完整基准，API 成本和时间都会明显上升。

## 5. 预计风险
1. 官方 RepoMem 代码不可用，只能按论文描述自己接。
2. SWE-bench 仓库历史可能不完整，影响 episodic memory 质量。
3. issue 与 commit 的显式关联可能稀疏，导致 memory 检索召回下降。
4. semantic summary 生成质量依赖模型。
5. 小样本结果波动大，可能不足以稳定复现论文数值。

## 6. 每阶段交付物
### 阶段 0
- `docs/00_paper_summary.md`
- `docs/01_reproduction_plan.md`

### 阶段 1
- `docs/02_locagent_code_reading.md`
- `docs/03_environment_setup.md`
- `results/locagent_verified_small/`
- `logs/locagent_small_run.log`

### 阶段 2
- `scripts/evaluate_localization.py`
- `docs/04_evaluation_protocol.md`
- `results/locagent_verified_small/eval_summary.json`
- `results/locagent_verified_small/eval_instances.csv`

### 阶段 3
- `repomem/episodic_memory.py`
- `repomem/index_commit_memory.py`
- `repomem/tools.py`
- `memory/episodic/<repo_name>/<instance_id>.jsonl`
- `memory/indexes/<repo_name>/<instance_id>/commit_bm25/`
- `docs/05_episodic_memory.md`

### 阶段 4
- `repomem/semantic_memory.py`
- `repomem/index_summary_memory.py`
- `memory/semantic/<repo_name>/<instance_id>.jsonl`
- `memory/indexes/<repo_name>/<instance_id>/summary_bm25/`
- `docs/06_semantic_memory.md`

### 阶段 5
- `docs/07_repomem_experiments.md`
- `results/repomem_full/`
- `results/repomem_ablation/`
- `docs/08_failure_analysis.md`

### 阶段 6
- `report/main.tex`
- `report/figures/`
- `report/tables/`

## 7. 当前策略
先以 LocAgent 为 baseline 跑通最小闭环，再按论文机制补齐 memory。这样即使官方 RepoMem 缺失，也能做出一个与论文方向一致、机制清晰、可解释的复现版本。

