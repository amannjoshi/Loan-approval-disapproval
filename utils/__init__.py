"""
Utilities Package for Loan Approval System
==========================================
Common utilities, validators, and helpers.

Includes:
- Input validation with security checks
- PII redaction for secure logging
- Audit logging (PII-free)
- Fairness analysis
- Exception handling
"""

from .validators import InputValidator, ValidationResult, ValidationReport
from .audit_logger import AuditLogger, AuditEvent, AuditEventType, DecisionOutcome
from .fairness_analyzer import FairnessAnalyzer
from .pii_redactor import (
    PIIRedactor,
    MaskingStrategy,
    RedactionConfig,
    redact_pii,
    mask_field,
    is_pii,
    get_redactor
)
from .exceptions import (
    LoanApprovalBaseException,
    ValidationException,
    ModelException,
    DataException,
    BusinessRuleException,
    SecurityException,
    ConfigurationException,
    ErrorCategory,
    ErrorSeverity,
    ExceptionHandler
)

__all__ = [
    # Validators
    'InputValidator',
    'ValidationResult',
    'ValidationReport',
    
    # PII Redaction
    'PIIRedactor',
    'MaskingStrategy',
    'RedactionConfig',
    'redact_pii',
    'mask_field',
    'is_pii',
    'get_redactor',
    
    # Audit
    'AuditLogger',
    'AuditEvent',
    'AuditEventType',
    'DecisionOutcome',
    
    # Fairness
    'FairnessAnalyzer',
    
    # Exceptions
    'LoanApprovalBaseException',
    'ValidationException',
    'ModelException',
    'DataException',
    'BusinessRuleException',
    'SecurityException',
    'ConfigurationException',
    'ErrorCategory',
    'ErrorSeverity',
    'ExceptionHandler'
]
