"""
Repository Layer
================
Data access layer implementing the Repository pattern for clean separation
between business logic and data persistence.

Supports:
- CRUD operations
- Complex queries
- Pagination
- Search and filtering
- Batch operations

Author: Loan Analytics Team
Version: 1.0.0
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from uuid import UUID

from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import (
    Applicant, LoanApplication, ApplicationAuditLog,
    ApplicationStatus, KYCStatus, EmploymentType
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common CRUD operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def commit(self):
        """Commit current transaction."""
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Commit failed: {e}")
            raise
    
    def rollback(self):
        """Rollback current transaction."""
        self.session.rollback()
    
    def refresh(self, entity):
        """Refresh entity from database."""
        self.session.refresh(entity)


class ApplicantRepository(BaseRepository):
    """
    Repository for Applicant entity operations.
    
    Handles all data access for loan applicants including personal info,
    income details, employment, and KYC status.
    """
    
    def create(self, applicant: Applicant) -> Applicant:
        """Create a new applicant."""
        try:
            self.session.add(applicant)
            self.session.flush()  # Get ID without committing
            logger.info(f"Created applicant: {applicant.id}")
            return applicant
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Failed to create applicant: {e}")
            raise ValueError(f"Applicant with this email/phone already exists")
    
    def get_by_id(self, applicant_id: UUID) -> Optional[Applicant]:
        """Get applicant by ID."""
        return self.session.query(Applicant).filter(
            Applicant.id == applicant_id
        ).first()
    
    def get_by_email(self, email: str) -> Optional[Applicant]:
        """Get applicant by email."""
        return self.session.query(Applicant).filter(
            Applicant.email == email.lower()
        ).first()
    
    def get_by_phone(self, phone: str) -> Optional[Applicant]:
        """Get applicant by phone number."""
        return self.session.query(Applicant).filter(
            Applicant.phone == phone
        ).first()
    
    def get_by_pan(self, pan: str) -> Optional[Applicant]:
        """Get applicant by PAN number."""
        return self.session.query(Applicant).filter(
            Applicant.pan_number == pan.upper()
        ).first()
    
    def get_by_aadhaar(self, aadhaar: str) -> Optional[Applicant]:
        """Get applicant by Aadhaar number."""
        return self.session.query(Applicant).filter(
            Applicant.aadhaar_number == aadhaar
        ).first()
    
    def update(self, applicant: Applicant, data: Dict[str, Any]) -> Applicant:
        """Update applicant fields."""
        for key, value in data.items():
            if hasattr(applicant, key) and key not in ['id', 'created_at']:
                setattr(applicant, key, value)
        applicant.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated applicant: {applicant.id}")
        return applicant
    
    def delete(self, applicant_id: UUID) -> bool:
        """Soft delete applicant (set is_active=False)."""
        applicant = self.get_by_id(applicant_id)
        if applicant:
            applicant.is_active = False
            applicant.updated_at = datetime.utcnow()
            self.session.flush()
            logger.info(f"Deactivated applicant: {applicant_id}")
            return True
        return False
    
    def hard_delete(self, applicant_id: UUID) -> bool:
        """Permanently delete applicant (use with caution!)."""
        applicant = self.get_by_id(applicant_id)
        if applicant:
            self.session.delete(applicant)
            self.session.flush()
            logger.info(f"Permanently deleted applicant: {applicant_id}")
            return True
        return False
    
    def search(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        city: Optional[str] = None,
        employment_type: Optional[EmploymentType] = None,
        kyc_status: Optional[KYCStatus] = None,
        min_income: Optional[float] = None,
        max_income: Optional[float] = None,
        min_cibil: Optional[int] = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Tuple[List[Applicant], int]:
        """
        Search applicants with filters and pagination.
        
        Returns:
            Tuple of (list of applicants, total count)
        """
        query = self.session.query(Applicant)
        
        # Apply filters
        filters = []
        
        if is_active is not None:
            filters.append(Applicant.is_active == is_active)
        
        if name:
            name_filter = or_(
                Applicant.first_name.ilike(f'%{name}%'),
                Applicant.last_name.ilike(f'%{name}%'),
                Applicant.middle_name.ilike(f'%{name}%')
            )
            filters.append(name_filter)
        
        if email:
            filters.append(Applicant.email.ilike(f'%{email}%'))
        
        if phone:
            filters.append(Applicant.phone.contains(phone))
        
        if city:
            filters.append(Applicant.city.ilike(f'%{city}%'))
        
        if employment_type:
            filters.append(Applicant.employment_type == employment_type)
        
        if kyc_status:
            filters.append(Applicant.kyc_status == kyc_status)
        
        if min_income:
            filters.append(Applicant.monthly_income >= min_income)
        
        if max_income:
            filters.append(Applicant.monthly_income <= max_income)
        
        if min_cibil:
            filters.append(Applicant.cibil_score >= min_cibil)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(Applicant, sort_by, Applicant.created_at)
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        applicants = query.offset(offset).limit(page_size).all()
        
        return applicants, total
    
    def get_all_active(self) -> List[Applicant]:
        """Get all active applicants."""
        return self.session.query(Applicant).filter(
            Applicant.is_active == True
        ).all()
    
    def count_by_kyc_status(self) -> Dict[str, int]:
        """Get count of applicants by KYC status."""
        results = self.session.query(
            Applicant.kyc_status,
            func.count(Applicant.id)
        ).filter(
            Applicant.is_active == True
        ).group_by(Applicant.kyc_status).all()
        
        return {status.value: count for status, count in results}
    
    def get_applicants_pending_kyc(self) -> List[Applicant]:
        """Get applicants with pending KYC verification."""
        return self.session.query(Applicant).filter(
            Applicant.is_active == True,
            Applicant.kyc_status == KYCStatus.PENDING
        ).all()
    
    def update_kyc_status(
        self,
        applicant_id: UUID,
        status: KYCStatus,
        verified_by: Optional[str] = None
    ) -> Optional[Applicant]:
        """Update KYC status for an applicant."""
        applicant = self.get_by_id(applicant_id)
        if applicant:
            applicant.kyc_status = status
            if status == KYCStatus.VERIFIED:
                applicant.kyc_verified_at = datetime.utcnow()
                applicant.kyc_verified_by = verified_by
            applicant.updated_at = datetime.utcnow()
            self.session.flush()
            logger.info(f"Updated KYC status for {applicant_id}: {status.value}")
            return applicant
        return None
    
    def get_high_value_applicants(self, min_income: float = 100000) -> List[Applicant]:
        """Get high-value applicants based on income."""
        return self.session.query(Applicant).filter(
            Applicant.is_active == True,
            Applicant.monthly_income >= min_income
        ).order_by(desc(Applicant.monthly_income)).all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get applicant statistics."""
        total = self.session.query(func.count(Applicant.id)).filter(
            Applicant.is_active == True
        ).scalar()
        
        avg_income = self.session.query(func.avg(Applicant.monthly_income)).filter(
            Applicant.is_active == True
        ).scalar()
        
        avg_cibil = self.session.query(func.avg(Applicant.cibil_score)).filter(
            Applicant.is_active == True,
            Applicant.cibil_score != None
        ).scalar()
        
        kyc_counts = self.count_by_kyc_status()
        
        return {
            'total_applicants': total,
            'average_income': round(avg_income, 2) if avg_income else 0,
            'average_cibil_score': round(avg_cibil) if avg_cibil else 0,
            'kyc_status_distribution': kyc_counts
        }


