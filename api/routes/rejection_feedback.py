"""
Rejection Feedback Routes
==========================
API endpoints for soft rejection and improvement suggestions.

These endpoints provide empathetic, constructive feedback to rejected applicants
with actionable improvement suggestions.

Author: Loan Analytics Team
Version: 1.0.0
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, require_analyst_or_above
from database.models import User
from services.soft_reject_service import (
    SoftRejectService,
    ApplicantContext,
    ImprovementCategory,
    ImprovementPriority,
    get_soft_reject_service
)


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RejectionFeedbackRequest(BaseModel):
    """Request for rejection feedback."""
    application_id: str
    
    # Applicant details
    applicant_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=18, le=100)
    monthly_income: Optional[float] = Field(None, ge=0)
    employment_type: Optional[str] = None
    employment_years: float = Field(default=0, ge=0)
    cibil_score: Optional[int] = Field(None, ge=300, le=900)
    existing_monthly_debt: float = Field(default=0, ge=0)
    
    # Loan details
    loan_amount_requested: float = Field(..., gt=0)
    loan_purpose: Optional[str] = None
    
    # Context
    is_first_time_applicant: bool = True
    previous_rejection_count: int = Field(default=0, ge=0)
    
    # Rejection details
    rejection_reasons: List[str] = Field(default_factory=list)
    ml_score: Optional[float] = Field(None, ge=0, le=1)
    rule_failures: Optional[List[dict]] = None


class ImprovementSuggestionResponse(BaseModel):
    """A single improvement suggestion."""
    category: str
    title: str
    description: str
    action_steps: List[str]
    expected_impact: str
    estimated_time: str
    priority: str
    difficulty: str
    resources: List[str]
    current_value: Optional[str] = None
    target_value: Optional[str] = None


class SoftRejectResponse(BaseModel):
    """Complete soft rejection response."""
    
    # Greeting and acknowledgment
    greeting: str
    acknowledgment: str
    
    # Outcome
    outcome: str
    outcome_message: str
    
    # Explanation
    primary_reason: str
    detailed_explanation: str
    factors_summary: List[str]
    
    # Improvements
    improvement_suggestions: List[ImprovementSuggestionResponse]
    quick_wins: List[str]
    
    # Timeline
    estimated_eligibility_date: Optional[str]
    eligibility_timeline: str
    
    # Encouragement
    encouragement_message: str
    
    # Actions
    immediate_actions: List[str]
    follow_up_options: List[str]
    
    # Support
    support_message: str
    contact_options: List[str]
    
    # Metadata
    application_id: str
    generated_at: str


class QuickFeedbackRequest(BaseModel):
    """Simple request for quick feedback."""
    cibil_score: Optional[int] = Field(None, ge=300, le=900)
    monthly_income: float = Field(..., gt=0)
    existing_emi: float = Field(default=0, ge=0)
    loan_amount: float = Field(..., gt=0)
    employment_months: int = Field(default=0, ge=0)


class QuickFeedbackResponse(BaseModel):
    """Quick eligibility feedback."""
    likely_outcome: str
    confidence: str
    key_strengths: List[str]
    areas_to_improve: List[str]
    quick_tips: List[str]
    estimated_approval_chance: str


# =============================================================================
# Routes
# =============================================================================

@router.post("/feedback", response_model=SoftRejectResponse)
async def get_rejection_feedback(
    request: RejectionFeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive, empathetic feedback for a rejected application.
    
    This endpoint provides:
    - Friendly explanation of rejection reasons
    - Personalized improvement suggestions
    - Timeline for potential reapplication
    - Immediate action items
    
    The response is designed to be user-friendly and encouraging,
    helping applicants understand how to improve their chances.
    """
    service = get_soft_reject_service()
    
    # Build applicant context
    context = ApplicantContext(
        name=request.applicant_name,
        age=request.age,
        income=Decimal(str(request.monthly_income)) if request.monthly_income else None,
        employment_type=request.employment_type,
        employment_years=request.employment_years,
        cibil_score=request.cibil_score,
        existing_debt=Decimal(str(request.existing_monthly_debt)),
        loan_amount_requested=Decimal(str(request.loan_amount_requested)),
        loan_purpose=request.loan_purpose,
        is_first_time_applicant=request.is_first_time_applicant,
        previous_rejection_count=request.previous_rejection_count
    )
    
    # Generate rejection reasons if not provided
    rejection_reasons = []
    for reason in request.rejection_reasons:
        rejection_reasons.append({"reason": reason})
    
    # Generate soft rejection response
    response = service.generate_soft_rejection(
        application_id=request.application_id,
        rejection_reasons=rejection_reasons,
        applicant_context=context,
        ml_score=request.ml_score,
        rule_failures=request.rule_failures
    )
    
    # Convert to response model
    return SoftRejectResponse(
        greeting=response.greeting,
        acknowledgment=response.acknowledgment,
        outcome=response.outcome,
        outcome_message=response.outcome_message,
        primary_reason=response.primary_reason,
        detailed_explanation=response.detailed_explanation,
        factors_summary=response.factors_summary,
        improvement_suggestions=[
            ImprovementSuggestionResponse(
                category=s.category.value,
                title=s.title,
                description=s.description,
                action_steps=s.action_steps,
                expected_impact=s.expected_impact,
                estimated_time=s.estimated_time,
                priority=s.priority.value,
                difficulty=s.difficulty.value,
                resources=s.resources,
                current_value=str(s.current_value) if s.current_value else None,
                target_value=str(s.target_value) if s.target_value else None
            )
            for s in response.improvement_suggestions
        ],
        quick_wins=response.quick_wins,
        estimated_eligibility_date=(
            response.estimated_eligibility_date.isoformat() 
            if response.estimated_eligibility_date else None
        ),
        eligibility_timeline=response.eligibility_timeline,
        encouragement_message=response.encouragement_message,
        immediate_actions=response.immediate_actions,
        follow_up_options=response.follow_up_options,
        support_message=response.support_message,
        contact_options=response.contact_options,
        application_id=response.application_id,
        generated_at=response.generated_at.isoformat()
    )


