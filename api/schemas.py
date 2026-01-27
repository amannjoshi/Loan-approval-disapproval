"""
API Validation Schemas
======================
Pydantic models for request/response validation at API layer.

All validation logic is centralized here to ensure:
- Consistent validation across endpoints
- Clear error messages
- Type safety
- Documentation via OpenAPI

Author: Loan Analytics Team
Version: 1.0.0
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import UUID
from enum import Enum

from pydantic import (
    BaseModel, 
    EmailStr, 
    Field, 
    field_validator,
    model_validator,
    ConfigDict
)


# =============================================================================
# Enums for Validation
# =============================================================================

class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class MaritalStatusEnum(str, Enum):
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"


class EducationEnum(str, Enum):
    HIGH_SCHOOL = "high_school"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    DOCTORATE = "doctorate"
    OTHER = "other"


class EmploymentTypeEnum(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    BUSINESS = "business"
    RETIRED = "retired"
    UNEMPLOYED = "unemployed"


class LoanTypeEnum(str, Enum):
    PERSONAL = "personal"
    HOME = "home"
    AUTO = "auto"
    EDUCATION = "education"
    BUSINESS = "business"
    GOLD = "gold"
    OTHER = "other"


class ApplicationStatusEnum(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class KYCStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    APPLICANT = "applicant"


class UserStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


# =============================================================================
# Base Schemas
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )


class PaginatedResponse(BaseSchema):
    """Base paginated response."""
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseSchema):
    """Simple message response."""
    success: bool
    message: str


# =============================================================================
# Authentication Schemas
# =============================================================================

class RegisterRequest(BaseSchema):
    """User registration request with validation."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20, pattern=r'^[\d\+\-\s\(\)]{10,20}$')
    
    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Ensure password has required complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name contains only allowed characters."""
        if not v.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
        return v.strip()


class LoginRequest(BaseSchema):
    """Login request."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseSchema):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseSchema):
    """Token refresh request."""
    refresh_token: str = Field(..., min_length=1)


class PasswordChangeRequest(BaseSchema):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Ensure new password has required complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserResponse(BaseSchema):
    """User response."""
    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    role: str
    status: str
    email_verified: bool
    last_login_at: Optional[str]
    created_at: str


# =============================================================================
# Applicant Schemas
# =============================================================================

class ApplicantCreateRequest(BaseSchema):
    """Create applicant request with comprehensive validation."""
    # Personal Information
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[datetime] = None
    gender: Optional[GenderEnum] = None
    marital_status: Optional[MaritalStatusEnum] = None
    dependents: int = Field(default=0, ge=0, le=20)
    education: Optional[EducationEnum] = None
    
    # Contact Information
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20, pattern=r'^[\d\+\-\s\(\)]{10,20}$')
    phone_secondary: Optional[str] = Field(None, max_length=20, pattern=r'^[\d\+\-\s\(\)]{10,20}$')
    
    # Address
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="India", max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20, pattern=r'^[A-Za-z0-9\s\-]{3,20}$')
    
    # Employment
    employment_type: Optional[EmploymentTypeEnum] = None
    employer_name: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=200)
    employment_years: int = Field(default=0, ge=0, le=60)
    employment_months: int = Field(default=0, ge=0, le=11)
    
    # Income & Financial
    income: Decimal = Field(..., ge=0, le=100000000, description="Monthly income")
    additional_income: Decimal = Field(default=0, ge=0, le=100000000)
    total_assets: Decimal = Field(default=0, ge=0, le=10000000000)
    total_liabilities: Decimal = Field(default=0, ge=0, le=10000000000)
    existing_loans_count: int = Field(default=0, ge=0, le=50)
    existing_emi: Decimal = Field(default=0, ge=0, le=10000000)
    monthly_expenses: Decimal = Field(default=0, ge=0, le=10000000)
    
    # Credit Information
    cibil_score: Optional[int] = Field(None, ge=300, le=900)
    credit_history_years: int = Field(default=0, ge=0, le=50)
    credit_utilization: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Assets
    owns_home: bool = False
    owns_car: bool = False
    home_value: Decimal = Field(default=0, ge=0, le=10000000000)
    car_value: Decimal = Field(default=0, ge=0, le=100000000)
    investments_value: Decimal = Field(default=0, ge=0, le=10000000000)
    savings_value: Decimal = Field(default=0, ge=0, le=10000000000)
    
    # Identity Documents
    pan_number: Optional[str] = Field(None, max_length=20, pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
    aadhaar_number: Optional[str] = Field(None, max_length=20, pattern=r'^\d{12}$')
    voter_id: Optional[str] = Field(None, max_length=50)
    passport_number: Optional[str] = Field(None, max_length=50)
    driving_license: Optional[str] = Field(None, max_length=50)
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate applicant is at least 18 years old."""
        if v:
            from datetime import date
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 18:
                raise ValueError('Applicant must be at least 18 years old')
            if age > 100:
                raise ValueError('Invalid date of birth')
        return v
    
    @model_validator(mode='after')
    def validate_financial_data(self):
        """Cross-field validation for financial data."""
        if self.existing_emi > self.income:
            raise ValueError('Existing EMI cannot exceed monthly income')
        if self.monthly_expenses > self.income + self.additional_income:
            raise ValueError('Monthly expenses cannot exceed total income')
        return self


class ApplicantUpdateRequest(BaseSchema):
    """Update applicant request - all fields optional."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    employment_type: Optional[EmploymentTypeEnum] = None
    employer_name: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=200)
    employment_years: Optional[int] = Field(None, ge=0, le=60)
    employment_months: Optional[int] = Field(None, ge=0, le=11)
    income: Optional[Decimal] = Field(None, ge=0, le=100000000)
    additional_income: Optional[Decimal] = Field(None, ge=0, le=100000000)
    cibil_score: Optional[int] = Field(None, ge=300, le=900)


