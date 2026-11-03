"""Domain models for Outmate GTM."""

from app.domain.models.company import (
    CompanyFundingStage,
    CompanyProfile,
    IndustryCategory,
)
from app.domain.models.evidence import (
    EvidenceRecord,
    EvidenceSourceType,
    VerificationStatus,
)
from app.domain.models.person import (
    ContactCoordinates,
    DecisionMaker,
    Department,
    SeniorityLevel,
)
from app.domain.models.report import (
    GTMReport,
    RelevanceScore,
    RelevanceTier,
    ScoredDecisionMaker,
)

__all__ = [
    "CompanyFundingStage",
    "CompanyProfile",
    "ContactCoordinates",
    "DecisionMaker",
    "Department",
    "EvidenceRecord",
    "EvidenceSourceType",
    "GTMReport",
    "IndustryCategory",
    "RelevanceScore",
    "RelevanceTier",
    "ScoredDecisionMaker",
    "SeniorityLevel",
    "VerificationStatus",
]
