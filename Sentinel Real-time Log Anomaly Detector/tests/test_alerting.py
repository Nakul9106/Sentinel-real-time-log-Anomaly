import time
from unittest.mock import MagicMock, patch

from sentinel.alerting import SlackNotifier, redact_secrets
from sentinel.parser import parse_line


def test_redact_secrets():
    raw1 = "GET /api/login?password=supersecret&user=admin HTTP/1.1"
    assert (
        redact_secrets(raw1)
        == "GET /api/login?password=***REDACTED***&user=admin HTTP/1.1"
    )

    raw2 = "Authorization: Bearer 12345abcdef"
    assert redact_secrets(raw2) == "Authorization: Bearer ***REDACTED***"

    raw3 = "Nothing to hide here"
    assert redact_secrets(raw3) == "Nothing to hide here"


@patch("sentinel.alerting.requests.post")
def test_slack_notifier_success(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="http://fake.url", cooldown_seconds=0)

    line = '10.0.0.1 - - [15/Jan/2025:10:00:00 +0000] "GET / HTTP/1.1" 200 123 "-" "-"'
    record = parse_line(line)

    notifier.notify(record, 5.0, "Test Reason", force=True)

    # Wait for the background thread to process
    time.sleep(0.1)
    notifier.stop()

    assert mock_post.called
    args, kwargs = mock_post.call_args
    assert kwargs["json"]["blocks"][1]["fields"][0]["text"] == "*Reason:*\nTest Reason"


@patch("sentinel.alerting.requests.post")
def test_slack_notifier_cooldown(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # High cooldown to ensure the second alert is skipped
    notifier = SlackNotifier(webhook_url="http://fake.url", cooldown_seconds=10)

    line = '10.0.0.1 - - [15/Jan/2025:10:00:00 +0000] "GET / HTTP/1.1" 200 123 "-" "-"'
    record = parse_line(line)

    # First alert should go through
    notifier.notify(record, 5.0, "Test Reason 1")
    # Second alert should be skipped due to cooldown
    notifier.notify(record, 6.0, "Test Reason 2")

    time.sleep(0.1)
    notifier.stop()

    assert mock_post.call_count == 1
