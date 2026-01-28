"""
Services Package for Loan Approval System
==========================================
Business logic and orchestration services.

Service Layer Architecture:
- Controllers are thin (HTTP handling only)
- All business logic in services
- All ML logic in ml_service
- Layered decisions in decision_engine
- Stateless API design
"""

from .loan_service import (
    LoanApplicationService,
    ApplicationInput,
    DecisionResult,
    ApplicationStatus,
    create_application_from_dict
)

from .ml_service import (
    MLPredictionService,
    ApplicantData,
    LoanData,
    PredictionResult,
    get_ml_service
)

from .decision_engine import (
    DecisionEngine,
    RuleEngine,
    MLScoringEngine,
    get_decision_engine,
    # DTOs
    ApplicantProfile,
    LoanRequest,
    FinalDecision,
    RuleResult,
    RuleEngineResult,
    MLScoreResult,
    # Enums
    DecisionOutcome,
    RuleStatus,
    RuleCategory
)

from .application_service import (
    ApplicationService,
    get_application_service,
    ApplicationNotFoundError,
    ApplicantNotFoundError,
    AccessDeniedError,
    InvalidStatusTransitionError,
    KYCRequiredError
)

from .rollback_service import (
    ModelRollbackService,
    DecisionHistoryStore,
    RollbackReason,
    RollbackStatus,
    DecisionRecord,
    RollbackRecord,
    ReExplanationResult,
    get_rollback_service
)

from .soft_reject_service import (
    SoftRejectService,
    ApplicantContext,
    SoftRejectResponse,
    ImprovementSuggestion,
    ImprovementCategory,
    ImprovementPriority,
    ImprovementDifficulty,
    get_soft_reject_service
)

from .anomaly_detection_service import (
    AnomalyDetectionService,
    Alert,
    AlertSeverity,
    AlertType,
    AlertStatus,
    ApplicationEvent,
    AnomalyMetrics,
    get_anomaly_detection_service
)

__all__ = [
    # Loan Service (Legacy)
    'LoanApplicationService',
    'ApplicationInput',
    'DecisionResult',
    'ApplicationStatus',
    'create_application_from_dict',
    
    # ML Prediction Service
    'MLPredictionService',
    'ApplicantData',
    'LoanData',
    'PredictionResult',
    'get_ml_service',
    
    # Decision Engine (Layered)
    'DecisionEngine',
    'RuleEngine',
    'MLScoringEngine',
    'get_decision_engine',
    'ApplicantProfile',
    'LoanRequest',
    'FinalDecision',
    'RuleResult',
    'RuleEngineResult',
    'MLScoreResult',
    'DecisionOutcome',
    'RuleStatus',
    'RuleCategory',
    
    # Application Service
    'ApplicationService',
    'get_application_service',
    'ApplicationNotFoundError',
    'ApplicantNotFoundError',
    'AccessDeniedError',
    'InvalidStatusTransitionError',
    'KYCRequiredError',
    
    # Rollback Service
    'ModelRollbackService',
    'DecisionHistoryStore',
    'RollbackReason',
    'RollbackStatus',
    'DecisionRecord',
    'RollbackRecord',
    'ReExplanationResult',
    'get_rollback_service',
    
    # Soft Reject Service
    'SoftRejectService',
    'ApplicantContext',
    'SoftRejectResponse',
    'ImprovementSuggestion',
    'ImprovementCategory',
    'ImprovementPriority',
    'ImprovementDifficulty',
    'get_soft_reject_service',
    
    # Anomaly Detection Service
    'AnomalyDetectionService',
    'Alert',
    'AlertSeverity',
    'AlertType',
    'AlertStatus',
    'ApplicationEvent',
    'AnomalyMetrics',
    'get_anomaly_detection_service'
]
