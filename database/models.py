"""
Database Models for Loan Approval System
=========================================
SQLAlchemy ORM models for PostgreSQL database.

Design Principles:
- UUID primary keys for all entities
- Soft deletes (never delete records, use is_deleted flag)
- Timestamps everywhere (created_at, updated_at, deleted_at)
- JSONB for flexible data storage
- Proper indexing for performance

Entities:
- User: Authentication and authorization
- Applicant: Personal info, income, employment, KYC status
- LoanApplication: Loan details, status, explanation, eligibility tips
- ApplicationAuditLog: Complete audit trail

Author: Loan Analytics Team
Version: 2.0.0
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum, Index, CheckConstraint, event
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================================
# Enums
# ============================================================================

class UserRole(PyEnum):
    """User roles for authorization."""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    APPLICANT = "applicant"


class UserStatus(PyEnum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class KYCStatus(PyEnum):
    """KYC verification status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    RESUBMISSION_REQUIRED = "resubmission_required"


class ApplicationStatus(PyEnum):
    """Loan application status."""
    DRAFT = "draft"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    DOCUMENTS_REQUIRED = "documents_required"
    APPROVED = "approved"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    REJECTED = "rejected"
    DISBURSEMENT_PENDING = "disbursement_pending"
    DISBURSED = "disbursed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class EmploymentType(PyEnum):
    """Employment type."""
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    SELF_EMPLOYED_PROFESSIONAL = "self_employed_professional"
    BUSINESS_OWNER = "business_owner"
    GOVERNMENT = "government"
    PSU = "psu"
    RETIRED = "retired"
    STUDENT = "student"
    UNEMPLOYED = "unemployed"
    HOMEMAKER = "homemaker"


class Gender(PyEnum):
    """Gender."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class MaritalStatus(PyEnum):
    """Marital status."""
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    SEPARATED = "separated"


class Education(PyEnum):
    """Education level."""
    BELOW_HIGH_SCHOOL = "below_high_school"
    HIGH_SCHOOL = "high_school"
    DIPLOMA = "diploma"
    GRADUATE = "graduate"
    POST_GRADUATE = "post_graduate"
    PROFESSIONAL = "professional"
    DOCTORATE = "doctorate"


class LoanType(PyEnum):
    """Loan types."""
    PERSONAL = "personal"
    HOME = "home"
    VEHICLE = "vehicle"
    EDUCATION = "education"
    BUSINESS = "business"
    GOLD = "gold"
    AGRICULTURE = "agriculture"
    CONSUMER_DURABLE = "consumer_durable"
    CREDIT_CARD = "credit_card"


class AuditAction(PyEnum):
    """Audit log actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STATUS_CHANGE = "status_change"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    VERIFICATION = "verification"
    APPROVAL = "approval"
    REJECTION = "rejection"
    DISBURSEMENT = "disbursement"


# ============================================================================
# Base Mixin for common fields
# ============================================================================

class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete support."""
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    
    def soft_delete(self, deleted_by_id: Optional[uuid.UUID] = None):
        """Mark record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by_id


class AuditMixin:
    """Mixin for audit fields."""
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


# ============================================================================
# User Entity (for JWT Authentication)
# ============================================================================

