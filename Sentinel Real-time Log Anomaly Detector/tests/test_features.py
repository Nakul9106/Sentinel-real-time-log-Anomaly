from sentinel.features import ContextTracker, FeatureExtractor, normalize_text
from sentinel.parser import LogRecord


def test_normalize_text():
    assert normalize_text("IP 192.168.1.1 is here") == "IP <IP> is here"
    assert normalize_text("ID is 12345") == "ID is <NUM>"


def test_context_tracker():
    tracker = ContextTracker(window_seconds=60)

    r1 = LogRecord(raw="", ip="1.2.3.4", status=200)
    features1 = tracker.update_and_get_features(r1, current_time=10.0)
    assert features1 == [0.0, 0.0, 0.0, 0.0]  # First request sees empty history

    r2 = LogRecord(raw="", ip="1.2.3.4", status=500)
    features2 = tracker.update_and_get_features(r2, current_time=20.0)
    assert features2 == [1.0, 0.0, 0.0, 1.0]  # Sees r1

    r3 = LogRecord(raw="", ip="5.6.7.8", status=200)
    features3 = tracker.update_and_get_features(r3, current_time=100.0)
    # r1 (time 10) should be dropped as it's older than 100-60=40
    # r2 (time 20) should also be dropped
    assert features3 == [0.0, 0.0, 0.0, 0.0]


def test_feature_extractor():
    records = [
        LogRecord(
            raw="",
            message="Normal request here",
            level="INFO",
            status=200,
            bytes_sent=500,
        ),
        LogRecord(
            raw="",
            message="SELECT * FROM users",
            level="ERROR",
            status=500,
            bytes_sent=10,
        ),
    ]

    extractor = FeatureExtractor(svd_components=2)
    extractor.fit(records)

    features = extractor.transform(records)
    assert features.shape[0] == 2
    # SVD components + numeric + context
    # Numeric: msg_len, tokens, digits, special, level, status, log_bytes, sqli, xss, trav, shell, scanner (12 features)
    # Context: reqs, errs, err_ratio, same_ip (4 features)
    assert features.shape[1] == 2 + 12 + 4

    # Check that the sqli signature is flagged for the second record
    # sqli is at index svd_components + 7 = 2 + 7 = 9
    assert features[1][9] >= 1.0
