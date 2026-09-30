import os
import threading
import time

import pytest

from sentinel.ingestor import LogTailer


def test_tailer_append(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("line1\n", encoding="utf-8")

    tailer = LogTailer(log_file, use_watchdog=False, poll_interval=0.01)

    lines_read = []

    def tail_thread():
        for line in tailer.tail():
            lines_read.append(line)

    t = threading.Thread(target=tail_thread)
    t.start()

    time.sleep(0.05)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write("line2\n")
        f.write("line3\n")

    time.sleep(0.1)
    tailer.stop()
    t.join(timeout=1.0)

    assert lines_read == ["line2", "line3"]


@pytest.mark.skipif(os.name == "nt", reason="Windows locks open files")
def test_tailer_rotation(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("line1\n", encoding="utf-8")

    tailer = LogTailer(log_file, use_watchdog=False, poll_interval=0.01)

    lines_read = []

    def tail_thread():
        for line in tailer.tail():
            lines_read.append(line)

    t = threading.Thread(target=tail_thread)
    t.start()

    time.sleep(0.05)

    # Simulate rotation by moving the file and creating a new one
    log_file.rename(tmp_path / "test.log.1")

    with open(log_file, "w", encoding="utf-8") as f:
        f.write("line2\n")

    time.sleep(0.1)
    tailer.stop()
    t.join(timeout=1.0)

    assert lines_read == ["line2"]


def test_tailer_truncation(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("line1\n", encoding="utf-8")

    tailer = LogTailer(log_file, use_watchdog=False, poll_interval=0.01)

    lines_read = []

    def tail_thread():
        for line in tailer.tail():
            lines_read.append(line)

    t = threading.Thread(target=tail_thread)
    t.start()

    time.sleep(0.05)

    # Simulate truncation (truncate to 0 first to ensure tailer detects size drop)
    with open(log_file, "w", encoding="utf-8") as f:
        pass

    time.sleep(0.05)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write("line2\n")

    time.sleep(0.1)
    tailer.stop()
    t.join(timeout=1.0)

    assert lines_read == ["line2"]
