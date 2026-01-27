"""
Custom Exceptions for Loan Approval System
==========================================
Centralized exception handling with detailed error categorization.

Author: Loan Analytics Team
Version: 1.0.0
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors in the system."""
    VALIDATION = "validation"
    MODEL = "model"
    DATA = "data"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    SECURITY = "security"
    BUSINESS_RULE = "business_rule"
    EXTERNAL = "external"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Contextual information about an error."""
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = "unknown"
    operation: str = "unknown"
    user_id: Optional[str] = None
    application_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class LoanApprovalBaseException(Exception):
    """
    Base exception for all loan approval system errors.
    
    Provides structured error information for logging and API responses.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            'error': True,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'timestamp': self.context.timestamp.isoformat(),
            'component': self.context.component,
            'operation': self.context.operation,
            'application_id': self.context.application_id,
            'request_id': self.context.request_id
        }
    
    def __str__(self) -> str:
        return f"[{self.category.value.upper()}] {self.message}"


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationException(LoanApprovalBaseException):
    """Base exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Any = None,
        expected_format: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.expected_format = expected_format
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            context=context
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'field': self.field_name,
            'invalid_value': str(self.invalid_value) if self.invalid_value else None,
            'expected_format': self.expected_format
        })
        return result


class InvalidFieldException(ValidationException):
    """Exception for invalid field values."""
    pass


class MissingFieldException(ValidationException):
    """Exception for missing required fields."""
    
    def __init__(self, field_name: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Required field '{field_name}' is missing",
            field_name=field_name,
            context=context
        )


class OutOfRangeException(ValidationException):
    """Exception for values outside allowed range."""
    
    def __init__(
        self,
        field_name: str,
        value: Any,
        min_value: Any = None,
        max_value: Any = None,
        context: Optional[ErrorContext] = None
    ):
        range_str = ""
        if min_value is not None and max_value is not None:
            range_str = f"between {min_value} and {max_value}"
        elif min_value is not None:
            range_str = f"at least {min_value}"
        elif max_value is not None:
            range_str = f"at most {max_value}"
        
        super().__init__(
            message=f"Field '{field_name}' value {value} is out of range. Expected {range_str}",
            field_name=field_name,
            invalid_value=value,
            expected_format=range_str,
            context=context
        )
        self.min_value = min_value
        self.max_value = max_value


class InvalidCategoricalValueException(ValidationException):
    """Exception for invalid categorical values."""
    
    def __init__(
        self,
        field_name: str,
        value: Any,
        allowed_values: List[str],
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Field '{field_name}' has invalid value '{value}'. Allowed: {allowed_values}",
            field_name=field_name,
            invalid_value=value,
            expected_format=f"One of: {allowed_values}",
            context=context
        )
        self.allowed_values = allowed_values


# ============================================================================
# Model Exceptions
# ============================================================================

class ModelException(LoanApprovalBaseException):
    """Base exception for model-related errors."""
    
    def __init__(
        self,
        message: str,
        model_id: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        self.model_id = model_id
        super().__init__(
            message=message,
            category=ErrorCategory.MODEL,
            severity=ErrorSeverity.ERROR,
            context=context,
            original_exception=original_exception
        )


class ModelNotTrainedException(ModelException):
    """Exception when trying to use an untrained model."""
    
    def __init__(self, context: Optional[ErrorContext] = None):
        super().__init__(
            message="Model has not been trained. Please train the model first.",
            context=context
        )


class ModelLoadException(ModelException):
    """Exception when failing to load a model."""
    
    def __init__(
        self,
        filepath: str,
        reason: str,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=f"Failed to load model from '{filepath}': {reason}",
            context=context,
            original_exception=original_exception
        )
        self.filepath = filepath


class ModelPredictionException(ModelException):
    """Exception during model prediction."""
    
    def __init__(
        self,
        reason: str,
        model_id: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=f"Prediction failed: {reason}",
            model_id=model_id,
            context=context,
            original_exception=original_exception
        )


class ExplainerException(ModelException):
    """Exception during SHAP explanation generation."""
    
    def __init__(
        self,
        reason: str,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=f"Failed to generate explanation: {reason}",
            context=context,
            original_exception=original_exception
        )


# ============================================================================
# Data Exceptions
# ============================================================================

class DataException(LoanApprovalBaseException):
    """Base exception for data-related errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.ERROR,
            context=context,
            original_exception=original_exception
        )


