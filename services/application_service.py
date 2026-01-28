"""
Application Service Layer
=========================
Business logic for loan applications, separate from controllers.

This service handles:
- Application creation/updates
- Status transitions
- ML prediction orchestration (via Decision Engine)
- Audit logging

Author: Loan Analytics Team
Version: 2.0.0
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID
import logging

from sqlalchemy.orm import Session

from database.models import (
    User, Applicant, LoanApplication, ApplicationStatus, LoanType,
    ApplicationAuditLog, AuditAction
)
from services.ml_service import (
    MLPredictionService, ApplicantData, LoanData, PredictionResult,
    get_ml_service
)
from services.decision_engine import (
    DecisionEngine, get_decision_engine,
    ApplicantProfile, LoanRequest, FinalDecision,
    DecisionOutcome, RuleEngineResult, MLScoreResult
)

logger = logging.getLogger(__name__)


class ApplicationServiceError(Exception):
    """Base exception for application service errors."""
    def __init__(self, message: str, code: str = "APPLICATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ApplicationNotFoundError(ApplicationServiceError):
    """Application not found."""
    def __init__(self, application_id: UUID):
        super().__init__(
            f"Application {application_id} not found",
            "APPLICATION_NOT_FOUND"
        )


class ApplicantNotFoundError(ApplicationServiceError):
    """Applicant not found."""
    def __init__(self, applicant_id: UUID):
        super().__init__(
            f"Applicant {applicant_id} not found",
            "APPLICANT_NOT_FOUND"
        )


class InvalidStatusTransitionError(ApplicationServiceError):
    """Invalid status transition."""
    def __init__(self, current: str, target: str):
        super().__init__(
            f"Cannot transition from {current} to {target}",
            "INVALID_STATUS_TRANSITION"
        )


class AccessDeniedError(ApplicationServiceError):
    """Access denied."""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "ACCESS_DENIED")


class KYCRequiredError(ApplicationServiceError):
    """KYC verification required."""
    def __init__(self):
        super().__init__(
            "Applicant KYC must be verified before submitting",
            "KYC_REQUIRED"
        )


class ApplicationService:
    """
    Service for loan application business logic.
    
    This service is stateless - all state is passed via parameters.
    Database session is injected for each operation.
    """
    
    # Valid status transitions
    STATUS_TRANSITIONS = {
        ApplicationStatus.DRAFT: [ApplicationStatus.PENDING, ApplicationStatus.CANCELLED],
        ApplicationStatus.PENDING: [ApplicationStatus.UNDER_REVIEW, ApplicationStatus.CANCELLED],
        ApplicationStatus.UNDER_REVIEW: [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED],
        ApplicationStatus.APPROVED: [ApplicationStatus.DISBURSED, ApplicationStatus.CANCELLED],
        ApplicationStatus.REJECTED: [],  # Terminal state
        ApplicationStatus.DISBURSED: [ApplicationStatus.CLOSED],
        ApplicationStatus.CLOSED: [],  # Terminal state
        ApplicationStatus.CANCELLED: [],  # Terminal state
    }
    
    def __init__(
        self,
        ml_service: Optional[MLPredictionService] = None,
        decision_engine: Optional[DecisionEngine] = None
    ):
        """Initialize with optional ML service and decision engine."""
        self._ml_service = ml_service or get_ml_service()
        self._decision_engine = decision_engine or get_decision_engine()
    
    def get_application(
        self,
        db: Session,
        application_id: UUID,
        user: User,
        include_deleted: bool = False
    ) -> LoanApplication:
        """
        Get application by ID with access control.
        
        Args:
            db: Database session
            application_id: Application UUID
            user: Current user for access control
            include_deleted: Whether to include soft-deleted applications
            
        Returns:
            LoanApplication instance
            
        Raises:
            ApplicationNotFoundError: If not found
            AccessDeniedError: If user doesn't have access
        """
        query = db.query(LoanApplication).filter(LoanApplication.id == application_id)
        
        if not include_deleted:
            query = query.filter(LoanApplication.is_deleted == False)
        
        application = query.first()
        
        if not application:
            raise ApplicationNotFoundError(application_id)
        
        # Access control for regular users
        if user.role.value == "applicant":
            if application.applicant.user_id != user.id:
                raise AccessDeniedError()
        
        return application
    
    def create_application(
        self,
        db: Session,
        applicant_id: UUID,
        loan_type: str,
        loan_amount: Decimal,
        loan_term_months: int,
        user: User,
        interest_rate_requested: Optional[Decimal] = None,
        purpose: Optional[str] = None,
        purpose_description: Optional[str] = None,
        collateral_type: Optional[str] = None,
        collateral_value: Decimal = Decimal(0),
        co_applicant_name: Optional[str] = None,
        co_applicant_income: Decimal = Decimal(0),
        co_applicant_relationship: Optional[str] = None
    ) -> LoanApplication:
        """
        Create a new loan application.
        
        Args:
            db: Database session
            applicant_id: Applicant UUID
            loan_type: Type of loan
            loan_amount: Requested amount
            loan_term_months: Term in months
            user: Creating user
            ... other optional fields
            
        Returns:
            Created LoanApplication
            
        Raises:
            ApplicantNotFoundError: If applicant not found
            AccessDeniedError: If user can't create for this applicant
        """
        # Verify applicant exists
        applicant = db.query(Applicant).filter(
            Applicant.id == applicant_id,
            Applicant.is_deleted == False
        ).first()
        
        if not applicant:
            raise ApplicantNotFoundError(applicant_id)
        
        # Access control
        if user.role.value == "applicant" and applicant.user_id != user.id:
            raise AccessDeniedError("Cannot create application for another user")
        
        # Parse loan type
        try:
            loan_type_enum = LoanType(loan_type)
        except ValueError:
            loan_type_enum = LoanType.PERSONAL
        
        # Create application
        application = LoanApplication(
            applicant_id=applicant_id,
            loan_type=loan_type_enum,
            loan_amount=loan_amount,
            loan_term_months=loan_term_months,
            interest_rate_requested=interest_rate_requested,
            purpose=purpose,
            purpose_description=purpose_description,
            collateral_type=collateral_type,
            collateral_value=collateral_value,
            co_applicant_name=co_applicant_name,
            co_applicant_income=co_applicant_income,
            co_applicant_relationship=co_applicant_relationship,
            status=ApplicationStatus.DRAFT,
            created_by=user.id,
            updated_by=user.id
        )
        
        db.add(application)
        db.flush()  # Get ID without committing
        
        # Create audit log
        self._create_audit_log(
            db, application, AuditAction.CREATE, user,
            new_values={"loan_amount": float(loan_amount), "loan_type": loan_type}
        )
        
        return application
    
    def update_application(
        self,
        db: Session,
        application_id: UUID,
        user: User,
        **updates
    ) -> LoanApplication:
        """
        Update a draft application.
        
        Args:
            db: Database session
            application_id: Application UUID
            user: Updating user
            **updates: Fields to update
            
        Returns:
            Updated LoanApplication
            
        Raises:
            ApplicationNotFoundError: If not found
            AccessDeniedError: If user can't update
            InvalidStatusTransitionError: If not in draft status
        """
        application = self.get_application(db, application_id, user)
        
        if application.status != ApplicationStatus.DRAFT:
            raise InvalidStatusTransitionError(
                application.status.value,
                "Only draft applications can be modified"
            )
        
        # Track old values
        old_values = {}
        for field in updates:
            if hasattr(application, field):
                old_values[field] = getattr(application, field)
                if isinstance(old_values[field], Decimal):
                    old_values[field] = float(old_values[field])
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(application, field) and value is not None:
                setattr(application, field, value)
        
        application.updated_by = user.id
        
        # Audit log
        new_values = {k: (float(v) if isinstance(v, Decimal) else v) 
                      for k, v in updates.items() if v is not None}
        
        self._create_audit_log(
            db, application, AuditAction.UPDATE, user,
            old_values=old_values,
            new_values=new_values
        )
        
        return application
    
    def submit_application(
        self,
        db: Session,
        application_id: UUID,
        user: User
    ) -> LoanApplication:
        """
        Submit a draft application for review.
        
        Args:
            db: Database session
            application_id: Application UUID
            user: Submitting user
            
        Returns:
            Submitted LoanApplication
            
        Raises:
            KYCRequiredError: If applicant KYC not verified
            InvalidStatusTransitionError: If not in draft status
        """
        application = self.get_application(db, application_id, user)
        
        if application.status != ApplicationStatus.DRAFT:
            raise InvalidStatusTransitionError(
                application.status.value,
                ApplicationStatus.SUBMITTED.value
            )
        
        # Verify KYC
        if application.applicant.kyc_status.value != "verified":
            raise KYCRequiredError()
        
        old_status = application.status.value
        application.status = ApplicationStatus.SUBMITTED
        application.submitted_at = datetime.utcnow()
        application.updated_by = user.id
        
        self._create_audit_log(
            db, application, AuditAction.STATUS_CHANGE, user,
            old_values={"status": old_status},
            new_values={"status": ApplicationStatus.SUBMITTED.value},
            notes="Application submitted for review"
        )
        
        return application
    
    def update_status(
        self,
        db: Session,
        application_id: UUID,
        new_status: ApplicationStatus,
        user: User,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        rejection_category: Optional[str] = None
    ) -> LoanApplication:
        """
        Update application status with validation.
        
        Args:
            db: Database session
            application_id: Application UUID
            new_status: Target status
            user: Updating user (must be staff)
            notes: Optional review notes
            rejection_reason: Required if rejecting
            rejection_category: Optional rejection category
            
        Returns:
            Updated LoanApplication
            
        Raises:
            InvalidStatusTransitionError: If transition not allowed
        """
        application = self.get_application(db, application_id, user)
        
        # Validate status transition
        allowed_transitions = self.STATUS_TRANSITIONS.get(application.status, [])
        if new_status not in allowed_transitions:
            raise InvalidStatusTransitionError(
                application.status.value,
                new_status.value
            )
        
        old_status = application.status.value
        application.status = new_status
        application.updated_by = user.id
        
        # Set timestamps based on status
        now = datetime.utcnow()
        if new_status == ApplicationStatus.UNDER_REVIEW:
            application.under_review_at = now
        elif new_status == ApplicationStatus.APPROVED:
            application.approved_at = now
            application.reviewed_by_id = user.id
            application.reviewed_at = now
        elif new_status == ApplicationStatus.REJECTED:
            application.rejected_at = now
            application.reviewed_by_id = user.id
            application.reviewed_at = now
            application.rejection_reason = rejection_reason
            application.rejection_category = rejection_category
        elif new_status == ApplicationStatus.DISBURSED:
            application.disbursed_at = now
        elif new_status == ApplicationStatus.CLOSED:
            application.closed_at = now
        
        if notes:
            application.review_notes = notes
        
        self._create_audit_log(
            db, application, AuditAction.STATUS_CHANGE, user,
            old_values={"status": old_status},
            new_values={"status": new_status.value},
            notes=notes
        )
        
        return application
    
    def run_prediction(
        self,
        db: Session,
        application_id: UUID,
        user: User,
        force_recalculate: bool = False
    ) -> Tuple[LoanApplication, PredictionResult]:
        """
        Run ML prediction for an application.
        
        Args:
            db: Database session
            application_id: Application UUID
            user: Requesting user
            force_recalculate: Force new prediction even if exists
            
        Returns:
            Tuple of (application, prediction_result)
        """
        application = self.get_application(db, application_id, user)
        
        # Return cached prediction if exists and not forcing recalculate
        if application.ml_predicted_at and not force_recalculate:
            # Build result from stored data
            return application, self._build_cached_prediction(application)
        
        # Build input data for ML service
        applicant = application.applicant
        
        applicant_data = ApplicantData(
            cibil_score=applicant.cibil_score,
            debt_to_income_ratio=float(applicant.debt_to_income_ratio) if applicant.debt_to_income_ratio else None,
            employment_years=applicant.employment_years,
            employment_months=applicant.employment_months,
            owns_home=applicant.owns_home,
            owns_car=applicant.owns_car,
            income=applicant.income,
            additional_income=applicant.additional_income,
            total_assets=applicant.total_assets,
            total_liabilities=applicant.total_liabilities,
            existing_loans_count=applicant.existing_loans_count,
            existing_emi=applicant.existing_emi,
            credit_history_years=applicant.credit_history_years
        )
        
        loan_data = LoanData(
            loan_amount=application.loan_amount,
            loan_term_months=application.loan_term_months,
            loan_type=application.loan_type.value if application.loan_type else "personal",
            collateral_value=application.collateral_value,
            co_applicant_income=application.co_applicant_income
        )
        
        # Run prediction via ML service
        result = self._ml_service.predict(applicant_data, loan_data)
        
        # Store prediction results
        application.ml_approval_probability = Decimal(str(result.approval_probability))
        application.ml_risk_score = Decimal(str(result.risk_score))
        application.ml_recommendation = result.recommendation
        application.ml_confidence = Decimal(str(result.confidence))
        application.ml_predicted_at = result.predicted_at
        application.ml_model_version = result.model_version
        application.xai_explanation = result.explanation
        application.eligibility_tips = result.eligibility_tips
        application.requires_manual_review = result.requires_manual_review
        application.updated_by = user.id
        
        # Audit log
        self._create_audit_log(
            db, application, AuditAction.ML_PREDICTION, user,
            new_values={
                "approval_probability": result.approval_probability,
                "risk_score": result.risk_score,
                "recommendation": result.recommendation
            },
            notes="ML prediction generated"
        )
        
        return application, result
    
    def run_decision(
        self,
        db: Session,
        application_id: UUID,
        user: User,
        force_recalculate: bool = False
    ) -> Tuple[LoanApplication, FinalDecision]:
        """
        Run three-layer decision engine for an application.
        
        Layer 1: Rule-based checks (fast, explainable)
        Layer 2: ML model scoring
        Layer 3: Final decision logic
        
        Args:
            db: Database session
            application_id: Application UUID
            user: Requesting user
            force_recalculate: Force new decision even if exists
            
        Returns:
            Tuple of (application, FinalDecision)
        """
        application = self.get_application(db, application_id, user)
        applicant = application.applicant
        
        # Build ApplicantProfile for decision engine
        profile = ApplicantProfile(
            date_of_birth=applicant.date_of_birth.date() if applicant.date_of_birth else None,
            age=applicant.age if hasattr(applicant, 'age') else self._calculate_age(applicant.date_of_birth),
            kyc_verified=(applicant.kyc_status.value == "verified"),
            pan_verified=applicant.pan_verified,
            aadhaar_verified=applicant.aadhaar_verified,
            monthly_income=applicant.income,
            additional_income=applicant.additional_income,
            employment_years=applicant.employment_years,
            employment_months=applicant.employment_months,
            employment_type=applicant.employment_type.value if applicant.employment_type else None,
            cibil_score=applicant.cibil_score,
            credit_history_years=applicant.credit_history_years,
            total_assets=applicant.total_assets,
            total_liabilities=applicant.total_liabilities,
            existing_emi=applicant.existing_emi,
            existing_loans_count=applicant.existing_loans_count,
            owns_home=applicant.owns_home,
            owns_car=applicant.owns_car
        )
        
        # Build LoanRequest for decision engine
        loan_request = LoanRequest(
            loan_amount=application.loan_amount,
            loan_term_months=application.loan_term_months,
            loan_type=application.loan_type.value if application.loan_type else "personal",
            purpose=application.purpose,
            collateral_value=application.collateral_value,
            collateral_type=application.collateral_type,
            co_applicant_income=application.co_applicant_income,
            interest_rate_requested=float(application.interest_rate_requested) if application.interest_rate_requested else None
        )
        
        # Run decision engine
        decision = self._decision_engine.evaluate(profile, loan_request)
        
        # Store decision results in application
        application.ml_approval_probability = Decimal(str(decision.ml_score_result.approval_score))
        application.ml_risk_score = Decimal(str(decision.ml_score_result.credit_risk_score))
        application.ml_recommendation = decision.outcome.value
        application.ml_confidence = Decimal(str(decision.ml_score_result.confidence))
        application.ml_predicted_at = decision.decision_timestamp
        application.ml_model_version = decision.ml_score_result.model_version
        
        # Store detailed explanation
        application.xai_explanation = {
            "outcome": decision.outcome.value,
            "combined_score": decision.combined_score,
            "decision_reason": decision.decision_reason,
            "detailed_reasons": decision.detailed_reasons,
            "rules_summary": {
                "passed": decision.rule_engine_result.passed,
                "total_rules": decision.rule_engine_result.total_rules,
                "passed_rules": decision.rule_engine_result.passed_rules,
                "failed_rules": decision.rule_engine_result.failed_rules,
                "warnings": decision.rule_engine_result.warning_rules
            },
            "ml_summary": {
                "credit_risk_score": decision.ml_score_result.credit_risk_score,
                "default_probability": decision.ml_score_result.default_probability,
                "approval_score": decision.ml_score_result.approval_score,
                "risk_factors": decision.ml_score_result.risk_factors
            },
            "rule_details": [
                {
                    "rule_id": r.rule_id,
                    "name": r.rule_name,
                    "status": r.status.value,
                    "message": r.message,
                    "category": r.category.value
                }
                for r in decision.rule_engine_result.results
            ]
        }
        
        application.eligibility_tips = decision.recommendations
        application.requires_manual_review = decision.requires_human_review
        
        if decision.requires_human_review:
            application.manual_review_reason = "; ".join(decision.review_reasons)
        
        application.updated_by = user.id
        
        # Audit log
        self._create_audit_log(
            db, application, AuditAction.ML_PREDICTION, user,
            new_values={
                "outcome": decision.outcome.value,
                "combined_score": decision.combined_score,
                "rules_passed": decision.rules_passed,
                "ml_approval_score": decision.ml_score_result.approval_score
            },
            notes=f"Decision engine: {decision.decision_reason}"
        )
        
        return application, decision
    
    def _calculate_age(self, date_of_birth) -> Optional[int]:
        """Calculate age from date of birth."""
        if not date_of_birth:
            return None
        from datetime import date
        today = date.today()
        dob = date_of_birth.date() if hasattr(date_of_birth, 'date') else date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    def soft_delete(
        self,
        db: Session,
        application_id: UUID,
        user: User
    ) -> None:
        """
        Soft delete an application.
        
        Args:
            db: Database session
            application_id: Application UUID
            user: Deleting user (must be admin/manager)
        """
        application = self.get_application(db, application_id, user)
        
        application.soft_delete(user.id)
        
        self._create_audit_log(
            db, application, AuditAction.DELETE, user,
            notes="Application soft deleted"
        )
    
    def _build_cached_prediction(self, application: LoanApplication) -> PredictionResult:
        """Build PredictionResult from cached application data."""
        return PredictionResult(
            approval_probability=float(application.ml_approval_probability),
            risk_score=float(application.ml_risk_score),
            recommendation=application.ml_recommendation,
            confidence=float(application.ml_confidence) if application.ml_confidence else 0.8,
            factors=application.xai_explanation.get("factors", []) if application.xai_explanation else [],
            explanation=application.xai_explanation or {},
            eligibility_tips=application.eligibility_tips or [],
            requires_manual_review=application.requires_manual_review,
            model_version=application.ml_model_version or "1.0.0",
            predicted_at=application.ml_predicted_at
        )
    
    def _create_audit_log(
        self,
        db: Session,
        application: LoanApplication,
        action: AuditAction,
        user: User,
        changes: Optional[dict] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        notes: Optional[str] = None,
        request_ip: Optional[str] = None
    ) -> ApplicationAuditLog:
        """Create audit log entry."""
        audit = ApplicationAuditLog(
            entity_type="loan_application",
            entity_id=application.id,
            application_id=application.id,
            user_id=user.id,
            action=action,
            changes=changes,
            old_values=old_values,
            new_values=new_values,
            notes=notes,
            ip_address=request_ip
        )
        db.add(audit)
        return audit


# Singleton for dependency injection
_application_service: Optional[ApplicationService] = None


def get_application_service() -> ApplicationService:
    """Get application service instance."""
    global _application_service
    if _application_service is None:
        _application_service = ApplicationService()
    return _application_service
