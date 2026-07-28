# 05 - Comparative Analysis: LocAgent Results vs Paper Baseline

## Executive Summary

[To be filled after evaluation completes]

## Evaluation Results

### Our Results

**Dataset**: SWE-bench Verified  
**Model**: anthropic/qwen-max  
**Sample Size**: 3 instances  
**Date**: 2026-07-28  

| Metric | Score |
|--------|-------|
| Acc@1 | [TBD]/3 |
| Acc@3 | [TBD]/3 |
| Acc@5 | [TBD]/3 |

### Paper Baseline

**Dataset**: SWE-bench Verified  
**Model**: Claude-3.5-Sonnet  
**Sample Size**: 500 instances  

| Metric | Paper Result |
|--------|--------------|
| Acc@1 | [From paper] |
| Acc@3 | [From paper] |
| Acc@5 | [From paper] |

## Instance-Level Comparison

| Instance ID | Ground Truth | Our Prediction | Acc@1 | Acc@3 | Acc@5 |
|-------------|--------------|----------------|-------|-------|-------|
| astropy__astropy-12907 | [file] | [file] | [0/1] | [0/1] | [0/1] |
| astropy__astropy-13033 | [file] | [file] | [0/1] | [0/1] | [0/1] |
| astropy__astropy-13236 | [file] | [file] | [0/1] | [0/1] | [0/1] |

## Key Differences

### 1. Model Selection
- **Paper**: Claude-3.5-Sonnet (optimized for code tasks)
- **Ours**: Qwen-Max (via Anthropic API)

### 2. Sample Size
- **Paper**: 500 instances (full dataset)
- **Ours**: 3 instances (small test)

### 3. Tool Availability
- **Paper**: Full LocAgent tool suite with working BM25
- **Ours**: Graph index + entity search (BM25 with error handling)

### 4. Execution Environment
- **Paper**: Production environment
- **Ours**: Development/test environment with local dataset

## Analysis

### Strengths
[To be filled based on results]

### Limitations
[To be filled based on results]

### Failure Cases
[To be filled based on results]

## Recommendations

1. **Model**: Consider testing with Claude-3.5-Sonnet for direct comparison
2. **Sample Size**: Increase to 10-50 instances for better statistics
3. **Tool Fix**: Resolve remaining BM25 index issues
4. **Post-processing**: Implement MRR merging for better results

## Conclusion

[To be filled after evaluation]

## Appendix

### Methodology
- Acc@k metric: 1 if all ground truth files in top-k predictions, else 0
- Ground truth: Files modified in the patch
- Predictions: Files identified by LocAgent

### Data Sources
- Predictions: `results/locagent_batch_fixed/loc_outputs.jsonl`
- Ground Truth: `hf_dataset_temp/data/test-00000-of-00001.parquet`
- Evaluation Script: `scripts/evaluate_localization.py`
