"""
Configuration Settings for Loan Approval System
================================================
Centralized configuration management for all system parameters.
Compliant with RBI guidelines and banking industry standards.

Author: Loan Analytics Team
Version: 3.0.0
Last Updated: January 2026
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import os


class RiskCategory(Enum):
    """Risk categorization based on RBI guidelines."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class LoanStatus(Enum):
    """Loan application status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    INCOMPLETE = "incomplete"


@dataclass
class CreditScoreConfig:
    """CIBIL/Credit score configuration."""
    min_score: int = 300
    max_score: int = 900
    excellent_threshold: int = 750
    good_threshold: int = 700
    fair_threshold: int = 650
    poor_threshold: int = 550
    
    # Score-based risk weights
    score_weights: Dict[str, float] = field(default_factory=lambda: {
        'excellent': 0.40,
        'good': 0.30,
        'fair': 0.15,
        'poor': -0.10,
        'very_poor': -0.30
    })


@dataclass
class DebtToIncomeConfig:
    """Debt-to-Income ratio thresholds (RBI guidelines)."""
    excellent_threshold: float = 0.20  # < 20% DTI
    good_threshold: float = 0.35       # < 35% DTI
    acceptable_threshold: float = 0.50  # < 50% DTI
    max_allowed: float = 0.60          # Maximum allowed DTI
    
    # FOIR (Fixed Obligation to Income Ratio) - RBI guideline
    foir_limit: float = 0.50


@dataclass
class LoanAmountConfig:
    """Loan amount limits and configurations."""
    min_amount: int = 50000           # ₹50,000
    max_amount: int = 5000000         # ₹50,00,000 (50 Lakhs)
    max_unsecured: int = 2500000      # ₹25 Lakhs for unsecured
    
    # Loan-to-Income multipliers
    max_loan_to_annual_income: float = 2.5
    salary_multiplier_salaried: float = 20      # Up to 20x monthly salary
    salary_multiplier_self_employed: float = 15 # Up to 15x for self-employed
    
    # Tenure limits (months)
    min_tenure: int = 12
    max_tenure: int = 84  # 7 years
    default_tenure: int = 36


@dataclass
class AgeConfig:
    """Age-related configurations."""
    min_age: int = 21           # Minimum age for loan
    max_age: int = 65           # Maximum age at loan maturity
    ideal_min_age: int = 25     # Ideal minimum
    ideal_max_age: int = 55     # Ideal maximum
    retirement_age: int = 60    # Standard retirement age


@dataclass  
class EmploymentConfig:
    """Employment stability criteria."""
    min_employment_months: int = 6      # Minimum 6 months in current job
    stable_employment_years: int = 2    # 2+ years considered stable
    highly_stable_years: int = 5        # 5+ years highly stable
    
    # Employment type risk weights
    employment_weights: Dict[str, float] = field(default_factory=lambda: {
        'Government': 0.15,
        'Salaried': 0.10,
        'Business Owner': 0.05,
        'Self-Employed': 0.00,
        'Retired': -0.05,
        'Unemployed': -0.30
    })


@dataclass
class FairnessConfig:
    """Fairness and bias detection thresholds."""
    disparate_impact_threshold: float = 0.80    # 80% rule
    demographic_parity_threshold: float = 0.10  # Max 10% difference
    equalized_odds_threshold: float = 0.10      # Max 10% TPR/FPR difference
    
    # Protected attributes to monitor
    protected_attributes: List[str] = field(default_factory=lambda: [
        'gender', 'age_group', 'marital_status', 'religion', 'caste'
    ])
    
    # Attributes that should NOT be used for decisions
    prohibited_features: List[str] = field(default_factory=lambda: [
        'religion', 'caste', 'nationality', 'ethnicity'
    ])


@dataclass
class ModelConfig:
    """Machine learning model configuration."""
    # Model selection
    primary_model: str = 'gradient_boosting'
    ensemble_models: List[str] = field(default_factory=lambda: [
        'gradient_boosting', 'random_forest', 'logistic_regression'
    ])
    
    # Training parameters
    test_size: float = 0.20
    validation_size: float = 0.10
    cv_folds: int = 5
    random_state: int = 42
    
    # Gradient Boosting parameters
    gb_params: Dict = field(default_factory=lambda: {
        'n_estimators': 200,
        'max_depth': 6,
        'learning_rate': 0.1,
        'min_samples_split': 20,
        'min_samples_leaf': 10,
        'subsample': 0.8,
        'validation_fraction': 0.1,
        'n_iter_no_change': 15,
        'random_state': 42
    })
    
    # Random Forest parameters
    rf_params: Dict = field(default_factory=lambda: {
        'n_estimators': 200,
        'max_depth': 10,
        'min_samples_split': 10,
        'min_samples_leaf': 5,
        'random_state': 42,
        'n_jobs': -1
    })
    
    # Logistic Regression parameters
    lr_params: Dict = field(default_factory=lambda: {
        'C': 1.0,
        'max_iter': 1000,
        'random_state': 42
    })
    
    # Decision thresholds
    approval_threshold: float = 0.50       # Default threshold
    high_confidence_threshold: float = 0.80
    manual_review_band: Tuple[float, float] = (0.40, 0.60)
    
    # Performance targets
    min_accuracy: float = 0.85
    min_auc_roc: float = 0.90
    max_false_positive_rate: float = 0.15


@dataclass
class ValidationConfig:
    """Input validation rules."""
    # Income validation (in INR)
    min_income: int = 15000
    max_income: int = 10000000  # 1 Crore
    
    # Loan amount validation
    min_loan: int = 50000
    max_loan: int = 5000000
    
    # String length limits
    max_name_length: int = 100
    max_city_length: int = 50
    
    # Numeric limits
    max_dependents: int = 10
    max_existing_loans: int = 15
    max_late_payments: int = 50


@dataclass
class AuditConfig:
    """Audit and logging configuration."""
    enable_audit_logging: bool = True
    log_predictions: bool = True
    log_explanations: bool = True
    retain_logs_days: int = 2555  # 7 years (RBI requirement)
    
    # Audit levels
    audit_level: str = 'FULL'  # MINIMAL, STANDARD, FULL
    
    # Log file paths
    audit_log_path: str = 'logs/audit'
    prediction_log_path: str = 'logs/predictions'
    error_log_path: str = 'logs/errors'


@dataclass
class InterestRateConfig:
    """Interest rate configuration for EMI calculation."""
    base_rate: float = 9.50  # RBI repo rate based
    
    # Risk-based pricing spreads
    risk_spreads: Dict[str, float] = field(default_factory=lambda: {
        'low': 2.0,      # Low risk: base + 2%
        'medium': 3.5,   # Medium risk: base + 3.5%
        'high': 5.0,     # High risk: base + 5%
        'very_high': 7.0 # Very high risk: base + 7%
    })
    
    # Credit score based adjustments
    score_adjustments: Dict[str, float] = field(default_factory=lambda: {
        'excellent': -1.0,  # 1% discount for excellent credit
        'good': -0.5,
        'fair': 0.0,
        'poor': 1.0,
        'very_poor': 2.0
    })


class SystemConfig:
    """Main system configuration aggregator."""
    
    def __init__(self):
        self.credit_score = CreditScoreConfig()
        self.dti = DebtToIncomeConfig()
        self.loan_amount = LoanAmountConfig()
        self.age = AgeConfig()
        self.employment = EmploymentConfig()
        self.fairness = FairnessConfig()
        self.model = ModelConfig()
        self.validation = ValidationConfig()
        self.audit = AuditConfig()
        self.interest_rate = InterestRateConfig()
        
        # Paths
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(self.base_path, 'models', 'loan_model.pkl')
        self.data_path = os.path.join(self.base_path, 'data', 'loan_applications.csv')
        self.log_path = os.path.join(self.base_path, 'logs')
    
    def get_risk_category(self, approval_probability: float) -> RiskCategory:
        """Determine risk category based on approval probability."""
        if approval_probability >= 0.80:
            return RiskCategory.LOW
        elif approval_probability >= 0.60:
            return RiskCategory.MEDIUM
        elif approval_probability >= 0.40:
            return RiskCategory.HIGH
        else:
            return RiskCategory.VERY_HIGH
    
    def get_loan_status(self, approval_probability: float) -> LoanStatus:
        """Determine loan status based on probability."""
        lower, upper = self.model.manual_review_band
        
        if approval_probability >= self.model.approval_threshold + 0.15:
            return LoanStatus.APPROVED
        elif approval_probability < self.model.approval_threshold - 0.15:
            return LoanStatus.REJECTED
        else:
            return LoanStatus.MANUAL_REVIEW
    
    def calculate_interest_rate(self, credit_score: int, 
                                 risk_category: RiskCategory) -> float:
        """Calculate applicable interest rate."""
        base = self.interest_rate.base_rate
        
        # Add risk spread
        spread = self.interest_rate.risk_spreads.get(
            risk_category.value, 
            self.interest_rate.risk_spreads['high']
        )
        
        # Add credit score adjustment
        if credit_score >= self.credit_score.excellent_threshold:
            score_adj = self.interest_rate.score_adjustments['excellent']
        elif credit_score >= self.credit_score.good_threshold:
            score_adj = self.interest_rate.score_adjustments['good']
        elif credit_score >= self.credit_score.fair_threshold:
            score_adj = self.interest_rate.score_adjustments['fair']
        elif credit_score >= self.credit_score.poor_threshold:
            score_adj = self.interest_rate.score_adjustments['poor']
        else:
            score_adj = self.interest_rate.score_adjustments['very_poor']
        
        return round(base + spread + score_adj, 2)


# Global config instance
CONFIG = SystemConfig()


# Feature lists for model
CATEGORICAL_FEATURES = [
    'gender', 'education', 'marital_status', 
    'employment_type', 'industry'
]

NUMERICAL_FEATURES = [
    'age', 'num_dependents', 'years_at_current_job',
    'monthly_income', 'existing_emi', 'num_existing_loans',
    'cibil_score', 'credit_history_years', 
    'late_payments_last_2_years', 'savings_balance',
    'years_with_bank', 'loan_amount', 'loan_tenure_months'
]

BOOLEAN_FEATURES = ['has_defaults', 'owns_property']

# Engineered features
ENGINEERED_FEATURES = [
    'debt_to_income_ratio',
    'loan_to_income_ratio', 
    'emi_to_income_ratio',
    'savings_to_loan_ratio',
    'income_stability_score',
    'credit_utilization_proxy'
]

# Display names mapping
FEATURE_DISPLAY_NAMES = {
    'age': 'Age',
    'gender': 'Gender',
    'education': 'Education Level',
    'marital_status': 'Marital Status',
    'num_dependents': 'Number of Dependents',
    'employment_type': 'Employment Type',
    'industry': 'Industry',
    'years_at_current_job': 'Years at Current Job',
    'monthly_income': 'Monthly Income (₹)',
    'existing_emi': 'Existing EMI (₹)',
    'num_existing_loans': 'Number of Existing Loans',
    'cibil_score': 'CIBIL Score',
    'credit_history_years': 'Credit History Length (Years)',
    'late_payments_last_2_years': 'Late Payments (Last 2 Years)',
    'has_defaults': 'Has Previous Defaults',
    'owns_property': 'Property Owner',
    'savings_balance': 'Savings Balance (₹)',
    'years_with_bank': 'Years with Bank',
    'loan_amount': 'Loan Amount Requested (₹)',
    'loan_tenure_months': 'Loan Tenure (Months)',
    'debt_to_income_ratio': 'Debt-to-Income Ratio',
    'loan_to_income_ratio': 'Loan-to-Income Ratio',
    'emi_to_income_ratio': 'EMI-to-Income Ratio',
    'savings_to_loan_ratio': 'Savings-to-Loan Ratio',
    'income_stability_score': 'Income Stability Score',
    'credit_utilization_proxy': 'Credit Utilization (Estimated)'
}