class LoanApplicationRepository(BaseRepository):
    """
    Repository for LoanApplication entity operations.
    
    Handles all data access for loan applications including status tracking,
    ML predictions, explanations, and eligibility tips.
    """
    
    def create(self, application: LoanApplication) -> LoanApplication:
        """Create a new loan application."""
        try:
            # Generate application number if not set
            if not application.application_number:
                application.application_number = application.generate_application_number()
            
            self.session.add(application)
            self.session.flush()
            logger.info(f"Created loan application: {application.application_number}")
            return application
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Failed to create application: {e}")
            raise ValueError(f"Failed to create loan application")
    
    def get_by_id(self, application_id: UUID) -> Optional[LoanApplication]:
        """Get application by ID with applicant data."""
        return self.session.query(LoanApplication).options(
            joinedload(LoanApplication.applicant)
        ).filter(
            LoanApplication.id == application_id
        ).first()
    
    def get_by_application_number(self, app_number: str) -> Optional[LoanApplication]:
        """Get application by application number."""
        return self.session.query(LoanApplication).options(
            joinedload(LoanApplication.applicant)
        ).filter(
            LoanApplication.application_number == app_number
        ).first()
    
    def get_by_applicant_id(self, applicant_id: UUID) -> List[LoanApplication]:
        """Get all applications for an applicant."""
        return self.session.query(LoanApplication).filter(
            LoanApplication.applicant_id == applicant_id
        ).order_by(desc(LoanApplication.created_at)).all()
    
    def update_status(
        self,
        application_id: UUID,
        status: ApplicationStatus,
        updated_by: str,
        remarks: Optional[str] = None
    ) -> Optional[LoanApplication]:
        """Update application status with audit trail."""
        application = self.get_by_id(application_id)
        if application:
            old_status = application.status
            application.status = status
            application.status_updated_at = datetime.utcnow()
            application.status_updated_by = updated_by
            
            if remarks:
                application.review_remarks = remarks
            
            # Create audit log
            audit_log = ApplicationAuditLog(
                application_id=application_id,
                action='status_change',
                field_name='status',
                old_value=old_status.value,
                new_value=status.value,
                changed_by=updated_by,
                remarks=remarks
            )
            self.session.add(audit_log)
            self.session.flush()
            
            logger.info(f"Updated application {application_id} status: {old_status.value} -> {status.value}")
            return application
        return None
    
    def update_ml_prediction(
        self,
        application_id: UUID,
        prediction_result: Dict[str, Any]
    ) -> Optional[LoanApplication]:
        """Update application with ML prediction results."""
        application = self.get_by_id(application_id)
        if application:
            # Update prediction fields
            application.approval_probability = prediction_result.get('approval_probability')
            application.confidence_score = prediction_result.get('confidence_score')
            application.risk_level = prediction_result.get('risk_level')
            application.model_version = prediction_result.get('model_version')
            application.model_id = prediction_result.get('model_id')
            
            # Update explanation fields
            application.decision_explanation = prediction_result.get('explanation')
            application.positive_factors = prediction_result.get('positive_factors', [])
            application.negative_factors = prediction_result.get('negative_factors', [])
            application.feature_contributions = prediction_result.get('feature_contributions', {})
            
            # Update eligibility tips
            application.eligibility_tips = prediction_result.get('eligibility_tips', [])
            application.action_items = prediction_result.get('action_items', [])
            
            # Set status based on prediction
            if prediction_result.get('approved'):
                if prediction_result.get('requires_manual_review'):
                    application.status = ApplicationStatus.UNDER_REVIEW
                    application.requires_manual_review = True
                    application.manual_review_reason = prediction_result.get('review_reason')
                else:
                    application.status = ApplicationStatus.APPROVED
            else:
                application.status = ApplicationStatus.REJECTED
                application.rejection_reason = prediction_result.get('rejection_reason', 'Application did not meet eligibility criteria')
            
            application.status_updated_at = datetime.utcnow()
            application.updated_at = datetime.utcnow()
            
            self.session.flush()
            logger.info(f"Updated ML prediction for application: {application_id}")
            return application
        return None
    
    def search(
        self,
        applicant_id: Optional[UUID] = None,
        status: Optional[ApplicationStatus] = None,
        statuses: Optional[List[ApplicationStatus]] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        loan_purpose: Optional[str] = None,
        risk_level: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        requires_review: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Tuple[List[LoanApplication], int]:
        """
        Search applications with filters and pagination.
        
        Returns:
            Tuple of (list of applications, total count)
        """
        query = self.session.query(LoanApplication).options(
            joinedload(LoanApplication.applicant)
        )
        
        filters = []
        
        if applicant_id:
            filters.append(LoanApplication.applicant_id == applicant_id)
        
        if status:
            filters.append(LoanApplication.status == status)
        
        if statuses:
            filters.append(LoanApplication.status.in_(statuses))
        
        if min_amount:
            filters.append(LoanApplication.loan_amount >= min_amount)
        
        if max_amount:
            filters.append(LoanApplication.loan_amount <= max_amount)
        
        if loan_purpose:
            filters.append(LoanApplication.loan_purpose.ilike(f'%{loan_purpose}%'))
        
        if risk_level:
            filters.append(LoanApplication.risk_level == risk_level)
        
        if date_from:
            filters.append(LoanApplication.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to:
            filters.append(LoanApplication.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        if requires_review is not None:
            filters.append(LoanApplication.requires_manual_review == requires_review)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(LoanApplication, sort_by, LoanApplication.created_at)
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        applications = query.offset(offset).limit(page_size).all()
        
        return applications, total
    
    def get_pending_applications(self) -> List[LoanApplication]:
        """Get all pending applications awaiting processing."""
        return self.session.query(LoanApplication).filter(
            LoanApplication.status.in_([
                ApplicationStatus.PENDING,
                ApplicationStatus.DRAFT
            ])
        ).order_by(asc(LoanApplication.created_at)).all()
    
    def get_applications_for_review(self) -> List[LoanApplication]:
        """Get applications requiring manual review."""
        return self.session.query(LoanApplication).options(
            joinedload(LoanApplication.applicant)
        ).filter(
            LoanApplication.status == ApplicationStatus.UNDER_REVIEW,
            LoanApplication.requires_manual_review == True
        ).order_by(asc(LoanApplication.created_at)).all()
    
    def count_by_status(self) -> Dict[str, int]:
        """Get count of applications by status."""
        results = self.session.query(
            LoanApplication.status,
            func.count(LoanApplication.id)
        ).group_by(LoanApplication.status).all()
        
        return {status.value: count for status, count in results}
    
    def get_statistics(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get loan application statistics."""
        query = self.session.query(LoanApplication)
        
        if date_from:
            query = query.filter(LoanApplication.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(LoanApplication.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        total = query.count()
        
        approved = query.filter(LoanApplication.status == ApplicationStatus.APPROVED).count()
        rejected = query.filter(LoanApplication.status == ApplicationStatus.REJECTED).count()
        pending = query.filter(LoanApplication.status.in_([
            ApplicationStatus.PENDING,
            ApplicationStatus.DRAFT,
            ApplicationStatus.UNDER_REVIEW
        ])).count()
        
        total_amount = query.filter(
            LoanApplication.status == ApplicationStatus.APPROVED
        ).with_entities(
            func.sum(LoanApplication.loan_amount)
        ).scalar() or 0
        
        avg_amount = query.with_entities(
            func.avg(LoanApplication.loan_amount)
        ).scalar() or 0
        
        avg_approval_probability = query.filter(
            LoanApplication.approval_probability != None
        ).with_entities(
            func.avg(LoanApplication.approval_probability)
        ).scalar() or 0
        
        status_counts = self.count_by_status()
        
        return {
            'total_applications': total,
            'approved_count': approved,
            'rejected_count': rejected,
            'pending_count': pending,
            'approval_rate': round(approved / total * 100, 2) if total > 0 else 0,
            'total_approved_amount': float(total_amount),
            'average_loan_amount': round(float(avg_amount), 2),
            'average_approval_probability': round(float(avg_approval_probability) * 100, 2),
            'status_distribution': status_counts
        }
    
    def get_recent_applications(self, limit: int = 10) -> List[LoanApplication]:
        """Get most recent applications."""
        return self.session.query(LoanApplication).options(
            joinedload(LoanApplication.applicant)
        ).order_by(desc(LoanApplication.created_at)).limit(limit).all()
    
    def get_application_audit_trail(self, application_id: UUID) -> List[ApplicationAuditLog]:
        """Get complete audit trail for an application."""
        return self.session.query(ApplicationAuditLog).filter(
            ApplicationAuditLog.application_id == application_id
        ).order_by(desc(ApplicationAuditLog.timestamp)).all()
    
    def approve_application(
        self,
        application_id: UUID,
        approved_by: str,
        approved_amount: Optional[float] = None,
        interest_rate: Optional[float] = None,
        tenure_months: Optional[int] = None,
        remarks: Optional[str] = None
    ) -> Optional[LoanApplication]:
        """Approve a loan application."""
        application = self.get_by_id(application_id)
        if application:
            application.status = ApplicationStatus.APPROVED
            application.status_updated_at = datetime.utcnow()
            application.status_updated_by = approved_by
            application.review_remarks = remarks
            
            if approved_amount:
                application.approved_amount = approved_amount
            if interest_rate:
                application.interest_rate = interest_rate
            if tenure_months:
                application.tenure_months = tenure_months
            
            # Create audit log
            audit_log = ApplicationAuditLog(
                application_id=application_id,
                action='approval',
                field_name='status',
                old_value=application.status.value,
                new_value=ApplicationStatus.APPROVED.value,
                changed_by=approved_by,
                remarks=remarks
            )
            self.session.add(audit_log)
            self.session.flush()
            
            logger.info(f"Application {application_id} approved by {approved_by}")
            return application
        return None
    
    def reject_application(
        self,
        application_id: UUID,
        rejected_by: str,
        rejection_reason: str,
        rejection_category: Optional[str] = None
    ) -> Optional[LoanApplication]:
        """Reject a loan application."""
        application = self.get_by_id(application_id)
        if application:
            old_status = application.status
            application.status = ApplicationStatus.REJECTED
            application.status_updated_at = datetime.utcnow()
            application.status_updated_by = rejected_by
            application.rejection_reason = rejection_reason
            application.rejection_category = rejection_category
            application.rejected_at = datetime.utcnow()
            
            # Create audit log
            audit_log = ApplicationAuditLog(
                application_id=application_id,
                action='rejection',
                field_name='status',
                old_value=old_status.value,
                new_value=ApplicationStatus.REJECTED.value,
                changed_by=rejected_by,
                remarks=rejection_reason
            )
            self.session.add(audit_log)
            self.session.flush()
            
            logger.info(f"Application {application_id} rejected by {rejected_by}")
            return application
        return None
    
    def get_risk_analysis(self) -> Dict[str, Any]:
        """Get risk level analysis of applications."""
        results = self.session.query(
            LoanApplication.risk_level,
            func.count(LoanApplication.id),
            func.avg(LoanApplication.loan_amount),
            func.avg(LoanApplication.approval_probability)
        ).filter(
            LoanApplication.risk_level != None
        ).group_by(LoanApplication.risk_level).all()
        
        return {
            risk_level: {
                'count': count,
                'average_amount': round(avg_amount, 2) if avg_amount else 0,
                'average_approval_probability': round(avg_prob * 100, 2) if avg_prob else 0
            }
            for risk_level, count, avg_amount, avg_prob in results
        }


class AuditLogRepository(BaseRepository):
    """Repository for audit log operations."""
    
    def create(self, audit_log: ApplicationAuditLog) -> ApplicationAuditLog:
        """Create a new audit log entry."""
        self.session.add(audit_log)
        self.session.flush()
        return audit_log
    
    def get_by_application(
        self,
        application_id: UUID,
        action: Optional[str] = None
    ) -> List[ApplicationAuditLog]:
        """Get audit logs for an application."""
        query = self.session.query(ApplicationAuditLog).filter(
            ApplicationAuditLog.application_id == application_id
        )
        
        if action:
            query = query.filter(ApplicationAuditLog.action == action)
        
        return query.order_by(desc(ApplicationAuditLog.timestamp)).all()
    
    def get_recent_activity(self, limit: int = 50) -> List[ApplicationAuditLog]:
        """Get recent audit activity across all applications."""
        return self.session.query(ApplicationAuditLog).order_by(
            desc(ApplicationAuditLog.timestamp)
        ).limit(limit).all()
    
    def get_activity_by_user(self, user_id: str, limit: int = 50) -> List[ApplicationAuditLog]:
        """Get audit activity for a specific user."""
        return self.session.query(ApplicationAuditLog).filter(
            ApplicationAuditLog.changed_by == user_id
        ).order_by(desc(ApplicationAuditLog.timestamp)).limit(limit).all()
