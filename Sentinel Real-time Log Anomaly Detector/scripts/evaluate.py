import argparse
import csv
from pathlib import Path

from sentinel.model import SentinelModel
from sentinel.parser import parse_line


def main():
    parser = argparse.ArgumentParser(description="Evaluate Sentinel Model")
    parser.add_argument(
        "--model", type=str, required=True, help="Path to trained model"
    )
    parser.add_argument("--log", type=str, required=True, help="Path to mixed log file")
    args = parser.parse_args()

    model_path = Path(args.model)
    log_path = Path(args.log)
    labels_path = log_path.with_suffix(".labels.csv")

    print(f"Loading model from {model_path}...")
    model = SentinelModel.load(str(model_path))

    records = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            records.append(parse_line(line))

    # Read labels
    labels = []  # (is_anomaly_true, anomaly_type)
    with open(labels_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels.append((int(row["label"]), row["type"]))

    if len(records) != len(labels):
        print(
            f"Warning: mismatched lengths ({len(records)} records vs {len(labels)} labels)"
        )

    print(f"Evaluating {len(records)} records...")

    # Predict in chunks to simulate somewhat realistic flow and memory usage
    preds = model.predict(records)
    scores = model.score(records)
    max_train_score = model.metadata.get("max_training_score", 0.0)

    from sentinel.signatures import check_signatures

    tp, fp, tn, fn = 0, 0, 0, 0
    type_stats = {}  # type -> {"total": 0, "caught": 0}

    for idx, (pred, score, record) in enumerate(zip(preds, scores, records)):
        sig_matches = check_signatures(record.message)
        has_sig = len(sig_matches) > 0

        is_anomaly_pred = (pred == -1) or (score > max_train_score) or has_sig
        is_anomaly_true, anom_type = labels[idx]

        if is_anomaly_true:
            if anom_type not in type_stats:
                type_stats[anom_type] = {"total": 0, "caught": 0}
            type_stats[anom_type]["total"] += 1
            if is_anomaly_pred:
                type_stats[anom_type]["caught"] += 1

        if is_anomaly_true and is_anomaly_pred:
            tp += 1
        elif is_anomaly_true and not is_anomaly_pred:
            fn += 1
        elif not is_anomaly_true and is_anomaly_pred:
            fp += 1
        elif not is_anomaly_true and not is_anomaly_pred:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    fa_rate = fp / (fp + tn) if (fp + tn) > 0 else 0

    print("\n--- RESULTS ---")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"True Negatives:  {tn}")
    print(f"False Negatives: {fn}")
    print(f"Overall Precision: {precision:.4f}")
    print(f"Overall Recall:    {recall:.4f}")
    print(f"F1 Score:          {f1:.4f}")
    print(f"False Alarm Rate (on normal data): {fa_rate:.4%}")

    print("\n--- RECALL PER ANOMALY TYPE ---")
    for anom_type, stats in type_stats.items():
        caught = stats["caught"]
        total = stats["total"]
        pct = caught / total if total > 0 else 0
        print(f"  {anom_type.ljust(15)}: {pct:.2%} ({caught}/{total})")


if __name__ == "__main__":
    main()
