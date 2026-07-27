# Environment Setup Notes

## Environment
- **Operating System**: Windows 11 Home China 10.0.26200
- **Python**: 3.11.15 (from conda env `locagent`, used via venv)
- **venv**: `C:\Users\18199\Desktop\codingAgent\stage2\venv_locagent_py311`
- **Working Directory**: `C:\Users\18199\Desktop\codingAgent\stage2`
- **LocAgent**: `C:\Users\18199\Desktop\codingAgent\stage2\LocAgent`

## Model Configuration
- **Model**: `qwen-max` via DashScope (Anthropic-compatible endpoint)
- **LiteLLM Format**: `anthropic/qwen-max`
- **API Endpoint**: `https://dashscope.aliyuncs.com/apps/anthropic`
- **API Key**: Set via `ANTHROPIC_API_KEY` environment variable (not committed)
- **Env Scripts**:
  - `LocAgent/scripts/env/set_env.sh` (bash/Git Bash)
  - `LocAgent/scripts/env/set_env.ps1` (PowerShell)

## Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/gersteinlab/LocAgent.git
cd LocAgent
```

### 2. Create Python Environment
```bash
# Use existing conda Python to create venv
C:\Users\18199\anaconda3\envs\locagent\python.exe -m venv venv_locagent_py311
```

### 3. Fix requirements.txt for Windows
The original `requirements.txt` contains Linux-only packages:
```diff
- nvidia-nccl-cu12==2.21.5
- triton==3.1.0
+ nvidia-nccl-cu12==2.21.5; sys_platform != "win32"
+ triton==3.1.0; sys_platform != "win32"
```

### 4. Install Dependencies
```bash
venv_locagent_py311\Scripts\pip.exe install -r LocAgent/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --prefer-binary
```

### 5. Fix f-string Syntax Error
`LocAgent/evaluation/eval_metric.py` contains f-string syntax errors that prevent imports:
- Lines ~54-55: Fix nested quotes in f-strings

### 6. Verify Installation
```python
import util, repo_index, plugins, dependency_graph
# Expected: imports succeed with warning "resource module not available on Windows"
```

## Windows Compatibility Fixes

### 1. Multiprocessing: `fork` → `spawn`
**File**: `auto_search_main.py:367`
```python
# Original (Linux only):
ctx = mp.get_context('fork')

# Fixed:
ctx = mp.get_context('spawn' if os.name == 'nt' else 'fork')
```

### 2. Cleanup: `rm -rf` → `shutil.rmtree`
**File**: `plugins/location_tools/repo_ops/repo_ops.py:115-117`
```python
# Original:
subprocess.run(["rm", "-rf", REPO_SAVE_DIR], check=True)

# Fixed:
import shutil
if REPO_SAVE_DIR and os.path.exists(REPO_SAVE_DIR):
    shutil.rmtree(REPO_SAVE_DIR, ignore_errors=True)
```

### 3. Dataset Download: Local Parquet Fallback
**Issue**: HuggingFace/Xet DNS resolution fails (`cas-bridge.xethub.hf.co` unreachable)
**Solution**: Download parquet via git from hf-mirror, patch `datasets.load_dataset`

```bash
# Download parquet
git clone --depth 1 https://hf-mirror.com/datasets/princeton-nlp/SWE-bench_Verified hf_dataset_temp

# Patch is in LocAgent/scripts/local_dataset_patch.py
# Wrapper: LocAgent/run_with_local_data.py
```

## Pre-built Indices

To avoid re-cloning repos and rebuilding indices on every run:

```bash
# Set index directories
export GRAPH_INDEX_DIR="index_data/SWE-bench_Verified/graph_index_v2.3"
export BM25_INDEX_DIR="index_data/SWE-bench_Verified/BM25_index"

# Build graph index (once)
python -c "
from dependency_graph.build_graph import build_graph
import pickle, os
G = build_graph('playground/{uuid}/astropy_astropy', global_import=True)
os.makedirs('$GRAPH_INDEX_DIR', exist_ok=True)
with open('$GRAPH_INDEX_DIR/astropy__astropy-12907.pkl', 'wb') as f:
    pickle.dump(G, f)
"

# Build BM25 index (once)
python -c "
from plugins.location_tools.retriever.bm25_retriever import build_code_retriever_from_repo
build_code_retriever_from_repo('playground/{uuid}/astropy_astropy', 
    persist_path='$BM25_INDEX_DIR/astropy__astropy-12907', show_progress=True)
"
```

## Run Commands

### Standard Run (with local data patch)
```bash
cd LocAgent
source ../venv_locagent_py311/Scripts/activate
. scripts/env/set_env.sh
export PYTHONPATH="$PYTHONPATH:$(pwd)"
export GRAPH_INDEX_DIR="index_data/SWE-bench_Verified/graph_index_v2.3"
export BM25_INDEX_DIR="index_data/SWE-bench_Verified/BM25_index"

