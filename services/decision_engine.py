"""
Decision Engine - Layered Loan Approval System
===============================================
Implements a three-layer decision architecture:

Layer 1: Rule-Based Checks (fast, explainable)
    - Age ≥ 21
    - Income ≥ threshold
    - KYC verified
    - Hard business rules that must pass

Layer 2: ML Model
    - Credit risk score
    - Default probability
    - Soft scoring based on patterns

Layer 3: Final Decision Logic
    - Rules PASS + ML score > threshold → APPROVE
    - Otherwise → REJECT or REVIEW

Author: Loan Analytics Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================

class DecisionOutcome(str, Enum):
    """Final decision outcome."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class RuleStatus(str, Enum):
    """Individual rule check status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class RuleCategory(str, Enum):
    """Category of business rules."""
    ELIGIBILITY = "eligibility"
    COMPLIANCE = "compliance"
    RISK = "risk"
    FRAUD = "fraud"


# =============================================================================
# Data Transfer Objects (DTOs)
# =============================================================================

@dataclass
class RuleResult:
    """Result of a single rule check."""
    rule_id: str
    rule_name: str
    category: RuleCategory
    status: RuleStatus
    message: str
    actual_value: Optional[Any] = None
    threshold: Optional[Any] = None
    weight: float = 1.0  # Importance weight for scoring


@dataclass
class RuleEngineResult:
    """Result from Layer 1: Rule-Based Checks."""
    passed: bool
    total_rules: int
    passed_rules: int
    failed_rules: int
    warning_rules: int
    results: List[RuleResult] = field(default_factory=list)
    blocking_failures: List[RuleResult] = field(default_factory=list)
    execution_time_ms: float = 0.0
    
    @property
    def pass_rate(self) -> float:
        """Calculate rule pass rate."""
        if self.total_rules == 0:
            return 0.0
        return self.passed_rules / self.total_rules


@dataclass
class MLScoreResult:
    """Result from Layer 2: ML Model."""
    credit_risk_score: float  # 0-100, lower is better
    default_probability: float  # 0-1, probability of default
    approval_score: float  # 0-1, likelihood of approval
    confidence: float  # Model confidence
    risk_factors: List[str] = field(default_factory=list)
    model_version: str = "1.0.0"
    execution_time_ms: float = 0.0


@dataclass
class FinalDecision:
    """Result from Layer 3: Final Decision Logic."""
    outcome: DecisionOutcome
    
    # Layer 1 Results
    rules_passed: bool
    rule_engine_result: RuleEngineResult
    
    # Layer 2 Results
    ml_score_result: MLScoreResult
    
    # Combined Analysis
    combined_score: float  # 0-100 overall score
    decision_reason: str
    detailed_reasons: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    decision_timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    
    # For manual review
    requires_human_review: bool = False
    review_reasons: List[str] = field(default_factory=list)


@dataclass
class ApplicantProfile:
    """Applicant information for decision engine."""
    # Demographics
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    
    # KYC
    kyc_verified: bool = False
    pan_verified: bool = False
    aadhaar_verified: bool = False
    
    # Income & Employment
    monthly_income: Decimal = Decimal("0")
    additional_income: Decimal = Decimal("0")
    employment_years: int = 0
    employment_months: int = 0
    employment_type: Optional[str] = None
    
    # Credit
    cibil_score: Optional[int] = None
    credit_history_years: int = 0
    
    # Assets & Liabilities
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    existing_emi: Decimal = Decimal("0")
    existing_loans_count: int = 0
    owns_home: bool = False
    owns_car: bool = False
    
    @property
    def total_income(self) -> Decimal:
        return self.monthly_income + self.additional_income
    
    @property
    def net_worth(self) -> Decimal:
        return self.total_assets - self.total_liabilities
    
    @property
    def debt_to_income_ratio(self) -> Optional[float]:
        if self.total_income > 0:
            return float(self.existing_emi / self.total_income) * 100
        return None
    
    @property
    def total_employment_years(self) -> float:
        return self.employment_years + (self.employment_months / 12)


@dataclass
class LoanRequest:
    """Loan request information for decision engine."""
    loan_amount: Decimal
    loan_term_months: int
    loan_type: str
    purpose: Optional[str] = None
    collateral_value: Decimal = Decimal("0")
    collateral_type: Optional[str] = None
    co_applicant_income: Decimal = Decimal("0")
    interest_rate_requested: Optional[float] = None
    
    @property
    def loan_to_value_ratio(self) -> Optional[float]:
        """Calculate LTV ratio if collateral exists."""
        if self.collateral_value > 0:
            return float(self.loan_amount / self.collateral_value) * 100
        return None


# =============================================================================
# Layer 1: Rule Engine (Fast, Explainable)
# =============================================================================

class RuleEngine:
    """
    Layer 1: Rule-based eligibility checks.
    
    These are hard rules that must pass before ML scoring.
    Fast execution, fully explainable decisions.
    """
    
    # Configurable thresholds (could load from DB/config)
    MIN_AGE = 21
    MAX_AGE = 65
    MIN_INCOME_PERSONAL = Decimal("15000")
    MIN_INCOME_HOME = Decimal("30000")
    MIN_INCOME_BUSINESS = Decimal("50000")
    MIN_CIBIL_SCORE = 300
    MAX_DTI_RATIO = 60.0  # Maximum debt-to-income ratio
    MIN_EMPLOYMENT_MONTHS = 6
    MAX_EXISTING_LOANS = 5
    MAX_LOAN_TO_INCOME_RATIO = 60  # Max loan amount as multiple of annual income
    
    def evaluate(
        self,
        applicant: ApplicantProfile,
        loan: LoanRequest
    ) -> RuleEngineResult:
        """
        Evaluate all rules against applicant and loan data.
        
        Returns RuleEngineResult with pass/fail status and details.
        """
        import time
        start_time = time.perf_counter()
        
        results: List[RuleResult] = []
        
        # === ELIGIBILITY RULES ===
        results.append(self._check_age(applicant))
        results.append(self._check_income(applicant, loan))
        results.append(self._check_kyc(applicant))
        results.append(self._check_employment(applicant))
        
        # === COMPLIANCE RULES ===
        results.append(self._check_cibil_minimum(applicant))
        results.append(self._check_existing_loans(applicant))
        
        # === RISK RULES ===
        results.append(self._check_dti_ratio(applicant))
        results.append(self._check_loan_to_income(applicant, loan))
        results.append(self._check_collateral(loan))
        
        # === FRAUD PREVENTION RULES ===
        results.append(self._check_identity_verification(applicant))
        
        # Calculate statistics
        passed = [r for r in results if r.status == RuleStatus.PASSED]
        failed = [r for r in results if r.status == RuleStatus.FAILED]
        warnings = [r for r in results if r.status == RuleStatus.WARNING]
        
        # Blocking failures are critical rules that must pass
        blocking_failures = [r for r in failed if r.weight >= 1.0]
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return RuleEngineResult(
            passed=len(blocking_failures) == 0,
            total_rules=len(results),
            passed_rules=len(passed),
            failed_rules=len(failed),
            warning_rules=len(warnings),
            results=results,
            blocking_failures=blocking_failures,
            execution_time_ms=round(execution_time, 2)
        )
    
    def _check_age(self, applicant: ApplicantProfile) -> RuleResult:
        """Check minimum and maximum age requirements."""
        age = applicant.age
        
        if age is None:
            return RuleResult(
                rule_id="AGE_001",
                rule_name="Age Eligibility",
                category=RuleCategory.ELIGIBILITY,
                status=RuleStatus.FAILED,
                message="Date of birth not provided",
                weight=1.0
            )
        
        if age < self.MIN_AGE:
            return RuleResult(
                rule_id="AGE_001",
                rule_name="Age Eligibility",
                category=RuleCategory.ELIGIBILITY,
                status=RuleStatus.FAILED,
                message=f"Applicant must be at least {self.MIN_AGE} years old",
                actual_value=age,
                threshold=self.MIN_AGE,
                weight=1.0  # Blocking rule
            )
        
        if age > self.MAX_AGE:
            return RuleResult(
                rule_id="AGE_001",
                rule_name="Age Eligibility",
                category=RuleCategory.ELIGIBILITY,
                status=RuleStatus.WARNING,
                message=f"Applicant is above typical lending age of {self.MAX_AGE}",
                actual_value=age,
                threshold=self.MAX_AGE,
                weight=0.5
            )
        
        return RuleResult(
            rule_id="AGE_001",
            rule_name="Age Eligibility",
            category=RuleCategory.ELIGIBILITY,
            status=RuleStatus.PASSED,
            message="Age requirement met",
            actual_value=age,
            threshold=self.MIN_AGE
        )
    
    def _check_income(self, applicant: ApplicantProfile, loan: LoanRequest) -> RuleResult:
        """Check minimum income based on loan type."""
        income = applicant.total_income
        
        # Determine minimum based on loan type
        min_income = self.MIN_INCOME_PERSONAL
        if loan.loan_type.lower() == "home":
            min_income = self.MIN_INCOME_HOME
        elif loan.loan_type.lower() == "business":
            min_income = self.MIN_INCOME_BUSINESS
        
        if income < min_income:
            return RuleResult(
                rule_id="INC_001",
                rule_name="Minimum Income",
                category=RuleCategory.ELIGIBILITY,
                status=RuleStatus.FAILED,
                message=f"Monthly income must be at least ₹{min_income:,.0f} for {loan.loan_type} loan",
                actual_value=float(income),
                threshold=float(min_income),
                weight=1.0  # Blocking rule
            )
        
        return RuleResult(
            rule_id="INC_001",
            rule_name="Minimum Income",
            category=RuleCategory.ELIGIBILITY,
            status=RuleStatus.PASSED,
            message="Income requirement met",
            actual_value=float(income),
            threshold=float(min_income)
        )
    
    def _check_kyc(self, applicant: ApplicantProfile) -> RuleResult:
        """Check KYC verification status."""
        if not applicant.kyc_verified:
            return RuleResult(
                rule_id="KYC_001",
                rule_name="KYC Verification",
                category=RuleCategory.COMPLIANCE,
                status=RuleStatus.FAILED,
                message="KYC verification is required",
                actual_value=False,
                threshold=True,
                weight=1.0  # Blocking rule
            )
        
        return RuleResult(
            rule_id="KYC_001",
            rule_name="KYC Verification",
            category=RuleCategory.COMPLIANCE,
            status=RuleStatus.PASSED,
            message="KYC verified",
            actual_value=True,
            threshold=True
        )
    
    def _check_employment(self, applicant: ApplicantProfile) -> RuleResult:
        """Check minimum employment duration."""
        total_months = (applicant.employment_years * 12) + applicant.employment_months
        
        if total_months < self.MIN_EMPLOYMENT_MONTHS:
            return RuleResult(
                rule_id="EMP_001",
                rule_name="Employment Duration",
                category=RuleCategory.ELIGIBILITY,
                status=RuleStatus.FAILED,
                message=f"Minimum {self.MIN_EMPLOYMENT_MONTHS} months of employment required",
                actual_value=total_months,
                threshold=self.MIN_EMPLOYMENT_MONTHS,
                weight=1.0  # Blocking rule
            )
        
        return RuleResult(
            rule_id="EMP_001",
            rule_name="Employment Duration",
            category=RuleCategory.ELIGIBILITY,
            status=RuleStatus.PASSED,
            message="Employment duration requirement met",
            actual_value=total_months,
            threshold=self.MIN_EMPLOYMENT_MONTHS
        )
    
    def _check_cibil_minimum(self, applicant: ApplicantProfile) -> RuleResult:
        """Check minimum CIBIL score requirement."""
        if applicant.cibil_score is None:
            return RuleResult(
                rule_id="CIB_001",
                rule_name="CIBIL Score Available",
                category=RuleCategory.COMPLIANCE,
                status=RuleStatus.WARNING,
                message="No CIBIL score available - manual review recommended",
                weight=0.5
            )
        
        if applicant.cibil_score < self.MIN_CIBIL_SCORE:
            return RuleResult(
                rule_id="CIB_001",
                rule_name="CIBIL Score Minimum",
                category=RuleCategory.COMPLIANCE,
                status=RuleStatus.FAILED,
                message=f"CIBIL score below minimum threshold of {self.MIN_CIBIL_SCORE}",
                actual_value=applicant.cibil_score,
                threshold=self.MIN_CIBIL_SCORE,
                weight=1.0
            )
        
        return RuleResult(
            rule_id="CIB_001",
            rule_name="CIBIL Score",
            category=RuleCategory.COMPLIANCE,
            status=RuleStatus.PASSED,
            message="CIBIL score meets minimum requirement",
            actual_value=applicant.cibil_score,
            threshold=self.MIN_CIBIL_SCORE
        )
    
    def _check_existing_loans(self, applicant: ApplicantProfile) -> RuleResult:
        """Check number of existing loans."""
        if applicant.existing_loans_count > self.MAX_EXISTING_LOANS:
            return RuleResult(
                rule_id="LOAN_001",
                rule_name="Existing Loans Limit",
                category=RuleCategory.RISK,
                status=RuleStatus.FAILED,
                message=f"Exceeded maximum of {self.MAX_EXISTING_LOANS} existing loans",
                actual_value=applicant.existing_loans_count,
                threshold=self.MAX_EXISTING_LOANS,
                weight=0.8
            )
        
        if applicant.existing_loans_count >= 3:
            return RuleResult(
                rule_id="LOAN_001",
                rule_name="Existing Loans",
                category=RuleCategory.RISK,
                status=RuleStatus.WARNING,
                message="Multiple existing loans detected",
                actual_value=applicant.existing_loans_count,
                threshold=3,
                weight=0.3
            )
        
        return RuleResult(
            rule_id="LOAN_001",
            rule_name="Existing Loans",
            category=RuleCategory.RISK,
            status=RuleStatus.PASSED,
            message="Existing loan count acceptable",
            actual_value=applicant.existing_loans_count,
            threshold=self.MAX_EXISTING_LOANS
        )
    
    def _check_dti_ratio(self, applicant: ApplicantProfile) -> RuleResult:
        """Check debt-to-income ratio."""
        dti = applicant.debt_to_income_ratio
        
        if dti is None:
            return RuleResult(
                rule_id="DTI_001",
                rule_name="Debt-to-Income Ratio",
                category=RuleCategory.RISK,
                status=RuleStatus.SKIPPED,
                message="Unable to calculate DTI (no income data)",
                weight=0.0
            )
        
        if dti > self.MAX_DTI_RATIO:
            return RuleResult(
                rule_id="DTI_001",
                rule_name="Debt-to-Income Ratio",
                category=RuleCategory.RISK,
                status=RuleStatus.FAILED,
                message=f"DTI ratio {dti:.1f}% exceeds maximum {self.MAX_DTI_RATIO}%",
                actual_value=round(dti, 2),
                threshold=self.MAX_DTI_RATIO,
                weight=0.9
            )
        
        if dti > 40:
            return RuleResult(
                rule_id="DTI_001",
                rule_name="Debt-to-Income Ratio",
                category=RuleCategory.RISK,
                status=RuleStatus.WARNING,
                message=f"DTI ratio {dti:.1f}% is elevated",
                actual_value=round(dti, 2),
                threshold=40,
                weight=0.3
            )
        
        return RuleResult(
            rule_id="DTI_001",
            rule_name="Debt-to-Income Ratio",
            category=RuleCategory.RISK,
            status=RuleStatus.PASSED,
            message=f"DTI ratio {dti:.1f}% is acceptable",
            actual_value=round(dti, 2),
            threshold=self.MAX_DTI_RATIO
        )
    
    def _check_loan_to_income(self, applicant: ApplicantProfile, loan: LoanRequest) -> RuleResult:
        """Check loan amount relative to annual income."""
        annual_income = float(applicant.total_income) * 12
        
        if annual_income <= 0:
            return RuleResult(
                rule_id="LTI_001",
                rule_name="Loan-to-Income Ratio",
                category=RuleCategory.RISK,
                status=RuleStatus.SKIPPED,
                message="Unable to calculate LTI (no income data)",
                weight=0.0
            )
        
        lti_ratio = (float(loan.loan_amount) / annual_income) * 100
        
        if lti_ratio > self.MAX_LOAN_TO_INCOME_RATIO:
            return RuleResult(
                rule_id="LTI_001",
                rule_name="Loan-to-Income Ratio",
                category=RuleCategory.RISK,
                status=RuleStatus.WARNING,
                message=f"Loan amount is {lti_ratio:.0f}% of annual income (high)",
                actual_value=round(lti_ratio, 1),
                threshold=self.MAX_LOAN_TO_INCOME_RATIO,
                weight=0.5
            )
        
        return RuleResult(
            rule_id="LTI_001",
            rule_name="Loan-to-Income Ratio",
            category=RuleCategory.RISK,
            status=RuleStatus.PASSED,
            message=f"Loan amount is {lti_ratio:.0f}% of annual income",
            actual_value=round(lti_ratio, 1),
            threshold=self.MAX_LOAN_TO_INCOME_RATIO
        )
    
    def _check_collateral(self, loan: LoanRequest) -> RuleResult:
        """Check collateral for secured loans."""
        if loan.loan_type.lower() in ["home", "auto", "gold"]:
            # Secured loans require collateral
            if float(loan.collateral_value) <= 0:
                return RuleResult(
                    rule_id="COL_001",
                    rule_name="Collateral Required",
                    category=RuleCategory.COMPLIANCE,
                    status=RuleStatus.WARNING,
                    message=f"Collateral recommended for {loan.loan_type} loan",
                    weight=0.4
                )
            
            ltv = loan.loan_to_value_ratio
            if ltv and ltv > 90:
                return RuleResult(
                    rule_id="COL_001",
                    rule_name="Loan-to-Value Ratio",
                    category=RuleCategory.RISK,
                    status=RuleStatus.WARNING,
                    message=f"LTV ratio {ltv:.1f}% is high",
                    actual_value=round(ltv, 1),
                    threshold=90,
                    weight=0.3
                )
        
        return RuleResult(
            rule_id="COL_001",
            rule_name="Collateral Check",
            category=RuleCategory.COMPLIANCE,
            status=RuleStatus.PASSED,
            message="Collateral requirements met",
            actual_value=float(loan.collateral_value) if loan.collateral_value else 0
        )
    
    def _check_identity_verification(self, applicant: ApplicantProfile) -> RuleResult:
        """Check identity document verification."""
        if not applicant.pan_verified and not applicant.aadhaar_verified:
            return RuleResult(
                rule_id="ID_001",
                rule_name="Identity Verification",
                category=RuleCategory.FRAUD,
                status=RuleStatus.WARNING,
                message="Neither PAN nor Aadhaar verified",
                weight=0.6
            )
        
        return RuleResult(
            rule_id="ID_001",
            rule_name="Identity Verification",
            category=RuleCategory.FRAUD,
            status=RuleStatus.PASSED,
            message="Identity documents verified",
            actual_value=True
        )


# =============================================================================
# Layer 2: ML Scoring Engine
# =============================================================================

class MLScoringEngine:
    """
    Layer 2: ML-based credit risk scoring.
    
    Computes:
    - Credit risk score (0-100, lower is better)
    - Default probability (0-1)
    - Approval score (0-1, higher is better)
    """
    
    MODEL_VERSION = "2.0.0"
    
    # Score weights for different factors
    WEIGHTS = {
        "cibil": 0.30,
        "dti": 0.20,
        "employment": 0.15,
        "assets": 0.15,
        "loan_characteristics": 0.10,
        "credit_history": 0.10
    }
    
    # CIBIL score bands
    CIBIL_EXCELLENT = 750
    CIBIL_GOOD = 700
    CIBIL_FAIR = 650
    CIBIL_POOR = 600
    
    def score(
        self,
        applicant: ApplicantProfile,
        loan: LoanRequest
    ) -> MLScoreResult:
        """
        Generate ML scores for the application.
        
        Returns comprehensive scoring with risk factors.
        """
        import time
        start_time = time.perf_counter()
        
        risk_factors = []
        
        # Calculate component scores (0-100 scale, lower is better for risk)
        cibil_score = self._score_cibil(applicant, risk_factors)
        dti_score = self._score_dti(applicant, risk_factors)
        employment_score = self._score_employment(applicant, risk_factors)
        asset_score = self._score_assets(applicant, risk_factors)
        loan_score = self._score_loan(applicant, loan, risk_factors)
        history_score = self._score_credit_history(applicant, risk_factors)
        
        # Weighted average for credit risk score
        credit_risk_score = (
            cibil_score * self.WEIGHTS["cibil"] +
            dti_score * self.WEIGHTS["dti"] +
            employment_score * self.WEIGHTS["employment"] +
            asset_score * self.WEIGHTS["assets"] +
            loan_score * self.WEIGHTS["loan_characteristics"] +
            history_score * self.WEIGHTS["credit_history"]
        )
        
        # Normalize to 0-100
        credit_risk_score = max(0, min(100, credit_risk_score))
        
        # Convert to default probability (sigmoid transformation)
        default_probability = self._risk_to_probability(credit_risk_score)
        
        # Approval score is inverse of default probability
        approval_score = 1 - default_probability
        
        # Compute confidence based on data completeness
        confidence = self._compute_confidence(applicant, loan)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return MLScoreResult(
            credit_risk_score=round(credit_risk_score, 2),
            default_probability=round(default_probability, 4),
            approval_score=round(approval_score, 4),
            confidence=round(confidence, 2),
            risk_factors=risk_factors,
            model_version=self.MODEL_VERSION,
            execution_time_ms=round(execution_time, 2)
        )
    
    def _score_cibil(self, applicant: ApplicantProfile, factors: List[str]) -> float:
        """Score based on CIBIL credit score."""
        if applicant.cibil_score is None:
            factors.append("No credit score available")
            return 60  # Moderate risk for unknown
        
        score = applicant.cibil_score
        
        if score >= self.CIBIL_EXCELLENT:
            factors.append(f"Excellent credit score ({score})")
            return 10  # Very low risk
        elif score >= self.CIBIL_GOOD:
            factors.append(f"Good credit score ({score})")
            return 25
        elif score >= self.CIBIL_FAIR:
            factors.append(f"Fair credit score ({score})")
            return 45
        elif score >= self.CIBIL_POOR:
            factors.append(f"Below average credit score ({score})")
            return 65
        else:
            factors.append(f"Poor credit score ({score})")
            return 85  # High risk
    
    def _score_dti(self, applicant: ApplicantProfile, factors: List[str]) -> float:
        """Score based on debt-to-income ratio."""
        dti = applicant.debt_to_income_ratio
        
        if dti is None:
            return 50
        
        if dti < 20:
            factors.append(f"Low debt burden ({dti:.1f}% DTI)")
            return 10
        elif dti < 35:
            factors.append(f"Manageable debt ({dti:.1f}% DTI)")
            return 30
        elif dti < 50:
            factors.append(f"Moderate debt level ({dti:.1f}% DTI)")
            return 55
        else:
            factors.append(f"High debt burden ({dti:.1f}% DTI)")
            return 80
    
    def _score_employment(self, applicant: ApplicantProfile, factors: List[str]) -> float:
        """Score based on employment stability."""
        years = applicant.total_employment_years
        
        if years >= 5:
            factors.append(f"Stable employment ({years:.1f} years)")
            return 15
        elif years >= 3:
            factors.append(f"Good employment history ({years:.1f} years)")
            return 30
        elif years >= 1:
            factors.append(f"Moderate employment tenure ({years:.1f} years)")
            return 50
        else:
            factors.append(f"Limited employment history ({years:.1f} years)")
            return 75
    
    def _score_assets(self, applicant: ApplicantProfile, factors: List[str]) -> float:
        """Score based on assets and ownership."""
        score = 50  # Base score
        
        if applicant.owns_home:
            score -= 20
            factors.append("Home owner")
        
        if applicant.owns_car:
            score -= 10
            factors.append("Vehicle owner")
        
        if applicant.net_worth > Decimal("1000000"):
            score -= 15
            factors.append("Strong net worth")
        elif applicant.net_worth > Decimal("500000"):
            score -= 10
        elif applicant.net_worth < 0:
            score += 20
            factors.append("Negative net worth")
        
        return max(0, min(100, score))
    
    def _score_loan(self, applicant: ApplicantProfile, loan: LoanRequest, factors: List[str]) -> float:
        """Score based on loan characteristics."""
        score = 40  # Base score
        
        # Loan-to-income ratio
        annual_income = float(applicant.total_income) * 12
        if annual_income > 0:
            lti = float(loan.loan_amount) / annual_income
            if lti > 5:
                score += 25
                factors.append("High loan-to-income ratio")
            elif lti < 2:
                score -= 15
                factors.append("Conservative loan amount")
        
        # Collateral coverage
        if float(loan.collateral_value) > 0:
            coverage = float(loan.collateral_value) / float(loan.loan_amount)
            if coverage >= 1.2:
                score -= 20
                factors.append("Well collateralized")
            elif coverage >= 1.0:
                score -= 10
                factors.append("Fully collateralized")
        
        # Co-applicant
        if float(loan.co_applicant_income) > 0:
            score -= 10
            factors.append("Co-applicant support")
        
        return max(0, min(100, score))
    
    def _score_credit_history(self, applicant: ApplicantProfile, factors: List[str]) -> float:
        """Score based on credit history length."""
        years = applicant.credit_history_years
        
        if years >= 7:
            factors.append(f"Established credit history ({years} years)")
            return 15
        elif years >= 3:
            return 35
        elif years >= 1:
            factors.append("Limited credit history")
            return 55
        else:
            factors.append("No credit history")
            return 75
    
    def _risk_to_probability(self, risk_score: float) -> float:
        """Convert risk score to default probability using sigmoid."""
        import math
        # Sigmoid transformation: maps 0-100 risk to ~0-1 probability
        # Center at 50, scale for reasonable spread
        x = (risk_score - 50) / 15
        return 1 / (1 + math.exp(-x))
    
    def _compute_confidence(self, applicant: ApplicantProfile, loan: LoanRequest) -> float:
        """Compute model confidence based on data completeness."""
        available = 0
        total = 10
        
        if applicant.cibil_score is not None:
            available += 2
        if applicant.total_income > 0:
            available += 2
        if applicant.employment_years > 0 or applicant.employment_months > 0:
            available += 1
        if applicant.total_assets > 0:
            available += 1
        if applicant.kyc_verified:
            available += 1
        if applicant.credit_history_years > 0:
            available += 1
        if float(loan.loan_amount) > 0:
            available += 1
        if loan.loan_term_months > 0:
            available += 1
        
        return available / total


# =============================================================================
# Layer 3: Decision Engine (Combines Rules + ML)
# =============================================================================

class DecisionEngine:
    """
    Layer 3: Final Decision Logic.
    
    Combines:
    - Rule-based checks (must pass)
    - ML scoring (threshold based)
    
    Decision Logic:
    - Rules PASS + ML approval score > threshold → APPROVE
    - Rules PASS + ML score borderline → MANUAL_REVIEW
    - Rules FAIL or ML score < threshold → REJECT
    """
    
    # Decision thresholds
    APPROVAL_THRESHOLD = 0.65  # ML approval score threshold for auto-approve
    REVIEW_THRESHOLD = 0.45   # Below this is auto-reject
    
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.ml_engine = MLScoringEngine()
    
    def evaluate(
        self,
        applicant: ApplicantProfile,
        loan: LoanRequest
    ) -> FinalDecision:
        """
        Run full three-layer evaluation.
        
        Args:
            applicant: Applicant profile data
            loan: Loan request data
            
        Returns:
            FinalDecision with complete analysis
        """
        import time
        start_time = time.perf_counter()
        
        detailed_reasons = []
        review_reasons = []
        recommendations = []
        
        # ======================
        # Layer 1: Rule Checks
        # ======================
        rule_result = self.rule_engine.evaluate(applicant, loan)
        
        if not rule_result.passed:
            # Rules failed - automatic rejection
            for failure in rule_result.blocking_failures:
                detailed_reasons.append(f"[RULE FAILED] {failure.message}")
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Generate recommendations for rejected applications
            recommendations = self._generate_rejection_recommendations(rule_result)
            
            return FinalDecision(
                outcome=DecisionOutcome.REJECTED,
                rules_passed=False,
                rule_engine_result=rule_result,
                ml_score_result=MLScoreResult(
                    credit_risk_score=0,
                    default_probability=0,
                    approval_score=0,
                    confidence=0,
                    risk_factors=["ML scoring skipped - rules failed"],
                    model_version=self.ml_engine.MODEL_VERSION
                ),
                combined_score=0,
                decision_reason="Application rejected due to failed eligibility rules",
                detailed_reasons=detailed_reasons,
                recommendations=recommendations,
                processing_time_ms=round(execution_time, 2),
                requires_human_review=False
            )
        
        detailed_reasons.append("[RULES] All eligibility rules passed")
        
        # ======================
        # Layer 2: ML Scoring
        # ======================
        ml_result = self.ml_engine.score(applicant, loan)
        
        # Add ML factors to reasons
        for factor in ml_result.risk_factors[:5]:  # Top 5 factors
            detailed_reasons.append(f"[ML] {factor}")
        
        # ======================
        # Layer 3: Final Decision
        # ======================
        
        # Calculate combined score (rules pass rate + ML score)
        combined_score = (rule_result.pass_rate * 30) + (ml_result.approval_score * 70)
        
        # Determine outcome
        if ml_result.approval_score >= self.APPROVAL_THRESHOLD:
            outcome = DecisionOutcome.APPROVED
            decision_reason = f"Application approved (ML score: {ml_result.approval_score:.2%})"
            recommendations = self._generate_approval_recommendations(applicant, loan, ml_result)
            
        elif ml_result.approval_score >= self.REVIEW_THRESHOLD:
            outcome = DecisionOutcome.MANUAL_REVIEW
            decision_reason = f"Manual review required (ML score: {ml_result.approval_score:.2%})"
            review_reasons = self._generate_review_reasons(rule_result, ml_result)
            recommendations = self._generate_review_recommendations(applicant, loan)
            
        else:
            outcome = DecisionOutcome.REJECTED
            decision_reason = f"Application rejected (ML score: {ml_result.approval_score:.2%})"
            recommendations = self._generate_rejection_recommendations(rule_result, ml_result)
        
        # Check for low confidence requiring review
        if ml_result.confidence < 0.6 and outcome == DecisionOutcome.APPROVED:
            outcome = DecisionOutcome.MANUAL_REVIEW
            review_reasons.append("Low model confidence due to incomplete data")
        
        # Check for warnings that might need review
        if rule_result.warning_rules >= 3 and outcome == DecisionOutcome.APPROVED:
            outcome = DecisionOutcome.MANUAL_REVIEW
            review_reasons.append("Multiple warning flags detected")
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return FinalDecision(
            outcome=outcome,
            rules_passed=True,
            rule_engine_result=rule_result,
            ml_score_result=ml_result,
            combined_score=round(combined_score, 2),
            decision_reason=decision_reason,
            detailed_reasons=detailed_reasons,
            recommendations=recommendations,
            processing_time_ms=round(execution_time, 2),
            requires_human_review=(outcome == DecisionOutcome.MANUAL_REVIEW),
            review_reasons=review_reasons
        )
    
    def _generate_rejection_recommendations(
        self,
        rule_result: RuleEngineResult,
        ml_result: Optional[MLScoreResult] = None
    ) -> List[str]:
        """Generate recommendations for rejected applications."""
        recommendations = []
        
        for failure in rule_result.blocking_failures:
            if failure.rule_id == "AGE_001":
                recommendations.append("Reapply when you meet the minimum age requirement")
            elif failure.rule_id == "INC_001":
                recommendations.append("Consider increasing income or applying for a smaller loan amount")
            elif failure.rule_id == "KYC_001":
                recommendations.append("Complete KYC verification and reapply")
            elif failure.rule_id == "EMP_001":
                recommendations.append("Build employment history and reapply after 6 months")
            elif failure.rule_id == "CIB_001":
                recommendations.append("Work on improving your credit score before reapplying")
            elif failure.rule_id == "DTI_001":
                recommendations.append("Reduce existing debt or increase income before reapplying")
        
        if ml_result and ml_result.approval_score < 0.3:
            recommendations.append("Consider applying with a co-applicant")
            recommendations.append("Provide additional collateral to strengthen your application")
        
        return recommendations[:5]  # Max 5 recommendations
    
    def _generate_approval_recommendations(
        self,
        applicant: ApplicantProfile,
        loan: LoanRequest,
        ml_result: MLScoreResult
    ) -> List[str]:
        """Generate recommendations for approved applications."""
        recommendations = []
        
        if float(loan.co_applicant_income) == 0:
            recommendations.append("Adding a co-applicant could improve your interest rate")
        
        if float(loan.collateral_value) == 0:
            recommendations.append("Providing collateral may qualify you for better terms")
        
        if ml_result.approval_score < 0.8:
            recommendations.append("Maintaining timely payments will improve future borrowing capacity")
        
        return recommendations
    
    def _generate_review_recommendations(
        self,
        applicant: ApplicantProfile,
        loan: LoanRequest
    ) -> List[str]:
        """Generate recommendations for applications under review."""
        recommendations = [
            "Provide additional income documentation",
            "Submit recent bank statements",
            "Ensure all KYC documents are current"
        ]
        
        if applicant.cibil_score is None:
            recommendations.append("Provide credit score report from CIBIL")
        
        return recommendations
    
    def _generate_review_reasons(
        self,
        rule_result: RuleEngineResult,
        ml_result: MLScoreResult
    ) -> List[str]:
        """Generate reasons for manual review."""
        reasons = []
        
        if ml_result.confidence < 0.7:
            reasons.append(f"Model confidence is low ({ml_result.confidence:.0%})")
        
        # Check for warnings
        warnings = [r for r in rule_result.results if r.status == RuleStatus.WARNING]
        for warning in warnings[:3]:
            reasons.append(f"Warning: {warning.message}")
        
        if 0.45 <= ml_result.approval_score < 0.65:
            reasons.append("Borderline ML score requires human judgment")
        
        return reasons


# =============================================================================
# Factory Function
# =============================================================================

_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get singleton decision engine instance."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine
