import argparse
from pathlib import Path

from sentinel.config import Config
from sentinel.model import SentinelModel
from sentinel.parser import parse_line


def main():
    parser = argparse.ArgumentParser(description="Train Sentinel Model")
    parser.add_argument(
        "--input", type=str, required=True, help="Input normal log file"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Output model path (.joblib)"
    )
    parser.add_argument(
        "--config", type=str, default="config.json", help="Path to config.json"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading normal data from {input_path}...")
    records = []
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            rec = parse_line(line)
            records.append(rec)

    print(f"Loading config from {args.config}...")
    config = Config.load(args.config)

    print(
        f"Loaded {len(records)} lines. Training model (contamination={config.model.contamination})..."
    )

    model = SentinelModel(config=config)

    # Simple split to measure false alarm rate on holdout (using 20% for testing)
    split_idx = int(len(records) * 0.8)
    train_records = records[:split_idx]
    test_records = records[split_idx:]

    model.fit(train_records)

    # Evaluate false alarms on held-out 20%
    if test_records:
        preds = model.predict(test_records)
        false_alarms = sum(1 for p in preds if p == -1)
        fa_rate = false_alarms / len(test_records)
        print(
            f"False alarm rate on 20% holdout ({len(test_records)} lines): {fa_rate:.4%} ({false_alarms} lines)"
        )

    model.save(str(output_path))
    print(f"Model saved to {output_path}")


if __name__ == "__main__":
    main()
