import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Normal data pools
IPS = [
    "192.168.1.10",
    "10.0.0.5",
    "172.16.0.4",
    "8.8.8.8",
    "1.1.1.1",
    "127.0.0.1",
    "192.168.2.20",
]
PATHS = [
    "/",
    "/index.html",
    "/api/v1/users",
    "/api/v1/products",
    "/images/logo.png",
    "/login",
    "/about",
    "/contact",
]
UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
]
METHODS = ["GET", "POST", "HEAD"]
STATUS_CODES = [200] * 50 + [304] * 10 + [301] * 5 + [404] * 5 + [401] * 2 + [500] * 1

# Anomaly data pools
ANOMALY_TYPES = [
    "sqli",
    "xss",
    "traversal",
    "scanner",
    "bruteforce",
    "error_burst",
    "long_url",
]
SQLI_PAYLOADS = ["' OR '1'='1", "UNION SELECT * FROM users", "'; DROP TABLE users--"]
XSS_PAYLOADS = ["<script>alert(1)</script>", "javascript:eval('1')"]
TRAVERSAL_PAYLOADS = ["../../../../etc/passwd", "..%2F..%2F..%2Fwindows%2Fwin.ini"]
SCANNER_UAS = ["sqlmap/1.5", "Nikto/2.1.6", "curl/7.68.0"]


def generate_normal_line(time_str):
    ip = random.choice(IPS)
    method = random.choices(METHODS, weights=[0.8, 0.15, 0.05])[0]
    path = random.choice(PATHS)
    status = random.choice(STATUS_CODES)
    bytes_sent = random.randint(200, 5000)
    ua = random.choice(UAS)
    return f'{ip} - - [{time_str}] "{method} {path} HTTP/1.1" {status} {bytes_sent} "-" "{ua}"'


def generate_anomaly(time_str, anomaly_type, burst_ip=None):
    ip = burst_ip if burst_ip else f"10.99.99.{random.randint(1, 254)}"
    method = "GET"
    path = "/api/v1/search?q="
    status = 200
    bytes_sent = random.randint(200, 5000)
    ua = random.choice(UAS)

    if anomaly_type == "sqli":
        path += random.choice(SQLI_PAYLOADS)
    elif anomaly_type == "xss":
        path += random.choice(XSS_PAYLOADS)
    elif anomaly_type == "traversal":
        path = random.choice(TRAVERSAL_PAYLOADS)
    elif anomaly_type == "scanner":
        ua = random.choice(SCANNER_UAS)
        path = random.choice(PATHS)
    elif anomaly_type == "bruteforce":
        method = "POST"
        path = "/login"
        status = 401
    elif anomaly_type == "error_burst":
        method = random.choice(METHODS)
        path = random.choice(PATHS)
        status = random.choice([500, 502, 503])
    elif anomaly_type == "long_url":
        path = "/" + "a" * 2000

    return f'{ip} - - [{time_str}] "{method} {path} HTTP/1.1" {status} {bytes_sent} "-" "{ua}"'


def main():
    parser = argparse.ArgumentParser(description="Log Generator")
    parser.add_argument("--mode", choices=["normal", "mixed"], required=True)
    parser.add_argument(
        "--lines",
        type=int,
        default=None,
        help="Number of lines to generate (required unless --live)",
    )
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--anomaly-rate", type=float, default=0.03)
    parser.add_argument("--labels", type=str)
    parser.add_argument(
        "--live", action="store_true", help="Generate logs continuously in real-time"
    )
    parser.add_argument(
        "--rate", type=int, default=10, help="Lines per second for live generation"
    )

    args = parser.parse_args()

    if not args.live and args.lines is None:
        parser.error("--lines is required unless --live is specified")

    random.seed(args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    labels_path = None
    if args.labels:
        labels_path = Path(args.labels)
    elif args.mode == "mixed" and not args.live:
        labels_path = out_path.with_suffix(".labels.csv")

    current_time = datetime(2025, 1, 15, 10, 0, 0)

    labels_data = []
    pending_anomalies = []

    import time

    # Open in append mode if live, else write
    file_mode = "a" if args.live else "w"
    lines_written = 0
    current_burst_ip = None

    print(f"Starting generation to {out_path} (live: {args.live})")

    with open(out_path, file_mode, encoding="utf-8") as f:
        while True:
            if not args.live and lines_written >= args.lines:
                break

            if args.live:
                current_time = datetime.now()

            time_str = current_time.strftime("%d/%b/%Y:%H:%M:%S +0000")

            if pending_anomalies:
                anomaly_type = pending_anomalies.pop(0)
                line = generate_anomaly(
                    time_str, anomaly_type, burst_ip=current_burst_ip
                )
                if not args.live:
                    labels_data.append([lines_written + 1, 1, anomaly_type])
            else:
                is_anomaly = (
                    args.mode == "mixed" and random.random() < args.anomaly_rate
                )

                if is_anomaly:
                    anomaly_type = random.choice(ANOMALY_TYPES)
                    current_burst_ip = f"10.99.99.{random.randint(1, 254)}"
                    if anomaly_type == "error_burst":
                        pending_anomalies = ["error_burst"] * random.randint(5, 15)
                    elif anomaly_type == "bruteforce":
                        pending_anomalies = ["bruteforce"] * random.randint(5, 15)

                    line = generate_anomaly(
                        time_str, anomaly_type, burst_ip=current_burst_ip
                    )
                    if not args.live:
                        labels_data.append([lines_written + 1, 1, anomaly_type])
                else:
                    line = generate_normal_line(time_str)
                    if not args.live:
                        labels_data.append([lines_written + 1, 0, "normal"])

            f.write(line + "\n")
            lines_written += 1

            if args.live:
                f.flush()
                time.sleep(1.0 / args.rate)
            else:
                # realistic traffic rhythm - wait between 0 and 2 seconds
                current_time += timedelta(milliseconds=random.randint(10, 2000))

    if labels_path and args.mode == "mixed" and not args.live:
        with open(labels_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["line_number", "label", "type"])
            writer.writerows(labels_data)

    print(f"Generated {lines_written} lines to {out_path}")
    if labels_path and args.mode == "mixed" and not args.live:
        print(f"Generated labels to {labels_path}")


if __name__ == "__main__":
    main()
