"""
Admin Routes
============
Administrative endpoints for system management, user management, and statistics.

Author: Loan Analytics Team
Version: 1.0.0
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from database.models import (
    User, UserRole, UserStatus, Applicant, LoanApplication,
    ApplicationStatus, LoanType, ApplicationAuditLog, UserSession
)
from api.dependencies import get_db, require_admin, require_manager_or_admin
from api.auth import hash_password, validate_password_strength
from api.config import get_settings

settings = get_settings()
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class CreateUserRequest(BaseModel):
    """Admin user creation request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(default="analyst", description="User role")


class UpdateUserRequest(BaseModel):
    """User update request."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
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
    is_deleted: bool


class PaginatedUsersResponse(BaseModel):
    """Paginated users response."""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SystemStatsResponse(BaseModel):
    """System statistics response."""
    total_users: int
    active_users: int
    total_applicants: int
    total_applications: int
    applications_by_status: dict
    applications_by_loan_type: dict
    total_loan_amount_requested: float
    total_loan_amount_approved: float
    average_loan_amount: float
    approval_rate: float
    rejection_rate: float
    pending_review_count: int


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    applications_today: int
    applications_this_week: int
    applications_this_month: int
    pending_review: int
    approved_today: int
    rejected_today: int
    disbursed_this_month: float
    average_processing_days: float


# =============================================================================
# Helper Functions
# =============================================================================

def user_to_response(user: User) -> UserResponse:
    """Convert user model to response."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.value,
        status=user.status.value,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        is_deleted=user.is_deleted
    )


# =============================================================================
# User Management Routes
# =============================================================================

@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    include_deleted: bool = Query(False),
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """
    List all users (manager/admin only).
    """
    query = db.query(User)
    
    if not include_deleted:
        query = query.filter(User.is_deleted == False)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    # Role filter
    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass
    
    # Status filter
    if status_filter:
        try:
            status_enum = UserStatus(status_filter)
            query = query.filter(User.status == status_enum)
        except ValueError:
            pass
    
    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    
    return PaginatedUsersResponse(
        items=[user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only).
    """
    # Validate password
    is_valid, issues = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "issues": issues}
        )
    
    # Check if email exists
    existing = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_deleted == False
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Parse role
    try:
        role_enum = UserRole(request.role)
    except ValueError:
        role_enum = UserRole.ANALYST
    
    # Create user
    user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        role=role_enum,
        status=UserStatus.ACTIVE,
        email_verified=True  # Admin-created users are pre-verified
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user_to_response(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get user by ID (manager/admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot modify self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own account via admin API"
        )
    
    update_data = request.model_dump(exclude_unset=True)
    
    # Convert role string to enum
    if 'role' in update_data:
        try:
            update_data['role'] = UserRole(update_data['role'])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {update_data['role']}"
            )
    
    # Convert status string to enum
    if 'status' in update_data:
        try:
            update_data['status'] = UserStatus(update_data['status'])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {update_data['status']}"
            )
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user_to_response(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Soft delete a user (admin only).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot delete self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user.soft_delete(current_user.id)
    db.commit()


@router.post("/users/{user_id}/restore", response_model=UserResponse)
async def restore_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Restore a soft-deleted user (admin only).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted user not found"
        )
    
    user.restore()
    db.commit()
    db.refresh(user)
    
    return user_to_response(user)


# =============================================================================
# Statistics Routes
# =============================================================================

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get system statistics (manager/admin only).
    """
    # User stats
    total_users = db.query(User).filter(User.is_deleted == False).count()
    active_users = db.query(User).filter(
        User.is_deleted == False,
        User.status == UserStatus.ACTIVE
    ).count()
    
    # Applicant stats
    total_applicants = db.query(Applicant).filter(Applicant.is_deleted == False).count()
    
    # Application stats
    total_applications = db.query(LoanApplication).filter(
        LoanApplication.is_deleted == False
    ).count()
    
    # Applications by status
    status_counts = db.query(
        LoanApplication.status,
        func.count(LoanApplication.id)
    ).filter(
        LoanApplication.is_deleted == False
    ).group_by(LoanApplication.status).all()
    
    applications_by_status = {s.value: c for s, c in status_counts}
    
    # Applications by loan type
    type_counts = db.query(
        LoanApplication.loan_type,
        func.count(LoanApplication.id)
    ).filter(
        LoanApplication.is_deleted == False
    ).group_by(LoanApplication.loan_type).all()
    
    applications_by_loan_type = {t.value: c for t, c in type_counts}
    
    # Loan amounts
    total_requested = db.query(
        func.sum(LoanApplication.loan_amount)
    ).filter(LoanApplication.is_deleted == False).scalar() or 0
    
    total_approved = db.query(
        func.sum(LoanApplication.loan_amount)
    ).filter(
        LoanApplication.is_deleted == False,
        LoanApplication.status == ApplicationStatus.APPROVED
    ).scalar() or 0
    
    avg_amount = db.query(
        func.avg(LoanApplication.loan_amount)
    ).filter(LoanApplication.is_deleted == False).scalar() or 0
    
    # Rates
    approved_count = applications_by_status.get("approved", 0)
    rejected_count = applications_by_status.get("rejected", 0)
    decided_count = approved_count + rejected_count
    
    approval_rate = (approved_count / decided_count * 100) if decided_count > 0 else 0
    rejection_rate = (rejected_count / decided_count * 100) if decided_count > 0 else 0
    
    # Pending review
    pending_review = db.query(LoanApplication).filter(
        LoanApplication.is_deleted == False,
        LoanApplication.requires_manual_review == True,
        LoanApplication.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW])
    ).count()
    
    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_applicants=total_applicants,
        total_applications=total_applications,
        applications_by_status=applications_by_status,
        applications_by_loan_type=applications_by_loan_type,
        total_loan_amount_requested=float(total_requested),
        total_loan_amount_approved=float(total_approved),
        average_loan_amount=float(avg_amount),
        approval_rate=round(approval_rate, 2),
        rejection_rate=round(rejection_rate, 2),
        pending_review_count=pending_review
    )


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics (manager/admin only).
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    
    # Applications today
    applications_today = db.query(LoanApplication).filter(
        LoanApplication.created_at >= today_start,
        LoanApplication.is_deleted == False
    ).count()
    
    # Applications this week
    applications_this_week = db.query(LoanApplication).filter(
        LoanApplication.created_at >= week_start,
        LoanApplication.is_deleted == False
    ).count()
    
    # Applications this month
    applications_this_month = db.query(LoanApplication).filter(
        LoanApplication.created_at >= month_start,
        LoanApplication.is_deleted == False
    ).count()
    
    # Pending review
    pending_review = db.query(LoanApplication).filter(
        LoanApplication.is_deleted == False,
        LoanApplication.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW])
    ).count()
    
    # Approved today
    approved_today = db.query(LoanApplication).filter(
        LoanApplication.approved_at >= today_start,
        LoanApplication.is_deleted == False
    ).count()
    
    # Rejected today
    rejected_today = db.query(LoanApplication).filter(
        LoanApplication.rejected_at >= today_start,
        LoanApplication.is_deleted == False
    ).count()
    
    # Disbursed this month
    disbursed_this_month = db.query(
        func.sum(LoanApplication.disbursement_amount)
    ).filter(
        LoanApplication.disbursed_at >= month_start,
        LoanApplication.is_deleted == False
    ).scalar() or 0
    
    # Average processing days (from submission to decision)
    processed = db.query(LoanApplication).filter(
        LoanApplication.submitted_at.isnot(None),
        LoanApplication.status.in_([ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]),
        LoanApplication.is_deleted == False
    ).all()
    
    if processed:
        total_days = sum(
            (app.approved_at or app.rejected_at - app.submitted_at).days
            for app in processed
            if (app.approved_at or app.rejected_at)
        )
        avg_processing = total_days / len(processed)
    else:
        avg_processing = 0
    
    return DashboardStats(
        applications_today=applications_today,
        applications_this_week=applications_this_week,
        applications_this_month=applications_this_month,
        pending_review=pending_review,
        approved_today=approved_today,
        rejected_today=rejected_today,
        disbursed_this_month=float(disbursed_this_month),
        average_processing_days=round(avg_processing, 1)
    )


