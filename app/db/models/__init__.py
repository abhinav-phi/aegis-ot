"""Model re-exports."""
from app.db.models.agent import AgentMessage, AgentRun
from app.db.models.approvals import ApprovalRequest
from app.db.models.base import coerce_uuid_columns
from app.db.models.datasets import Dataset, DatasetRun
from app.db.models.evaluation import (
    AuditLog,
    ChannelReduction,
    EvaluationRun,
    InjectionCase,
    MetricRow,
)
from app.db.models.identity import RefreshToken, User, UserRole
from app.db.models.incidents import Incident, ThreatMapping
from app.db.models.pipeline import Anomaly, AnomalyExplanation, Detection, ModelVersion
from app.db.models.rag import RagChunk, RagDocument, RetrievalEvent
from app.db.models.sandbox import SimulatedAction
from app.db.models.validator import MitigationPlan, ValidatorResult

coerce_uuid_columns()

__all__ = [
    "AgentMessage", "AgentRun", "Anomaly", "AnomalyExplanation", "ApprovalRequest",
    "AuditLog", "ChannelReduction", "Dataset", "DatasetRun", "Detection",
    "EvaluationRun", "Incident", "InjectionCase", "MetricRow", "MitigationPlan",
    "ModelVersion", "RagChunk", "RagDocument", "RefreshToken", "RetrievalEvent",
    "SimulatedAction", "ThreatMapping", "User", "UserRole", "ValidatorResult",
]
