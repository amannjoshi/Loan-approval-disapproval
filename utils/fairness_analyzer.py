"""
Fairness & Bias Analysis Module
================================
This module provides tools for detecting and measuring bias in
loan approval decisions across different demographic groups.

Key metrics implemented:
- Demographic Parity
- Equalized Odds
- Disparate Impact Ratio
- Statistical Parity Difference

Author: Loan Analytics Team
Last Updated: January 2026
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


class FairnessAnalyzer:
    """
    Analyzes machine learning model predictions for bias and fairness.
    
    This class helps banks ensure their loan approval AI models comply
    with fair lending regulations and don't discriminate against
    protected groups.
    """
    
    def __init__(self, predictions: np.ndarray, actuals: np.ndarray, 
                 protected_attributes: pd.DataFrame):
        """
        Initialize the fairness analyzer.
        
        Parameters:
        -----------
        predictions : np.ndarray
            Model predictions (0 or 1)
        actuals : np.ndarray
            Actual outcomes (0 or 1)
        protected_attributes : pd.DataFrame
            DataFrame with protected attribute columns (gender, age group, etc.)
        """
        self.predictions = predictions
        self.actuals = actuals
        self.protected_attrs = protected_attributes
        
    def demographic_parity(self, attribute: str) -> Dict:
        """
        Calculate demographic parity (statistical parity).
        
        Measures whether the probability of positive prediction is
        the same across different groups.
        
        A fair model should have similar approval rates across groups.
        
        Parameters:
        -----------
        attribute : str
            Protected attribute to analyze
            
        Returns:
        --------
        dict
            Approval rates per group and parity metrics
        """
        groups = self.protected_attrs[attribute].unique()
        group_rates = {}
        
        for group in groups:
            mask = self.protected_attrs[attribute] == group
            approval_rate = self.predictions[mask].mean()
            group_rates[group] = {
                'approval_rate': float(approval_rate),
                'sample_size': int(mask.sum()),
                'approved_count': int(self.predictions[mask].sum())
            }
        
        # Calculate max disparity
        rates = [g['approval_rate'] for g in group_rates.values()]
        max_rate = max(rates)
        min_rate = min(rates)
        
        disparity = max_rate - min_rate
        
        # Disparate impact ratio (80% rule)
        # Should be >= 0.8 for fair model
        disparate_impact = min_rate / max_rate if max_rate > 0 else 0
        
        return {
            'attribute': attribute,
            'group_metrics': group_rates,
            'max_disparity': float(disparity),
            'disparate_impact_ratio': float(disparate_impact),
            'passes_80_percent_rule': disparate_impact >= 0.8,
            'fairness_assessment': self._assess_disparity(disparity)
        }
    
    def equalized_odds(self, attribute: str) -> Dict:
        """
        Calculate equalized odds metric.
        
        Measures whether the model has equal true positive rates
        and false positive rates across groups.
        
        Parameters:
        -----------
        attribute : str
            Protected attribute to analyze
            
        Returns:
        --------
        dict
            TPR and FPR per group and equalized odds metrics
        """
        groups = self.protected_attrs[attribute].unique()
        group_metrics = {}
        
        for group in groups:
            mask = self.protected_attrs[attribute] == group
            
            # True positives and actual positives
            actual_pos = self.actuals[mask] == 1
            pred_pos = self.predictions[mask] == 1
            
            # True Positive Rate (Recall)
            tpr = (pred_pos & actual_pos).sum() / actual_pos.sum() if actual_pos.sum() > 0 else 0
            
            # False Positive Rate
            actual_neg = self.actuals[mask] == 0
            fpr = (pred_pos & actual_neg).sum() / actual_neg.sum() if actual_neg.sum() > 0 else 0
            
            group_metrics[group] = {
                'true_positive_rate': float(tpr),
                'false_positive_rate': float(fpr),
                'sample_size': int(mask.sum())
            }
        
        # Calculate disparity in TPR and FPR
        tprs = [g['true_positive_rate'] for g in group_metrics.values()]
        fprs = [g['false_positive_rate'] for g in group_metrics.values()]
        
        tpr_disparity = max(tprs) - min(tprs)
        fpr_disparity = max(fprs) - min(fprs)
        
        return {
            'attribute': attribute,
            'group_metrics': group_metrics,
            'tpr_disparity': float(tpr_disparity),
            'fpr_disparity': float(fpr_disparity),
            'equalized_odds_satisfied': tpr_disparity < 0.1 and fpr_disparity < 0.1
        }
    
    def generate_fairness_report(self, attributes: List[str]) -> Dict:
        """
        Generate comprehensive fairness report for multiple attributes.
        
        Parameters:
        -----------
        attributes : list
            List of protected attributes to analyze
            
        Returns:
        --------
        dict
            Complete fairness analysis report
        """
        report = {
            'summary': {},
            'demographic_parity': {},
            'equalized_odds': {},
            'recommendations': []
        }
        
        overall_fair = True
        issues = []
        
        for attr in attributes:
            # Demographic parity analysis
            dp = self.demographic_parity(attr)
            report['demographic_parity'][attr] = dp
            
            if not dp['passes_80_percent_rule']:
                overall_fair = False
                issues.append(
                    f"Potential bias detected in '{attr}': "
                    f"Disparate impact ratio is {dp['disparate_impact_ratio']:.2%}"
                )
            
            # Equalized odds analysis
            eo = self.equalized_odds(attr)
            report['equalized_odds'][attr] = eo
            
            if not eo['equalized_odds_satisfied']:
                overall_fair = False
                issues.append(
                    f"Unequal error rates detected in '{attr}': "
                    f"TPR disparity: {eo['tpr_disparity']:.2%}, "
                    f"FPR disparity: {eo['fpr_disparity']:.2%}"
                )
        
        # Generate recommendations
        if not overall_fair:
            report['recommendations'].extend([
                "Consider retraining the model with bias mitigation techniques",
                "Review the features used - some may be proxies for protected attributes",
                "Implement ongoing monitoring for fairness metrics",
                "Consider using fairness-aware algorithms"
            ])
        else:
            report['recommendations'].append(
                "Model meets basic fairness criteria. Continue monitoring."
            )
        
        report['summary'] = {
            'overall_fair': overall_fair,
            'issues_found': len(issues),
            'issues': issues,
            'attributes_analyzed': attributes
        }
        
        return report
    
    def _assess_disparity(self, disparity: float) -> str:
        """Provide human-readable assessment of disparity level."""
        if disparity < 0.05:
            return "Excellent - Very low bias detected"
        elif disparity < 0.10:
            return "Good - Minimal bias detected"
        elif disparity < 0.15:
            return "Acceptable - Some bias present, monitor closely"
        elif disparity < 0.20:
            return "Concerning - Notable bias detected, review recommended"
        else:
            return "Poor - Significant bias detected, action required"
    
    def compare_similar_profiles(self, df: pd.DataFrame, 
                                 varying_attribute: str) -> pd.DataFrame:
        """
        Compare predictions for similar profiles that differ only
        in the specified attribute.
        
        This helps identify if the model treats similar applicants
        differently based on protected characteristics.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Full applicant data
        varying_attribute : str
            Attribute to vary while keeping others similar
            
        Returns:
        --------
        pd.DataFrame
            Comparison results
        """
        # Group by similar characteristics (excluding the varying attribute)
        grouping_cols = [
            'education', 'employment_type', 'cibil_score',
            'monthly_income', 'loan_amount'
        ]
        grouping_cols = [c for c in grouping_cols if c in df.columns and c != varying_attribute]
        
        # Bin numerical columns for grouping
        df_binned = df.copy()
        if 'cibil_score' in grouping_cols:
            df_binned['cibil_score'] = pd.cut(df['cibil_score'], 
                                               bins=[0, 600, 700, 800, 900],
                                               labels=['Poor', 'Fair', 'Good', 'Excellent'])
        if 'monthly_income' in grouping_cols:
            df_binned['monthly_income'] = pd.cut(df['monthly_income'],
                                                  bins=[0, 30000, 50000, 75000, 100000, float('inf')],
                                                  labels=['<30K', '30-50K', '50-75K', '75-100K', '>100K'])
        if 'loan_amount' in grouping_cols:
            df_binned['loan_amount'] = pd.cut(df['loan_amount'],
                                               bins=[0, 200000, 500000, 1000000, float('inf')],
                                               labels=['<2L', '2-5L', '5-10L', '>10L'])
        
        df_binned['predicted'] = self.predictions
        df_binned['varying_attr'] = df[varying_attribute]
        
        # Compare approval rates within similar groups
        comparison = df_binned.groupby(grouping_cols + ['varying_attr'])['predicted'].agg(['mean', 'count'])
        comparison.columns = ['approval_rate', 'sample_size']
        
        return comparison.reset_index()


def create_age_groups(ages: pd.Series) -> pd.Series:
    """Convert age to age groups for fairness analysis."""
    bins = [0, 25, 35, 45, 55, 100]
    labels = ['18-25', '26-35', '36-45', '46-55', '55+']
    return pd.cut(ages, bins=bins, labels=labels)


def create_income_groups(incomes: pd.Series) -> pd.Series:
    """Convert income to income groups for fairness analysis."""
    bins = [0, 25000, 50000, 75000, 100000, float('inf')]
    labels = ['Below 25K', '25K-50K', '50K-75K', '75K-1L', 'Above 1L']
    return pd.cut(incomes, bins=bins, labels=labels)


def generate_fairness_summary_text(report: Dict) -> str:
    """
    Generate human-readable fairness summary.
    
    Parameters:
    -----------
    report : dict
        Output from generate_fairness_report()
        
    Returns:
    --------
    str
        Human-readable summary
    """
    lines = [
        "═" * 60,
        "         FAIRNESS & BIAS ANALYSIS REPORT",
        "═" * 60,
        ""
    ]
    
    summary = report['summary']
    status = "✅ PASSED" if summary['overall_fair'] else "⚠️ NEEDS REVIEW"
    
    lines.append(f"Overall Status: {status}")
    lines.append(f"Issues Found: {summary['issues_found']}")
    lines.append("")
    
    # Demographic parity details
    lines.append("─" * 60)
    lines.append("APPROVAL RATE BY DEMOGRAPHIC GROUP")
    lines.append("─" * 60)
    
    for attr, data in report['demographic_parity'].items():
        lines.append(f"\n{attr.upper()}:")
        for group, metrics in data['group_metrics'].items():
            rate = metrics['approval_rate'] * 100
            count = metrics['sample_size']
            lines.append(f"  {group}: {rate:.1f}% approval rate (n={count})")
        
        lines.append(f"  → Disparity: {data['max_disparity']*100:.1f}%")
        lines.append(f"  → Assessment: {data['fairness_assessment']}")
    
    # Issues and recommendations
    if summary['issues']:
        lines.append("")
        lines.append("─" * 60)
        lines.append("⚠️  IDENTIFIED ISSUES")
        lines.append("─" * 60)
        for issue in summary['issues']:
            lines.append(f"  • {issue}")
    
    lines.append("")
    lines.append("─" * 60)
    lines.append("📋 RECOMMENDATIONS")
    lines.append("─" * 60)
    for rec in report['recommendations']:
        lines.append(f"  • {rec}")
    
    lines.append("")
    lines.append("═" * 60)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the fairness analyzer
    import sys
    sys.path.append('..')
    from data.data_generator import generate_synthetic_data
    from models.loan_model import LoanApprovalModel
    
    print("Testing Fairness Analyzer...")
    
    # Generate data
    df = generate_synthetic_data(n_samples=3000)
    
    # Train model
    model = LoanApprovalModel()
    model.train(df)
    
    # Get predictions
    X = model.preprocess_data(df, is_training=False)
    predictions = model.model.predict(X)
    
    # Create protected attributes dataframe
    protected_attrs = pd.DataFrame({
        'gender': df['gender'],
        'age_group': create_age_groups(df['age']),
        'income_group': create_income_groups(df['monthly_income'])
    })
    
    # Analyze fairness
    analyzer = FairnessAnalyzer(predictions, df['loan_approved'].values, protected_attrs)
    report = analyzer.generate_fairness_report(['gender', 'age_group'])
    
    # Print summary
    print(generate_fairness_summary_text(report))