# =============================================================================
# Audit Log Routes
# =============================================================================

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit logs (admin only).
    """
    query = db.query(ApplicationAuditLog)
    
    if entity_type:
        query = query.filter(ApplicationAuditLog.entity_type == entity_type)
    
    if action:
        from database.models import AuditAction
        try:
            action_enum = AuditAction(action)
            query = query.filter(ApplicationAuditLog.action == action_enum)
        except ValueError:
            pass
    
    if user_id:
        query = query.filter(ApplicationAuditLog.user_id == user_id)
    
    if start_date:
        query = query.filter(ApplicationAuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(ApplicationAuditLog.created_at <= end_date)
    
    total = query.count()
    offset = (page - 1) * page_size
    
    logs = query.order_by(
        ApplicationAuditLog.created_at.desc()
    ).offset(offset).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": str(log.id),
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id),
                "action": log.action.value,
                "user_id": str(log.user_id) if log.user_id else None,
                "user_name": log.user.full_name if log.user else "System",
                "changes": log.changes,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "notes": log.notes,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


# =============================================================================
# Session Management Routes
# =============================================================================

@router.get("/sessions")
async def list_active_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List active sessions (admin only).
    """
    query = db.query(UserSession).filter(
        UserSession.is_active == True,
        UserSession.revoked == False
    )
    
    if user_id:
        query = query.filter(UserSession.user_id == user_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    
    sessions = query.order_by(
        UserSession.last_used_at.desc()
    ).offset(offset).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "user_email": s.user.email if s.user else None,
                "device_name": s.device_name,
                "device_type": s.device_type,
                "browser": s.browser,
                "ip_address": s.ip_address,
                "location": s.location,
                "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "created_at": s.created_at.isoformat()
            }
            for s in sessions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke a specific session (admin only).
    """
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    session.revoked = True
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = f"Admin revoked by {current_user.email}"
    
    db.commit()
    
    return {"success": True, "message": "Session revoked"}


@router.post("/users/{user_id}/revoke-all-sessions")
async def revoke_all_user_sessions(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke all sessions for a user (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Increment token version to invalidate all tokens
    user.refresh_token_version += 1
    
    # Revoke all sessions
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).all()
    
    for session in sessions:
        session.is_active = False
        session.revoked = True
        session.revoked_at = datetime.utcnow()
        session.revoked_reason = f"All sessions revoked by admin {current_user.email}"
    
    db.commit()
    
    return {"success": True, "message": f"Revoked {len(sessions)} sessions"}
