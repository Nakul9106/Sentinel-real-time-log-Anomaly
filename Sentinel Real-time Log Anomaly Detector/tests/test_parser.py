from sentinel.parser import parse_line


def test_parse_nginx_combined():
    line = '127.0.0.1 - - [15/Jan/2025:10:23:45 +0000] "GET /api/v1/users HTTP/1.1" 200 1024 "-" "Mozilla/5.0"'
    record = parse_line(line)
    assert record.parse_ok is True
    assert record.source_format == "nginx"
    assert record.ip == "127.0.0.1"
    assert record.timestamp == "15/Jan/2025:10:23:45 +0000"
    assert record.method == "GET"
    assert record.path == "/api/v1/users"
    assert record.status == 200
    assert record.bytes_sent == 1024
    assert record.level == "INFO"
    assert record.user_agent == "Mozilla/5.0"
    assert record.message == "GET /api/v1/users HTTP/1.1 Mozilla/5.0"


def test_parse_nginx_errors():
    line = '192.168.1.1 - - [15/Jan/2025:10:23:45 +0000] "POST /login HTTP/1.1" 500 45 "-" "curl/7.68.0"'
    record = parse_line(line)
    assert record.parse_ok is True
    assert record.status == 500
    assert record.level == "ERROR"

    line2 = '10.0.0.1 - - [15/Jan/2025:10:23:45 +0000] "GET /admin HTTP/1.1" 403 12 "-" "BadBot"'
    record2 = parse_line(line2)
    assert record2.parse_ok is True
    assert record2.status == 403
    assert record2.level == "WARNING"


def test_parse_app_log():
    line = "2025-01-15 10:23:45,123 ERROR [payments] Timeout calling gateway"
    record = parse_line(line)
    assert record.parse_ok is True
    assert record.source_format == "app"
    assert record.timestamp == "2025-01-15 10:23:45,123"
    assert record.level == "ERROR"
    assert record.message == "Timeout calling gateway"


def test_parse_app_log_no_component():
    line = "2025-01-15 10:23:45 INFO Application started successfully"
    record = parse_line(line)
    assert record.parse_ok is True
    assert record.source_format == "app"
    assert record.level == "INFO"
    assert record.message == "Application started successfully"


def test_parse_fallback():
    line = "Some random text that is not a log line"
    record = parse_line(line)
    assert record.parse_ok is False
    assert record.message == line
    assert record.raw == line


def test_parse_empty():
    record = parse_line("")
    assert record.parse_ok is False
    assert record.message == ""


def test_parse_malformed_nginx():
    line = '127.0.0.1 - - [15/Jan/2025:10:23:45 +0000] "GET / HTTP/1.1" ABC - "-" "-"'
    record = parse_line(line)
    # The regex \d{3} for status won't match "ABC", so it falls back to parsing failure
    assert record.parse_ok is False
    assert record.message == line


def test_parse_never_raises():
    try:
        parse_line(None)  # type: ignore
    except Exception:
        assert False, "parse_line raised an exception"