@router.post("/quick-check", response_model=QuickFeedbackResponse)
async def quick_eligibility_check(
    request: QuickFeedbackRequest
):
    """
    Quick eligibility pre-check with improvement tips.
    
    This is a lightweight endpoint that doesn't require authentication,
    allowing potential applicants to check their likely outcome before
    formally applying. Provides immediate feedback on strengths and
    areas to improve.
    """
    strengths = []
    improvements = []
    tips = []
    
    # Analyze CIBIL score
    if request.cibil_score:
        if request.cibil_score >= 750:
            strengths.append("🌟 Excellent credit score")
        elif request.cibil_score >= 700:
            strengths.append("✅ Good credit score")
        elif request.cibil_score >= 650:
            improvements.append("📈 Credit score could be higher")
            tips.append("Pay all bills on time to improve your credit score")
        else:
            improvements.append("📊 Credit score needs improvement")
            tips.append("Focus on timely payments and reducing credit utilization")
    else:
        improvements.append("❓ Credit score not provided")
        tips.append("Check your free credit report at CIBIL website")
    
    # Analyze DTI ratio
    dti = (request.existing_emi / request.monthly_income * 100) if request.monthly_income > 0 else 0
    if dti < 30:
        strengths.append("✅ Low debt-to-income ratio")
    elif dti < 50:
        improvements.append("⚖️ Moderate debt level")
        tips.append("Try to reduce existing EMIs before applying")
    else:
        improvements.append("⚠️ High debt-to-income ratio")
        tips.append("Pay off some existing loans to improve your eligibility")
    
    # Analyze loan-to-income ratio
    annual_income = request.monthly_income * 12
    lti = (request.loan_amount / annual_income * 100) if annual_income > 0 else 0
    if lti <= 40:
        strengths.append("✅ Loan amount is well within your income capacity")
    elif lti <= 60:
        improvements.append("💡 Consider a smaller loan amount")
    else:
        improvements.append("⚠️ Loan amount is high relative to income")
        tips.append("Consider reducing the loan amount or increasing down payment")
    
    # Analyze employment
    if request.employment_months >= 24:
        strengths.append("✅ Good employment stability")
    elif request.employment_months >= 6:
        improvements.append("📅 Employment tenure is still building")
    else:
        improvements.append("⏰ Need more employment history")
        tips.append("Wait a few more months at your current job before applying")
    
    # Determine likely outcome
    score = len(strengths) * 2 - len(improvements)
    if score >= 4:
        likely_outcome = "likely_approval"
        confidence = "high"
        chance = "70-90%"
    elif score >= 2:
        likely_outcome = "possible_approval"
        confidence = "medium"
        chance = "50-70%"
    elif score >= 0:
        likely_outcome = "needs_improvement"
        confidence = "medium"
        chance = "30-50%"
    else:
        likely_outcome = "unlikely_approval"
        confidence = "high"
        chance = "Below 30%"
    
    return QuickFeedbackResponse(
        likely_outcome=likely_outcome,
        confidence=confidence,
        key_strengths=strengths if strengths else ["Keep building your financial profile!"],
        areas_to_improve=improvements if improvements else ["You're on the right track!"],
        quick_tips=tips if tips else ["Maintain your good financial habits!"],
        estimated_approval_chance=chance
    )


