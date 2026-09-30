import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LogRecord:
    raw: str
    timestamp: str | None = None
    level: str | None = None
    ip: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    bytes_sent: int | None = None
    user_agent: str | None = None
    message: str | None = None
    source_format: str | None = None
    parse_ok: bool = False


# Nginx/Apache Combined Log Format
# Example: 127.0.0.1 - - [15/Jan/2025:10:23:45 +0000] "GET /api/v1/users HTTP/1.1" 200 1024 "-" "Mozilla/5.0"
NGINX_COMBINED_REGEX = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<request>[^"]*)" '
    r"(?P<status>\d{3}) (?P<bytes_sent>\d+|-)"
    r'(?: "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)")?'
)

# Generic App Log Format
# Example: 2025-01-15 10:23:45,123 ERROR [payments] Timeout calling gateway
APP_LOG_REGEX = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?)\s+"
    r"(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\s+"
    r"(?:\[(?P<component>[^\]]+)\]\s+)?"
    r"(?P<message>.*)$"
)


def _get_level_from_status(status: int) -> str:
    if status >= 500:
        return "ERROR"
    elif status >= 400:
        return "WARNING"
    return "INFO"


def parse_line(line: str) -> LogRecord:
    """
    Parses a single log line into a LogRecord.
    Never raises an exception.
    """
    if not line:
        return LogRecord(raw=line, parse_ok=False, message="")

    line = line.strip()

    try:
        # Try generic app log first as it is strict on timestamp/level at the start
        app_match = APP_LOG_REGEX.match(line)
        if app_match:
            d = app_match.groupdict()
            level = d["level"].upper()
            if level == "WARN":
                level = "WARNING"
            if level == "FATAL":
                level = "CRITICAL"

            return LogRecord(
                raw=line,
                timestamp=d["timestamp"],
                level=level,
                message=d["message"],
                source_format="app",
                parse_ok=True,
            )

        # Try nginx combined
        nginx_match = NGINX_COMBINED_REGEX.match(line)
        if nginx_match:
            d = nginx_match.groupdict()
            status_str = d["status"]
            status = int(status_str) if status_str.isdigit() else None

            bytes_str = d["bytes_sent"]
            bytes_sent = int(bytes_str) if bytes_str and bytes_str.isdigit() else 0

            request = d["request"] or ""
            req_parts = request.split()
            method = req_parts[0] if len(req_parts) > 0 else None
            path = req_parts[1] if len(req_parts) > 1 else None

            ua = d.get("user_agent") or ""
            message = f"{request} {ua}".strip()

            level = _get_level_from_status(status) if status else "INFO"

            return LogRecord(
                raw=line,
                timestamp=d["timestamp"],
                level=level,
                ip=d["ip"],
                method=method,
                path=path,
                status=status,
                bytes_sent=bytes_sent,
                user_agent=ua,
                message=message,
                source_format="nginx",
                parse_ok=True,
            )

    except Exception:
        # Failsafe
        pass

    # Fallback
    return LogRecord(raw=line, parse_ok=False, message=line)