class ApplicantResponse(BaseSchema):
    """Applicant response."""
    id: str
    applicant_ref: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str
    city: Optional[str]
    state: Optional[str]
    country: str
    employment_type: Optional[str]
    employer_name: Optional[str]
    income: float
    cibil_score: Optional[int]
    kyc_status: str
    risk_score: Optional[float]
    risk_category: Optional[str]
    created_at: str
    updated_at: str


# =============================================================================
# Loan Application Schemas
# =============================================================================

class ApplicationCreateRequest(BaseSchema):
    """Create loan application request with validation."""
    applicant_id: UUID
    loan_type: LoanTypeEnum = Field(default=LoanTypeEnum.PERSONAL)
    loan_amount: Decimal = Field(..., gt=0, le=100000000, description="Requested loan amount")
    loan_term_months: int = Field(..., ge=1, le=360, description="Loan term in months")
    interest_rate_requested: Optional[Decimal] = Field(None, ge=0, le=50)
    purpose: Optional[str] = Field(None, max_length=500)
    purpose_description: Optional[str] = Field(None, max_length=1000)
    collateral_type: Optional[str] = Field(None, max_length=100)
    collateral_value: Decimal = Field(default=0, ge=0, le=10000000000)
    co_applicant_name: Optional[str] = Field(None, max_length=200)
    co_applicant_income: Decimal = Field(default=0, ge=0, le=100000000)
    co_applicant_relationship: Optional[str] = Field(None, max_length=100)
    
    @model_validator(mode='after')
    def validate_collateral(self):
        """Validate collateral data consistency."""
        if self.collateral_value > 0 and not self.collateral_type:
            raise ValueError('Collateral type is required when collateral value is provided')
        return self


class ApplicationUpdateRequest(BaseSchema):
    """Update loan application request."""
    loan_amount: Optional[Decimal] = Field(None, gt=0, le=100000000)
    loan_term_months: Optional[int] = Field(None, ge=1, le=360)
    purpose: Optional[str] = Field(None, max_length=500)
    purpose_description: Optional[str] = Field(None, max_length=1000)
    collateral_value: Optional[Decimal] = Field(None, ge=0, le=10000000000)


