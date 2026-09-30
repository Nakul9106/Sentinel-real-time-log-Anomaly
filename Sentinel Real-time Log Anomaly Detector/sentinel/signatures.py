import re

# Signatures for known attacks
SIGNATURES = {
    "sqli": re.compile(
        r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|;\s*--|'\s*or\s*'1'\s*=\s*'1)"
    ),
    "xss": re.compile(r"(?i)(<script>|javascript:|onerror\s*=)"),
    "traversal": re.compile(r"(?i)(\.\./|\.\.\\|%2e%2e%2f|/etc/passwd|win\.ini)"),
    "shell": re.compile(
        r"(?i)(\||\b;\b|`|\$\(|\b/bin/sh\b|\b/bin/bash\b|\bcmd\.exe\b)"
    ),
    "scanner": re.compile(r"(?i)(sqlmap|nikto|nmap|nessus|openvas|zmap)"),
}


def check_signatures(text: str) -> dict[str, int]:
    """
    Checks the given text against known signatures.
    Returns a dictionary of signature names and their match counts.
    """
    matches = {}
    if not text:
        return matches

    for name, pattern in SIGNATURES.items():
        count = len(pattern.findall(text))
        if count > 0:
            matches[name] = count
    return matches
