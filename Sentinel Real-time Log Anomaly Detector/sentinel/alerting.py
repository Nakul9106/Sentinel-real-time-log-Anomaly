import json
import logging
import os
import queue
import re
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Basic secret redaction patterns
REDACTION_PATTERNS = [
    (
        re.compile(r"(?i)(password|passwd|pwd|secret|key|token|auth)=[^&\s]+"),
        r"\1=***REDACTED***",
    ),
    (
        re.compile(r"(?i)authorization:\s*(bearer|basic)\s+[^\s]+"),
        r"Authorization: \1 ***REDACTED***",
    ),
]


def redact_secrets(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SlackNotifier:
    def __init__(
        self,
        webhook_url: str | None = None,
        cooldown_seconds: int = 60,
        dry_run: bool = False,
    ):
        self.webhook_url = webhook_url or os.environ.get("SENTINEL_SLACK_WEBHOOK")
        self.cooldown_seconds = cooldown_seconds
        self.dry_run = dry_run

        self._last_alert_time = 0.0
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._stop_event.set()
        self._queue.put(None)  # wake up worker
        self._worker_thread.join(timeout=2.0)

    def _build_block_kit(self, record, score, reason) -> dict[str, Any]:
        redacted_raw = redact_secrets(record.raw)

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Sentinel Anomaly Detected",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Reason:*\n{reason}"},
                        {"type": "mrkdwn", "text": f"*Anomaly Score:*\n{score:.4f}"},
                    ],
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*IP Address:*\n{record.ip or 'Unknown'}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Path:*\n{record.path or 'Unknown'}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Raw Log:*\n```{redacted_raw}```",
                    },
                },
            ]
        }

    def notify(self, record, score: float, reason: str, force: bool = False):
        """Queue an alert to be sent to Slack."""
        now = time.time()
        if not force and (now - self._last_alert_time) < self.cooldown_seconds:
            # Rate limited
            logger.debug("Alert skipped due to cooldown.")
            return

        self._last_alert_time = now
        payload = self._build_block_kit(record, score, reason)
        self._queue.put(payload)

    def _send_with_backoff(self, payload: dict):
        if self.dry_run:
            print("[DRY RUN] Slack Payload:")
            print(json.dumps(payload, indent=2))
            return

        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured. Cannot send alert.")
            return

        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=5.0)
                response.raise_for_status()
                return  # Success
            except requests.RequestException as e:
                logger.error(f"Failed to send Slack alert (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                payload = self._queue.get(timeout=0.5)
                if payload is None:
                    break
                self._send_with_backoff(payload)
                self._queue.task_done()
            except queue.Empty:
                continue


class FileNotifier:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def notify(self, record, score: float, reason: str, force: bool = False):
        payload = {
            "timestamp": time.time(),
            "reason": reason,
            "score": score,
            "ip": record.ip,
            "path": record.path,
            "raw": redact_secrets(record.raw)
        }
        with open(self.filepath, "a") as f:
            f.write(json.dumps(payload) + "\n")
