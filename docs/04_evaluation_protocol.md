# Evaluation Protocol

## Scope

This stage evaluates LocAgent's file-level localization output on the small
SWE-bench-verified run saved under `results/locagent_verified_small/`.

The evaluator is `scripts/evaluate_localization.py`. It reads LocAgent JSONL
localization outputs, derives ground truth files from each instance's
SWE-bench `patch` field, and writes:

- `results/locagent_verified_small/eval_summary.json`
- `results/locagent_verified_small/eval_instances.csv`

## Ground Truth Source

The file-level ground truth comes from the SWE-bench instance `patch` field.
For each patch, the evaluator parses the unified diff and extracts the modified
file paths with LocAgent's existing utility:

```python
util.benchmark.parse_patch.get_oracle_filenames(patch)
```

For the current small run, the patch is already embedded in
`loc_outputs.jsonl` under `meta_data.patch`, so evaluation does not need to
download the dataset again.

## Metrics

For each issue, let `G` be the set of ground-truth modified files and `P_k` be
the top-k predicted files.

Acc@1 is:

```text
1 if G is a subset of P_1, else 0
```

Acc@3 is:

```text
1 if G is a subset of P_3, else 0
```

Acc@5 is:

```text
1 if G is a subset of P_5, else 0
```

This is a strict coverage metric. If an issue modifies two files, Acc@k is 1
only when both files appear in the top-k predictions.

The final summary reports the mean Acc@1, Acc@3, and Acc@5 over all evaluated
instances.

## Why File-Level Localization

File-level localization is the most stable first evaluation target for this
Windows reproduction because:

- SWE-bench patches give reliable modified-file labels.
- LocAgent's parser and merge step already produce `found_files`.
- File-level success is easier to compare across models whose final text may
not consistently include function/class formatting.
- It is the right coarse checkpoint before moving to module/function-level
localization and patch generation.

## Relation To LocAgent / Paper Evaluation

LocAgent's repository includes evaluation code in:

- `LocAgent/evaluation/eval_metric.py`
- `LocAgent/util/benchmark/parse_patch.py`
- `LocAgent/util/benchmark/gen_oracle_locations.py`

The implemented script follows the same file-level idea used by LocAgent's
evaluation helpers: compare predicted file paths against oracle files parsed
from SWE-bench patch metadata.

The difference is output shape. The repository evaluator mainly produces
aggregate metrics and also supports module/function-level evaluation when
oracle locations are available. This stage's script is deliberately narrower:
it focuses on file-level Acc@1/3/5 and additionally emits a per-instance CSV
with problem text, predictions, tool calls, token usage, cost if available, and
an initially empty `failure_type`.

## Current Small-Run Result

For `astropy__astropy-12907`, the ground-truth modified file is:

```text
astropy/modeling/separable.py
```

The current merged prediction ranks:

```text
astropy/modeling/models.py
astropy/modeling/separable.py
astropy/modeling/core.py
```

Therefore:

- Acc@1 = 0
- Acc@3 = 1
- Acc@5 = 1

Token usage and cost are reported only if present in LocAgent output or
`loc_trajs.jsonl`. The current result directory does not include
`loc_trajs.jsonl`, so these fields are left empty rather than estimated.

## Run Command

From `C:\Users\18199\Desktop\codingAgent\stage2`:

```powershell
.\venv_locagent_py311\Scripts\python.exe scripts\evaluate_localization.py
```
