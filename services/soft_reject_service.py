"""
Soft Reject Service - Compassionate Rejection with Improvement Roadmap
=======================================================================
Provides empathetic, constructive feedback when loan applications are rejected.

Instead of a simple "REJECTED", we:
1. Acknowledge the applicant's effort
2. Explain reasons in friendly, non-technical language
3. Provide personalized improvement suggestions
4. Offer a clear pathway to future approval
5. Estimate time to become eligible

Author: Loan Analytics Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================

class ImprovementCategory(str, Enum):
    """Categories of improvement suggestions."""
    CREDIT_SCORE = "credit_score"
    INCOME = "income"
    EMPLOYMENT = "employment"
    DEBT_REDUCTION = "debt_reduction"
    DOCUMENTATION = "documentation"
    SAVINGS = "savings"
    COLLATERAL = "collateral"
    LOAN_ADJUSTMENT = "loan_adjustment"
    TIME_BASED = "time_based"


class ImprovementPriority(str, Enum):
    """Priority level for improvement suggestions."""
    CRITICAL = "critical"  # Must fix before any chance of approval
    HIGH = "high"          # Significant impact on approval
    MEDIUM = "medium"      # Would help but not blocking
    LOW = "low"            # Nice to have improvements


class ImprovementDifficulty(str, Enum):
    """How difficult is the improvement to achieve."""
    EASY = "easy"          # Can be done in days/weeks
    MODERATE = "moderate"  # Takes a few months
    CHALLENGING = "challenging"  # Takes 6+ months of effort


# =============================================================================
# Data Transfer Objects
# =============================================================================

@dataclass
class ImprovementSuggestion:
    """A single improvement suggestion."""
    category: ImprovementCategory
    title: str
    description: str
    action_steps: List[str]
    expected_impact: str
    estimated_time: str
    priority: ImprovementPriority
    difficulty: ImprovementDifficulty
    resources: List[str] = field(default_factory=list)
    current_value: Optional[Any] = None
    target_value: Optional[Any] = None


@dataclass
class SoftRejectResponse:
    """Complete soft rejection response with empathetic messaging."""
    
    # Empathetic opening
    greeting: str
    acknowledgment: str
    
    # Main outcome
    outcome: str  # "not_approved_this_time"
    outcome_message: str
    
    # Explanation (friendly, non-technical)
    primary_reason: str
    detailed_explanation: str
    factors_summary: List[str]
    
    # Improvement roadmap
    improvement_suggestions: List[ImprovementSuggestion]
    quick_wins: List[str]  # Things they can do immediately
    
    # Future outlook
    estimated_eligibility_date: Optional[datetime]
    eligibility_timeline: str
    encouragement_message: str
    
    # Next steps
    immediate_actions: List[str]
    follow_up_options: List[str]
    
    # Support
    support_message: str
    contact_options: List[str]
    
    # Metadata
    application_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApplicantContext:
    """Context about the applicant for personalized messaging."""
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[Decimal] = None
    employment_type: Optional[str] = None
    employment_years: float = 0
    cibil_score: Optional[int] = None
    existing_debt: Decimal = Decimal("0")
    loan_amount_requested: Decimal = Decimal("0")
    loan_purpose: Optional[str] = None
    is_first_time_applicant: bool = True
    previous_rejection_count: int = 0


# =============================================================================
# Soft Reject Service
# =============================================================================

class SoftRejectService:
    """
    Service for generating compassionate, constructive rejection responses.
    
    Philosophy:
    - Every rejection is an opportunity to help
    - Clear, actionable advice builds trust
    - Empathy in communication
    - Focus on what CAN be done, not what failed
    """
    
    # Friendly greetings based on time of day
    GREETINGS = {
        "morning": "Good morning",
        "afternoon": "Good afternoon", 
        "evening": "Good evening"
    }
    
    # Acknowledgment templates
    ACKNOWLEDGMENTS = [
        "Thank you for taking the time to apply with us.",
        "We appreciate you considering us for your financial needs.",
        "Thank you for your application and for trusting us with your goals.",
        "We're grateful you chose to apply with us."
    ]
    
    # Encouragement messages
    ENCOURAGEMENTS = [
        "We believe in your potential to achieve your financial goals.",
        "This is just one step in your financial journey, and we're here to help.",
        "Many of our successful borrowers started exactly where you are today.",
        "With the right steps, approval could be well within your reach.",
        "Your financial future is full of possibilities – let's work towards them together."
    ]
    
    # Support messages
    SUPPORT_MESSAGES = [
        "Our team is here to support you on your journey to financial wellness.",
        "We're committed to helping you reach your goals, even if it takes a little time.",
        "Please don't hesitate to reach out if you have questions about improving your profile."
    ]
    
    def generate_soft_rejection(
        self,
        application_id: str,
        rejection_reasons: List[Dict[str, Any]],
        applicant_context: ApplicantContext,
        ml_score: Optional[float] = None,
        rule_failures: Optional[List[Dict[str, Any]]] = None
    ) -> SoftRejectResponse:
        """
        Generate a comprehensive, empathetic soft rejection response.
        
        Args:
            application_id: Unique application identifier
            rejection_reasons: List of reasons for rejection
            applicant_context: Context about the applicant
            ml_score: ML model approval score (0-1)
            rule_failures: List of failed rule checks
            
        Returns:
            SoftRejectResponse with complete empathetic response
        """
        # Get personalized greeting
        greeting = self._get_greeting(applicant_context.name)
        
        # Get acknowledgment
        acknowledgment = self._get_acknowledgment(applicant_context)
        
        # Analyze rejection and generate friendly explanation
        primary_reason, detailed_explanation = self._generate_friendly_explanation(
            rejection_reasons, rule_failures, applicant_context
        )
        
        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(
            rejection_reasons, rule_failures, applicant_context, ml_score
        )
        
        # Generate quick wins
        quick_wins = self._generate_quick_wins(suggestions, applicant_context)
        
        # Estimate eligibility timeline
        estimated_date, timeline_message = self._estimate_eligibility_timeline(
            suggestions, applicant_context
        )
        
        # Generate immediate actions
        immediate_actions = self._generate_immediate_actions(suggestions, applicant_context)
        
        # Generate follow-up options
        follow_up_options = self._generate_follow_up_options(applicant_context)
        
        # Generate factors summary (friendly language)
        factors_summary = self._generate_factors_summary(rejection_reasons, rule_failures)
        
        # Get encouragement and support messages
        encouragement = self._get_encouragement_message(applicant_context)
        support_message = self._get_support_message()
        
        return SoftRejectResponse(
            greeting=greeting,
            acknowledgment=acknowledgment,
            outcome="not_approved_this_time",
            outcome_message=self._generate_outcome_message(applicant_context),
            primary_reason=primary_reason,
            detailed_explanation=detailed_explanation,
            factors_summary=factors_summary,
            improvement_suggestions=suggestions,
            quick_wins=quick_wins,
            estimated_eligibility_date=estimated_date,
            eligibility_timeline=timeline_message,
            encouragement_message=encouragement,
            immediate_actions=immediate_actions,
            follow_up_options=follow_up_options,
            support_message=support_message,
            contact_options=[
                "📧 Email our support team for personalized guidance",
                "📞 Call our helpline for immediate assistance",
                "💬 Chat with us on our website",
                "📅 Schedule a free financial consultation"
            ],
            application_id=application_id
        )
    
    def _get_greeting(self, name: Optional[str]) -> str:
        """Get time-appropriate personalized greeting."""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            time_greeting = self.GREETINGS["morning"]
        elif 12 <= hour < 17:
            time_greeting = self.GREETINGS["afternoon"]
        else:
            time_greeting = self.GREETINGS["evening"]
        
        if name:
            return f"{time_greeting}, {name}! 👋"
        return f"{time_greeting}! 👋"
    
    def _get_acknowledgment(self, context: ApplicantContext) -> str:
        """Get personalized acknowledgment."""
        import random
        base = random.choice(self.ACKNOWLEDGMENTS)
        
        if context.is_first_time_applicant:
            return f"{base} We're honored to be part of your financial journey."
        elif context.previous_rejection_count > 0:
            return f"{base} We truly appreciate your persistence and determination."
        return base
    
    def _generate_outcome_message(self, context: ApplicantContext) -> str:
        """Generate friendly outcome message."""
        if context.loan_purpose:
            return (
                f"After carefully reviewing your application for a {context.loan_purpose.lower()} loan, "
                f"we're unable to approve it at this time. But this isn't the end of your journey – "
                f"it's an opportunity to strengthen your profile for future success."
            )
        return (
            "After carefully reviewing your application, we're unable to approve it at this time. "
            "But don't be discouraged – we've identified clear steps you can take to improve "
            "your chances for the future."
        )
    
    def _generate_friendly_explanation(
        self,
        rejection_reasons: List[Dict[str, Any]],
        rule_failures: Optional[List[Dict[str, Any]]],
        context: ApplicantContext
    ) -> Tuple[str, str]:
        """Generate friendly, non-technical explanation of rejection."""
        
        # Analyze main factors
        primary_issues = []
        
        if rule_failures:
            for failure in rule_failures:
                rule_id = failure.get('rule_id', '')
                
                if 'AGE' in rule_id:
                    primary_issues.append('age_requirement')
                elif 'INC' in rule_id:
                    primary_issues.append('income')
                elif 'KYC' in rule_id:
                    primary_issues.append('documentation')
                elif 'EMP' in rule_id:
                    primary_issues.append('employment')
                elif 'CIB' in rule_id or 'CIBIL' in rule_id:
                    primary_issues.append('credit_score')
                elif 'DTI' in rule_id:
                    primary_issues.append('debt_level')
        
        # Generate primary reason (friendly)
        if 'credit_score' in primary_issues:
            primary_reason = "Your credit history needs a bit more building"
            detailed = (
                "Credit scores are like a financial report card – they tell lenders how you've "
                "managed borrowed money in the past. Your current score suggests there's room "
                "to grow, which is completely normal and something many people work on successfully."
            )
        elif 'income' in primary_issues:
            primary_reason = "The loan amount is currently a bit high for your income level"
            detailed = (
                "We want to make sure any loan you take on is comfortable to repay. "
                "Right now, the requested amount would put too much pressure on your monthly budget. "
                "This is actually about protecting you from financial stress."
            )
        elif 'debt_level' in primary_issues:
            primary_reason = "Your current debt obligations are a bit high"
            detailed = (
                "You're currently managing some existing debts, and adding more right now "
                "might stretch your budget too thin. Reducing some current obligations first "
                "will put you in a much stronger position."
            )
        elif 'employment' in primary_issues:
            primary_reason = "Your employment history is still building"
            detailed = (
                "Lenders like to see stable employment history as it indicates steady income. "
                "You're on the right track – just a bit more time in your current role will "
                "make a big difference to your application strength."
            )
        elif 'documentation' in primary_issues:
            primary_reason = "Some documentation needs to be completed"
            detailed = (
                "We need to verify your identity and financial information to process your loan. "
                "This is a quick fix – once you complete the required verification, you'll be "
                "one step closer to approval."
            )
        elif 'age_requirement' in primary_issues:
            primary_reason = "Age eligibility criteria weren't met"
            detailed = (
                "Our lending policies have age requirements to ensure responsible lending. "
                "This is a temporary situation – time is on your side!"
            )
        else:
            primary_reason = "A combination of factors affected this decision"
            detailed = (
                "Several aspects of your financial profile need strengthening for loan approval. "
                "The good news? Each of these can be improved with the right approach. "
                "We've outlined exactly what you can do below."
            )
        
        return primary_reason, detailed
    
    def _generate_improvement_suggestions(
        self,
        rejection_reasons: List[Dict[str, Any]],
        rule_failures: Optional[List[Dict[str, Any]]],
        context: ApplicantContext,
        ml_score: Optional[float]
    ) -> List[ImprovementSuggestion]:
        """Generate personalized improvement suggestions."""
        suggestions = []
        
        # Credit Score Improvements
        if context.cibil_score and context.cibil_score < 700:
            suggestions.append(ImprovementSuggestion(
                category=ImprovementCategory.CREDIT_SCORE,
                title="Build Your Credit Score 📈",
                description=(
                    "Your credit score is like your financial reputation. "
                    "Here's how to boost it steadily and sustainably."
                ),
                action_steps=[
                    "Pay all existing bills and EMIs on time – this is the #1 factor",
                    "Keep credit card usage below 30% of your limit",
                    "Don't close old credit accounts – they show history",
                    "Check your credit report for errors and dispute any mistakes",
                    "Avoid applying for multiple new credits at once"
                ],
                expected_impact=f"Could improve score by 50-100 points over 6-12 months",
                estimated_time="3-12 months",
                priority=ImprovementPriority.HIGH,
                difficulty=ImprovementDifficulty.MODERATE,
                resources=[
                    "Free credit report from CIBIL/Experian",
                    "Credit improvement guides online",
                    "Financial wellness apps"
                ],
                current_value=context.cibil_score,
                target_value=700
            ))
        
        # Income Enhancement
        if context.income and context.loan_amount_requested:
            if float(context.loan_amount_requested) > float(context.income) * 60:
                suggestions.append(ImprovementSuggestion(
                    category=ImprovementCategory.INCOME,
                    title="Strengthen Your Income Profile 💼",
                    description=(
                        "A higher or more diversified income makes you a stronger borrower. "
                        "Here are practical ways to enhance your earning power."
                    ),
                    action_steps=[
                        "Consider a side income through freelancing or part-time work",
                        "Document all income sources properly with bank statements",
                        "If married, consider a joint application with spouse's income",
                        "Ask your employer for a salary certificate or increment letter",
                        "Report any rental income or investment returns"
                    ],
                    expected_impact="Higher income directly increases loan eligibility",
                    estimated_time="Immediate to 6 months",
                    priority=ImprovementPriority.HIGH,
                    difficulty=ImprovementDifficulty.MODERATE,
                    resources=[
                        "Freelancing platforms",
                        "Skill development courses",
                        "Income documentation checklist"
                    ],
                    current_value=float(context.income) if context.income else None,
                    target_value=float(context.loan_amount_requested) / 48 if context.loan_amount_requested else None
                ))
        
        # Debt Reduction
        if context.existing_debt > 0:
            dti = float(context.existing_debt / context.income * 100) if context.income else 0
            if dti > 40:
                suggestions.append(ImprovementSuggestion(
                    category=ImprovementCategory.DEBT_REDUCTION,
                    title="Lighten Your Debt Load 🎯",
                    description=(
                        "Reducing existing debt frees up your budget and shows lenders "
                        "you can handle new obligations responsibly."
                    ),
                    action_steps=[
                        "List all debts and prioritize high-interest ones first",
                        "Consider debt consolidation for lower interest rates",
                        "Make extra payments on smallest debts (debt snowball method)",
                        "Avoid taking on new debt while paying down existing ones",
                        "Negotiate with lenders for better repayment terms"
                    ],
                    expected_impact=f"Reducing DTI from {dti:.0f}% to below 40% significantly improves approval chances",
                    estimated_time="3-12 months",
                    priority=ImprovementPriority.HIGH,
                    difficulty=ImprovementDifficulty.MODERATE,
                    resources=[
                        "Debt reduction calculators",
                        "Financial counseling services",
                        "Debt consolidation options"
                    ],
                    current_value=f"{dti:.0f}%",
                    target_value="Below 40%"
                ))
        
        # Employment Stability
        if context.employment_years < 1:
            suggestions.append(ImprovementSuggestion(
                category=ImprovementCategory.EMPLOYMENT,
                title="Build Employment Stability 🏢",
                description=(
                    "Longer tenure at your job shows stability and reliable income. "
                    "Stay the course – time will work in your favor."
                ),
                action_steps=[
                    "Focus on excelling in your current role",
                    "Avoid job changes for the next 6-12 months if possible",
                    "Document any promotions or salary increases",
                    "Maintain good relationships with your employer",
                    "Keep all employment records organized"
                ],
                expected_impact="6+ months of employment significantly improves approval odds",
                estimated_time="6-12 months",
                priority=ImprovementPriority.MEDIUM,
                difficulty=ImprovementDifficulty.EASY,
                resources=[
                    "Career development resources",
                    "Professional certification programs"
                ],
                current_value=f"{context.employment_years:.1f} years",
                target_value="1+ years"
            ))
        
        # Loan Amount Adjustment
        suggestions.append(ImprovementSuggestion(
            category=ImprovementCategory.LOAN_ADJUSTMENT,
            title="Consider Adjusting Your Loan Request 📋",
            description=(
                "Sometimes a smaller loan amount or different terms can make the difference "
                "between rejection and approval."
            ),
            action_steps=[
                "Consider applying for a smaller loan amount",
                "Opt for a longer tenure to reduce EMI burden",
                "Provide collateral if you have assets (car, gold, FD)",
                "Add a co-applicant with good credit history",
                "Save for a larger down payment to reduce loan amount"
            ],
            expected_impact="A right-sized loan dramatically increases approval chances",
            estimated_time="Immediate",
            priority=ImprovementPriority.MEDIUM,
            difficulty=ImprovementDifficulty.EASY,
            resources=[
                "Loan EMI calculators",
                "Loan eligibility calculators",
                "Financial planning tools"
            ]
        ))
        
        # Savings Buffer
        suggestions.append(ImprovementSuggestion(
            category=ImprovementCategory.SAVINGS,
            title="Build Your Savings Cushion 💰",
            description=(
                "Having savings shows financial responsibility and gives you a buffer "
                "for emergencies, making you a lower-risk borrower."
            ),
            action_steps=[
                "Set up automatic monthly savings transfers",
                "Aim to save 3-6 months of expenses as emergency fund",
                "Consider fixed deposits for higher returns",
                "Track expenses and identify areas to cut",
                "Maintain consistent savings for 3+ months before reapplying"
            ],
            expected_impact="Demonstrates financial discipline to lenders",
            estimated_time="3-6 months",
            priority=ImprovementPriority.MEDIUM,
            difficulty=ImprovementDifficulty.MODERATE,
            resources=[
                "Budgeting apps",
                "Savings challenges",
                "High-yield savings accounts"
            ]
        ))
        
        # Sort by priority
        priority_order = {
            ImprovementPriority.CRITICAL: 0,
            ImprovementPriority.HIGH: 1,
            ImprovementPriority.MEDIUM: 2,
            ImprovementPriority.LOW: 3
        }
        suggestions.sort(key=lambda x: priority_order[x.priority])
        
        return suggestions[:6]  # Return top 6 most relevant
    
    def _generate_quick_wins(
        self,
        suggestions: List[ImprovementSuggestion],
        context: ApplicantContext
    ) -> List[str]:
        """Generate quick, actionable wins the applicant can do today."""
        quick_wins = [
            "✅ Check your credit report for free and look for errors",
            "✅ Set up auto-pay for all existing bills to avoid late payments",
            "✅ Calculate your monthly budget to identify savings opportunities"
        ]
        
        if context.cibil_score and context.cibil_score < 750:
            quick_wins.append("✅ Request a credit limit increase on existing cards (don't use it!)")
        
        quick_wins.append("✅ Gather all income documents (salary slips, bank statements)")
        quick_wins.append("✅ Complete any pending KYC verification")
        
        return quick_wins[:5]
    
    def _estimate_eligibility_timeline(
        self,
        suggestions: List[ImprovementSuggestion],
        context: ApplicantContext
    ) -> Tuple[Optional[datetime], str]:
        """Estimate when the applicant might become eligible."""
        
        # Analyze suggestion difficulties
        critical_suggestions = [s for s in suggestions if s.priority == ImprovementPriority.CRITICAL]
        high_suggestions = [s for s in suggestions if s.priority == ImprovementPriority.HIGH]
        
        # Estimate months needed
        months_needed = 3  # Base minimum
        
        if critical_suggestions:
            months_needed = 12
        elif len(high_suggestions) >= 2:
            months_needed = 9
        elif high_suggestions:
            months_needed = 6
        
        estimated_date = datetime.utcnow() + timedelta(days=months_needed * 30)
        
        if months_needed <= 3:
            timeline_message = (
                "With focused effort on the suggestions above, you could be ready to "
                "reapply in as little as 3 months! 🎯"
            )
        elif months_needed <= 6:
            timeline_message = (
                "If you follow our recommendations, you should be in a much stronger position "
                "to reapply within 6 months. We'll be happy to see your application again! 📅"
            )
        else:
            timeline_message = (
                "Building a stronger financial profile takes time, but it's worth it. "
                "Give yourself 9-12 months to implement these changes, and you'll be "
                "amazed at the progress. We're rooting for you! 🌟"
            )
        
        return estimated_date, timeline_message
    
    def _generate_immediate_actions(
        self,
        suggestions: List[ImprovementSuggestion],
        context: ApplicantContext
    ) -> List[str]:
        """Generate immediate action steps."""
        actions = [
            "📝 Download your free credit report and review it carefully",
            "📊 Create a simple monthly budget to track income and expenses",
            "🎯 Pick ONE improvement area to focus on first"
        ]
        
        if suggestions:
            top_suggestion = suggestions[0]
            if top_suggestion.action_steps:
                actions.append(f"⭐ Priority: {top_suggestion.action_steps[0]}")
        
        actions.append("📅 Set a calendar reminder to reapply in the recommended timeframe")
        
        return actions
    
    def _generate_follow_up_options(self, context: ApplicantContext) -> List[str]:
        """Generate follow-up options for the applicant."""
        options = [
            "🔔 Get notified when your profile improves enough for approval",
            "📚 Access our free financial literacy resources",
            "🤝 Connect with a financial advisor for personalized guidance",
            "📱 Track your improvement progress with our app"
        ]
        
        if context.loan_purpose:
            options.append(f"💡 Explore alternative financing options for your {context.loan_purpose.lower()}")
        
        return options
    
    def _generate_factors_summary(
        self,
        rejection_reasons: List[Dict[str, Any]],
        rule_failures: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """Generate friendly summary of factors."""
        factors = []
        
        if rule_failures:
            for failure in rule_failures[:4]:
                message = failure.get('message', failure.get('rule_name', 'Factor'))
                # Make it friendlier
                friendly_message = message.replace("must", "ideally should")
                friendly_message = friendly_message.replace("required", "needed")
                friendly_message = friendly_message.replace("failed", "needs attention")
                factors.append(f"📌 {friendly_message}")
        
        if not factors:
            factors.append("📌 Overall profile needs strengthening across multiple areas")
        
        return factors
    
    def _get_encouragement_message(self, context: ApplicantContext) -> str:
        """Get personalized encouragement message."""
        import random
        
        if context.previous_rejection_count > 1:
            return (
                "Your persistence is admirable! Many successful borrowers faced initial setbacks. "
                "Each application teaches us something new, and you're getting closer to your goal."
            )
        
        return random.choice(self.ENCOURAGEMENTS)
    
    def _get_support_message(self) -> str:
        """Get support message."""
        import random
        return random.choice(self.SUPPORT_MESSAGES)


# =============================================================================
# Factory Function
# =============================================================================

_soft_reject_service: Optional[SoftRejectService] = None


def get_soft_reject_service() -> SoftRejectService:
    """Get singleton soft reject service instance."""
    global _soft_reject_service
    if _soft_reject_service is None:
        _soft_reject_service = SoftRejectService()
    return _soft_reject_service
