"""
Database Service Layer
======================
Service layer integrating ML predictions with database persistence.

This module bridges the gap between ML model predictions and database storage,
providing a complete workflow for loan application processing.

Author: Loan Analytics Team
Version: 1.0.0
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from uuid import UUID
from dataclasses import dataclass, field

from database import (
    get_db, get_session_context,
    Applicant, LoanApplication, ApplicationAuditLog,
    ApplicantRepository, LoanApplicationRepository, AuditLogRepository,
    ApplicationStatus, KYCStatus, EmploymentType, Gender, MaritalStatus, Education
)

logger = logging.getLogger(__name__)


@dataclass
class ApplicantInput:
    """Input data for creating/updating an applicant."""
    # Personal Info
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    dependents: int = 0
    education: Optional[str] = None
    
    # Contact Info
    email: str = ""
    phone: str = ""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    # Income Details
    monthly_income: float = 0
    other_income: float = 0
    income_proof_type: Optional[str] = None
    
    # Employment
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    industry: Optional[str] = None
    designation: Optional[str] = None
    years_at_current_job: float = 0
    total_experience: float = 0
    
    # Financial
    existing_emi: float = 0
    number_of_existing_loans: int = 0
    savings_amount: float = 0
    cibil_score: Optional[int] = None
    credit_history_years: float = 0
    late_payments_last_year: int = 0
    has_defaults: bool = False
    
    # Assets
    owns_property: bool = False
    property_value: float = 0
    owns_vehicle: bool = False
    
    # KYC
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    
    def to_applicant(self) -> Applicant:
        """Convert input to Applicant entity."""
        applicant = Applicant(
            first_name=self.first_name,
            last_name=self.last_name,
            middle_name=self.middle_name,
            date_of_birth=self.date_of_birth,
            dependents=self.dependents,
            email=self.email.lower() if self.email else None,
            phone=self.phone,
            address=self.address,
            city=self.city,
            state=self.state,
            pincode=self.pincode,
            monthly_income=self.monthly_income,
            other_income=self.other_income,
            income_proof_type=self.income_proof_type,
            employer_name=self.employer_name,
            industry=self.industry,
            designation=self.designation,
            years_at_current_job=self.years_at_current_job,
            total_experience=self.total_experience,
            existing_emi=self.existing_emi,
            number_of_existing_loans=self.number_of_existing_loans,
            savings_amount=self.savings_amount,
            cibil_score=self.cibil_score,
            credit_history_years=self.credit_history_years,
            late_payments_last_year=self.late_payments_last_year,
            has_defaults=self.has_defaults,
            owns_property=self.owns_property,
            property_value=self.property_value,
            owns_vehicle=self.owns_vehicle,
            pan_number=self.pan_number.upper() if self.pan_number else None,
            aadhaar_number=self.aadhaar_number,
            kyc_status=KYCStatus.PENDING
        )
        
        # Set enums
        if self.gender:
            try:
                applicant.gender = Gender(self.gender.lower())
            except ValueError:
                pass
        
        if self.marital_status:
            try:
                applicant.marital_status = MaritalStatus(self.marital_status.lower())
            except ValueError:
                pass
        
        if self.education:
            try:
                applicant.education = Education(self.education.lower())
            except ValueError:
                pass
        
        if self.employment_type:
            try:
                applicant.employment_type = EmploymentType(self.employment_type.lower())
            except ValueError:
                pass
        
        return applicant


@dataclass
class LoanApplicationInput:
    """Input data for creating a loan application."""
    applicant_id: UUID
    loan_amount: float
    tenure_months: int
    loan_purpose: str
    loan_type: Optional[str] = None
    interest_rate: Optional[float] = None
    processing_fee: Optional[float] = None


@dataclass
class ApplicationResult:
    """Result of loan application processing."""
    success: bool
    application_id: Optional[UUID] = None
    application_number: Optional[str] = None
    status: Optional[str] = None
    approval_probability: Optional[float] = None
    risk_level: Optional[str] = None
    explanation: Optional[str] = None
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    eligibility_tips: List[str] = field(default_factory=list)
    error: Optional[str] = None


class LoanDatabaseService:
    """
    Service for loan application processing with database persistence.
    
    Integrates:
    - Applicant management
    - Loan application creation
    - ML prediction integration
    - Status management
    - Audit logging
    """
    
    def __init__(self, ml_service=None):
        """
        Initialize the service.
        
        Args:
            ml_service: Optional ML service for predictions (LoanApplicationService)
        """
        self.db = get_db()
        self.ml_service = ml_service
    
    def create_applicant(self, input_data: ApplicantInput) -> Tuple[bool, Optional[Applicant], Optional[str]]:
        """
        Create a new applicant.
        
        Returns:
            Tuple of (success, applicant, error_message)
        """
        try:
            with get_session_context() as session:
                repo = ApplicantRepository(session)
                
                # Check for existing applicant
                if input_data.email:
                    existing = repo.get_by_email(input_data.email)
                    if existing:
                        return False, None, "Applicant with this email already exists"
                
                if input_data.phone:
                    existing = repo.get_by_phone(input_data.phone)
                    if existing:
                        return False, None, "Applicant with this phone number already exists"
                
                # Create applicant
                applicant = input_data.to_applicant()
                applicant = repo.create(applicant)
                
                logger.info(f"Created applicant: {applicant.id}")
                return True, applicant, None
                
        except Exception as e:
            logger.error(f"Failed to create applicant: {e}")
            return False, None, str(e)
    
    def get_applicant(self, applicant_id: UUID) -> Optional[Applicant]:
        """Get applicant by ID."""
        with get_session_context() as session:
            repo = ApplicantRepository(session)
            return repo.get_by_id(applicant_id)
    
    def update_applicant(
        self, 
        applicant_id: UUID, 
        updates: Dict[str, Any]
    ) -> Tuple[bool, Optional[Applicant], Optional[str]]:
        """Update applicant details."""
        try:
            with get_session_context() as session:
                repo = ApplicantRepository(session)
                applicant = repo.get_by_id(applicant_id)
                
                if not applicant:
                    return False, None, "Applicant not found"
                
                applicant = repo.update(applicant, updates)
                logger.info(f"Updated applicant: {applicant_id}")
                return True, applicant, None
                
        except Exception as e:
            logger.error(f"Failed to update applicant: {e}")
            return False, None, str(e)
    
    def create_loan_application(
        self,
        input_data: LoanApplicationInput,
        process_immediately: bool = True
    ) -> ApplicationResult:
        """
        Create a loan application and optionally process it.
        
        Args:
            input_data: Loan application input data
            process_immediately: If True, run ML prediction immediately
        
        Returns:
            ApplicationResult with processing details
        """
        try:
            with get_session_context() as session:
                applicant_repo = ApplicantRepository(session)
                loan_repo = LoanApplicationRepository(session)
                
                # Verify applicant exists
                applicant = applicant_repo.get_by_id(input_data.applicant_id)
                if not applicant:
                    return ApplicationResult(
                        success=False,
                        error="Applicant not found"
                    )
                
                # Create loan application
                application = LoanApplication(
                    applicant_id=input_data.applicant_id,
                    loan_amount=input_data.loan_amount,
                    tenure_months=input_data.tenure_months,
                    loan_purpose=input_data.loan_purpose,
                    loan_type=input_data.loan_type,
                    interest_rate=input_data.interest_rate,
                    processing_fee=input_data.processing_fee,
                    status=ApplicationStatus.PENDING
                )
                
                # Calculate EMI if interest rate provided
                if input_data.interest_rate:
                    monthly_rate = input_data.interest_rate / 12 / 100
                    if monthly_rate > 0:
                        emi = input_data.loan_amount * monthly_rate * (1 + monthly_rate) ** input_data.tenure_months
                        emi /= ((1 + monthly_rate) ** input_data.tenure_months - 1)
                        application.calculated_emi = round(emi, 2)
                        application.total_payable = round(emi * input_data.tenure_months, 2)
                
                application = loan_repo.create(application)
                
                result = ApplicationResult(
                    success=True,
                    application_id=application.id,
                    application_number=application.application_number,
                    status=application.status.value
                )
                
                # Process with ML if requested and service available
                if process_immediately and self.ml_service:
                    prediction_result = self._process_with_ml(applicant, application, session)
                    result.approval_probability = prediction_result.get('approval_probability')
                    result.risk_level = prediction_result.get('risk_level')
                    result.explanation = prediction_result.get('explanation')
                    result.positive_factors = prediction_result.get('positive_factors', [])
                    result.negative_factors = prediction_result.get('negative_factors', [])
                    result.eligibility_tips = prediction_result.get('eligibility_tips', [])
                    result.status = application.status.value
                
                logger.info(f"Created loan application: {application.application_number}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to create loan application: {e}")
            return ApplicationResult(success=False, error=str(e))
    
    def _process_with_ml(
        self,
        applicant: Applicant,
        application: LoanApplication,
        session
    ) -> Dict[str, Any]:
        """
        Process application with ML model.
        
        Converts applicant data to model input format and runs prediction.
        """
        try:
            # Convert to ML input format
            ml_input = applicant.to_model_input()
            ml_input['loan_amount'] = application.loan_amount
            ml_input['tenure_months'] = application.tenure_months
            ml_input['loan_purpose'] = application.loan_purpose
            
            # Run ML prediction
            prediction = self.ml_service.process_application(ml_input)
            
            # Update application with prediction
            loan_repo = LoanApplicationRepository(session)
            prediction_data = {
                'approval_probability': prediction.probability,
                'confidence_score': getattr(prediction, 'confidence', None),
                'risk_level': prediction.risk_level,
                'model_version': getattr(prediction, 'model_version', None),
                'explanation': prediction.explanation,
                'positive_factors': prediction.positive_factors,
                'negative_factors': prediction.negative_factors,
                'feature_contributions': getattr(prediction, 'feature_contributions', {}),
                'eligibility_tips': self._generate_eligibility_tips(prediction),
                'action_items': self._generate_action_items(prediction, applicant),
                'approved': prediction.approved,
                'requires_manual_review': getattr(prediction, 'requires_manual_review', False),
                'review_reason': getattr(prediction, 'manual_review_reason', None),
                'rejection_reason': None if prediction.approved else self._generate_rejection_reason(prediction)
            }
            
            loan_repo.update_ml_prediction(application.id, prediction_data)
            
            return prediction_data
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return {
                'error': str(e),
                'approval_probability': None,
                'risk_level': 'unknown'
            }
    
    def _generate_eligibility_tips(self, prediction) -> List[str]:
        """Generate eligibility improvement tips based on prediction."""
        tips = []
        
        for factor in prediction.negative_factors:
            factor_lower = factor.lower()
            
            if 'income' in factor_lower:
                tips.append("Consider increasing your income or reducing existing EMIs to improve debt-to-income ratio")
            elif 'credit' in factor_lower or 'cibil' in factor_lower:
                tips.append("Work on improving your credit score by paying bills on time and reducing credit utilization")
            elif 'employment' in factor_lower or 'job' in factor_lower:
                tips.append("Longer tenure with current employer increases approval chances")
            elif 'debt' in factor_lower or 'emi' in factor_lower:
                tips.append("Consider paying off existing loans to reduce your debt burden")
            elif 'loan amount' in factor_lower:
                tips.append("Consider applying for a lower loan amount based on your income")
            elif 'history' in factor_lower:
                tips.append("Build a longer credit history with responsible credit usage")
        
        # Add general tips if needed
        if len(tips) < 2:
            tips.extend([
                "Maintain a credit score above 750 for better approval chances",
                "Keep your debt-to-income ratio below 40%",
                "Ensure all documents are complete and verified"
            ])
        
        return tips[:5]  # Limit to 5 tips
    
    def _generate_action_items(self, prediction, applicant: Applicant) -> List[str]:
        """Generate specific action items for the applicant."""
        actions = []
        
        # Check KYC status
        if applicant.kyc_status != KYCStatus.VERIFIED:
            actions.append("Complete KYC verification to proceed with application")
        
        # Check CIBIL score
        if applicant.cibil_score and applicant.cibil_score < 700:
            actions.append(f"Improve credit score from {applicant.cibil_score} to above 700")
        
        # Check debt ratio
        if applicant.monthly_income > 0:
            debt_ratio = applicant.existing_emi / applicant.monthly_income
            if debt_ratio > 0.4:
                actions.append(f"Reduce debt-to-income ratio from {debt_ratio*100:.0f}% to below 40%")
        
        # Check employment
        if applicant.years_at_current_job < 1:
            actions.append("Consider applying after completing 1 year with current employer")
        
        return actions
    
    def _generate_rejection_reason(self, prediction) -> str:
        """Generate a comprehensive rejection reason."""
        reasons = prediction.negative_factors[:3]
        if reasons:
            return f"Application did not meet eligibility criteria: {'; '.join(reasons)}"
        return "Application did not meet the minimum eligibility requirements"
    
    def get_application(self, application_id: UUID) -> Optional[LoanApplication]:
        """Get loan application by ID."""
        with get_session_context() as session:
            repo = LoanApplicationRepository(session)
            return repo.get_by_id(application_id)
    
    def get_application_by_number(self, app_number: str) -> Optional[LoanApplication]:
        """Get loan application by application number."""
        with get_session_context() as session:
            repo = LoanApplicationRepository(session)
            return repo.get_by_application_number(app_number)
    
    def get_applicant_applications(self, applicant_id: UUID) -> List[LoanApplication]:
        """Get all applications for an applicant."""
        with get_session_context() as session:
            repo = LoanApplicationRepository(session)
            return repo.get_by_applicant_id(applicant_id)
    
    def update_application_status(
        self,
        application_id: UUID,
        status: ApplicationStatus,
        updated_by: str,
        remarks: Optional[str] = None
    ) -> Tuple[bool, Optional[LoanApplication], Optional[str]]:
        """Update application status."""
        try:
            with get_session_context() as session:
                repo = LoanApplicationRepository(session)
                application = repo.update_status(
                    application_id, status, updated_by, remarks
                )
                
                if application:
                    return True, application, None
                return False, None, "Application not found"
                
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False, None, str(e)
    
    def approve_application(
        self,
        application_id: UUID,
        approved_by: str,
        approved_amount: Optional[float] = None,
        interest_rate: Optional[float] = None,
        remarks: Optional[str] = None
    ) -> Tuple[bool, Optional[LoanApplication], Optional[str]]:
        """Approve a loan application."""
        try:
            with get_session_context() as session:
                repo = LoanApplicationRepository(session)
                application = repo.approve_application(
                    application_id, approved_by, approved_amount, interest_rate, remarks=remarks
                )
                
                if application:
                    logger.info(f"Application {application_id} approved by {approved_by}")
                    return True, application, None
                return False, None, "Application not found"
                
        except Exception as e:
            logger.error(f"Failed to approve application: {e}")
            return False, None, str(e)
    
    def reject_application(
        self,
        application_id: UUID,
        rejected_by: str,
        rejection_reason: str
    ) -> Tuple[bool, Optional[LoanApplication], Optional[str]]:
        """Reject a loan application."""
        try:
            with get_session_context() as session:
                repo = LoanApplicationRepository(session)
                application = repo.reject_application(
                    application_id, rejected_by, rejection_reason
                )
                
                if application:
                    logger.info(f"Application {application_id} rejected by {rejected_by}")
                    return True, application, None
                return False, None, "Application not found"
                
        except Exception as e:
            logger.error(f"Failed to reject application: {e}")
            return False, None, str(e)
    
    def search_applications(
        self,
        **filters
    ) -> Tuple[List[LoanApplication], int]:
        """Search applications with filters."""
        with get_session_context() as session:
            repo = LoanApplicationRepository(session)
            return repo.search(**filters)
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for dashboard."""
        with get_session_context() as session:
            applicant_repo = ApplicantRepository(session)
            loan_repo = LoanApplicationRepository(session)
            
            return {
                'applicants': applicant_repo.get_statistics(),
                'applications': loan_repo.get_statistics(),
                'risk_analysis': loan_repo.get_risk_analysis(),
                'pending_review': len(loan_repo.get_applications_for_review()),
                'pending_processing': len(loan_repo.get_pending_applications())
            }
    
    def get_application_history(self, application_id: UUID) -> List[Dict[str, Any]]:
        """Get audit history for an application."""
        with get_session_context() as session:
            repo = AuditLogRepository(session)
            logs = repo.get_by_application(application_id)
            
            return [
                {
                    'timestamp': log.timestamp.isoformat(),
                    'action': log.action,
                    'field': log.field_name,
                    'old_value': log.old_value,
                    'new_value': log.new_value,
                    'changed_by': log.changed_by,
                    'remarks': log.remarks
                }
                for log in logs
            ]


