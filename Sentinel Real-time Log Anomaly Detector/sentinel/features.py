import re
import time

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from .parser import LogRecord
from .signatures import check_signatures


class ContextTracker:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.history = []  # list of dicts: {"time": float, "status": int, "ip": str}

    def _cleanup(self, current_time: float):
        cutoff = current_time - self.window_seconds
        self.history = [x for x in self.history if x["time"] > cutoff]

    def update_and_get_features(
        self, record: LogRecord, current_time: float = None
    ) -> list[float]:
        if current_time is None:
            current_time = time.time()

        self._cleanup(current_time)

        reqs_in_window = len(self.history)
        errs_in_window = sum(
            1 for x in self.history if x["status"] and x["status"] >= 500
        )
        same_ip_count = sum(1 for x in self.history if x["ip"] == record.ip)

        error_ratio = errs_in_window / reqs_in_window if reqs_in_window > 0 else 0.0

        if record.status is not None:
            self.history.append(
                {"time": current_time, "status": record.status, "ip": record.ip}
            )

        return [
            float(reqs_in_window),
            float(errs_in_window),
            error_ratio,
            float(same_ip_count),
        ]


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\d+\.\d+\.\d+\.\d+", "<IP>", text)
    text = re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "<UUID>",
        text,
    )
    text = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", text)
    text = re.sub(r"\d+", "<NUM>", text)
    return text


class FeatureExtractor:
    def __init__(
        self,
        tfidf_max_features: int = 2000,
        svd_components: int = 30,
        window_seconds: int = 60,
    ):
        self.tfidf = TfidfVectorizer(max_features=tfidf_max_features)
        self.svd = TruncatedSVD(n_components=svd_components, random_state=42)
        self.context_tracker = ContextTracker(window_seconds=window_seconds)
        self.is_fitted = False
        self.svd_components = svd_components

    def _extract_numeric(self, record: LogRecord) -> list[float]:
        msg = record.message or ""
        msg_len = len(msg)
        token_count = len(msg.split())

        digit_count = sum(c.isdigit() for c in msg)
        digit_ratio = digit_count / msg_len if msg_len > 0 else 0.0

        special_count = sum(not c.isalnum() and not c.isspace() for c in msg)
        special_ratio = special_count / msg_len if msg_len > 0 else 0.0

        level_code = 0
        if record.level == "WARNING":
            level_code = 1
        elif record.level == "ERROR":
            level_code = 2
        elif record.level in ["CRITICAL", "FATAL"]:
            level_code = 3

        status_class = 0
        if record.status:
            status_class = record.status // 100

        bytes_sent = record.bytes_sent or 0
        log_bytes = np.log1p(bytes_sent)

        # Signatures
        sig_matches = check_signatures(msg)
        sqli_cnt = sig_matches.get("sqli", 0)
        xss_cnt = sig_matches.get("xss", 0)
        traversal_cnt = sig_matches.get("traversal", 0)
        shell_cnt = sig_matches.get("shell", 0)
        scanner_cnt = sig_matches.get("scanner", 0)

        return [
            float(msg_len),
            float(token_count),
            digit_ratio,
            special_ratio,
            float(level_code),
            float(status_class),
            float(log_bytes),
            float(sqli_cnt),
            float(xss_cnt),
            float(traversal_cnt),
            float(shell_cnt),
            float(scanner_cnt),
        ]

    def fit(self, records: list[LogRecord]):
        texts = [normalize_text(r.message) for r in records]
        tfidf_matrix = self.tfidf.fit_transform(texts)
        if tfidf_matrix.shape[1] > self.svd_components:
            self.svd.fit(tfidf_matrix)
        self.is_fitted = True

    def transform(self, records: list[LogRecord], live: bool = False) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("FeatureExtractor is not fitted")

        texts = [normalize_text(r.message) for r in records]
        tfidf_matrix = self.tfidf.transform(texts)

        if tfidf_matrix.shape[1] > self.svd_components:
            text_features = self.svd.transform(tfidf_matrix)
        else:
            text_features = tfidf_matrix.toarray()
            pad_width = self.svd_components - text_features.shape[1]
            if pad_width > 0:
                text_features = np.pad(
                    text_features, ((0, 0), (0, pad_width)), mode="constant"
                )

        numeric_features = []
        for i, record in enumerate(records):
            num = self._extract_numeric(record)
            if live:
                current_time = time.time()
            else:
                current_time = float(i)
            ctx = self.context_tracker.update_and_get_features(
                record, current_time=current_time
            )
            numeric_features.append(num + ctx)

        num_arr = np.array(numeric_features)
        combined = np.hstack((text_features, num_arr))
        return combined
