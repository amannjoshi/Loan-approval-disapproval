"""
ML Prediction Service
=====================
Handles all ML-related business logic, separate from controllers.

This service is responsible for:
- Running ML predictions
- Generating explanations (XAI)
- Computing risk scores
- Generating eligibility tips

Author: Loan Analytics Team
Version: 1.0.0
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ApplicantData:
    """Applicant data for ML prediction - immutable input."""
    cibil_score: Optional[int]
    debt_to_income_ratio: Optional[float]
    employment_years: int
    employment_months: int
    owns_home: bool
    owns_car: bool
    income: Decimal
    additional_income: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    existing_loans_count: int
    existing_emi: Decimal
    credit_history_years: int


@dataclass
class LoanData:
    """Loan application data for ML prediction - immutable input."""
    loan_amount: Decimal
    loan_term_months: int
    loan_type: str
    collateral_value: Decimal
    co_applicant_income: Decimal


@dataclass
class PredictionResult:
    """ML prediction result - immutable output."""
    approval_probability: float
    risk_score: float
    recommendation: str  # 'approve', 'review', 'reject'
    confidence: float
    factors: List[str]
    explanation: Dict[str, Any]
    eligibility_tips: List[str]
    requires_manual_review: bool
    model_version: str
    predicted_at: datetime


class MLPredictionService:
    """
    Service for ML predictions.
    
    This service is stateless - all state is passed in via parameters
    and returned via result objects.
    """
    
    MODEL_VERSION = "1.0.0"
    
    # Thresholds (could be loaded from config)
    APPROVAL_THRESHOLD = 0.7
    REVIEW_THRESHOLD = 0.4
    EXCELLENT_CIBIL = 750
    GOOD_CIBIL = 700
    POOR_CIBIL = 600
    LOW_DTI = 30
    HIGH_DTI = 50
    STABLE_EMPLOYMENT_YEARS = 5
    MIN_EMPLOYMENT_YEARS = 2
    
    def predict(
        self,
        applicant: ApplicantData,
        loan: LoanData
    ) -> PredictionResult:
        """
        Run ML prediction for a loan application.
        
        This is a pure function - given the same inputs, it will
        always produce the same outputs.
        
        Args:
            applicant: Applicant data
            loan: Loan application data
            
        Returns:
            PredictionResult with all prediction details
        """
        # Compute risk score and factors
        risk_score, factors = self._compute_risk_score(applicant, loan)
        
        # Normalize risk score
        risk_score = max(0.0, min(100.0, risk_score))
        
        # Compute approval probability
        approval_probability = (100.0 - risk_score) / 100.0
        
        # Determine recommendation
        recommendation = self._get_recommendation(approval_probability)
        
        # Generate explanation
        explanation = self._generate_explanation(applicant, loan, factors)
        
        # Generate tips
        tips = self._generate_eligibility_tips(applicant, loan)
        
        # Compute confidence (based on data completeness)
        confidence = self._compute_confidence(applicant)
        
        return PredictionResult(
            approval_probability=round(approval_probability, 4),
            risk_score=round(risk_score, 2),
            recommendation=recommendation,
            confidence=confidence,
            factors=factors,
            explanation=explanation,
            eligibility_tips=tips,
            requires_manual_review=(recommendation == "review"),
            model_version=self.MODEL_VERSION,
            predicted_at=datetime.utcnow()
        )
    
    def _compute_risk_score(
        self,
        applicant: ApplicantData,
        loan: LoanData
    ) -> Tuple[float, List[str]]:
        """
        Compute risk score based on applicant and loan data.
        
        Returns:
            Tuple of (risk_score, list_of_factors)
        """
        risk_score = 50.0  # Base score
        factors = []
        
        # Credit score impact
        if applicant.cibil_score:
            if applicant.cibil_score >= self.EXCELLENT_CIBIL:
                risk_score -= 20
                factors.append("Excellent credit score")
            elif applicant.cibil_score >= self.GOOD_CIBIL:
                risk_score -= 10
                factors.append("Good credit score")
            elif applicant.cibil_score < self.POOR_CIBIL:
                risk_score += 20
                factors.append("Low credit score")
        else:
            risk_score += 10
            factors.append("No credit score available")
        
        # Debt-to-income ratio impact
        dti = applicant.debt_to_income_ratio
        if dti is not None:
            if dti < self.LOW_DTI:
                risk_score -= 15
                factors.append("Low debt-to-income ratio")
            elif dti > self.HIGH_DTI:
                risk_score += 15
                factors.append("High debt-to-income ratio")
        
        # Employment stability
        total_employment = applicant.employment_years + (applicant.employment_months / 12)
        if total_employment >= self.STABLE_EMPLOYMENT_YEARS:
            risk_score -= 10
            factors.append("Stable employment history")
        elif total_employment < 1:
            risk_score += 10
            factors.append("Short employment history")
        
        # Asset ownership
        if applicant.owns_home:
            risk_score -= 10
            factors.append("Home owner")
        
        if applicant.owns_car:
            risk_score -= 5
            factors.append("Vehicle owner")
        
        # Loan-to-income ratio
        monthly_income = float(applicant.income + applicant.additional_income)
        if monthly_income > 0:
            loan_to_income = float(loan.loan_amount) / (monthly_income * 12)
            if loan_to_income > 5:
                risk_score += 15
                factors.append("High loan-to-income ratio")
            elif loan_to_income < 2:
                risk_score -= 5
                factors.append("Conservative loan amount")
        
        # Collateral impact
        if float(loan.collateral_value) > 0:
            collateral_coverage = float(loan.collateral_value) / float(loan.loan_amount)
            if collateral_coverage >= 1.0:
                risk_score -= 10
                factors.append("Fully collateralized")
            elif collateral_coverage >= 0.5:
                risk_score -= 5
                factors.append("Partially collateralized")
        
        # Existing debt burden
        if applicant.existing_loans_count > 3:
            risk_score += 10
            factors.append("Multiple existing loans")
        
        # Credit history length
        if applicant.credit_history_years >= 5:
            risk_score -= 5
            factors.append("Long credit history")
        elif applicant.credit_history_years < 1:
            risk_score += 5
            factors.append("Short credit history")
        
        # Co-applicant income boost
        if float(loan.co_applicant_income) > 0:
            risk_score -= 5
            factors.append("Co-applicant income")
        
        return risk_score, factors
    
    def _get_recommendation(self, approval_probability: float) -> str:
        """Get recommendation based on approval probability."""
        if approval_probability >= self.APPROVAL_THRESHOLD:
            return "approve"
        elif approval_probability >= self.REVIEW_THRESHOLD:
            return "review"
        else:
            return "reject"
    
    def _generate_explanation(
        self,
        applicant: ApplicantData,
        loan: LoanData,
        factors: List[str]
    ) -> Dict[str, Any]:
        """Generate XAI explanation."""
        dti = applicant.debt_to_income_ratio
        
        return {
            "factors": factors,
            "cibil_impact": self._get_cibil_impact(applicant.cibil_score),
            "dti_impact": self._get_dti_impact(dti),
            "employment_impact": self._get_employment_impact(
                applicant.employment_years,
                applicant.employment_months
            ),
            "loan_type": loan.loan_type,
            "summary": self._generate_summary(factors)
        }
    
    def _get_cibil_impact(self, cibil_score: Optional[int]) -> str:
        """Determine CIBIL score impact."""
        if cibil_score is None:
            return "unknown"
        if cibil_score >= self.GOOD_CIBIL:
            return "positive"
        elif cibil_score < self.POOR_CIBIL:
            return "negative"
        return "neutral"
    
    def _get_dti_impact(self, dti: Optional[float]) -> str:
        """Determine DTI impact."""
        if dti is None:
            return "unknown"
        if dti < 40:
            return "positive"
        return "negative"
    
    def _get_employment_impact(self, years: int, months: int) -> str:
        """Determine employment impact."""
        total = years + (months / 12)
        if total >= 3:
            return "positive"
        elif total < 1:
            return "negative"
        return "neutral"
    
    def _generate_summary(self, factors: List[str]) -> str:
        """Generate a human-readable summary."""
        positive = [f for f in factors if any(
            word in f.lower() for word in 
            ['excellent', 'good', 'stable', 'low debt', 'owner', 'collateral', 'long', 'conservative', 'co-applicant']
        )]
        negative = [f for f in factors if any(
            word in f.lower() for word in 
            ['low credit', 'high', 'short', 'multiple', 'no credit']
        )]
        
        if len(positive) > len(negative):
            return "Overall positive profile with strong financial indicators"
        elif len(negative) > len(positive):
            return "Profile shows some risk factors that need attention"
        return "Mixed profile - manual review recommended"
    
    def _generate_eligibility_tips(
        self,
        applicant: ApplicantData,
        loan: LoanData
    ) -> List[str]:
        """Generate actionable tips for improving eligibility."""
        tips = []
        
        # Credit score tips
        if applicant.cibil_score and applicant.cibil_score < self.GOOD_CIBIL:
            tips.append("Improve credit score by paying bills on time and reducing credit utilization")
        
        # DTI tips
        if applicant.debt_to_income_ratio and applicant.debt_to_income_ratio > 40:
            tips.append("Reduce existing debt to improve debt-to-income ratio")
        
        # Employment tips
        total_employment = applicant.employment_years + (applicant.employment_months / 12)
        if total_employment < self.MIN_EMPLOYMENT_YEARS:
            tips.append("Longer employment history improves approval chances")
        
        # Loan amount tips
        monthly_income = float(applicant.income + applicant.additional_income)
        if monthly_income > 0:
            loan_to_income = float(loan.loan_amount) / (monthly_income * 12)
            if loan_to_income > 4:
                tips.append("Consider a smaller loan amount relative to your income")
        
        # Collateral tips
        if float(loan.collateral_value) == 0 and float(loan.loan_amount) > 500000:
            tips.append("Adding collateral can improve approval chances for large loans")
        
        # Co-applicant tips
        if float(loan.co_applicant_income) == 0:
            tips.append("Adding a co-applicant with stable income can strengthen the application")
        
        # Savings tips
        if float(applicant.total_assets) < float(loan.loan_amount) * 0.1:
            tips.append("Building savings/assets can demonstrate financial stability")
        
        return tips
    
    def _compute_confidence(self, applicant: ApplicantData) -> float:
        """
        Compute prediction confidence based on data completeness.
        
        Returns a value between 0.5 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Add confidence for each available data point
        if applicant.cibil_score is not None:
            confidence += 0.15
        
        if applicant.debt_to_income_ratio is not None:
            confidence += 0.1
        
        if applicant.employment_years > 0:
            confidence += 0.1
        
        if float(applicant.income) > 0:
            confidence += 0.1
        
        if applicant.credit_history_years > 0:
            confidence += 0.05
        
        return min(1.0, round(confidence, 2))


# Singleton instance for dependency injection
_ml_service: Optional[MLPredictionService] = None


def get_ml_service() -> MLPredictionService:
    """Get ML prediction service instance."""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLPredictionService()
    return _ml_service