@router.get("/improvement-tips")
async def get_improvement_tips(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get general improvement tips for loan eligibility.
    
    Returns categorized tips for improving loan approval chances.
    No authentication required - available as a public resource.
    """
    all_tips = {
        "credit_score": {
            "title": "Improve Your Credit Score 📈",
            "description": "Your credit score is one of the most important factors in loan approval",
            "tips": [
                "Pay all bills and EMIs on time - this is the #1 factor",
                "Keep credit card utilization below 30% of your limit",
                "Don't close old credit accounts - they show history",
                "Check your credit report regularly for errors",
                "Avoid applying for multiple credits in a short period",
                "Mix of credit types (credit card + loan) is good"
            ],
            "timeline": "3-12 months to see improvement"
        },
        "income": {
            "title": "Strengthen Your Income Profile 💼",
            "description": "Higher documented income increases loan eligibility",
            "tips": [
                "Document all sources of income properly",
                "Get salary certificates and increment letters",
                "Consider a co-applicant to combine incomes",
                "Explore side income opportunities",
                "Keep 6+ months of bank statements ready",
                "Report rental income and investment returns"
            ],
            "timeline": "Immediate to 6 months"
        },
        "debt_management": {
            "title": "Manage Your Existing Debt 📊",
            "description": "Lower debt-to-income ratio makes you a better borrower",
            "tips": [
                "Pay off smallest debts first (snowball method)",
                "Consider debt consolidation for lower interest",
                "Avoid taking new debt while applying",
                "Negotiate better terms with existing lenders",
                "Use windfalls (bonus, gifts) to pay down debt",
                "Aim for DTI ratio below 40%"
            ],
            "timeline": "3-12 months"
        },
        "employment": {
            "title": "Build Employment Stability 🏢",
            "description": "Stable employment shows reliable income potential",
            "tips": [
                "Stay at your current job for at least 6-12 months",
                "Avoid job changes while loan application is pending",
                "Document all employment history",
                "Get employment verification letter",
                "Promotions and raises help your case",
                "Self-employed? Keep 2+ years of ITR ready"
            ],
            "timeline": "6-12 months"
        },
        "documentation": {
            "title": "Perfect Your Documentation 📋",
            "description": "Complete documentation speeds up approval",
            "tips": [
                "Complete KYC verification (Aadhaar, PAN)",
                "Keep 6 months of salary slips ready",
                "Maintain clean bank statements",
                "Have property documents ready if applicable",
                "Get all documents attested where required",
                "Organize documents before applying"
            ],
            "timeline": "1-2 weeks"
        },
        "savings": {
            "title": "Build Your Savings 💰",
            "description": "Savings show financial discipline and provide security",
            "tips": [
                "Build emergency fund of 3-6 months expenses",
                "Maintain consistent savings pattern",
                "Consider fixed deposits for stability",
                "Don't withdraw savings before applying",
                "Show steady account balance growth",
                "Document all savings and investments"
            ],
            "timeline": "3-6 months"
        }
    }
    
    if category and category in all_tips:
        return {category: all_tips[category]}
    
    return all_tips


@router.get("/faq")
async def get_rejection_faq():
    """
    Get frequently asked questions about loan rejection.
    
    Public endpoint providing helpful information to rejected applicants.
    """
    return {
        "faqs": [
            {
                "question": "Why was my loan application rejected?",
                "answer": "Loan applications can be rejected for various reasons including credit score, income levels, existing debt, employment stability, or incomplete documentation. Our feedback system provides specific reasons and improvement suggestions for your case."
            },
            {
                "question": "How long should I wait before reapplying?",
                "answer": "We recommend waiting 3-6 months while working on the improvement suggestions provided. This gives you time to strengthen your profile and allows credit bureaus to reflect positive changes."
            },
            {
                "question": "Will rejection affect my credit score?",
                "answer": "The loan application itself (hard inquiry) may cause a small, temporary dip in your score. However, the rejection itself doesn't directly affect your score. Multiple applications in a short period can have a larger impact."
            },
            {
                "question": "Can I appeal the decision?",
                "answer": "While formal appeals aren't typically available for automated decisions, you can work on the improvement areas and reapply. If you believe there was an error, contact our support team."
            },
            {
                "question": "What's the fastest way to improve my chances?",
                "answer": "The quickest improvements are: reducing existing debt, adding a co-applicant, providing collateral, or applying for a smaller loan amount. Credit score improvements take longer (3-6 months)."
            },
            {
                "question": "Does checking my eligibility affect my credit score?",
                "answer": "Our quick eligibility check is a 'soft inquiry' and does NOT affect your credit score. You can check multiple times without any impact."
            }
        ],
        "support": {
            "email": "support@loanapproval.com",
            "phone": "1800-XXX-XXXX",
            "hours": "Monday-Saturday, 9 AM - 6 PM"
        }
    }
