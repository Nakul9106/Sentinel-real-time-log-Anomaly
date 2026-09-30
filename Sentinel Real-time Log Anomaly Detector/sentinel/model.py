from datetime import datetime

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .config import Config
from .features import FeatureExtractor
from .parser import LogRecord


class SentinelModel:
    def __init__(self, config: Config = None):
        if config is None:
            config = Config()

        m_cfg = config.model
        self.feature_extractor = FeatureExtractor(
            tfidf_max_features=m_cfg.tfidf_max_features,
            svd_components=m_cfg.svd_components,
            window_seconds=m_cfg.window_seconds,
        )
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=m_cfg.n_estimators,
            contamination=m_cfg.contamination,
            random_state=m_cfg.random_state,
            n_jobs=-1,
        )
        self.metadata = {}
        self.is_fitted = False

    def fit(self, records: list[LogRecord]):
        self.feature_extractor.fit(records)
        X = self.feature_extractor.transform(records)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)

        self.is_fitted = True

        # Calculate score percentiles for context
        scores = -self.model.decision_function(X_scaled)

        self.metadata = {
            "training_date": datetime.now().isoformat(),
            "row_count": len(records),
            "scikit_learn_version": sklearn.__version__,
            "contamination": self.model.contamination,
            "n_estimators": self.model.n_estimators,
            "max_training_score": float(np.max(scores)),
            "p99_training_score": float(np.percentile(scores, 99)),
        }

    def _prepare_data(self, records: list[LogRecord], live: bool = False) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Model is not fitted")
        X = self.feature_extractor.transform(records, live=live)
        return self.scaler.transform(X)

    def predict(self, records: list[LogRecord], live: bool = False) -> np.ndarray:
        X_scaled = self._prepare_data(records, live=live)
        return self.model.predict(X_scaled)

    def score(self, records: list[LogRecord], live: bool = False) -> np.ndarray:
        X_scaled = self._prepare_data(records, live=live)
        # Higher score = more anomalous
        return -self.model.decision_function(X_scaled)

    def save(self, path: str):
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted model")

        joblib.dump(
            {
                "feature_extractor": self.feature_extractor,
                "scaler": self.scaler,
                "model": self.model,
                "metadata": self.metadata,
            },
            path,
        )

    @classmethod
    def load(cls, path: str) -> "SentinelModel":
        data = joblib.load(path)

        loaded_sklearn = data.get("metadata", {}).get("scikit_learn_version")
        if loaded_sklearn and loaded_sklearn != sklearn.__version__:
            import logging

            logging.getLogger(__name__).warning(
                f"Model was trained with scikit-learn {loaded_sklearn}, but current is {sklearn.__version__}"
            )

        instance = cls()
        instance.feature_extractor = data["feature_extractor"]
        instance.scaler = data["scaler"]
        instance.model = data["model"]
        instance.metadata = data["metadata"]
        instance.is_fitted = True
        return instance