class DataQualityException(DataException):
    """Exception for data quality issues."""
    
    def __init__(
        self,
        message: str,
        issues: List[str],
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"{message}: {issues}",
            context=context
        )
        self.issues = issues


class InsufficientDataException(DataException):
    """Exception when there's not enough data for an operation."""
    
    def __init__(
        self,
        required: int,
        available: int,
        operation: str = "operation",
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Insufficient data for {operation}. Required: {required}, Available: {available}",
            context=context
        )
        self.required = required
        self.available = available


# ============================================================================
# Business Rule Exceptions
# ============================================================================

class BusinessRuleException(LoanApprovalBaseException):
    """Base exception for business rule violations."""
    
    def __init__(
        self,
        message: str,
        rule_name: str,
        context: Optional[ErrorContext] = None
    ):
        self.rule_name = rule_name
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_RULE,
            severity=ErrorSeverity.WARNING,
            context=context
        )


class EligibilityException(BusinessRuleException):
    """Exception when applicant doesn't meet eligibility criteria."""
    
    def __init__(
        self,
        reason: str,
        criteria: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Eligibility check failed: {reason}",
            rule_name=criteria,
            context=context
        )


class PolicyViolationException(BusinessRuleException):
    """Exception when application violates lending policies."""
    
    def __init__(
        self,
        policy: str,
        violation_details: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Policy violation - {policy}: {violation_details}",
            rule_name=policy,
            context=context
        )


# ============================================================================
# Security Exceptions
# ============================================================================

class SecurityException(LoanApprovalBaseException):
    """Base exception for security-related issues."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )


class InputSanitizationException(SecurityException):
    """Exception when malicious input is detected."""
    
    def __init__(
        self,
        field_name: str,
        threat_type: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Potential {threat_type} detected in field '{field_name}'",
            context=context
        )
        self.field_name = field_name
        self.threat_type = threat_type


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationException(LoanApprovalBaseException):
    """Base exception for configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        self.config_key = config_key
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.ERROR,
            context=context
        )


class MissingConfigurationException(ConfigurationException):
    """Exception when required configuration is missing."""
    
    def __init__(
        self,
        config_key: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Required configuration '{config_key}' is missing",
            config_key=config_key,
            context=context
        )


class InvalidConfigurationException(ConfigurationException):
    """Exception when configuration value is invalid."""
    
    def __init__(
        self,
        config_key: str,
        value: Any,
        expected: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=f"Invalid configuration for '{config_key}': {value}. Expected: {expected}",
            config_key=config_key,
            context=context
        )


# ============================================================================
# Exception Handler
# ============================================================================

class ExceptionHandler:
    """
    Centralized exception handler for the loan approval system.
    
    Provides consistent error handling, logging, and response formatting.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def handle(self, exception: Exception, context: Optional[ErrorContext] = None) -> Dict[str, Any]:
        """
        Handle an exception and return a standardized response.
        
        Parameters:
        -----------
        exception : Exception
            The exception to handle
        context : ErrorContext, optional
            Additional context about the error
            
        Returns:
        --------
        dict
            Standardized error response
        """
        if isinstance(exception, LoanApprovalBaseException):
            error_response = exception.to_dict()
        else:
            # Wrap unknown exceptions
            error_response = {
                'error': True,
                'message': str(exception),
                'category': ErrorCategory.SYSTEM.value,
                'severity': ErrorSeverity.ERROR.value,
                'timestamp': datetime.now().isoformat(),
                'component': context.component if context else 'unknown',
                'operation': context.operation if context else 'unknown'
            }
        
        # Log the error
        if self.logger:
            log_message = f"[{error_response['category']}] {error_response['message']}"
            
            if error_response['severity'] == ErrorSeverity.CRITICAL.value:
                self.logger.critical(log_message)
            elif error_response['severity'] == ErrorSeverity.ERROR.value:
                self.logger.error(log_message)
            elif error_response['severity'] == ErrorSeverity.WARNING.value:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
        
        return error_response
    
    def is_recoverable(self, exception: Exception) -> bool:
        """Check if an exception is recoverable."""
        non_recoverable = (
            ConfigurationException,
            SecurityException,
            ModelLoadException
        )
        return not isinstance(exception, non_recoverable)
