"""MLflow tracking bridge (R20/R22): best-effort artifact + metric logging.

Fail-open by design: MLflow unavailability must never corrupt a training run
or an eval (telemetry is auxiliary; safety guards follow R46 instead and fail
closed). Every call is bounded and exception-safe; callers record success in
`model_versions.metrics_summary["mlflow_logged"]`.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("aegis.mlflow")


def log_training_run(*, run_name: str, params: dict, metrics: dict,
                     artifact_bytes: bytes | None = None,
                     artifact_name: str = "artifact.bin") -> bool:
    """Log one detector-training run. Returns True iff MLflow accepted it."""
    try:
        import mlflow  # optional dependency
    except ImportError:
        log.debug("mlflow_not_installed")
        return False
    try:
        mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params({k: v for k, v in params.items()
                               if isinstance(v, (str, int, float, bool))})
            mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
            if artifact_bytes:
                import tempfile
                from pathlib import Path

                with tempfile.TemporaryDirectory() as td:
                    p = Path(td) / artifact_name
                    p.write_bytes(artifact_bytes)
                    mlflow.log_artifact(str(p))
        return True
    except Exception as exc:
        log.warning("mlflow_log_failed", exc_info=exc)
        return False
