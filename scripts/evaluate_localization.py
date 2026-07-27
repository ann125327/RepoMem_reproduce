#!/usr/bin/env python
"""Evaluate LocAgent file-level localization outputs.

The evaluator is intentionally small and dependency-light: it reads LocAgent's
JSONL localization output, derives file-level ground truth from the SWE-bench
patch field, and writes both per-instance and aggregate Acc@k reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCAGENT_ROOT = ROOT / "LocAgent"
if str(LOCAGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(LOCAGENT_ROOT))

try:
    from util.benchmark.parse_patch import get_oracle_filenames
except Exception:
    get_oracle_filenames = None


DEFAULT_OUTPUT_DIR = ROOT / "results" / "locagent_verified_small"
DEFAULT_LOC_FILE = DEFAULT_OUTPUT_DIR / "merged_loc_outputs_mrr.jsonl"
FALLBACK_LOC_FILE = DEFAULT_OUTPUT_DIR / "loc_outputs.jsonl"
DEFAULT_SUMMARY_FILE = DEFAULT_OUTPUT_DIR / "eval_summary.json"
DEFAULT_INSTANCES_FILE = DEFAULT_OUTPUT_DIR / "eval_instances.csv"
DEFAULT_LOG_FILE = DEFAULT_OUTPUT_DIR / "localize.log"

TOOL_NAMES = (
    "explore_tree_structure",
    "search_code_snippets",
    "get_entity_contents",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def normalize_path(path: str) -> str:
    path = path.strip().strip("`'\"")
    path = path.replace("\\", "/")
    path = re.sub(r"/+", "/", path)
    while path.startswith("./"):
        path = path[2:]
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    return path


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = normalize_path(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def flatten_prediction_list(value: Any) -> list[str]:
    """Flatten LocAgent predictions while preserving the model's ranking order."""
    flattened: list[str] = []

    def visit(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            flattened.append(node)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                visit(child)

    visit(value)
    return unique_preserve_order(flattened)


def fallback_oracle_filenames(patch: str) -> set[str]:
    files: set[str] = set()
    for match in re.finditer(r"^diff --git a/(.*?) b/(.*?)$", patch, flags=re.MULTILINE):
        source, target = match.groups()
        chosen = target if target != "/dev/null" else source
        if chosen and chosen != "/dev/null":
            files.add(chosen)
    return files


def ground_truth_from_patch(patch: str) -> list[str]:
    if not patch:
        return []

    if get_oracle_filenames is not None:
        try:
            return unique_preserve_order(sorted(get_oracle_filenames(patch)))
        except Exception:
            pass

    return unique_preserve_order(sorted(fallback_oracle_filenames(patch)))


def covers_all_ground_truth(predicted: list[str], ground_truth: list[str]) -> int:
    if not ground_truth:
        return 0
    return int(set(ground_truth).issubset(set(predicted)))


def parse_tool_calls_from_log(log_file: Path) -> dict[str, list[str]]:
    if not log_file.exists():
        return {}

    tool_calls_by_instance: dict[str, list[str]] = {}
    current_instance: str | None = None
    setup_pattern = re.compile(r"setup localize ([\w.\-]+__[\w.\-]+-\d+)")
    tool_pattern = re.compile(r"\b(" + "|".join(map(re.escape, TOOL_NAMES)) + r")\s*\(")

    with log_file.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            setup_match = setup_pattern.search(line)
            if setup_match:
                current_instance = setup_match.group(1)
                tool_calls_by_instance.setdefault(current_instance, [])

            if current_instance is None:
                continue

            for tool_match in tool_pattern.finditer(line):
                tool_calls_by_instance.setdefault(current_instance, []).append(tool_match.group(1))

    return tool_calls_by_instance


def load_usage_by_instance(output_dir: Path, loc_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    usage_by_instance: dict[str, dict[str, Any]] = {}

    for row in loc_rows:
        usage = row.get("usage")
        if isinstance(usage, dict):
            usage_by_instance[row["instance_id"]] = usage

    traj_file = output_dir / "loc_trajs.jsonl"
    if traj_file.exists():
        for row in read_jsonl(traj_file):
            usage = row.get("usage")
            if isinstance(usage, dict):
                usage_by_instance[row["instance_id"]] = usage

    return usage_by_instance


def make_instance_row(
    loc_row: dict[str, Any],
    tool_calls: list[str],
    usage: dict[str, Any] | None,
) -> dict[str, Any]:
    meta_data = loc_row.get("meta_data") or {}
    patch = meta_data.get("patch") or loc_row.get("patch") or ""
    predicted_files = flatten_prediction_list(loc_row.get("found_files", []))
    ground_truth_files = ground_truth_from_patch(patch)

    predicted_top1 = predicted_files[:1]
    predicted_top3 = predicted_files[:3]
    predicted_top5 = predicted_files[:5]

    return {
        "instance_id": loc_row.get("instance_id", ""),
        "repo": meta_data.get("repo") or loc_row.get("repo", ""),
        "problem_statement": meta_data.get("problem_statement") or loc_row.get("problem_statement", ""),
        "ground_truth_files": ground_truth_files,
        "predicted_files_top1": predicted_top1,
        "predicted_files_top3": predicted_top3,
        "predicted_files_top5": predicted_top5,
        "acc@1": covers_all_ground_truth(predicted_top1, ground_truth_files),
        "acc@3": covers_all_ground_truth(predicted_top3, ground_truth_files),
        "acc@5": covers_all_ground_truth(predicted_top5, ground_truth_files),
        "tool_calls": tool_calls,
        "token usage": usage,
        "cost": (usage or {}).get("cost($)") if usage else None,
        "failure_type": "",
    }


def write_instances_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "instance_id",
        "repo",
        "problem_statement",
        "ground_truth_files",
        "predicted_files_top1",
        "predicted_files_top3",
        "predicted_files_top5",
        "acc@1",
        "acc@3",
        "acc@5",
        "tool_calls",
        "token usage",
        "cost",
        "failure_type",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            for key in (
                "ground_truth_files",
                "predicted_files_top1",
                "predicted_files_top3",
                "predicted_files_top5",
                "tool_calls",
                "token usage",
            ):
                csv_row[key] = json.dumps(csv_row[key], ensure_ascii=False)
            writer.writerow(csv_row)


def make_summary(rows: list[dict[str, Any]], loc_file: Path, log_file: Path) -> dict[str, Any]:
    total = len(rows)

    def mean_metric(name: str) -> float:
        if total == 0:
            return 0.0
        return round(sum(int(row[name]) for row in rows) / total, 4)

    return {
        "loc_file": str(loc_file),
        "log_file": str(log_file) if log_file.exists() else None,
        "num_instances": total,
        "metrics": {
            "acc@1": mean_metric("acc@1"),
            "acc@3": mean_metric("acc@3"),
            "acc@5": mean_metric("acc@5"),
        },
        "metric_definition": (
            "Acc@k = 1 iff the top-k predicted files cover all ground-truth "
            "files modified by the SWE-bench patch; otherwise 0."
        ),
        "instances": [
            {
                "instance_id": row["instance_id"],
                "ground_truth_files": row["ground_truth_files"],
                "predicted_files_top5": row["predicted_files_top5"],
                "acc@1": row["acc@1"],
                "acc@3": row["acc@3"],
                "acc@5": row["acc@5"],
                "failure_type": row["failure_type"],
            }
            for row in rows
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loc-file", type=Path, default=DEFAULT_LOC_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-file", type=Path, default=DEFAULT_SUMMARY_FILE)
    parser.add_argument("--instances-file", type=Path, default=DEFAULT_INSTANCES_FILE)
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_FILE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loc_file = args.loc_file
    if not loc_file.exists() and loc_file == DEFAULT_LOC_FILE and FALLBACK_LOC_FILE.exists():
        loc_file = FALLBACK_LOC_FILE
    if not loc_file.exists():
        raise FileNotFoundError(f"Localization output not found: {loc_file}")

    loc_rows = read_jsonl(loc_file)
    tool_calls_by_instance = parse_tool_calls_from_log(args.log_file)
    usage_by_instance = load_usage_by_instance(args.output_dir, loc_rows)

    instance_rows = [
        make_instance_row(
            row,
            tool_calls_by_instance.get(row.get("instance_id", ""), []),
            usage_by_instance.get(row.get("instance_id", "")),
        )
        for row in loc_rows
    ]

    write_instances_csv(instance_rows, args.instances_file)
    summary = make_summary(instance_rows, loc_file, args.log_file)
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_file.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {args.summary_file}")
    print(f"Wrote {args.instances_file}")
    print(json.dumps(summary["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
