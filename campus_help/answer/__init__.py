"""Extractive source-unit support for Campus Help."""

from .models import (
    ExtractionMethod,
    SourceSpan,
    SourceUnit,
    UnitType,
    EvidenceSelection,
    EvidenceCitation,
    ScoredSourceUnit,
    SelectionDiagnostics,
    ExtractiveDraft,
    QuotedEvidence,
    AnswerStatus,
    ValidationContext,
    ValidationIssue,
    ValidationIssueCode,
    ValidatedEvidence,
    ValidationResult,
    ValidationIssueSeverity,
    QuestionIntentType,
    EvidenceRequirement,
    QuestionValidationPlan,
    SufficiencyEvaluation,
    CandidateEvidenceMatch,
    RequirementMatchDiagnostics,
    EvidenceMatchReport,
    AssessmentReadiness,
    QuestionEvidenceAssessment,
)
from .source_units import extract_source_units
from .evidence import SELECTION_THRESHOLD, score_source_units, select_evidence
from .assembly import (
    AssemblyValidationError,
    assemble_evidence,
    format_citation,
)
from .validation import (
    ProvenanceValidationError,
    validate_evidence,
)
from .sufficiency import evaluate_evidence_sufficiency
from .question_planning import create_question_plan
from .evidence_matching import match_evidence_requirements
from .sufficiency_pipeline import evaluate_question_evidence

__all__ = [
    "ExtractionMethod",
    "EvidenceSelection",
    "EvidenceCitation",
    "ExtractiveDraft",
    "QuotedEvidence",
    "AnswerStatus",
    "ValidationContext",
    "ValidationIssue",
    "ValidationIssueCode",
    "ValidatedEvidence",
    "ValidationResult",
    "ValidationIssueSeverity",
    "QuestionIntentType",
    "EvidenceRequirement",
    "QuestionValidationPlan",
    "SufficiencyEvaluation",
    "evaluate_evidence_sufficiency",
    "create_question_plan",
    "CandidateEvidenceMatch",
    "RequirementMatchDiagnostics",
    "EvidenceMatchReport",
    "match_evidence_requirements",
    "AssessmentReadiness",
    "QuestionEvidenceAssessment",
    "evaluate_question_evidence",
    "ScoredSourceUnit",
    "SelectionDiagnostics",
    "SELECTION_THRESHOLD",
    "AssemblyValidationError",
    "assemble_evidence",
    "format_citation",
    "ProvenanceValidationError",
    "validate_evidence",
    "SourceSpan",
    "SourceUnit",
    "UnitType",
    "extract_source_units",
    "score_source_units",
    "select_evidence",
]
