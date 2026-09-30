import argparse
import logging
import sys
from pathlib import Path

from sentinel.alerting import SlackNotifier, FileNotifier
from sentinel.config import Config
from sentinel.ingestor import LogTailer
from sentinel.model import SentinelModel
from sentinel.parser import parse_line
from sentinel.signatures import check_signatures

# Basic logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class ConsoleNotifier:
    def notify(self, record, score, reason):
        print(f"\n[ALERT] {reason}")
        print(f"        Score: {score:.4f}")
        print(f"        Log: {record.raw}")


def main():
    parser = argparse.ArgumentParser(
        description="Sentinel: Real-time Log Anomaly Detection"
    )
    parser.add_argument(
        "--model", type=str, required=True, help="Path to trained model"
    )
    parser.add_argument(
        "--log", type=str, required=True, help="Path to log file to tail"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Use polling instead of watchdog for tailing",
    )
    parser.add_argument(
        "--test-alert", action="store_true", help="Send a test alert and exit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print alerts instead of sending to Slack",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        help="Seconds between identical alerts (overrides config)",
    )
    parser.add_argument(
        "--config", type=str, default="config.json", help="Path to config.json"
    )
    parser.add_argument(
        "--out-alerts", type=str, help="Path to write JSON alerts for web dashboard"
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    log_path = Path(args.log)

    if not model_path.exists():
        logger.error(f"Model not found at {model_path}")
        sys.exit(1)

    config = Config.load(args.config)
    cooldown = (
        args.cooldown if args.cooldown is not None else config.alerting.cooldown_seconds
    )

    slack = SlackNotifier(cooldown_seconds=cooldown, dry_run=args.dry_run)
    console = ConsoleNotifier()
    file_notifier = FileNotifier(args.out_alerts) if args.out_alerts else None

    if args.test_alert:
        logger.info("Sending test alert...")
        from sentinel.parser import LogRecord

        dummy = LogRecord(
            raw='127.0.0.1 - - [15/Jan/2025:10:00:00 +0000] "GET /test HTTP/1.1" 200 123 "-" "-"',
            ip="127.0.0.1",
            path="/test",
        )
        slack.notify(dummy, 99.99, "Test Alert via --test-alert", force=True)
        slack.stop()
        sys.exit(0)

    logger.info(f"Loading Sentinel model from {model_path}...")
    model = SentinelModel.load(str(model_path))
    max_train_score = model.metadata.get("max_training_score", 0.0)

    tailer = LogTailer(log_path, use_watchdog=not args.poll)

    logger.info(f"Watching {log_path} for anomalies (live)...")
    try:
        for line in tailer.tail():
            try:
                record = parse_line(line)
                if not record.parse_ok:
                    continue  # Ignore completely unparseable lines for inference

                # In live mode, predict takes a list of one record
                pred = model.predict([record], live=True)[0]
                score = model.score([record], live=True)[0]

                sig_matches = check_signatures(record.message)
                has_sig = len(sig_matches) > 0

                is_anomaly = (pred == -1) or (score > max_train_score) or has_sig

                if is_anomaly:
                    reasons = []
                    if has_sig:
                        reasons.append(f"Signature Match: {list(sig_matches.keys())}")
                    if (pred == -1) or (score > max_train_score):
                        reasons.append("ML Anomaly")

                    reason_str = " | ".join(reasons)
                    console.notify(record, score, reason_str)
                    slack.notify(record, score, reason_str)
                    if file_notifier:
                        file_notifier.notify(record, score, reason_str)
            except Exception as e:
                logger.error(f"Error processing line: {e}")

    except KeyboardInterrupt:
        logger.info("Stopping Sentinel...")
    finally:
        tailer.stop()
        slack.stop()


if __name__ == "__main__":
    main()