python run_with_local_data.py \
  --dataset 'princeton-nlp/SWE-bench_Verified' \
  --split 'test' \
  --model 'anthropic/qwen-max' \
  --localize --merge \
  --output_folder '../results/locagent_verified_small' \
  --eval_n_limit 1 \
  --num_processes 1 \
  --num_samples 1 \
  --use_function_calling \
  --simple_desc \
  --timeout 300
```

### Single-Process Test (for debugging)
```bash
python scripts/test_single_process.py
```

## Known Issues

1. **HuggingFace/Xet Unreachable**: DNS resolution fails for `cas-bridge.xethub.hf.co`
   - Workaround: Use `hf-mirror.com` + git clone + local parquet patch

2. **`fork` not available on Windows**: Multiprocessing spawn mode required
   - Fixed: Uses `spawn` on Windows, `fork` on Unix

3. **`rm -rf` not portable**: Unix command not available on Windows
   - Fixed: Uses `shutil.rmtree()`

4. **Subprocess Manager.Queue stability**: With `spawn` mode, Manager.Queue connections can be unstable when subprocesses create nested subprocesses
   - Workaround: Use single-process mode for debugging; for production, consider Linux environment

5. **Model name requires provider prefix**: `qwen-max` needs `anthropic/` prefix for LiteLLM
   - Use: `--model 'anthropic/qwen-max'`

6. **Git clone is slow**: astropy repo takes ~3 minutes to clone on this network

7. **Model protocol compliance (BLOCKING)**: `qwen-vl-plus` 不稳定，`qwen-max` 是当前可用模型
   - 期望格式：`<execute_ipython>...</execute_ipython>` 或 `<finish>` 标签
   - 实际输出：长段分析文本，无结构化标签
   - 结果：无法形成有效工具调用链，主进程等待超时 (15 min) → 保存空定位结果
   - 建议：换用支持结构化输出的模型（如 GPT-4o、Claude 系列），或在 system prompt 中强化格式约束

## Verification Results

### ✅ 数据层 — 通过
- LOCAL_DATASET_PATCH 成功将 `princeton-nlp/SWE-bench_Verified` 加载为本地 parquet
- 成功加载 500 条样本，`eval_n_limit=1` 生效

### ✅ 仓库准备 — 通过
- `astropy/astropy` 成功 clone
- `set_current_issue()` 成功加载 graph 索引和 BM25 索引
- 图索引：16,407 nodes, 120,364 edges (33MB)
- BM25 索引：496 files parsed

### ⚠️ 模型本地化 — 部分成功（qwen-max）
- 将 `auto_search_process` 改为直接调用，避免 spawn 丢失全局状态
- `litellm.completion(model="anthropic/qwen-max")` 全部成功
- 工具调用链正常：`explore_tree_structure` → `search_code_snippets` → `get_entity_contents`
- LLM 正确识别 `astropy/modeling/separable.py:separability_matrix` 和 `CompoundModel`
- 与真实 patch 吻合：`separable.py` 第 242 行 `_cstack` 函数 `= 1` → `= right`
- **遗留**：`found_files` 为 `[[]]`，输出解析器未从分析文本中提取结构化结果
- 总耗时约 4 分钟，未超时

## Change Log

| Date | Change |
|------|--------|
| 2026-07-25 | Initial clone, attempted conda env (failed) |
| 2026-07-25 | Created venv with Python 3.11.15 |
| 2026-07-25 | Fixed requirements.txt Windows compatibility |
| 2026-07-25 | Fixed f-string syntax errors in eval_metric.py |
| 2026-07-26 | Downloaded SWE-bench_Verified parquet via hf-mirror git |
| 2026-07-26 | Created local_dataset_patch.py and run_with_local_data.py |
| 2026-07-26 | Fixed fork→spawn in auto_search_main.py |
| 2026-07-26 | Fixed rm→shutil in repo_ops.py |
| 2026-07-26 | Pre-built graph index (16k nodes) and BM25 index |
| 2026-07-26 | API 连通性验证通过（单进程 20 轮交互） |
| 2026-07-26 | qwen-vl-plus 实验失败（未按工具协议输出，15 min 超时） |
| 2026-07-26 | 改 `auto_search_process` 为直接调用，解决 spawn 丢失全局状态 |
| 2026-07-26 | qwen-max 实验部分成功：LLM 正确定位 separable.py，输出解析器待改进 |

## Final Status
- qwen-max result rebuilt into results/locagent_verified_small/loc_outputs.jsonl
- found_files now parses as non-empty
- results/locagent_verified_small/merged_loc_outputs_mrr.jsonl generated
