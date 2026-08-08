"""ML-C.1 protocol exceptions."""
from __future__ import annotations


class ProtocolViolation(Exception):
    """Raised when code attempts a prohibited protocol action."""


class PreflightError(Exception):
    """Raised when one or more fail-closed preflight checks fail."""

    def __init__(self, blockers: list[str]) -> None:
        self.blockers = list(blockers)
        super().__init__("Preflight blocked: " + "; ".join(self.blockers))


class ExperimentStoreError(Exception):
    """Raised for invalid experiment-store operations."""


class ImmutabilityError(Exception):
    """Raised when an immutable completed experiment is changed."""


class LabelIntegrityError(Exception):
    """Raised when TRAIN/DEVELOPMENT/prediction morphology labels are invalid."""
