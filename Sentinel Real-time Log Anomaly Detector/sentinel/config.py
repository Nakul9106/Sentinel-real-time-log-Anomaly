import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModelConfig:
    tfidf_max_features: int = 2000
    svd_components: int = 30
    window_seconds: int = 60
    n_estimators: int = 200
    contamination: float = 0.005
    random_state: int = 42


@dataclass
class AlertingConfig:
    cooldown_seconds: int = 60
    slack_webhook_env_var: str = "SENTINEL_SLACK_WEBHOOK"


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)

    @classmethod
    def load(cls, path: str) -> "Config":
        p = Path(path)
        if not p.exists():
            return cls()

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        model_cfg = ModelConfig(**data.get("model", {}))
        alert_cfg = AlertingConfig(**data.get("alerting", {}))
        return cls(model=model_cfg, alerting=alert_cfg)
