# Improving Code Localization with Repository Memory: Paper Summary

## 1. 论文解决什么问题
论文研究的是 **code localization**：给定 issue 描述和仓库版本，自动定位最可能需要修改的源文件。作者关注的是，现有定位智能体虽然能利用代码结构和检索工具，但往往仍像“每次从零开始”，缺少对仓库历史知识的长期记忆。

## 2. 为什么 code localization 很重要
code localization 是很多仓库级软件工程任务的前置步骤，尤其是 bug 修复、patch 生成、重构和维护。定位不准会直接导致后续修改范围扩大、上下文浪费、错误补丁甚至修复失败。

## 3. LocAgent 的做法
LocAgent 是本文的直接 baseline。它把仓库解析为异构图，并在 ReAct 式交互中使用工具逐步搜索、遍历和读取代码实体，核心是利用结构化代码关系帮助 LLM 定位候选文件。

## 4. LocAgent 的局限
LocAgent 仍把每个问题当作新任务处理，没有显式利用仓库历史。论文指出，它在一些样本中能追踪到初始实体，但难以继续深入推理到真正的错误源；当仓库历史中其实已有相似修复模式或文件职责信息时，LocAgent 也不会主动使用这些先验。

## 5. RepoMem 的核心 motivation
RepoMem 的动机是：真实开发者不会只看当前仓库快照，而会利用仓库历史修复记录和长期积累的“文件功能知识”。论文尝试把这种 repository memory 显式喂给定位智能体，让它少走弯路。

## 6. RepoMem 的两个 memory
### Episodic memory
情节记忆，来自仓库过去的提交历史。每条记忆通常包含 commit SHA、commit message、timestamp、changed files、diff summary，必要时还会带 linked issue 信息。它负责回答“以前类似问题是怎么修的”。

### Semantic memory
语义记忆，针对仓库中最活跃的文件生成文件级摘要，概括文件职责、核心功能和常见用途。它负责回答“这个文件通常是干什么的”。

## 7. RepoMem 新增了哪些工具
论文在 LocAgent 基础上新增四个 memory 工具：

1. `SearchCommit(query, top_k)`：按查询词检索历史提交。
2. `ExamineCommit(id)`：查看某条提交的完整上下文。
3. `ViewSummary(file_name)`：查看某个文件的语义摘要。
4. `SearchSummary(query, top_k)`：在文件摘要集合中做搜索。

## 8. 论文使用的数据集
论文在两个基准上评估：

1. **SWE-bench-verified**：来自 12 个仓库，共 500 个示例。
2. **SWE-bench-live**：由 lite 和 verified 的交集构建，再过滤掉需要修改超过 5 个文件的样本，共 130 个示例，来自 62 个仓库。

## 9. 评价指标
主要指标是 **file-level Accuracy@k**，即预测的前 k 个文件是否完全覆盖真实修改文件。论文还报告了下游 resolve rate，并分析了 token cost 与运行开销。

## 10. 主要实验结果
在 SWE-bench-verified 上：

- LocAgent: Acc@1 64.8, Acc@3 70.4, Acc@5 71.6
- RepoMem only episodic: 67.8, 72.4, 74.3
- RepoMem only semantic: 65.0, 71.0, 72.8
- RepoMem full: **68.6, 74.5, 76.5**

在 SWE-bench-live 上：

- LocAgent: 59.2, 60.8, 63.1
- RepoMem only episodic: 60.0, 61.5, 64.6
- RepoMem only semantic: 56.9, 61.5, 63.9
- RepoMem full: **60.8, 63.9, 66.2**

结论是 RepoMem 在两个基准上都优于 LocAgent，且完整版本最好。

## 11. 消融实验结论
消融结果表明：

- 仅 episodic memory 就能带来稳定增益。
- 仅 semantic memory 也有效，但通常略弱于 episodic。
- 两者结合最好，说明历史修复模式和文件职责摘要是互补信息。
- 更丰富提交历史的仓库收益更明显；历史稀疏仓库提升可能有限甚至受噪声影响。
- BM25 + LLM tokenizer 的检索方式优于普通空格分词 BM25。

## 12. 论文承认的局限性
论文明确承认：

- 对提交历史和 issue 链接质量有依赖，链路缺失会影响 episodic memory。
- 历史稀疏仓库里，memory 可能不够有用，甚至分散注意力。
- 固定窗口和静态记忆构建未必最优。
- 检索噪声会带来额外 token 成本和推理负担。

## 13. 与 LocAgent 的关系
LocAgent 是直接 baseline。RepoMem 不是替代 LocAgent，而是在 LocAgent 的工具框架上加入 repository memory，让 agent 能利用仓库长期历史进行更像人类开发者的定位。

