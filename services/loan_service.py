"""
Loan Application Service Layer
==============================
Business logic layer that orchestrates all components:
- Input validation
- Model prediction
- Explanation generation
- Fairness checking
- Audit logging

This service acts as the central coordinator for the entire
loan approval workflow.

Author: Loan Analytics Team
Version: 2.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApplicationStatus(Enum):
    """Loan application status codes."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    MANUAL_REVIEW = "manual_review"
    ERROR = "error"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class ApplicationInput:
    """
    Structured input for loan application.
    
    Validates and normalizes all input fields.
    """
    # Personal Information
    age: int
    gender: str
    education: str
    marital_status: str
    num_dependents: int
    
    # Employment Information
    employment_type: str
    industry: str
    years_at_current_job: float
    monthly_income: float
    
    # Financial Information
    existing_emi: float
    num_existing_loans: int
    savings_balance: float
    
    # Credit Information
    cibil_score: int
    credit_history_years: int
    late_payments_last_2_years: int
    has_defaults: bool
    
    # Property
    owns_property: bool
    
    # Banking Relationship
    years_with_bank: int
    
    # Loan Details
    loan_amount: float
    loan_tenure_months: int
    loan_purpose: str = "Personal"
    
    # Metadata
    application_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for model input."""
        data = {
            'age': [self.age],
            'gender': [self.gender],
            'education': [self.education],
            'marital_status': [self.marital_status],
            'num_dependents': [self.num_dependents],
            'employment_type': [self.employment_type],
            'industry': [self.industry],
            'years_at_current_job': [self.years_at_current_job],
            'monthly_income': [self.monthly_income],
            'existing_emi': [self.existing_emi],
            'num_existing_loans': [self.num_existing_loans],
            'savings_balance': [self.savings_balance],
            'cibil_score': [self.cibil_score],
            'credit_history_years': [self.credit_history_years],
            'late_payments_last_2_years': [self.late_payments_last_2_years],
            'has_defaults': [self.has_defaults],
            'owns_property': [self.owns_property],
            'years_with_bank': [self.years_with_bank],
            'loan_amount': [self.loan_amount],
            'loan_tenure_months': [self.loan_tenure_months]
        }
        return pd.DataFrame(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'age': self.age,
            'gender': self.gender,
            'education': self.education,
            'marital_status': self.marital_status,
            'num_dependents': self.num_dependents,
            'employment_type': self.employment_type,
            'industry': self.industry,
            'years_at_current_job': self.years_at_current_job,
            'monthly_income': self.monthly_income,
            'existing_emi': self.existing_emi,
            'num_existing_loans': self.num_existing_loans,
            'savings_balance': self.savings_balance,
            'cibil_score': self.cibil_score,
            'credit_history_years': self.credit_history_years,
            'late_payments_last_2_years': self.late_payments_last_2_years,
            'has_defaults': self.has_defaults,
            'owns_property': self.owns_property,
            'years_with_bank': self.years_with_bank,
            'loan_amount': self.loan_amount,
            'loan_tenure_months': self.loan_tenure_months,
            'loan_purpose': self.loan_purpose,
            'application_id': self.application_id,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class DecisionResult:
    """
    Comprehensive loan decision result.
    
    Contains all information about the decision including
    explanations and recommendations.
    """
    # Decision
    application_id: str
    status: ApplicationStatus
    approved: bool
    approval_probability: float
    confidence: float
    
    # Risk Assessment
    risk_level: str
    risk_description: str
    requires_manual_review: bool
    
    # Explanations
    positive_factors: List[Dict]
    negative_factors: List[Dict]
    all_contributions: List[Dict]
    
    # Recommendations
    recommendations: List[str]
    improvement_tips: List[str]
    
    # Interest Rate (if approved)
    suggested_interest_rate: Optional[float]
    suggested_emi: Optional[float]
    
    # Metadata
    model_id: str
    processing_time_ms: float
    timestamp: datetime
    validation_passed: bool
    validation_warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'application_id': self.application_id,
            'status': self.status.value,
            'approved': self.approved,
            'approval_probability': self.approval_probability,
            'confidence': self.confidence,
            'risk_level': self.risk_level,
            'risk_description': self.risk_description,
            'requires_manual_review': self.requires_manual_review,
            'positive_factors': self.positive_factors,
            'negative_factors': self.negative_factors,
            'all_contributions': self.all_contributions,
            'recommendations': self.recommendations,
            'improvement_tips': self.improvement_tips,
            'suggested_interest_rate': self.suggested_interest_rate,
            'suggested_emi': self.suggested_emi,
            'model_id': self.model_id,
            'processing_time_ms': self.processing_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'validation_passed': self.validation_passed,
            'validation_warnings': self.validation_warnings
        }


class LoanApplicationService:
    """
    Main service class for loan application processing.
    
    Coordinates all components:
    - Validation
    - Prediction
    - Explanation
    - Recommendations
    - Audit logging
    """
    
    def __init__(self, model=None, validator=None, audit_logger=None, config=None):
        """
        Initialize the service.
        
        Parameters:
        -----------
        model : LoanApprovalModel, optional
            Pre-trained loan approval model
        validator : InputValidator, optional
            Input validation service
        audit_logger : AuditLogger, optional
            Audit logging service
        config : SystemConfig, optional
            System configuration
        """
        self.model = model
        self.validator = validator
        self.audit_logger = audit_logger
        self.config = config
        
        # Interest rate calculation parameters
        self.base_interest_rate = 10.0  # Base rate 10%
        self.risk_premium = {
            'low': 0.0,
            'medium': 2.0,
            'high': 4.0,
            'very_high': 6.0
        }
    
    def set_model(self, model):
        """Set the prediction model."""
        self.model = model
    
    def set_validator(self, validator):
        """Set the input validator."""
        self.validator = validator
    
    def set_audit_logger(self, audit_logger):
        """Set the audit logger."""
        self.audit_logger = audit_logger
    
    def process_application(self, application: ApplicationInput) -> DecisionResult:
        """
        Process a loan application end-to-end.
        
        Steps:
        1. Validate input
        2. Make prediction
        3. Generate explanation
        4. Calculate recommendations
        5. Log the decision
        
        Parameters:
        -----------
        application : ApplicationInput
            The loan application to process
            
        Returns:
        --------
        DecisionResult
            Complete decision with explanations
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Validate Input
            validation_passed = True
            validation_warnings = []
            
            if self.validator:
                df = application.to_dataframe()
                validation_report = self.validator.validate_application(df.iloc[0].to_dict())
                validation_passed = validation_report.is_valid
                validation_warnings = [r.message for r in validation_report.warnings]
                
                if not validation_passed:
                    # Return validation failed result
                    errors = [r.message for r in validation_report.errors]
                    return DecisionResult(
                        application_id=application.application_id,
                        status=ApplicationStatus.VALIDATION_FAILED,
                        approved=False,
                        approval_probability=0.0,
                        confidence=0.0,
                        risk_level='unknown',
                        risk_description='Validation failed',
                        requires_manual_review=True,
                        positive_factors=[],
                        negative_factors=[],
                        all_contributions=[],
                        recommendations=['Please correct the validation errors and resubmit'],
                        improvement_tips=errors,
                        suggested_interest_rate=None,
                        suggested_emi=None,
                        model_id='N/A',
                        processing_time_ms=(time.time() - start_time) * 1000,
                        timestamp=datetime.now(),
                        validation_passed=False,
                        validation_warnings=errors
                    )
            
            # Step 2: Make Prediction
            if self.model is None or not self.model.is_trained:
                raise ValueError("Model not available or not trained")
            
            df = application.to_dataframe()
            prediction = self.model.predict(df)
            explanation = self.model.explain_prediction(df)
            
            # Handle backward compatibility with older model outputs
            probability = prediction.get('approval_probability', prediction.get('probability', 0.5))
            risk_level = prediction.get('risk_level', 'medium')
            risk_description = prediction.get('risk_description', 'Standard risk assessment')
            requires_manual = prediction.get('requires_manual_review', 0.35 <= probability <= 0.65)
            model_id = prediction.get('model_id', 'legacy_model')
            confidence = prediction.get('confidence', max(probability, 1 - probability))
            
            # Step 3: Generate Recommendations
            recommendations, improvement_tips = self._generate_recommendations(
                application, prediction, explanation
            )
            
            # Step 4: Calculate Interest Rate
            suggested_rate = None
            suggested_emi = None
            
            if prediction['approved']:
                suggested_rate = self._calculate_interest_rate(risk_level)
                suggested_emi = self._calculate_emi(
                    application.loan_amount,
                    suggested_rate,
                    application.loan_tenure_months
                )
            
            # Step 5: Determine Status
            if requires_manual:
                status = ApplicationStatus.MANUAL_REVIEW
            elif prediction['approved']:
                status = ApplicationStatus.APPROVED
            else:
                status = ApplicationStatus.DENIED
            
            # Create result
            result = DecisionResult(
                application_id=application.application_id,
                status=status,
                approved=prediction['approved'],
                approval_probability=probability,
                confidence=confidence,
                risk_level=risk_level,
                risk_description=risk_description,
                requires_manual_review=requires_manual,
                positive_factors=explanation.get('positive_factors', []),
                negative_factors=explanation.get('negative_factors', []),
                all_contributions=explanation.get('all_contributions', []),
                recommendations=recommendations,
                improvement_tips=improvement_tips,
                suggested_interest_rate=suggested_rate,
                suggested_emi=suggested_emi,
                model_id=model_id,
                processing_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                validation_passed=validation_passed,
                validation_warnings=validation_warnings
            )
            
            # Step 6: Log Decision
            if self.audit_logger:
                self.audit_logger.log_decision(
                    application_id=application.application_id,
                    approved=prediction['approved'],
                    probability=prediction['approval_probability'],
                    risk_level=prediction['risk_level'],
                    model_id=prediction['model_id'],
                    features=application.to_dict(),
                    explanation=explanation
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing application: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Log error
            if self.audit_logger:
                self.audit_logger.log_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={'application_id': application.application_id}
                )
            
            return DecisionResult(
                application_id=application.application_id,
                status=ApplicationStatus.ERROR,
                approved=False,
                approval_probability=0.0,
                confidence=0.0,
                risk_level='unknown',
                risk_description='Error processing application',
                requires_manual_review=True,
                positive_factors=[],
                negative_factors=[],
                all_contributions=[],
                recommendations=['An error occurred. Please contact support.'],
                improvement_tips=[],
                suggested_interest_rate=None,
                suggested_emi=None,
                model_id='N/A',
                processing_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                validation_passed=False,
                validation_warnings=[str(e)]
            )
    
    def _generate_recommendations(
        self, 
        application: ApplicationInput, 
        prediction: Dict, 
        explanation: Dict
    ) -> Tuple[List[str], List[str]]:
        """Generate actionable recommendations based on the decision."""
        recommendations = []
        improvement_tips = []
        
        # Get risk level with backward compatibility
        risk_level = prediction.get('risk_level', 'medium')
        requires_manual = prediction.get('requires_manual_review', False)
        
        if prediction['approved']:
            recommendations.append("✅ Congratulations! Your loan application has been approved!")
            recommendations.append(f"📊 Risk assessment: {risk_level.title() if risk_level else 'Standard'}")
            
            if requires_manual:
                recommendations.append("⏳ Final approval pending manual review")
                recommendations.append("📞 A loan officer will contact you within 2-3 business days")
        else:
            # SOFT REJECTION - Friendly, specific messaging
            primary_issue = self._identify_primary_issue(explanation)
            recommendations.append(f"❌ Loan not approved: {primary_issue['reason']}")
            recommendations.append(f"💡 {primary_issue['suggestion']}")
            recommendations.append("🔄 You can reapply after making the suggested improvements")
        
        # Generate improvement tips based on negative factors
        for factor in explanation.get('negative_factors', [])[:5]:
            feature = factor.get('feature', '')
            display_name = factor.get('display_name', feature)
            value = factor.get('display_value', factor.get('value', ''))
            
            if 'cibil' in feature.lower():
                improvement_tips.append(
                    f"📈 Credit score ({value}) needs improvement → "
                    "Pay all EMIs on time for 6 months to boost your score by 50-80 points"
                )
            elif 'debt_to_income' in feature.lower() or 'emi_to_income' in feature.lower():
                improvement_tips.append(
                    f"💳 High debt-to-income ratio ({value}) → "
                    "Pay off ₹20,000-30,000 of existing debt to improve eligibility"
                )
            elif 'late_payments' in feature.lower():
                improvement_tips.append(
                    f"⏰ Late payments ({value}) affecting score → "
                    "Set up auto-pay and maintain 6 months of timely payments"
                )
            elif 'loan_amount' in feature.lower() or 'loan_to_income' in feature.lower():
                improvement_tips.append(
                    f"📉 Loan amount too high for income → "
                    "Try applying for 20-30% lower amount or add a co-applicant"
                )
            elif 'savings' in feature.lower():
                improvement_tips.append(
                    f"🏦 Low savings ({value}) → "
                    "Build 3 months of EMI amount as savings before reapplying"
                )
            elif 'employment' in feature.lower() or 'years_at' in feature.lower():
                improvement_tips.append(
                    f"💼 Short employment tenure → "
                    "Wait 3-6 more months at current job before reapplying"
                )
            elif 'defaults' in feature.lower():
                improvement_tips.append(
                    "⚠️ Previous defaults on record → "
                    "Clear outstanding dues and wait 12 months for score recovery"
                )
        
        # Remove duplicates while preserving order
        improvement_tips = list(dict.fromkeys(improvement_tips))
        
        return recommendations, improvement_tips[:5]
    
    def _identify_primary_issue(self, explanation: Dict) -> Dict[str, str]:
        """Identify the primary reason for rejection and provide specific suggestion."""
        negative_factors = explanation.get('negative_factors', [])
        
        if not negative_factors:
            return {
                'reason': 'Multiple factors need improvement',
                'suggestion': 'Review all areas and reapply in 3-6 months'
            }
        
        # Get the most impactful negative factor
        top_factor = negative_factors[0]
        feature = top_factor.get('feature', '').lower()
        value = top_factor.get('display_value', top_factor.get('value', ''))
        
        # Map features to friendly reasons and specific suggestions
        issue_mapping = {
            'cibil': {
                'reason': f'Low credit score ({value})',
                'suggestion': 'Pay all EMIs on time for 6 months to improve your score'
            },
            'credit_score': {
                'reason': f'Credit score below threshold ({value})',
                'suggestion': 'Improve score by timely EMI payments for 6 months'
            },
            'debt_to_income': {
                'reason': f'High existing debt ({value})',
                'suggestion': 'Reduce existing EMIs by ₹10,000-15,000/month before reapplying'
            },
            'emi_to_income': {
                'reason': f'EMI burden too high ({value})',
                'suggestion': 'Pay off one existing loan or increase income before reapplying'
            },
            'late_payment': {
                'reason': f'Recent late payments ({value})',
                'suggestion': 'Maintain 6 consecutive months of on-time payments'
            },
            'loan_amount': {
                'reason': 'Loan amount too high for income',
                'suggestion': 'Apply for a smaller amount or add a co-applicant with income'
            },
            'income': {
                'reason': f'Income below requirement ({value})',
                'suggestion': 'Document additional income sources or wait for salary increase'
            },
            'employment': {
                'reason': f'Insufficient employment history ({value})',
                'suggestion': 'Reapply after completing 6+ months at current job'
            },
            'savings': {
                'reason': f'Low savings balance ({value})',
                'suggestion': 'Build savings of at least 3x monthly EMI before reapplying'
            },
            'default': {
                'reason': 'Previous loan default on record',
                'suggestion': 'Clear dues and wait 12 months while maintaining good credit'
            }
        }
        
        # Find matching issue
        for key, issue in issue_mapping.items():
            if key in feature:
                return issue
        
        # Default response
        return {
            'reason': f'{top_factor.get("display_name", "Financial factor")} needs improvement',
            'suggestion': 'Address the highlighted concern and reapply in 3 months'
        }
    
    def _calculate_interest_rate(self, risk_level: str) -> float:
        """Calculate suggested interest rate based on risk level."""
        premium = self.risk_premium.get(risk_level, 4.0)
        return round(self.base_interest_rate + premium, 2)
    
    def _calculate_emi(self, principal: float, annual_rate: float, 
                       tenure_months: int) -> float:
        """Calculate EMI using standard formula."""
        if tenure_months == 0:
            return principal
        
        monthly_rate = annual_rate / 100 / 12
        
        if monthly_rate == 0:
            return round(principal / tenure_months, 2)
        
        emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / \
              (((1 + monthly_rate) ** tenure_months) - 1)
        
        return round(emi, 2)
    
    def batch_process(self, applications: List[ApplicationInput]) -> List[DecisionResult]:
        """Process multiple applications in batch."""
        results = []
        for app in applications:
            result = self.process_application(app)
            results.append(result)
        return results
    
    def get_decision_summary(self, result: DecisionResult) -> str:
        """Generate a human-readable summary of the decision."""
        lines = []
        
        if result.approved:
            # APPROVED - Celebrate!
            lines = [
                "╔" + "═" * 68 + "╗",
                "║" + " " * 20 + "🎉 LOAN APPROVED! 🎉" + " " * 20 + "║",
                "╚" + "═" * 68 + "╝",
                "",
                f"  📋 Application ID: {result.application_id[:8]}...",
                f"  ✅ Status: APPROVED",
                f"  📊 Approval Confidence: {result.approval_probability:.0%}",
                ""
            ]
            
            if result.suggested_interest_rate:
                lines.extend([
                    "  💰 YOUR LOAN TERMS:",
                    f"     • Interest Rate: {result.suggested_interest_rate}% p.a.",
                    f"     • Monthly EMI: ₹{result.suggested_emi:,.0f}",
                    ""
                ])
            
            if result.positive_factors:
                lines.append("  🌟 YOUR STRENGTHS:")
                for f in result.positive_factors[:3]:
                    name = f.get('display_name', f.get('feature', 'Factor'))
                    lines.append(f"     ✓ {name}")
                lines.append("")
                
        else:
            # REJECTED - Soft, helpful messaging
            lines = [
                "╔" + "═" * 68 + "╗",
                "║" + " " * 15 + "📋 APPLICATION STATUS UPDATE" + " " * 16 + "║",
                "╚" + "═" * 68 + "╝",
                "",
                f"  📋 Application ID: {result.application_id[:8]}...",
                ""
            ]
            
            # Show the specific rejection reason and improvement
            if result.recommendations:
                for rec in result.recommendations[:3]:
                    lines.append(f"  {rec}")
                lines.append("")
            
            # Show improvement tips with clear actionable steps
            if result.improvement_tips:
                lines.append("  📈 HOW TO IMPROVE YOUR CHANCES:")
                lines.append("  " + "─" * 40)
                for i, tip in enumerate(result.improvement_tips[:3], 1):
                    lines.append(f"  {i}. {tip}")
                lines.append("")
            
            # Estimated timeline
            lines.extend([
                "  ⏱️ RECOMMENDED TIMELINE:",
                "     Reapply after addressing above improvements (typically 3-6 months)",
                ""
            ])
            
            # Encouragement
            lines.extend([
                "  💪 Remember: This is a temporary setback, not a permanent barrier!",
                "     Many applicants succeed on their second attempt.",
                ""
            ])
        
        # Footer
        lines.extend([
            "─" * 70,
            f"  ⚙️ Processed in {result.processing_time_ms:.0f}ms | Model: {result.model_id[:12]}...",
            "─" * 70
        ])
        
        return "\n".join(lines)


