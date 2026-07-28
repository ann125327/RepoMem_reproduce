#!/bin/bash
# 打包LocAgent代码给老师

PACKAGE_NAME="locagent_package_$(date +%Y%m%d).tar.gz"

echo "开始打包LocAgent代码..."

# 创建临时目录
TMP_DIR="locagent_package_$(date +%s)"
mkdir -p "$TMP_DIR"

# 复制必要文件
echo "复制LocAgent代码..."
cp -r LocAgent/*.py "$TMP_DIR/" 2>/dev/null || true
cp -r LocAgent/plugins "$TMP_DIR/" 
cp -r LocAgent/util "$TMP_DIR/"
cp -r LocAgent/dependency_graph "$TMP_DIR/"
cp -r LocAgent/scripts "$TMP_DIR/"
cp LocAgent/requirements.txt "$TMP_DIR/"
cp LocAgent/README.md "$TMP_DIR/"

# 复制评估脚本和数据集
echo "复制评估脚本和数据集..."
mkdir -p "$TMP_DIR/hf_dataset_temp/data"
cp hf_dataset_temp/data/test-00000-of-00001.parquet "$TMP_DIR/hf_dataset_temp/data/"
cp scripts/evaluate_localization.py "$TMP_DIR/"

# 创建运行脚本
cat > "$TMP_DIR/run_full_evaluation.sh" << 'RUNSCRIPT'
#!/bin/bash
# SWE-bench Verified完整评估脚本

# 设置环境变量
export LOCAL_DATASET_PATCH=true
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your_api_key_here}"

# 创建必要的目录
mkdir -p index_data/SWE-bench_Verified/graph_index_v2.3
mkdir -p index_data/SWE-bench_Verified/BM25_index
mkdir -p results/locagent_full_500

export GRAPH_INDEX_DIR=index_data/SWE-bench_Verified/graph_index_v2.3
export BM25_INDEX_DIR=index_data/SWE-bench_Verified/BM25_index

echo "开始LocAgent完整评估（500个实例）..."
echo "预计时间：6-10小时（首次运行需构建索引）"
echo "预计费用：\$600-900"

# 运行评估
python auto_search_main.py \
    --localize \
    --merge \
    --model anthropic/qwen-max \
    --dataset princeton-nlp/SWE-bench_Verified \
    --num_samples 500 \
    --output_folder results/locagent_full_500 \
    --max_attempt_num 1 \
    --num_processes 30 \
    --use_function_calling \
    --simple_desc

# 运行评估脚本
echo "生成评估报告..."
python scripts/evaluate_localization.py \
    results/locagent_full_500/loc_outputs.jsonl \
    hf_dataset_temp/data/test-00000-of-00001.parquet \
    results/locagent_full_500

echo "评估完成！"
echo "结果位置：results/locagent_full_500/"
RUNSCRIPT

chmod +x "$TMP_DIR/run_full_evaluation.sh"

# 创建说明文档
cat > "$TMP_DIR/README_FOR_TEACHER.md" << 'README'
# LocAgent完整评估包 - 使用说明

## 文件内容

本压缩包包含运行LocAgent在SWE-bench Verified数据集（500实例）上所需的所有代码和配置。

**包含文件：**
- LocAgent源代码
- 评估脚本
- SWE-bench Verified数据集（本地parquet）
- 运行脚本

**不包含（会在运行时自动生成）：**
- 图索引（19GB）- 首次运行时自动构建
- BM25索引（2.5GB）- 首次运行时自动构建
- GitHub代码库 - 动态下载

## 环境要求

**硬件：**
- CPU: 建议30+核心（用于并行处理）
- 内存: 建议64GB（最少32GB）
- 磁盘: 至少30GB可用空间
  - 索引文件：约20GB
  - 临时代码库：约10GB
  - 结果文件：约1GB

**软件：**
- Python 3.11+
- Git
- Conda（推荐）

## 安装步骤

1. **解压代码包**
   ```bash
   tar -xzf locagent_package_*.tar.gz
   cd locagent_package
   ```

2. **创建虚拟环境**
   ```bash
   conda create -n locagent python=3.11
   conda activate locagent
   pip install -r requirements.txt
   ```

3. **设置API密钥**
   ```bash
   export ANTHROPIC_API_KEY="your_alibaba_cloud_api_key"
   ```
   
   **获取API密钥：**
   - 访问：https://dashscope.aliyun.com/
   - 注册并获取API Key
   - 或使用其他Anthropic兼容的API

4. **运行评估**
   ```bash
   ./run_full_evaluation.sh
   ```

## 时间和成本

**预计时间：**
- 环境配置：10分钟
- 首次索引构建：2-4小时
- 评估运行：3-5小时
- **总计：6-10小时**

**API费用：**
- 使用Qwen-Max：约$600-900 (¥4,000-6,500)
- 使用Claude-3.5-Sonnet：约$700-1,000

**监控建议：**
- 设置API费用监控和限额
- 定期检查日志文件
- 可以中断后继续（支持断点续传）

## 输出结果

**结果文件位置：** `results/locagent_full_500/`

**主要文件：**
- `loc_outputs.jsonl` - 定位结果
- `loc_trajs.jsonl` - 执行轨迹
- `eval_summary.json` - 评估摘要
- `eval_instances.csv` - 详细结果

**评估指标：**
- Acc@1: Top-1准确率
- Acc@3: Top-3准确率
- Acc@5: Top-5准确率

## 故障排除

**问题1：索引构建失败**
- 检查磁盘空间（需要30GB）
- 确保可以访问GitHub
- 检查网络连接

**问题2：API调用失败**
- 检查API密钥是否正确
- 检查API配额是否充足
- 查看日志文件了解详细错误

**问题3：内存不足**
- 减少并行进程数（修改`--num_processes`）
- 增加系统内存
- 分批处理（如分5次，每次100个实例）

## 分批运行（可选）

如果资源有限，可以分批运行：

```bash
# 第一批：实例1-100
python auto_search_main.py --num_samples 100 --eval_n_limit 0 --output_folder results/batch1

# 第二批：实例101-200
python auto_search_main.py --num_samples 100 --eval_n_limit 100 --output_folder results/batch2

# ...以此类推
```

## 联系支持

如遇问题，请查看：
- 日志文件：`results/locagent_full_500/localize.log`
- LocAgent GitHub: https://github.com/gersteinlab/LocAgent
- 论文：https://arxiv.org/abs/2503.09089
README

# 打包
echo "创建压缩包..."
tar -czf "$PACKAGE_NAME" "$TMP_DIR"

# 清理临时目录
rm -rf "$TMP_DIR"

# 显示结果
echo ""
echo "✅ 打包完成！"
echo ""
echo "文件名: $PACKAGE_NAME"
echo "大小: $(du -h "$PACKAGE_NAME" | cut -f1)"
echo ""
echo "内容："
echo "  - LocAgent源代码"
echo "  - 评估脚本"
echo "  - SWE-bench Verified数据集"
echo "  - 运行脚本和说明文档"
echo ""
echo "下一步："
echo "  1. 将 $PACKAGE_NAME 发送给老师"
echo "  2. 老师解压后按照 README_FOR_TEACHER.md 操作"
