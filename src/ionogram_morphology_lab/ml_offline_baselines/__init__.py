"""ML-C.1 sealed, development-only offline baseline API."""
from .baselines import (
    LogisticRegressionBaseline,
    MajorityClassBaseline,
    NearestCentroidBaseline,
    get_baseline,
    list_baselines,
)
from .constants import *
from .errors import ExperimentStoreError, ImmutabilityError, PreflightError, ProtocolViolation
from .features import FEATURE_CONTRACT, FeatureScaler, extract_features_for_frame, normalize_frame, pool16_features
from .models import ExperimentConfig, ExperimentRecord
from .runner import run_experiment
from .store import OfflineBaselineStore

__all__ = [
    "ExperimentConfig", "ExperimentRecord", "OfflineBaselineStore", "run_experiment",
    "MajorityClassBaseline", "NearestCentroidBaseline", "LogisticRegressionBaseline",
    "get_baseline", "list_baselines", "FeatureScaler", "FEATURE_CONTRACT",
    "normalize_frame", "pool16_features", "extract_features_for_frame", "ProtocolViolation",
    "PreflightError", "ExperimentStoreError", "ImmutabilityError",
]
