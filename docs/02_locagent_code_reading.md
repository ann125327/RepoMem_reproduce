# LocAgent Code Reading Notes

## Repository Structure
```
LocAgent/
├── auto_search_main.py              # Main entry point for localization
├── run_with_local_data.py           # Wrapper for local dataset patch (added for Windows)
├── dependency_graph/                # Graph construction utilities
│   ├── batch_build_graph.py        # Batch graph construction for multiple repos
│   ├── build_graph.py              # Individual graph building using tree-sitter
│   └── traverse_graph.py           # Graph traversal logic
├── evaluation/                      # Evaluation scripts
│   ├── eval_metric.py              # Main evaluation metrics (Accuracy@k)
│   └── run_evaluation.ipynb        # Evaluation notebook
├── plugins/                         # Agent tool definitions
│   └── location_tools/             # Code search and navigation tools
│       ├── repo_ops/repo_ops.py    # Core tool implementations
│       └── retriever/bm25_retriever.py  # BM25 code retrieval
├── util/                           # Utility modules
│   ├── actions/                    # Action parsing (response → tool calls)
│   ├── prompts/                    # Prompt templates and pipelines
│   ├── runtime/                    # Runtime utilities (function calling, IPython)
│   ├── cost_analysis.py            # Token cost tracking
│   ├── process_output.py           # Output merging and ranking
│   └── benchmark/                  # Repo setup and data utilities
├── repo_index/                     # Repository indexing (BM25, vector)
├── scripts/                        # Run scripts and env setup
└── requirements.txt                # Python dependencies
```

## Main Entry Point
`auto_search_main.py` is the primary entry point with the following command-line interface:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dataset` | `princeton-nlp/SWE-bench_Lite` | HuggingFace dataset name |
| `--split` | `test` | Dataset split |
| `--eval_n_limit` | `0` | Limit number of instances (0 = all) |
| `--model` | `openai/gpt-4o-2024-05-13` | LLM model (LiteLLM format) |
| `--localize` | flag | Enable localization mode |
| `--merge` | flag | Merge results from multiple samples |
| `--output_folder` | required | Output directory |
| `--num_processes` | `-1` | Parallel worker count |
| `--num_samples` | `2` | Samples per instance |
| `--use_function_calling` | flag | Enable LLM function calling |
| `--simple_desc` | flag | Simplified tool descriptions |
| `--timeout` | `900` | Per-instance timeout (seconds) |
| `--ranking_method` | `mrr` | Ranking method (mrr/majority) |

## Data Loading Flow

1. **Dataset Loading**: `datasets.load_dataset(args.dataset, split=args.split)`
   - Default: `princeton-nlp/SWE-bench_Lite` (500 instances)
   - Also supports: `princeton-nlp/SWE-bench_Verified`, `princeton-nlp/SWE-bench`
   - Dataset fields: `instance_id`, `repo`, `base_commit`, `problem_statement`, `patch`, `test_patch`, `hints_text`, `FAIL_TO_PASS`, `PASS_TO_PASS`

2. **Filtering**: `filter_dataset()` checks `config.toml` for `selected_ids` list
   - If `config.toml` exists with matching list, filters to those IDs only

3. **Limiting**: `eval_n_limit` parameter limits to first N instances

## Dependency Graph Construction

Located in `dependency_graph/`:

1. **`build_graph.py`**: Uses tree-sitter to parse Python source files
   - Extracts: classes, functions, imports, dependencies
   - Creates `nx.MultiDiGraph` with node types: DIRECTORY, FILE, CLASS, FUNCTION
   - Edge type: CONTAINS (hierarchical relationships)
   - `global_import=True` processes all imports for dependency tracking

2. **`batch_build_graph.py`**: Batch processing across multiple repos
   ```bash
   python dependency_graph/batch_build_graph.py \
     --dataset 'princeton-nlp/SWE-bench_Verified' \
     --split 'test' \
     --num_processes 4 \
     --download_repo
   ```
   - Pulls repos from GitHub at specified commits
   - Builds graph for each repo, saves as `.pkl` files
   - Index saved to `index_data/{DATASET}/graph_index_v2.3/`

3. **Graph Persistence**:
   - Graph index files: `{GRAPH_INDEX_DIR}/{instance_id}.pkl`
   - Loaded on demand by `set_current_issue()` in `repo_ops.py`

## Agent Tools

### Available Tools (from `util/runtime/function_calling.py`)

| Tool | Function | Description |
|------|----------|-------------|
| `FinishTool` | `finish` | End the localization session |
| `SearchRepoTool` | `search_code_snippets` | BM25 keyword search across codebase |
| `SearchEntityTool` | `get_entity_contents` | Get content of specific code entities |
| `ExploreTreeStructure` | `explore_tree_structure` | Navigate code dependency graph |

### Tool Execution

Tools are executed via two modes:
1. **Function Calling** (`--use_function_calling`): LLM calls tools via structured API
2. **CodeAct** (default for most models): LLM writes `<execute_ipython>...</execute_ipython>` code blocks

The `execute_ipython()` function runs Python code in an IPython shell with tools injected into the namespace.

## Localization Output Format

Output is saved as JSONL in `{output_folder}/loc_outputs.jsonl`:

```json
{
  "instance_id": "astropy__astropy-12907",
  "found_files": [["file1.py", "file2.py"], ...],
  "found_modules": [["module1", "module2"], ...],
  "found_entities": [["file:entity", ...], ...],
  "raw_output_loc": ["LLM response text"],
  "meta_data": {
    "repo": "astropy/astropy",
    "base_commit": "d16bfe05...",
    "problem_statement": "...",
    "patch": "..."
  },
  "usage": {"cost($)": "0.15", "prompt_tokens": 85000, "completion_tokens": 12000}
}
```

- `found_files`/`found_modules`/`found_entities`: Multi-sample ranked lists
- `raw_output_loc`: Raw LLM responses from each sample
- After `--merge`, results are saved to `merged_loc_outputs.jsonl` with MRR/majority ranking

## Evaluation

Located in `evaluation/eval_metric.py`:
- `filtered_instances()`: Get instances that pass filter criteria
- Metrics: Accuracy@k for file-level localization
- Compares predicted files against `patch` changes in the dataset

## Key Files Summary

| File | Purpose |
|------|---------|
| `auto_search_main.py` | Main execution script with `localize()`, `merge()`, `main()` |
| `dependency_graph/build_graph.py` | Tree-sitter based graph construction |
| `plugins/location_tools/repo_ops/repo_ops.py` | Core tool implementations + `set_current_issue()` |
| `plugins/location_tools/retriever/bm25_retriever.py` | BM25 index building and querying |
| `util/prompts/pipelines/auto_search_prompt.py` | Task instructions and prompts |
| `util/actions/action_parser.py` | Parses LLM responses into tool actions |
| `util/runtime/execute_ipython.py` | Executes tool code in IPython shell |
| `util/runtime/function_calling.py` | Tool definitions for LLM function calling |
| `util/process_output.py` | Output merging and ranking logic |
| `evaluation/eval_metric.py` | Evaluation metrics |
