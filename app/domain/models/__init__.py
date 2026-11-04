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
    generate_evidence_id,
)
from app.domain.models.person import (
    ContactCoordinates,
    DecisionInfluenceCategory,
    DecisionMaker,
    DecisionMakerAssessment,
    Department,
    EmploymentStatus,
    RoleCategory,
    SeniorityLevel,
    generate_person_id,
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
    "DecisionInfluenceCategory",
    "DecisionMaker",
    "DecisionMakerAssessment",
    "Department",
    "EmploymentStatus",
    "EvidenceRecord",
    "EvidenceSourceType",
    "GTMReport",
    "IndustryCategory",
    "RelevanceScore",
    "RelevanceTier",
    "RoleCategory",
    "ScoredDecisionMaker",
    "SeniorityLevel",
    "VerificationStatus",
    "generate_evidence_id",
    "generate_person_id",
]
