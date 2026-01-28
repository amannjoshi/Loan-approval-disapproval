"""
Utilities Package for Loan Approval System
==========================================
Common utilities, validators, and helpers.

Includes:
- Input validation with security checks
- PII redaction for secure logging
- Data masking for privacy
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
from .data_masking import (
    DataMasker,
    DataType,
    MaskedData,
    MaskedDisplay,
    get_data_masker,
    mask_pan,
    mask_aadhaar,
    mask_phone,
    mask_email,
    mask_name,
    mask_account,
    mask_card,
    mask_sensitive,
    mask_dict
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
    
    # Data Masking
    'DataMasker',
    'DataType',
    'MaskedData',
    'MaskedDisplay',
    'get_data_masker',
    'mask_pan',
    'mask_aadhaar',
    'mask_phone',
    'mask_email',
    'mask_name',
    'mask_account',
    'mask_card',
    'mask_sensitive',
    'mask_dict',
    
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
