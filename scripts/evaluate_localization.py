
#!/usr/bin/env python3
import json, os, re, csv
from pathlib import Path
import pandas as pd

def extract_modified_files(patch):
    if not patch or pd.isna(patch):
        return set()
    return set(re.findall(r'diff --git a/(.*?) b/.*?', patch))

def load_predictions(pred_file):
    predictions = {}
    with open(pred_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            predictions[data['instance_id']] = data
    return predictions

def load_ground_truth(dataset_path, instance_ids=None):
    df = pd.read_parquet(dataset_path)
    ground_truth = {}
    for _, row in df.iterrows():
        iid = row['instance_id']
        if instance_ids and iid not in instance_ids:
            continue
        ground_truth[iid] = {
            'repo': row['repo'],
            'problem_statement': row['problem_statement'],
            'modified_files': extract_modified_files(row['patch'])
        }
    return ground_truth

def extract_predicted_files(pred_data):
    if pred_data.get('found_files'):
        ff = pred_data['found_files']
        if isinstance(ff, list) and len(ff) > 0:
            if isinstance(ff[0], list):
                return [f for fl in ff for f in fl if f]
            return [f for f in ff if f]
    
    if pred_data.get('raw_output_loc'):
        raw = pred_data['raw_output_loc']
        if isinstance(raw, list):
            raw = '
'.join(raw)
        files = re.findall(r'([a-zA-Z_][a-zA-Z0-9_\-/]*\.py)', raw)
        seen = set()
        return [f for f in files if f not in seen and not seen.add(f) and not f.startswith('test_')][:10]
    return []

def calculate_acc_at_k(pred_files, gt_files, k):
    if not gt_files:
        return False, 0
    top_k = set(pred_files[:k])
    return gt_files.issubset(top_k), len(top_k & gt_files)

def main():
    pred_file = 'results/locagent_verified_batch_final/loc_outputs.jsonl'
    dataset = 'hf_dataset_temp/data/test-00000-of-00001.parquet'
    output = 'results/locagent_verified_batch_final'
    
    print("Loading predictions...")
    predictions = load_predictions(pred_file)
    print(f"Found {len(predictions)} instances")
    
    print("Loading ground truth...")
    gt = load_ground_truth(dataset, list(predictions.keys()))
    print(f"Found {len(gt)} matching instances")
    
    results = []
    stats = {'total': 0, 'acc1': 0, 'acc3': 0, 'acc5': 0}
    
    for iid in sorted(predictions.keys()):
        if iid not in gt:
            continue
        stats['total'] += 1
        
        pred_files = extract_predicted_files(predictions[iid])
        gt_files = gt[iid]['modified_files']
        
        acc1, m1 = calculate_acc_at_k(pred_files, gt_files, 1)
        acc3, m3 = calculate_acc_at_k(pred_files, gt_files, 3)
        acc5, m5 = calculate_acc_at_k(pred_files, gt_files, 5)
        
        stats['acc1'] += acc1
        stats['acc3'] += acc3
        stats['acc5'] += acc5
        
        print(f"
{iid}: GT={len(gt_files)} files, Pred={len(pred_files)} files")
        print(f"  Acc@1={int(acc1)}, Acc@3={int(acc3)}, Acc@5={int(acc5)}")
        
        results.append({
            'instance_id': iid,
            'repo': gt[iid]['repo'],
            'ground_truth_files': '; '.join(sorted(gt_files)),
            'predicted_files_top1': pred_files[0] if pred_files else '',
            'predicted_files_top5': '; '.join(pred_files[:5]),
            'acc_at_1': int(acc1),
            'acc_at_3': int(acc3),
            'acc_at_5': int(acc5)
        })
    
    print(f"

SUMMARY:")
    print(f"Total: {stats['total']}")
    print(f"Acc@1: {stats['acc1']}/{stats['total']} = {stats['acc1']/stats['total']*100:.1f}%")
    print(f"Acc@3: {stats['acc3']}/{stats['total']} = {stats['acc3']/stats['total']*100:.1f}%")
    print(f"Acc@5: {stats['acc5']}/{stats['total']} = {stats['acc5']/stats['total']*100:.1f}%")
    
    with open(os.path.join(output, 'eval_summary.json'), 'w') as f:
        json.dump({
            'total_instances': stats['total'],
            'acc_at_1': stats['acc1'],
            'acc_at_3': stats['acc3'],
            'acc_at_5': stats['acc5'],
            'acc_at_1_pct': stats['acc1']/stats['total']*100
        }, f, indent=2)
    
    with open(os.path.join(output, 'eval_instances.csv'), 'w', newline='') as f:
        if results:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)

if __name__ == '__main__':
    main()