class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User entity for authentication and authorization.
    
    Supports JWT-based authentication with refresh tokens.
    """
    __tablename__ = 'users'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Role & Status
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Session management
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # JWT tracking
    refresh_token_version = Column(Integer, default=1)
    
    # Preferences (JSON)
    preferences = Column(JSONB, default=dict)
    
    # Linked applicant (if user is also an applicant)
    linked_applicant_id = Column(UUID(as_uuid=True), ForeignKey('applicants.id'), nullable=True)
    
    # Extra Data
    extra_data = Column(JSONB, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
        Index('idx_user_status', 'status'),
        Index('idx_user_created', 'created_at'),
        Index('idx_user_not_deleted', 'is_deleted'),
    )
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE and not self.is_deleted
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary."""
        data = {
            'id': str(self.id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role.value,
            'status': self.status.value,
            'email_verified': self.email_verified,
            'avatar_url': self.avatar_url,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_sensitive:
            data['linked_applicant_id'] = str(self.linked_applicant_id) if self.linked_applicant_id else None
            data['preferences'] = self.preferences
        
        return data
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"


# ============================================================================
# Applicant Entity
# ============================================================================

class Applicant(Base, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """
    Applicant entity containing all applicant information.
    """
    __tablename__ = 'applicants'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference number (human readable)
    applicant_ref = Column(String(50), unique=True, nullable=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    marital_status = Column(Enum(MaritalStatus), nullable=True)
    num_dependents = Column(Integer, default=0)
    education = Column(Enum(Education), nullable=True)
    
    # Contact Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_primary = Column(String(20), nullable=False, index=True)
    phone_alternate = Column(String(20), nullable=True)
    
    # Current Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default='India')
    residence_type = Column(String(50), nullable=True)
    years_at_current_address = Column(Float, default=0)
    
    # Permanent Address (if different)
    permanent_address_same = Column(Boolean, default=True)
    permanent_address = Column(JSONB, nullable=True)
    
    # Income Details
    monthly_income = Column(Float, nullable=False, default=0)
    annual_income = Column(Float, nullable=True)
    other_income = Column(Float, default=0)
    other_income_source = Column(String(255), nullable=True)
    income_proof_type = Column(String(100), nullable=True)
    income_verified = Column(Boolean, default=False)
    income_verified_at = Column(DateTime(timezone=True), nullable=True)
    income_verified_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Employment Information
    employment_type = Column(Enum(EmploymentType), nullable=True)
    employer_name = Column(String(255), nullable=True)
    employer_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    employee_id = Column(String(50), nullable=True)
    years_at_current_job = Column(Float, default=0)
    total_work_experience = Column(Float, default=0)
    
    # Office Address
    office_address = Column(Text, nullable=True)
    office_email = Column(String(255), nullable=True)
    office_phone = Column(String(20), nullable=True)
    
    # Employment verification
    employment_verified = Column(Boolean, default=False)
    employment_verified_at = Column(DateTime(timezone=True), nullable=True)
    employment_verified_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Financial Information
    existing_emi = Column(Float, default=0)
    num_existing_loans = Column(Integer, default=0)
    existing_loans_details = Column(JSONB, default=list)
    
    # Bank Details
    primary_bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    account_type = Column(String(50), nullable=True)
    years_with_bank = Column(Integer, default=0)
    average_monthly_balance = Column(Float, nullable=True)
    
    # Savings & Investments
    savings_balance = Column(Float, default=0)
    investments_value = Column(Float, default=0)
    investment_details = Column(JSONB, default=list)
    
    # Credit Information
    cibil_score = Column(Integer, nullable=True)
    cibil_fetched_at = Column(DateTime(timezone=True), nullable=True)
    credit_history_years = Column(Integer, default=0)
    num_credit_cards = Column(Integer, default=0)
    total_credit_limit = Column(Float, default=0)
    credit_utilization = Column(Float, nullable=True)
    late_payments_last_12_months = Column(Integer, default=0)
    late_payments_last_24_months = Column(Integer, default=0)
    has_defaults = Column(Boolean, default=False)
    has_written_off = Column(Boolean, default=False)
    has_settled_accounts = Column(Boolean, default=False)
    
    # Assets
    owns_property = Column(Boolean, default=False)
    property_details = Column(JSONB, default=list)
    total_property_value = Column(Float, default=0)
    owns_vehicle = Column(Boolean, default=False)
    vehicle_details = Column(JSONB, default=list)
    other_assets = Column(JSONB, default=list)
    total_assets_value = Column(Float, default=0)
    
    # Liabilities
    total_liabilities = Column(Float, default=0)
    net_worth = Column(Float, nullable=True)
    
    # KYC Information
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.PENDING, index=True)
    kyc_initiated_at = Column(DateTime(timezone=True), nullable=True)
    kyc_completed_at = Column(DateTime(timezone=True), nullable=True)
    kyc_verified_by = Column(UUID(as_uuid=True), nullable=True)
    kyc_rejection_reason = Column(Text, nullable=True)
    kyc_expiry_date = Column(Date, nullable=True)
    
    # Identity Documents
    pan_number = Column(String(20), nullable=True, index=True)
    pan_verified = Column(Boolean, default=False)
    pan_verified_at = Column(DateTime(timezone=True), nullable=True)
    pan_name = Column(String(255), nullable=True)
    
    aadhaar_number = Column(String(20), nullable=True)
    aadhaar_verified = Column(Boolean, default=False)
    aadhaar_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    passport_number = Column(String(20), nullable=True)
    passport_expiry = Column(Date, nullable=True)
    voter_id = Column(String(20), nullable=True)
    driving_license = Column(String(30), nullable=True)
    driving_license_expiry = Column(Date, nullable=True)
    
    # Document Storage
    documents = Column(JSONB, default=list)
    
    # Risk Assessment
    risk_score = Column(Float, nullable=True)
    risk_category = Column(String(50), nullable=True)
    risk_factors = Column(JSONB, default=list)
    risk_assessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extra Data
    source_channel = Column(String(50), nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    referral_code = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSONB, default=list)
    extra_data = Column(JSONB, default=dict)
    
    # Relationships
    loan_applications = relationship(
        "LoanApplication",
        back_populates="applicant",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_applicant_email', 'email'),
        Index('idx_applicant_phone', 'phone_primary'),
        Index('idx_applicant_pan', 'pan_number'),
        Index('idx_applicant_ref', 'applicant_ref'),
        Index('idx_applicant_kyc_status', 'kyc_status'),
        Index('idx_applicant_created', 'created_at'),
        Index('idx_applicant_not_deleted', 'is_deleted'),
        Index('idx_applicant_city', 'city'),
        CheckConstraint('monthly_income >= 0', name='check_positive_income'),
        CheckConstraint('cibil_score IS NULL OR (cibil_score >= 300 AND cibil_score <= 900)', 
                       name='check_cibil_range'),
    )
    
    @staticmethod
    def generate_applicant_ref() -> str:
        """Generate unique applicant reference."""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:8].upper()
        return f"APP-{timestamp}-{random_part}"
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int:
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return 0
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def debt_to_income_ratio(self) -> float:
        """Calculate debt-to-income ratio."""
        if self.monthly_income and self.monthly_income > 0:
            return round((self.existing_emi / self.monthly_income) * 100, 2)
        return 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            'id': str(self.id),
            'applicant_ref': self.applicant_ref,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'age': self.age,
            'gender': self.gender.value if self.gender else None,
            'marital_status': self.marital_status.value if self.marital_status else None,
            'num_dependents': self.num_dependents,
            'education': self.education.value if self.education else None,
            'email': self.email,
            'phone_primary': self.phone_primary,
            'city': self.city,
            'state': self.state,
            'monthly_income': self.monthly_income,
            'annual_income': self.annual_income,
            'employment_type': self.employment_type.value if self.employment_type else None,
            'employer_name': self.employer_name,
            'industry': self.industry,
            'years_at_current_job': self.years_at_current_job,
            'total_work_experience': self.total_work_experience,
            'existing_emi': self.existing_emi,
            'num_existing_loans': self.num_existing_loans,
            'cibil_score': self.cibil_score,
            'credit_history_years': self.credit_history_years,
            'has_defaults': self.has_defaults,
            'owns_property': self.owns_property,
            'kyc_status': self.kyc_status.value if self.kyc_status else None,
            'risk_category': self.risk_category,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_model_input(self) -> dict:
        """Convert to ML model input format."""
        return {
            'age': self.age,
            'gender': self.gender.value.title() if self.gender else 'Other',
            'education': self.education.value.replace('_', ' ').title() if self.education else 'Graduate',
            'marital_status': self.marital_status.value.title() if self.marital_status else 'Single',
            'num_dependents': self.num_dependents or 0,
            'employment_type': self.employment_type.value.replace('_', ' ').title() if self.employment_type else 'Salaried',
            'industry': self.industry or 'Other',
            'years_at_current_job': self.years_at_current_job or 0,
            'monthly_income': self.monthly_income or 0,
            'existing_emi': self.existing_emi or 0,
            'num_existing_loans': self.num_existing_loans or 0,
            'savings_balance': self.savings_balance or 0,
            'cibil_score': self.cibil_score or 650,
            'credit_history_years': self.credit_history_years or 0,
            'late_payments_last_2_years': self.late_payments_last_24_months or 0,
            'has_defaults': self.has_defaults or False,
            'owns_property': self.owns_property or False,
            'years_with_bank': self.years_with_bank or 0
        }
    
    def __repr__(self):
        return f"<Applicant(id={self.id}, ref='{self.applicant_ref}', name='{self.full_name}')>"


# ============================================================================
# Loan Application Entity
# ============================================================================

class LoanApplication(Base, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """
    Loan Application entity with full tracking.
    """
    __tablename__ = 'loan_applications'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Applicant Reference
    applicant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('applicants.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    
    # Loan Details
    loan_type = Column(Enum(LoanType), default=LoanType.PERSONAL, nullable=False)
    loan_amount = Column(Float, nullable=False)
    loan_amount_approved = Column(Float, nullable=True)
    tenure_months = Column(Integer, nullable=False)
    tenure_approved = Column(Integer, nullable=True)
    loan_purpose = Column(String(255), nullable=False)
    loan_purpose_details = Column(Text, nullable=True)
    
    # Interest & Fees
    interest_rate_requested = Column(Float, nullable=True)
    interest_rate_offered = Column(Float, nullable=True)
    interest_rate_final = Column(Float, nullable=True)
    processing_fee_percent = Column(Float, nullable=True)
    processing_fee_amount = Column(Float, nullable=True)
    other_charges = Column(JSONB, default=dict)
    
    # EMI Details
    emi_amount = Column(Float, nullable=True)
    total_interest = Column(Float, nullable=True)
    total_payable = Column(Float, nullable=True)
    first_emi_date = Column(Date, nullable=True)
    
    # Application Status
    status = Column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True
    )
    status_reason = Column(Text, nullable=True)
    status_updated_at = Column(DateTime(timezone=True), default=func.now())
    status_updated_by = Column(UUID(as_uuid=True), nullable=True)
    status_history = Column(JSONB, default=list)
    
    # Application Timeline
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_via = Column(String(50), nullable=True)
    under_review_at = Column(DateTime(timezone=True), nullable=True)
    under_review_by = Column(UUID(as_uuid=True), nullable=True)
    decision_at = Column(DateTime(timezone=True), nullable=True)
    decision_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)
    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    disbursed_by = Column(UUID(as_uuid=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # ML Model Prediction Results
    ml_processed = Column(Boolean, default=False)
    ml_processed_at = Column(DateTime(timezone=True), nullable=True)
    approval_probability = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    risk_score = Column(Float, nullable=True)
    model_id = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    
    # Decision Explanation (XAI)
    decision_explanation = Column(Text, nullable=True)
    explanation_summary = Column(String(500), nullable=True)
    positive_factors = Column(JSONB, default=list)
    negative_factors = Column(JSONB, default=list)
    feature_contributions = Column(JSONB, default=dict)
    
    # Eligibility Tips
    eligibility_tips = Column(JSONB, default=list)
    action_items = Column(JSONB, default=list)
    improvement_potential = Column(Float, nullable=True)
    
    # Manual Review
    requires_manual_review = Column(Boolean, default=False)
    manual_review_reasons = Column(JSONB, default=list)
    manual_review_priority = Column(String(20), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_decision = Column(String(50), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Rejection Details
    rejection_reason = Column(Text, nullable=True)
    rejection_category = Column(String(100), nullable=True)
    rejection_codes = Column(JSONB, default=list)
    can_reapply = Column(Boolean, default=True)
    reapply_after_date = Column(Date, nullable=True)
    appeal_allowed = Column(Boolean, default=False)
    appeal_deadline = Column(Date, nullable=True)
    
    # Disbursement Details
    disbursement_mode = Column(String(50), nullable=True)
    disbursement_account_number = Column(String(50), nullable=True)
    disbursement_account_name = Column(String(255), nullable=True)
    disbursement_bank = Column(String(100), nullable=True)
    disbursement_ifsc = Column(String(20), nullable=True)
    disbursement_amount = Column(Float, nullable=True)
    disbursement_reference = Column(String(100), nullable=True)
    disbursement_status = Column(String(50), nullable=True)
    
    # Documents
    required_documents = Column(JSONB, default=list)
    submitted_documents = Column(JSONB, default=list)
    pending_documents = Column(JSONB, default=list)
    document_verification_status = Column(String(50), nullable=True)
    
    # Co-applicant / Guarantor
    has_co_applicant = Column(Boolean, default=False)
    co_applicant_id = Column(UUID(as_uuid=True), nullable=True)
    has_guarantor = Column(Boolean, default=False)
    guarantor_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Collateral (for secured loans)
    is_secured = Column(Boolean, default=False)
    collateral_type = Column(String(100), nullable=True)
    collateral_value = Column(Float, nullable=True)
    collateral_details = Column(JSONB, default=dict)
    ltv_ratio = Column(Float, nullable=True)
    
    # Extra Data
    source_channel = Column(String(50), nullable=True)
    device_info = Column(JSONB, default=dict)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    tags = Column(JSONB, default=list)
    extra_data = Column(JSONB, default=dict)
    
    # Relationships
    applicant = relationship("Applicant", back_populates="loan_applications")
    audit_logs = relationship(
        "ApplicationAuditLog",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_loan_applicant', 'applicant_id'),
        Index('idx_loan_status', 'status'),
        Index('idx_loan_created', 'created_at'),
        Index('idx_loan_submitted', 'submitted_at'),
        Index('idx_loan_app_number', 'application_number'),
        Index('idx_loan_not_deleted', 'is_deleted'),
        Index('idx_loan_requires_review', 'requires_manual_review'),
        Index('idx_loan_assigned', 'assigned_to'),
        Index('idx_loan_risk', 'risk_level'),
        CheckConstraint('loan_amount >= 10000', name='check_min_loan_amount'),
        CheckConstraint('tenure_months >= 3 AND tenure_months <= 360', 
                       name='check_tenure_range'),
    )
    
    @staticmethod
    def generate_application_number() -> str:
        """Generate unique application number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:6].upper()
        return f"LA-{timestamp}-{random_part}"
    
    def get_status_display(self) -> dict:
        """Get status display with icon and color."""
        status_config = {
            ApplicationStatus.DRAFT: {"label": "Draft", "icon": "📝", "color": "gray"},
            ApplicationStatus.PENDING: {"label": "Pending Review", "icon": "⏳", "color": "yellow"},
            ApplicationStatus.UNDER_REVIEW: {"label": "Under Review", "icon": "🔍", "color": "blue"},
            ApplicationStatus.DOCUMENTS_REQUIRED: {"label": "Documents Required", "icon": "📋", "color": "orange"},
            ApplicationStatus.APPROVED: {"label": "Approved", "icon": "✅", "color": "green"},
            ApplicationStatus.CONDITIONALLY_APPROVED: {"label": "Conditionally Approved", "icon": "⚠️", "color": "yellow"},
            ApplicationStatus.REJECTED: {"label": "Rejected", "icon": "❌", "color": "red"},
            ApplicationStatus.DISBURSEMENT_PENDING: {"label": "Disbursement Pending", "icon": "💳", "color": "blue"},
            ApplicationStatus.DISBURSED: {"label": "Disbursed", "icon": "💰", "color": "green"},
            ApplicationStatus.CANCELLED: {"label": "Cancelled", "icon": "🚫", "color": "gray"},
            ApplicationStatus.CLOSED: {"label": "Closed", "icon": "✔️", "color": "gray"},
        }
        return status_config.get(self.status, {"label": str(self.status.value), "icon": "❓", "color": "gray"})
    
    def add_status_history(self, new_status: ApplicationStatus, by_user_id: Optional[uuid.UUID] = None, reason: str = None):
        """Add entry to status history."""
        history_entry = {
            'status': new_status.value,
            'at': datetime.utcnow().isoformat(),
            'by': str(by_user_id) if by_user_id else None,
            'reason': reason
        }
        if self.status_history is None:
            self.status_history = []
        self.status_history.append(history_entry)
    
    def to_dict(self, include_ml: bool = True, include_tips: bool = True) -> dict:
        """Convert to dictionary."""
        data = {
            'id': str(self.id),
            'application_number': self.application_number,
            'applicant_id': str(self.applicant_id),
            'loan_type': self.loan_type.value if self.loan_type else None,
            'loan_amount': self.loan_amount,
            'loan_amount_approved': self.loan_amount_approved,
            'tenure_months': self.tenure_months,
            'loan_purpose': self.loan_purpose,
            'status': self.status.value if self.status else None,
            'status_display': self.get_status_display(),
            'interest_rate_final': self.interest_rate_final,
            'emi_amount': self.emi_amount,
            'total_payable': self.total_payable,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'decision_at': self.decision_at.isoformat() if self.decision_at else None,
        }
        
        if include_ml:
            data.update({
                'approval_probability': self.approval_probability,
                'confidence_score': self.confidence_score,
                'risk_level': self.risk_level,
                'decision_explanation': self.decision_explanation,
                'positive_factors': self.positive_factors,
                'negative_factors': self.negative_factors,
                'requires_manual_review': self.requires_manual_review,
            })
        
        if include_tips:
            data.update({
                'eligibility_tips': self.eligibility_tips,
                'action_items': self.action_items,
            })
        
        return data
    
    def __repr__(self):
        return f"<LoanApplication(id={self.id}, number='{self.application_number}', status='{self.status.value}')>"


# ============================================================================
# Application Audit Log Entity
# ============================================================================

class ApplicationAuditLog(Base, TimestampMixin):
    """
    Audit log for tracking all changes to entities.
    Never deleted - provides complete audit trail for compliance.
    """
    __tablename__ = 'application_audit_logs'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey('loan_applications.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    applicant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Action Details
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    
    # Change Details
    field_name = Column(String(100), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    changes = Column(JSONB, default=dict)
    
    # Context
    performed_by = Column(UUID(as_uuid=True), nullable=True)
    performed_by_name = Column(String(255), nullable=True)
    performed_by_role = Column(String(50), nullable=True)
    
    # Request Context
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True)
    
    # Additional Info
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    extra_data = Column(JSONB, default=dict)
    
    # Relationships
    application = relationship("LoanApplication", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_application', 'application_id'),
        Index('idx_audit_applicant', 'applicant_id'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_performed_by', 'performed_by'),
        Index('idx_audit_created', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'entity_type': self.entity_type,
            'entity_id': str(self.entity_id),
            'action': self.action.value,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'performed_by': str(self.performed_by) if self.performed_by else None,
            'performed_by_name': self.performed_by_name,
            'reason': self.reason,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action.value}', entity='{self.entity_type}')>"


# ============================================================================
# Session/Token Tracking (for JWT management)
# ============================================================================

class UserSession(Base, TimestampMixin):
    """
    Track user sessions and refresh tokens.
    """
    __tablename__ = 'user_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Token Info
    refresh_token_jti = Column(String(255), unique=True, nullable=False, index=True)
    access_token_jti = Column(String(255), nullable=True)
    
    # Session Info
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), default=func.now())
    
    # Revocation
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('idx_session_user', 'user_id'),
        Index('idx_session_token', 'refresh_token_jti'),
        Index('idx_session_active', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