class StatusUpdateRequest(BaseSchema):
    """Application status update request."""
    status: ApplicationStatusEnum
    notes: Optional[str] = Field(None, max_length=1000)
    rejection_reason: Optional[str] = Field(None, max_length=500)
    rejection_category: Optional[str] = Field(None, max_length=100)
    
    @model_validator(mode='after')
    def validate_rejection_fields(self):
        """Validate rejection fields are provided when rejecting."""
        if self.status == ApplicationStatusEnum.REJECTED:
            if not self.rejection_reason:
                raise ValueError('Rejection reason is required when rejecting an application')
        return self


class ApplicationResponse(BaseSchema):
    """Application response."""
    id: str
    application_number: str
    applicant_id: str
    applicant_name: str
    loan_type: str
    loan_amount: float
    loan_term_months: int
    interest_rate_offered: Optional[float]
    monthly_emi: Optional[float]
    status: str
    status_display: str
    ml_approval_probability: Optional[float]
    ml_risk_score: Optional[float]
    ml_recommendation: Optional[str]
    submitted_at: Optional[str]
    created_at: str
    updated_at: str


class ApplicationDetailResponse(ApplicationResponse):
    """Detailed application response."""
    interest_rate_requested: Optional[float]
    purpose: Optional[str]
    purpose_description: Optional[str]
    collateral_type: Optional[str]
    collateral_value: float
    processing_fee: float
    co_applicant_name: Optional[str]
    co_applicant_income: float
    co_applicant_relationship: Optional[str]
    
    # ML Predictions
    ml_predicted_at: Optional[str]
    ml_model_version: Optional[str]
    xai_explanation: Optional[Dict[str, Any]]
    eligibility_tips: Optional[List[str]]
    
    # Manual Review
    requires_manual_review: bool
    manual_review_reason: Optional[str]
    reviewed_by_name: Optional[str]
    reviewed_at: Optional[str]
    review_notes: Optional[str]
    
    # Timeline
    under_review_at: Optional[str]
    approved_at: Optional[str]
    rejected_at: Optional[str]
    disbursed_at: Optional[str]
    
    # Rejection details
    rejection_reason: Optional[str]
    rejection_category: Optional[str]
    appeal_deadline: Optional[str]
    
    # Disbursement
    disbursement_amount: Optional[float]
    disbursement_account: Optional[str]


class PredictionRequest(BaseSchema):
    """ML prediction request."""
    recalculate: bool = Field(default=False, description="Force recalculation")


class PredictionResponse(BaseSchema):
    """ML prediction response."""
    application_id: str
    approval_probability: float = Field(..., ge=0, le=1)
    risk_score: float = Field(..., ge=0, le=100)
    recommendation: str
    confidence: float = Field(..., ge=0, le=1)
    explanation: Dict[str, Any]
    eligibility_tips: List[str]
    predicted_at: str
    model_version: str


# =============================================================================
# Admin Schemas
# =============================================================================

class CreateUserRequest(BaseSchema):
    """Admin user creation request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRoleEnum = Field(default=UserRoleEnum.ANALYST)


class UpdateUserRequest(BaseSchema):
    """User update request."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[UserRoleEnum] = None
    status: Optional[UserStatusEnum] = None


class SystemStatsResponse(BaseSchema):
    """System statistics response."""
    total_users: int
    active_users: int
    total_applicants: int
    total_applications: int
    applications_by_status: Dict[str, int]
    applications_by_loan_type: Dict[str, int]
    total_loan_amount_requested: float
    total_loan_amount_approved: float
    average_loan_amount: float
    approval_rate: float
    rejection_rate: float
    pending_review_count: int


class DashboardStatsResponse(BaseSchema):
    """Dashboard statistics response."""
    applications_today: int
    applications_this_week: int
    applications_this_month: int
    pending_review: int
    approved_today: int
    rejected_today: int
    disbursed_this_month: float
    average_processing_days: float


# =============================================================================
# Pagination Schemas
# =============================================================================

class PaginatedUsersResponse(PaginatedResponse):
    """Paginated users response."""
    items: List[UserResponse]


class PaginatedApplicantsResponse(PaginatedResponse):
    """Paginated applicants response."""
    items: List[ApplicantResponse]


class PaginatedApplicationsResponse(PaginatedResponse):
    """Paginated applications response."""
    items: List[ApplicationResponse]