# ============================================================================
# Quick Application Processing (for Streamlit integration)
# ============================================================================

def process_quick_application(
    applicant_data: Dict[str, Any],
    loan_data: Dict[str, Any],
    ml_service=None
) -> ApplicationResult:
    """
    Process a quick loan application (creates applicant and application together).
    
    This is a convenience function for the Streamlit frontend.
    
    Args:
        applicant_data: Dictionary with applicant information
        loan_data: Dictionary with loan information
        ml_service: Optional ML service for predictions
    
    Returns:
        ApplicationResult with processing details
    """
    service = LoanDatabaseService(ml_service)
    
    # Create applicant input
    applicant_input = ApplicantInput(
        first_name=applicant_data.get('first_name', 'Unknown'),
        last_name=applicant_data.get('last_name', 'Unknown'),
        email=applicant_data.get('email', ''),
        phone=applicant_data.get('phone', ''),
        monthly_income=applicant_data.get('monthly_income', 0),
        employment_type=applicant_data.get('employment_type'),
        years_at_current_job=applicant_data.get('years_at_current_job', 0),
        total_experience=applicant_data.get('total_experience', 0),
        existing_emi=applicant_data.get('existing_emi', 0),
        cibil_score=applicant_data.get('cibil_score'),
        credit_history_years=applicant_data.get('credit_history_years', 0),
        dependents=applicant_data.get('dependents', 0),
        owns_property=applicant_data.get('owns_property', False),
        education=applicant_data.get('education')
    )
    
    # Create applicant
    success, applicant, error = service.create_applicant(applicant_input)
    
    if not success:
        return ApplicationResult(success=False, error=error)
    
    # Create loan application input
    loan_input = LoanApplicationInput(
        applicant_id=applicant.id,
        loan_amount=loan_data.get('loan_amount', 0),
        tenure_months=loan_data.get('tenure_months', 12),
        loan_purpose=loan_data.get('loan_purpose', 'Personal'),
        loan_type=loan_data.get('loan_type'),
        interest_rate=loan_data.get('interest_rate')
    )
    
    # Create and process application
    return service.create_loan_application(loan_input, process_immediately=True)
