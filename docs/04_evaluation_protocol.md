# 04 - File-Level Localization Evaluation Protocol

## Evaluation Metrics

### Accuracy at k (Acc@k)

**Definition:** For each issue, Acc@k = 1 if ALL ground truth modified files are contained within the top-k predicted files, otherwise Acc@k = 0.

**Formula:**
```
Acc@k = 1 if GroundTruthFiles ⊆ TopKPredictedFiles
Acc@k = 0 otherwise
```

**Metrics:**
- **Acc@1**: Can the correct file be identified as the top-1 prediction?
- **Acc@3**: Are all correct files in the top-3 predictions?
- **Acc@5**: Are all correct files in the top-5 predictions?

### Why Acc@k?

This metric is appropriate for file-level localization because:

1. **Developer Workflow**: Developers typically want to know the top-k most relevant files, not just a single file
2. **Multi-file Changes**: Many issues require modifications across multiple files
3. **Ranking Quality**: Acc@k measures both recall (finding all files) and ranking quality (how high they're ranked)

## File-Level Localization

### Why File-Level?

We evaluate at the file level rather than function/class level for several reasons:

1. **Practical Relevance**: Developers need to know which files to open and modify
2. **Tool Integration**: File-level localization integrates better with IDEs and code review tools
3. **Ground Truth Availability**: SWE-bench provides patch-level ground truth from which we can extract modified files
4. **Evaluation Simplicity**: File-level comparison is unambiguous and easy to interpret

### Ground Truth Extraction

Ground truth files are extracted from the unified diff patch in SWE-bench:

```python
def extract_modified_files(patch):
    # Pattern: "diff --git a/path/to/file b/path/to/file"
    files = re.findall(r'diff --git a/(.*?) b/.*?', patch)
    return set(files)
```

## Comparison with Paper Evaluation

### Similarities with LocAgent Paper

1. **Dataset**: Both use SWE-bench Verified dataset
2. **Task Definition**: Both evaluate file-level localization
3. **Metrics**: Both report Acc@k metrics

### Differences

| Aspect | Paper | Our Evaluation |
|--------|-------|----------------|
| Sample Size | Full dataset (500 instances) | Small subset (3-10 instances) |
| Model | Claude-3.5-Sonnet | Qwen-Max (via Anthropic API) |
| Execution | Production environment | Development/test environment |
| Post-processing | Advanced MRR merging | Basic file extraction |
| Tool Availability | Full tool access | Limited by BM25 errors |

### Current Results

**Batch Evaluation (2026-07-28):**

- **Total Instances**: 3
- **Acc@1**: 0/3 (0.0%)
- **Acc@3**: 0/3 (0.0%)
- **Acc@5**: 0/3 (0.0%)

**Issues Identified:**

1. **BM25 Index Error**: `ValueError: kth(=-1) out of bounds` prevents search tools from working
2. **Empty Predictions**: All instances returned empty file predictions
3. **Tool Failure**: `search_code_snippets` function failed consistently

## Evaluation Pipeline

### Input Files

1. **Predictions**: `results/locagent_verified_batch_final/loc_outputs.jsonl`
   - Contains model predictions for each instance
   - Fields: `instance_id`, `found_files`, `raw_output_loc`

2. **Ground Truth**: `hf_dataset_temp/data/test-00000-of-00001.parquet`
   - SWE-bench Verified dataset
   - Fields: `instance_id`, `patch`, `problem_statement`

### Output Files

1. **`eval_summary.json`**: Overall statistics
   ```json
   {
     "total_instances": 3,
     "acc_at_1": 0,
     "acc_at_3": 0,
     "acc_at_5": 0,
     "acc_at_1_pct": 0.0
   }
   ```

2. **`eval_instances.csv`**: Detailed per-instance results
   - Columns: `instance_id`, `repo`, `ground_truth_files`, `predicted_files_top1`, `acc_at_1`, etc.

### Evaluation Script

Located at: `scripts/evaluate_localization.py`

**Usage:**
```bash
python scripts/evaluate_localization.py [pred_file] [dataset_path] [output_dir]
```

## Recommendations for Improvement

1. **Fix BM25 Index**: Resolve the `kth out of bounds` error in search tools
2. **Increase Sample Size**: Evaluate on larger subset (10-50 instances) for better statistical significance
3. **Model Selection**: Test with Claude-3.5-Sonnet for direct comparison with paper
4. **Error Handling**: Add retry logic for tool failures
5. **Post-processing**: Implement MRR (Mean Reciprocal Rank) merging for multiple predictions

## Conclusion

The current evaluation framework is **structurally sound** but needs technical fixes to the BM25 search functionality. Once resolved, it can properly evaluate file-level localization performance against SWE-bench Verified benchmarks.

**Next Steps:**
1. Debug and fix BM25 index errors
2. Re-run evaluation with working tools
3. Compare results with LocAgent paper baseline
4. Document any additional insights from successful runs
