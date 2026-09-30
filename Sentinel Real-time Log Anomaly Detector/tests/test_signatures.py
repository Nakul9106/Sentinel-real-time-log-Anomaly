from sentinel.signatures import check_signatures


def test_check_signatures_sqli():
    matches = check_signatures("SELECT * FROM users WHERE id = '1' OR '1'='1'")
    assert matches.get("sqli") == 2


def test_check_signatures_xss():
    matches = check_signatures("<script>alert(1)</script>")
    assert matches.get("xss") == 1


def test_check_signatures_traversal():
    matches = check_signatures("GET /../../../../etc/passwd")
    assert matches.get("traversal") == 4  # matches ../ and /etc/passwd


def test_check_signatures_scanner():
    matches = check_signatures("sqlmap/1.5")
    assert matches.get("scanner") == 1


def test_check_signatures_none():
    matches = check_signatures("Just a normal log message")
    assert len(matches) == 0
