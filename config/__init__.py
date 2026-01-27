"""
Configuration Package for Loan Approval System
===============================================
Centralized configuration management for the application.
"""

from .settings import (
    SystemConfig,
    CreditScoreConfig,
    DebtToIncomeConfig,
    LoanAmountConfig,
    AgeConfig,
    EmploymentConfig,
    FairnessConfig,
    ModelConfig,
    ValidationConfig,
    AuditConfig,
    InterestRateConfig,
    RiskCategory,
    LoanStatus,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    BOOLEAN_FEATURES,
    ALL_FEATURES,
    FEATURE_DISPLAY_NAMES
)

# Default system configuration
default_config = SystemConfig()

__all__ = [
    'SystemConfig',
    'CreditScoreConfig',
    'DebtToIncomeConfig',
    'LoanAmountConfig',
    'AgeConfig',
    'EmploymentConfig',
    'FairnessConfig',
    'ModelConfig',
    'ValidationConfig',
    'AuditConfig',
    'InterestRateConfig',
    'RiskCategory',
    'LoanStatus',
    'CATEGORICAL_FEATURES',
    'NUMERICAL_FEATURES',
    'BOOLEAN_FEATURES',
    'ALL_FEATURES',
    'FEATURE_DISPLAY_NAMES',
    'default_config'
]
