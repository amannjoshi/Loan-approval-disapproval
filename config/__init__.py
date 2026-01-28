"""
Configuration Package for Loan Approval System
===============================================
Centralized configuration management for the application.

Includes:
- System configuration
- Security settings (JWT, HTTPS, Rate Limiting)
- Model configuration
- Feature definitions
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

from .security import (
    SecuritySettings,
    get_security_settings,
    PII_FIELDS,
    PARTIAL_MASK_FIELDS
)

# Default system configuration
default_config = SystemConfig()

__all__ = [
    # System Configuration
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
    'default_config',
    
    # Security Configuration
    'SecuritySettings',
    'get_security_settings',
    'PII_FIELDS',
    'PARTIAL_MASK_FIELDS',
]
