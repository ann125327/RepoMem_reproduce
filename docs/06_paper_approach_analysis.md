# 论文做法分析：如何避免大文件传输

## 论文的方案

### 方法1：动态下载代码库（推荐）

**核心机制：**
```python
python dependency_graph/batch_build_graph.py \
    --dataset 'princeton-nlp/SWE-bench_Verified' \
    --download_repo \  # 关键！运行时下载
    --num_processes 50
```

**优势：**
- ✅ 不需要预先存储所有代码库
- ✅ 索引按需构建
- ✅ 代码库可以删除，只保留索引

**流程：**
1. 读取数据集，获取所有instance_id
2. 对每个instance：
   - 从GitHub克隆代码库（特定commit）
   - 构建图索引和BM25索引
   - 保存索引文件
   - 删除代码库（可选）
3. 最终只有索引文件，没有源代码

### 方法2：按需构建索引（更优）

**关键代码特性：**
```python
# auto_search_main.py 中的逻辑
persist_path = os.path.join(GRAPH_INDEX_DIR, instance["instance_id"])
if os.path.exists(persist_path):
    # 使用已有索引
    load_index(persist_path)
else:
    # 动态构建索引
    repo_dir = setup_repo(instance_data)
    build_index(repo_dir, persist_path)
```

**这意味着：**
- ✅ 只需要打包代码和配置
- ✅ 索引在目标机器上按需构建
- ✅ 首次运行时会自动构建索引
- ✅ 后续运行复用已有索引

## 推荐给您的方案

### 方案A：轻量级打包（推荐）⭐

**只打包必要文件：**

```bash
# 需要打包的内容（约50MB）
LocAgent/
├── code/                    # 全部代码
├── requirements.txt         # 依赖
├── auto_search_main.py      # 主脚本
├── scripts/                 # 运行脚本
└── README.md

# 数据集（约2MB）
hf_dataset_temp/data/test-00000-of-00001.parquet

# 配置文件（几KB）
run_batch_with_api.sh
scripts/evaluate_localization.py

# 总计：约50MB，非常小！
```

**不需要打包：**
- ❌ index_data/（19GB）- 让老师机器上动态构建
- ❌ results/（几百MB）- 运行后生成

**老师那边的操作：**
```bash
# 1. 解压代码包（50MB）
tar -xzf locagent_code.tar.gz

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export ANTHROPIC_API_KEY="xxx"
export LOCAL_DATASET_PATCH=true

# 4. 运行评估（首次会自动构建索引）
python auto_search_main.py --localize --merge \
    --model anthropic/qwen-max \
    --dataset princeton-nlp/SWE-bench_Verified \
    --num_samples 500 \
    --download_repo \  # 自动下载代码库
    --num_processes 30
```

**优势：**
- ✅ 打包文件极小（50MB）
- ✅ 可以轻松传输
- ✅ 索引在目标机器构建，无需传输
- ✅ 代码库自动下载，用完可删

### 方案B：部分预构建索引（折中）

**只预构建10个示例的索引：**

```bash
# 构建10个实例的索引
python dependency_graph/batch_build_graph.py \
    --dataset 'princeton-nlp/SWE-bench_Verified' \
    --num_samples 10 \
    --download_repo

# 打包内容（约350MB = 33MB×10 + 代码50MB）
- 代码：50MB
- 10个索引：330MB
- 数据集：2MB
总计：约350MB
```

**优势：**
- ✅ 打包大小适中（350MB）
- ✅ 可以验证流程
- ✅ 后续490个索引动态构建

### 方案C：全量索引（不推荐）

**打包全部19GB索引：**
- ❌ 文件太大，传输困难
- ❌ 可能超过邮件/网盘限制
- ❌ 不必要，可以动态构建

## 实施建议

### 最佳实践（方案A）：

**您这边：**
```bash
# 1. 准备代码包（约50MB）
tar -czf locagent_package.tar.gz \
    LocAgent/*.py \
    LocAgent/plugins \
    LocAgent/util \
    LocAgent/dependency_graph \
    LocAgent/scripts \
    LocAgent/requirements.txt \
    LocAgent/README.md \
    hf_dataset_temp/data/test-00000-of-00001.parquet \
    scripts/evaluate_localization.py \
    run_batch_with_api.sh

# 2. 准备运行说明文档
# 见下面的"老师那边操作指南"
```

**老师那边：**
```bash
# 1. 解压（几秒钟）
tar -xzf locagent_package.tar.gz

# 2. 创建虚拟环境（几分钟）
conda create -n locagent python=3.11
conda activate locagent
pip install -r requirements.txt

# 3. 设置API密钥
export ANTHROPIC_API_KEY="老师的密钥"

# 4. 运行评估（首次会自动下载代码库并构建索引）
python auto_search_main.py --localize --merge \
    --model anthropic/qwen-max \
    --dataset princeton-nlp/SWE-bench_Verified \
    --num_samples 500 \
    --download_repo \
    --num_processes 30 \
    --use_function_calling \
    --simple_desc
```

### 时间和成本分析

**老师那边的总时间：**
1. 环境配置：10分钟
2. 首次索引构建：2-4小时（一次性）
3. 评估运行：3-5小时
4. **总计：6-10小时**

**API费用：**
- 仍然约$600-900（与之前估算一致）

**磁盘空间：**
- 运行时需要：约20GB（索引）+ 10GB（临时代码库）
- 运行后可以删除代码库，只保留索引和结果

## 技术细节说明

### 索引构建流程

```python
# 伪代码说明
for instance in dataset:
    if 索引存在:
        加载索引
    else:
        # 1. 克隆代码库到临时目录
        repo_dir = clone_repo(instance)
        
        # 2. 解析代码，构建图索引
        graph_index = build_graph(repo_dir)
        
        # 3. 构建BM25索引
        bm25_index = build_bm25(repo_dir)
        
        # 4. 保存索引（持久化）
        save_index(graph_index, f"{instance_id}.pkl")
        save_index(bm25_index, f"{instance_id}_bm25")
        
        # 5. 清理临时代码库（可选）
        # rm -rf repo_dir
```

### 为什么可以动态构建

**关键点：**
1. SWE-bench数据集包含每个instance的：
   - repo名称
   - base_commit
   - patch信息

2. `setup_repo()`函数会：
   ```python
   def setup_repo(instance_data):
       # 1. 从GitHub克隆代码库
       git clone https://github.com/{repo}
       # 2. 切换到特定commit
       git checkout {base_commit}
       # 3. 返回代码库路径
       return repo_path
   ```

3. 索引构建器会：
   ```python
   def build_graph(repo_path):
       # 解析所有Python文件
       # 提取类、函数、导入关系
       # 构建依赖图
       # 返回图索引
   ```

**所以：**
- ✅ 不需要预先存储代码库
- ✅ 可以随时从GitHub下载
- ✅ 索引可以重建，不是唯一资源

## 总结

**推荐方案：轻量级打包（方案A）**

**原因：**
1. 打包文件小（50MB），易于传输
2. 流程简单，老师操作方便
3. 索引按需构建，无需预先生成
4. 与论文推荐做法一致

**需要提供给老师的：**
1. ✅ 代码包（50MB）
2. ✅ 运行脚本和说明
3. ✅ API密钥配置指南
4. ✅ 环境要求说明

**不需要提供：**
1. ❌ 索引文件（19GB）
2. ❌ 代码库源码（动态下载）
3. ❌ 结果文件（运行生成）

**预期效果：**
- 您：准备50MB的代码包，10分钟
- 老师：解压+配置+运行，6-10小时完成全部
- 成本：API费用$600-900