def create_application_from_dict(data: Dict[str, Any]) -> ApplicationInput:
    """
    Create ApplicationInput from a dictionary.
    
    Useful for converting form data or API requests.
    """
    return ApplicationInput(
        age=int(data.get('age', 30)),
        gender=str(data.get('gender', 'Male')),
        education=str(data.get('education', 'Graduate')),
        marital_status=str(data.get('marital_status', 'Single')),
        num_dependents=int(data.get('num_dependents', 0)),
        employment_type=str(data.get('employment_type', 'Salaried')),
        industry=str(data.get('industry', 'IT')),
        years_at_current_job=float(data.get('years_at_current_job', 1)),
        monthly_income=float(data.get('monthly_income', 50000)),
        existing_emi=float(data.get('existing_emi', 0)),
        num_existing_loans=int(data.get('num_existing_loans', 0)),
        savings_balance=float(data.get('savings_balance', 100000)),
        cibil_score=int(data.get('cibil_score', 700)),
        credit_history_years=int(data.get('credit_history_years', 3)),
        late_payments_last_2_years=int(data.get('late_payments_last_2_years', 0)),
        has_defaults=bool(data.get('has_defaults', False)),
        owns_property=bool(data.get('owns_property', False)),
        years_with_bank=int(data.get('years_with_bank', 2)),
        loan_amount=float(data.get('loan_amount', 500000)),
        loan_tenure_months=int(data.get('loan_tenure_months', 36)),
        loan_purpose=str(data.get('loan_purpose', 'Personal'))
    )


if __name__ == "__main__":
    # Test the service
    print("Testing Loan Application Service...")
    
    # Create a test application
    test_data = {
        'age': 35,
        'gender': 'Male',
        'education': 'Graduate',
        'marital_status': 'Married',
        'num_dependents': 2,
        'employment_type': 'Salaried',
        'industry': 'IT',
        'years_at_current_job': 5,
        'monthly_income': 75000,
        'existing_emi': 10000,
        'num_existing_loans': 1,
        'savings_balance': 300000,
        'cibil_score': 750,
        'credit_history_years': 8,
        'late_payments_last_2_years': 0,
        'has_defaults': False,
        'owns_property': True,
        'years_with_bank': 5,
        'loan_amount': 1000000,
        'loan_tenure_months': 60,
        'loan_purpose': 'Home Improvement'
    }
    
    application = create_application_from_dict(test_data)
    print(f"Created application: {application.application_id}")
    print(f"DataFrame shape: {application.to_dataframe().shape}")
    
    print("\nService layer ready for integration!")
