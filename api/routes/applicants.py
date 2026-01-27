"""
Applicants Routes
=================
CRUD operations for loan applicants.

Controllers are thin - only handle:
- Request/response transformation
- HTTP status codes
- Delegating to service layer

No business logic in controllers - validation in schemas.

Author: Loan Analytics Team
Version: 2.0.0
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database.models import User, Applicant, KYCStatus, EmploymentType, Gender, MaritalStatus, Education
from api.dependencies import get_db, get_current_user, require_roles
from api.config import get_settings
from api.schemas import (
    ApplicantCreateRequest,
    ApplicantUpdateRequest,
    ApplicantResponse,
    PaginatedApplicantsResponse,
    KYCStatusEnum
)

settings = get_settings()
router = APIRouter()


# =============================================================================
# Additional Response Schemas (for detailed responses)
# =============================================================================

from pydantic import BaseModel


class ApplicantDetailResponse(ApplicantResponse):
    """Detailed applicant response."""
    middle_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    dependents: int = 0
    education: Optional[str] = None
    phone_secondary: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    address_years: int = 0
    job_title: Optional[str] = None
    employment_years: int = 0
    employment_months: int = 0
    additional_income: float = 0
    total_assets: float = 0
    total_liabilities: float = 0
    net_worth: float = 0
    existing_loans_count: int = 0
    existing_emi: float = 0
    monthly_expenses: float = 0
    debt_to_income_ratio: Optional[float] = None
    credit_history_years: int = 0
    credit_utilization: Optional[float] = None
    owns_home: bool = False
    owns_car: bool = False
    pan_verified: bool = False
    aadhaar_verified: bool = False
    kyc_verified_at: Optional[str] = None
    applications_count: int = 0


# =============================================================================
# Helper Functions
# =============================================================================

def applicant_to_response(applicant: Applicant) -> ApplicantResponse:
    """Convert applicant model to response."""
    return ApplicantResponse(
        id=str(applicant.id),
        applicant_ref=applicant.applicant_ref,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        full_name=applicant.full_name,
        email=applicant.email,
        phone=applicant.phone,
        city=applicant.city,
        state=applicant.state,
        country=applicant.country,
        employment_type=applicant.employment_type.value if applicant.employment_type else None,
        employer_name=applicant.employer_name,
        income=float(applicant.income),
        cibil_score=applicant.cibil_score,
        kyc_status=applicant.kyc_status.value,
        risk_score=float(applicant.risk_score) if applicant.risk_score else None,
        risk_category=applicant.risk_category,
        created_at=applicant.created_at.isoformat(),
        updated_at=applicant.updated_at.isoformat()
    )


def applicant_to_detail_response(applicant: Applicant) -> ApplicantDetailResponse:
    """Convert applicant model to detailed response."""
    return ApplicantDetailResponse(
        id=str(applicant.id),
        applicant_ref=applicant.applicant_ref,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        full_name=applicant.full_name,
        middle_name=applicant.middle_name,
        email=applicant.email,
        phone=applicant.phone,
        phone_secondary=applicant.phone_secondary,
        date_of_birth=applicant.date_of_birth.isoformat() if applicant.date_of_birth else None,
        gender=applicant.gender.value if applicant.gender else None,
        marital_status=applicant.marital_status.value if applicant.marital_status else None,
        dependents=applicant.dependents,
        education=applicant.education.value if applicant.education else None,
        address=applicant.address,
        city=applicant.city,
        state=applicant.state,
        country=applicant.country,
        postal_code=applicant.postal_code,
        address_years=applicant.address_years,
        employment_type=applicant.employment_type.value if applicant.employment_type else None,
        employer_name=applicant.employer_name,
        job_title=applicant.job_title,
        employment_years=applicant.employment_years,
        employment_months=applicant.employment_months,
        income=float(applicant.income),
        additional_income=float(applicant.additional_income),
        total_assets=float(applicant.total_assets),
        total_liabilities=float(applicant.total_liabilities),
        net_worth=float(applicant.net_worth),
        existing_loans_count=applicant.existing_loans_count,
        existing_emi=float(applicant.existing_emi),
        monthly_expenses=float(applicant.monthly_expenses),
        debt_to_income_ratio=float(applicant.debt_to_income_ratio) if applicant.debt_to_income_ratio else None,
        credit_history_years=applicant.credit_history_years,
        credit_utilization=float(applicant.credit_utilization) if applicant.credit_utilization else None,
        cibil_score=applicant.cibil_score,
        owns_home=applicant.owns_home,
        owns_car=applicant.owns_car,
        pan_verified=applicant.pan_verified,
        aadhaar_verified=applicant.aadhaar_verified,
        kyc_status=applicant.kyc_status.value,
        kyc_verified_at=applicant.kyc_verified_at.isoformat() if applicant.kyc_verified_at else None,
        risk_score=float(applicant.risk_score) if applicant.risk_score else None,
        risk_category=applicant.risk_category,
        applications_count=len(applicant.applications) if applicant.applications else 0,
        created_at=applicant.created_at.isoformat(),
        updated_at=applicant.updated_at.isoformat()
    )


# =============================================================================
# Routes
# =============================================================================

@router.get("", response_model=PaginatedApplicantsResponse)
async def list_applicants(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    kyc_status: Optional[str] = Query(None, description="Filter by KYC status"),
    risk_category: Optional[str] = Query(None, description="Filter by risk category"),
    min_income: Optional[float] = Query(None, ge=0, description="Minimum income"),
    max_income: Optional[float] = Query(None, ge=0, description="Maximum income"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List applicants with pagination and filters.
    
    Staff can view all applicants, regular users can only view their own.
    """
    query = db.query(Applicant).filter(Applicant.is_deleted == False)
    
    # Regular users can only see their own applicant profiles
    if current_user.role.value == "applicant":
        query = query.filter(Applicant.user_id == current_user.id)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Applicant.first_name.ilike(search_term),
                Applicant.last_name.ilike(search_term),
                Applicant.email.ilike(search_term),
                Applicant.phone.ilike(search_term),
                Applicant.applicant_ref.ilike(search_term)
            )
        )
    
    # KYC status filter
    if kyc_status:
        try:
            status_enum = KYCStatus(kyc_status)
            query = query.filter(Applicant.kyc_status == status_enum)
        except ValueError:
            pass
    
    # Risk category filter
    if risk_category:
        query = query.filter(Applicant.risk_category == risk_category)
    
    # Income filters
    if min_income is not None:
        query = query.filter(Applicant.income >= min_income)
    if max_income is not None:
        query = query.filter(Applicant.income <= max_income)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    applicants = query.order_by(Applicant.created_at.desc()).offset(offset).limit(page_size).all()
    
    return PaginatedApplicantsResponse(
        items=[applicant_to_response(a) for a in applicants],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=ApplicantDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_applicant(
    request: ApplicantCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new applicant profile.
    
    Validation is handled by the schema (ApplicantCreateRequest):
    - Age validation (18+ years)
    - Financial cross-field validation
    - PAN/Aadhaar format validation
    """
    # Check if email already exists
    existing = db.query(Applicant).filter(
        Applicant.email == request.email.lower(),
        Applicant.is_deleted == False
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Applicant with this email already exists"
        )
    
    # Create applicant
    applicant_data = request.model_dump(exclude_unset=True)
    applicant_data['email'] = applicant_data['email'].lower()
    applicant_data['created_by'] = current_user.id
    applicant_data['updated_by'] = current_user.id
    
    # Link to user if creating own profile
    if current_user.email.lower() == request.email.lower():
        applicant_data['user_id'] = current_user.id
    
    # Convert schema enums to DB enums
    if 'gender' in applicant_data and applicant_data['gender']:
        applicant_data['gender'] = Gender(applicant_data['gender'].value if hasattr(applicant_data['gender'], 'value') else applicant_data['gender'])
    if 'marital_status' in applicant_data and applicant_data['marital_status']:
        applicant_data['marital_status'] = MaritalStatus(applicant_data['marital_status'].value if hasattr(applicant_data['marital_status'], 'value') else applicant_data['marital_status'])
    if 'education' in applicant_data and applicant_data['education']:
        applicant_data['education'] = Education(applicant_data['education'].value if hasattr(applicant_data['education'], 'value') else applicant_data['education'])
    if 'employment_type' in applicant_data and applicant_data['employment_type']:
        applicant_data['employment_type'] = EmploymentType(applicant_data['employment_type'].value if hasattr(applicant_data['employment_type'], 'value') else applicant_data['employment_type'])
    
    applicant = Applicant(**applicant_data)
    
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    
    return applicant_to_detail_response(applicant)


@router.get("/{applicant_id}", response_model=ApplicantDetailResponse)
async def get_applicant(
    applicant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get applicant details by ID.
    """
    applicant = db.query(Applicant).filter(
        Applicant.id == applicant_id,
        Applicant.is_deleted == False
    ).first()
    
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant not found"
        )
    
    # Check access
    if current_user.role.value == "applicant" and applicant.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return applicant_to_detail_response(applicant)


@router.patch("/{applicant_id}", response_model=ApplicantDetailResponse)
async def update_applicant(
    applicant_id: UUID,
    request: ApplicantUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update applicant details.
    
    Validation is handled by the schema (ApplicantUpdateRequest).
    """
    applicant = db.query(Applicant).filter(
        Applicant.id == applicant_id,
        Applicant.is_deleted == False
    ).first()
    
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant not found"
        )
    
    # Check access
    if current_user.role.value == "applicant" and applicant.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    
    # Convert schema enums to DB enums
    if 'employment_type' in update_data and update_data['employment_type']:
        update_data['employment_type'] = EmploymentType(update_data['employment_type'].value if hasattr(update_data['employment_type'], 'value') else update_data['employment_type'])
    
    for field, value in update_data.items():
        setattr(applicant, field, value)
    
    applicant.updated_by = current_user.id
    
    db.commit()
    db.refresh(applicant)
    
    return applicant_to_detail_response(applicant)


@router.delete("/{applicant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_applicant(
    applicant_id: UUID,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db)
):
    """
    Soft delete an applicant (admin/manager only).
    """
    applicant = db.query(Applicant).filter(
        Applicant.id == applicant_id,
        Applicant.is_deleted == False
    ).first()
    
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant not found"
        )
    
    # Soft delete
    applicant.soft_delete(current_user.id)
    db.commit()


@router.post("/{applicant_id}/verify-kyc", response_model=ApplicantDetailResponse)
async def verify_kyc(
    applicant_id: UUID,
    status_value: str = Query(..., description="KYC status: pending, in_progress, verified, rejected, expired"),
    notes: Optional[str] = Query(None, description="Verification notes"),
    current_user: User = Depends(require_roles("admin", "manager", "analyst")),
    db: Session = Depends(get_db)
):
    """
    Update KYC verification status (staff only).
    """
    applicant = db.query(Applicant).filter(
        Applicant.id == applicant_id,
        Applicant.is_deleted == False
    ).first()
    
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant not found"
        )
    
    try:
        kyc_status = KYCStatus(status_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid KYC status: {status_value}"
        )
    
    applicant.kyc_status = kyc_status
    
    if kyc_status == KYCStatus.VERIFIED:
        applicant.kyc_verified_at = datetime.utcnow()
        applicant.kyc_verified_by = current_user.id
    
    if notes:
        applicant.kyc_notes = notes
    
    applicant.updated_by = current_user.id
    db.commit()
    db.refresh(applicant)
    
    return applicant_to_detail_response(applicant)


@router.get("/{applicant_id}/risk-assessment")
async def get_risk_assessment(
    applicant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get risk assessment for an applicant.
    """
    applicant = db.query(Applicant).filter(
        Applicant.id == applicant_id,
        Applicant.is_deleted == False
    ).first()
    
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant not found"
        )
    
    # Check access
    if current_user.role.value == "applicant" and applicant.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "applicant_id": str(applicant.id),
        "applicant_ref": applicant.applicant_ref,
        "risk_score": float(applicant.risk_score) if applicant.risk_score else None,
        "risk_category": applicant.risk_category,
        "risk_factors": applicant.risk_factors,
        "debt_to_income_ratio": float(applicant.debt_to_income_ratio) if applicant.debt_to_income_ratio else None,
        "cibil_score": applicant.cibil_score,
        "credit_history_years": applicant.credit_history_years,
        "net_worth": float(applicant.net_worth),
        "monthly_surplus": float(applicant.monthly_surplus),
        "kyc_status": applicant.kyc_status.value,
        "computed_at": applicant.updated_at.isoformat()
    }
