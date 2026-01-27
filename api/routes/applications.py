"""
Applications Routes
===================
REST API endpoints for loan applications.

Controllers are thin - only handle:
- Request/response transformation
- HTTP status codes
- Delegating to service layer

No business logic or ML code in controllers.

Author: Loan Analytics Team
Version: 2.0.0
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.models import User, Applicant, LoanApplication, ApplicationAuditLog
from api.dependencies import get_db, get_current_user, require_roles
from api.schemas import (
    ApplicationCreateRequest,
    ApplicationUpdateRequest,
    StatusUpdateRequest,
    ApplicationResponse,
    ApplicationDetailResponse,
    PaginatedApplicationsResponse,
    PredictionRequest,
    PredictionResponse,
    ApplicationStatusEnum
)
from services.application_service import (
    ApplicationService,
    get_application_service,
    ApplicationNotFoundError,
    ApplicantNotFoundError,
    AccessDeniedError,
    InvalidStatusTransitionError,
    KYCRequiredError
)

router = APIRouter()


# =============================================================================
# Response Mappers (Thin layer - just data transformation)
# =============================================================================

def to_response(app: LoanApplication) -> ApplicationResponse:
    """Map domain model to API response."""
    return ApplicationResponse(
        id=str(app.id),
        application_number=app.application_number,
        applicant_id=str(app.applicant_id),
        applicant_name=app.applicant.full_name if app.applicant else "Unknown",
        loan_type=app.loan_type.value if app.loan_type else "personal",
        loan_amount=float(app.loan_amount),
        loan_term_months=app.loan_term_months,
        interest_rate_offered=float(app.interest_rate_offered) if app.interest_rate_offered else None,
        monthly_emi=float(app.monthly_emi) if app.monthly_emi else None,
        status=app.status.value,
        status_display=app.status.value.replace("_", " ").title(),
        ml_approval_probability=float(app.ml_approval_probability) if app.ml_approval_probability else None,
        ml_risk_score=float(app.ml_risk_score) if app.ml_risk_score else None,
        ml_recommendation=app.ml_recommendation,
        submitted_at=app.submitted_at.isoformat() if app.submitted_at else None,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat()
    )


def to_detail_response(app: LoanApplication) -> ApplicationDetailResponse:
    """Map domain model to detailed API response."""
    return ApplicationDetailResponse(
        id=str(app.id),
        application_number=app.application_number,
        applicant_id=str(app.applicant_id),
        applicant_name=app.applicant.full_name if app.applicant else "Unknown",
        loan_type=app.loan_type.value if app.loan_type else "personal",
        loan_amount=float(app.loan_amount),
        loan_term_months=app.loan_term_months,
        interest_rate_requested=float(app.interest_rate_requested) if app.interest_rate_requested else None,
        interest_rate_offered=float(app.interest_rate_offered) if app.interest_rate_offered else None,
        monthly_emi=float(app.monthly_emi) if app.monthly_emi else None,
        purpose=app.purpose,
        purpose_description=app.purpose_description,
        collateral_type=app.collateral_type,
        collateral_value=float(app.collateral_value),
        processing_fee=float(app.processing_fee),
        co_applicant_name=app.co_applicant_name,
        co_applicant_income=float(app.co_applicant_income),
        co_applicant_relationship=app.co_applicant_relationship,
        status=app.status.value,
        status_display=app.status.value.replace("_", " ").title(),
        ml_approval_probability=float(app.ml_approval_probability) if app.ml_approval_probability else None,
        ml_risk_score=float(app.ml_risk_score) if app.ml_risk_score else None,
        ml_recommendation=app.ml_recommendation,
        ml_predicted_at=app.ml_predicted_at.isoformat() if app.ml_predicted_at else None,
        ml_model_version=app.ml_model_version,
        xai_explanation=app.xai_explanation,
        eligibility_tips=app.eligibility_tips,
        requires_manual_review=app.requires_manual_review,
        manual_review_reason=app.manual_review_reason,
        reviewed_by_name=app.reviewed_by.full_name if app.reviewed_by else None,
        reviewed_at=app.reviewed_at.isoformat() if app.reviewed_at else None,
        review_notes=app.review_notes,
        submitted_at=app.submitted_at.isoformat() if app.submitted_at else None,
        under_review_at=app.under_review_at.isoformat() if app.under_review_at else None,
        approved_at=app.approved_at.isoformat() if app.approved_at else None,
        rejected_at=app.rejected_at.isoformat() if app.rejected_at else None,
        disbursed_at=app.disbursed_at.isoformat() if app.disbursed_at else None,
        rejection_reason=app.rejection_reason,
        rejection_category=app.rejection_category,
        appeal_deadline=app.appeal_deadline.isoformat() if app.appeal_deadline else None,
        disbursement_amount=float(app.disbursement_amount) if app.disbursement_amount else None,
        disbursement_account=app.disbursement_account,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat()
    )


# =============================================================================
# Exception Handler Helper
# =============================================================================

def handle_service_error(error: Exception) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    if isinstance(error, ApplicationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message)
    if isinstance(error, ApplicantNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message)
    if isinstance(error, AccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message)
    if isinstance(error, InvalidStatusTransitionError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message)
    if isinstance(error, KYCRequiredError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message)
    # Unknown error
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# =============================================================================
# Routes (Thin controllers - delegate to service)
# =============================================================================

@router.get("", response_model=PaginatedApplicationsResponse)
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by application number or applicant name"),
    status_filter: Optional[ApplicationStatusEnum] = Query(None, alias="status"),
    loan_type: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List loan applications with pagination and filters.
    
    Regular users can only see their own applications.
    Staff can see all applications.
    """
    from sqlalchemy import or_
    from database.models import ApplicationStatus as DBApplicationStatus, LoanType as DBLoanType
    
    query = db.query(LoanApplication).filter(LoanApplication.is_deleted == False)
    
    # Access control: regular users see only their applications
    if current_user.role.value == "applicant":
        applicant = db.query(Applicant).filter(
            Applicant.user_id == current_user.id,
            Applicant.is_deleted == False
        ).first()
        
        if applicant:
            query = query.filter(LoanApplication.applicant_id == applicant.id)
        else:
            return PaginatedApplicationsResponse(
                items=[], total=0, page=page, page_size=page_size, pages=0
            )
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.join(Applicant).filter(
            or_(
                LoanApplication.application_number.ilike(search_term),
                Applicant.first_name.ilike(search_term),
                Applicant.last_name.ilike(search_term)
            )
        )
    
    if status_filter:
        try:
            status_enum = DBApplicationStatus(status_filter.value)
            query = query.filter(LoanApplication.status == status_enum)
        except ValueError:
            pass
    
    if loan_type:
        try:
            type_enum = DBLoanType(loan_type)
            query = query.filter(LoanApplication.loan_type == type_enum)
        except ValueError:
            pass
    
    if min_amount is not None:
        query = query.filter(LoanApplication.loan_amount >= min_amount)
    if max_amount is not None:
        query = query.filter(LoanApplication.loan_amount <= max_amount)
    
    # Pagination
    total = query.count()
    offset = (page - 1) * page_size
    applications = query.order_by(
        LoanApplication.created_at.desc()
    ).offset(offset).limit(page_size).all()
    
    return PaginatedApplicationsResponse(
        items=[to_response(a) for a in applications],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=ApplicationDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Create a new loan application."""
    try:
        application = service.create_application(
            db=db,
            applicant_id=request.applicant_id,
            loan_type=request.loan_type.value,
            loan_amount=request.loan_amount,
            loan_term_months=request.loan_term_months,
            user=current_user,
            interest_rate_requested=request.interest_rate_requested,
            purpose=request.purpose,
            purpose_description=request.purpose_description,
            collateral_type=request.collateral_type,
            collateral_value=request.collateral_value,
            co_applicant_name=request.co_applicant_name,
            co_applicant_income=request.co_applicant_income,
            co_applicant_relationship=request.co_applicant_relationship
        )
        db.commit()
        db.refresh(application)
        return to_detail_response(application)
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)


@router.get("/{application_id}", response_model=ApplicationDetailResponse)
async def get_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Get application details by ID."""
    try:
        application = service.get_application(db, application_id, current_user)
        return to_detail_response(application)
    except Exception as e:
        raise handle_service_error(e)


@router.patch("/{application_id}", response_model=ApplicationDetailResponse)
async def update_application(
    application_id: UUID,
    request: ApplicationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Update a loan application (only in draft status)."""
    try:
        updates = request.model_dump(exclude_unset=True)
        application = service.update_application(
            db=db,
            application_id=application_id,
            user=current_user,
            **updates
        )
        db.commit()
        db.refresh(application)
        return to_detail_response(application)
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)


@router.post("/{application_id}/submit", response_model=ApplicationDetailResponse)
async def submit_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Submit a draft application for review."""
    try:
        application = service.submit_application(db, application_id, current_user)
        db.commit()
        db.refresh(application)
        return to_detail_response(application)
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)


@router.post("/{application_id}/status", response_model=ApplicationDetailResponse)
async def update_status(
    application_id: UUID,
    request: StatusUpdateRequest,
    current_user: User = Depends(require_roles("admin", "manager", "analyst")),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Update application status (staff only)."""
    from database.models import ApplicationStatus as DBApplicationStatus
    
    try:
        new_status = DBApplicationStatus(request.status.value)
        application = service.update_status(
            db=db,
            application_id=application_id,
            new_status=new_status,
            user=current_user,
            notes=request.notes,
            rejection_reason=request.rejection_reason,
            rejection_category=request.rejection_category
        )
        db.commit()
        db.refresh(application)
        return to_detail_response(application)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {request.status}"
        )
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)


@router.post("/{application_id}/predict", response_model=PredictionResponse)
async def run_prediction(
    application_id: UUID,
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """
    Run ML prediction for a loan application (legacy endpoint).
    
    ML logic is handled by the service layer - controller only handles
    request/response transformation.
    """
    try:
        application, result = service.run_prediction(
            db=db,
            application_id=application_id,
            user=current_user,
            force_recalculate=request.recalculate
        )
        db.commit()
        
        return PredictionResponse(
            application_id=str(application.id),
            approval_probability=result.approval_probability,
            risk_score=result.risk_score,
            recommendation=result.recommendation,
            confidence=result.confidence,
            explanation=result.explanation,
            eligibility_tips=result.eligibility_tips,
            predicted_at=result.predicted_at.isoformat(),
            model_version=result.model_version
        )
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)


@router.post("/{application_id}/decision")
async def run_decision(
    application_id: UUID,
    recalculate: bool = Query(False, description="Force recalculation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """
    Run three-layer decision engine for a loan application.
    
    Decision Engine Architecture:
    
    **Layer 1: Rule-Based Checks** (fast, explainable)
    - Age ≥ 21
    - Income ≥ threshold (varies by loan type)
    - KYC verified
    - Employment minimum
    - Existing loans limit
    
    **Layer 2: ML Model**
    - Credit risk score (0-100)
    - Default probability (0-1)
    - Approval score (0-1)
    
    **Layer 3: Final Decision Logic**
    - Rules PASS + ML approval score > 0.65 → APPROVED
    - Rules PASS + ML score 0.45-0.65 → MANUAL_REVIEW
    - Rules FAIL or ML score < 0.45 → REJECTED
    
    Returns comprehensive decision with explanations and recommendations.
    """
    try:
        application, decision = service.run_decision(
            db=db,
            application_id=application_id,
            user=current_user,
            force_recalculate=recalculate
        )
        db.commit()
        
        return {
            "application_id": str(application.id),
            "application_number": application.application_number,
            
            # Final Decision
            "outcome": decision.outcome.value,
            "decision_reason": decision.decision_reason,
            "combined_score": decision.combined_score,
            "requires_human_review": decision.requires_human_review,
            
            # Layer 1: Rule Results
            "rules": {
                "passed": decision.rules_passed,
                "summary": {
                    "total": decision.rule_engine_result.total_rules,
                    "passed": decision.rule_engine_result.passed_rules,
                    "failed": decision.rule_engine_result.failed_rules,
                    "warnings": decision.rule_engine_result.warning_rules,
                    "pass_rate": round(decision.rule_engine_result.pass_rate * 100, 1)
                },
                "details": [
                    {
                        "rule_id": r.rule_id,
                        "name": r.rule_name,
                        "category": r.category.value,
                        "status": r.status.value,
                        "message": r.message,
                        "actual_value": r.actual_value,
                        "threshold": r.threshold
                    }
                    for r in decision.rule_engine_result.results
                ],
                "blocking_failures": [
                    {
                        "rule_id": r.rule_id,
                        "name": r.rule_name,
                        "message": r.message
                    }
                    for r in decision.rule_engine_result.blocking_failures
                ],
                "execution_time_ms": decision.rule_engine_result.execution_time_ms
            },
            
            # Layer 2: ML Results
            "ml_scores": {
                "credit_risk_score": decision.ml_score_result.credit_risk_score,
                "default_probability": decision.ml_score_result.default_probability,
                "approval_score": decision.ml_score_result.approval_score,
                "confidence": decision.ml_score_result.confidence,
                "risk_factors": decision.ml_score_result.risk_factors,
                "model_version": decision.ml_score_result.model_version,
                "execution_time_ms": decision.ml_score_result.execution_time_ms
            },
            
            # Explanations
            "detailed_reasons": decision.detailed_reasons,
            "recommendations": decision.recommendations,
            "review_reasons": decision.review_reasons if decision.requires_human_review else [],
            
            # Metadata
            "decision_timestamp": decision.decision_timestamp.isoformat(),
            "processing_time_ms": decision.processing_time_ms
        }
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)


@router.get("/{application_id}/audit-log")
async def get_audit_log(
    application_id: UUID,
    current_user: User = Depends(require_roles("admin", "manager", "analyst")),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Get audit log for an application (staff only)."""
    try:
        application = service.get_application(db, application_id, current_user)
        
        logs = db.query(ApplicationAuditLog).filter(
            ApplicationAuditLog.application_id == application_id
        ).order_by(ApplicationAuditLog.created_at.desc()).all()
        
        return {
            "application_id": str(application_id),
            "logs": [
                {
                    "id": str(log.id),
                    "action": log.action.value,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "user_name": log.user.full_name if log.user else "System",
                    "changes": log.changes,
                    "old_values": log.old_values,
                    "new_values": log.new_values,
                    "notes": log.notes,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
        }
    except Exception as e:
        raise handle_service_error(e)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: UUID,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service)
):
    """Soft delete a loan application (admin/manager only)."""
    try:
        service.soft_delete(db, application_id, current_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise handle_service_error(e)
