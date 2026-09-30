import subprocess
import sys
import time
from pathlib import Path


def test_e2e_anomaly_detection(tmp_path):
    # Setup paths
    log_file = tmp_path / "live_e2e.log"
    model_file = Path("models/sentinel_model.joblib")

    # Ensure model exists, if not we skip or error out (assume it's trained from previous steps)
    if not model_path_exists(model_file):
        print("Model not found, skipping E2E test. Run train.py first.")
        return

    # Start generator
    gen_cmd = [
        sys.executable,
        "scripts/generate_logs.py",
        "--mode",
        "mixed",
        "--out",
        str(log_file),
        "--live",
        "--rate",
        "50",
    ]
    gen_proc = subprocess.Popen(gen_cmd)

    # Start sentinel (give generator a tiny head start to create file)
    time.sleep(1)
    sentinel_cmd = [
        sys.executable,
        "-u",
        "-m",
        "sentinel",
        "--model",
        str(model_file),
        "--log",
        str(log_file),
        "--dry-run",
        "--cooldown",
        "0",
    ]

    # We use subprocess.PIPE to read output
    # We run it for a few seconds
    sentinel_proc = subprocess.Popen(
        sentinel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # Wait for generator to generate and sentinel to read
    time.sleep(5)

    # Terminate generator
    gen_proc.terminate()

    # Let Sentinel process the last lines
    time.sleep(1)

    # Kill sentinel
    sentinel_proc.terminate()

    try:
        stdout, stderr = sentinel_proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        sentinel_proc.kill()
        stdout, stderr = sentinel_proc.communicate()

    # Verify that an alert was triggered
    assert "[ALERT]" in stdout, (
        f"Expected [ALERT] in output. Got:\n{stdout}\nSTDERR:\n{stderr}"
    )


def model_path_exists(path):
    return Path(path).exists()
