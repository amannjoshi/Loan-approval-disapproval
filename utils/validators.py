"""
Input Validation Module
========================
Comprehensive validation for loan application data.
Ensures data integrity, security, and compliance.

Author: Loan Analytics Team
Version: 3.0.0
Last Updated: January 2026
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    field: str
    value: Any
    message: str
    severity: str = "error"  # error, warning, info
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report for an application."""
    is_valid: bool
    errors: List[ValidationResult] = field(default_factory=list)
    warnings: List[ValidationResult] = field(default_factory=list)
    sanitized_data: Optional[Dict] = None
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_error(self, result: ValidationResult):
        self.errors.append(result)
        self.is_valid = False
    
    def add_warning(self, result: ValidationResult):
        self.warnings.append(result)
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        if self.is_valid:
            if self.warnings:
                return f"✅ Valid with {len(self.warnings)} warning(s)"
            return "✅ All validations passed"
        return f"❌ Invalid: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"


class InputValidator:
    """
    Comprehensive input validation for loan applications.
    
    Features:
    - Type validation
    - Range validation
    - Business rule validation
    - Security sanitization
    - Cross-field validation
    """
    
    # Valid options for categorical fields
    VALID_GENDERS = {'Male', 'Female', 'Other'}
    VALID_EDUCATION = {'High School', 'Graduate', 'Post Graduate', 'Professional', 'Doctorate'}
    VALID_MARITAL_STATUS = {'Single', 'Married', 'Divorced', 'Widowed'}
    VALID_EMPLOYMENT_TYPES = {'Salaried', 'Self-Employed', 'Business Owner', 'Government', 'Retired', 'Unemployed'}
    VALID_INDUSTRIES = {
        'Information Technology', 'IT', 'Banking & Finance', 'Finance', 'Healthcare', 'Education',
        'Manufacturing', 'Retail', 'Real Estate', 'Hospitality', 'Agriculture',
        'Transportation', 'Telecommunications', 'Media & Entertainment', 'Government', 'Other'
    }
    VALID_LOAN_PURPOSES = {
        'Personal Expenses', 'Personal', 'Home Renovation', 'Home Improvement', 
        'Medical Emergency', 'Medical', 'Education', 'Wedding', 'Debt Consolidation', 
        'Business Expansion', 'Business', 'Vehicle Purchase', 'Vehicle',
        'Travel', 'Electronics/Appliances', 'Other'
    }

    
    # Numeric constraints
    CONSTRAINTS = {
        'age': {'min': 18, 'max': 70, 'type': int},
        'monthly_income': {'min': 10000, 'max': 50000000, 'type': (int, float)},
        'loan_amount': {'min': 25000, 'max': 10000000, 'type': (int, float)},
        'loan_tenure_months': {'min': 6, 'max': 120, 'type': int},
        'cibil_score': {'min': 300, 'max': 900, 'type': int},
        'existing_emi': {'min': 0, 'max': 5000000, 'type': (int, float)},
        'num_existing_loans': {'min': 0, 'max': 20, 'type': int},
        'num_dependents': {'min': 0, 'max': 15, 'type': int},
        'years_at_current_job': {'min': 0, 'max': 50, 'type': (int, float)},
        'credit_history_years': {'min': 0, 'max': 50, 'type': (int, float)},
        'late_payments_last_2_years': {'min': 0, 'max': 100, 'type': int},
        'savings_balance': {'min': 0, 'max': 100000000, 'type': (int, float)},
        'years_with_bank': {'min': 0, 'max': 50, 'type': (int, float)},
    }
    
    # SQL injection / XSS patterns to block - Comprehensive security patterns
    DANGEROUS_PATTERNS = [
        # XSS Patterns
        r'<script[^>]*>',
        r'</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<svg[^>]*onload',
        r'<img[^>]*onerror',
        r'data:text/html',
        r'expression\s*\(',
        
        # SQL Injection Patterns
        r'union\s+select',
        r'union\s+all\s+select',
        r'drop\s+table',
        r'drop\s+database',
        r'insert\s+into',
        r'delete\s+from',
        r'update\s+\w+\s+set',
        r'truncate\s+table',
        r'alter\s+table',
        r'exec\s*\(',
        r'execute\s*\(',
        r'xp_cmdshell',
        r'sp_executesql',
        r"'\s*or\s+'?1'?\s*=\s*'?1",
        r"'\s*or\s+''='",
        r';\s*--',
        r'/\*.*\*/',
        r';\s*$',
        r'waitfor\s+delay',
        r'benchmark\s*\(',
        r'sleep\s*\(',
        
        # Path Traversal
        r'\.\./\.\.',
        r'\.\.\\\.\.\\',
        r'%2e%2e%2f',
        r'%252e%252e%252f',
        
        # Command Injection
        r';\s*cat\s+',
        r';\s*ls\s+',
        r'\|\s*cat\s+',
        r'`.*`',
        r'\$\(.*\)',
        
        # LDAP Injection
        r'\)\s*\(\|',
        r'\)\s*\(&',
        r'\*\)\s*\(',
    ]
    
    def __init__(self):
        self.dangerous_pattern = re.compile(
            '|'.join(self.DANGEROUS_PATTERNS), 
            re.IGNORECASE
        )
    
    def validate_application(self, data: Dict) -> ValidationReport:
        """
        Validate a complete loan application.
        
        Parameters:
        -----------
        data : dict
            Application data dictionary
            
        Returns:
        --------
        ValidationReport
            Complete validation report
        """
        report = ValidationReport(is_valid=True)
        sanitized = {}
        
        try:
            # 1. Required fields check
            self._check_required_fields(data, report)
            
            if not report.is_valid:
                return report
            
            # 2. Individual field validation
            for field, value in data.items():
                result = self.validate_field(field, value)
                if result:
                    if result.severity == 'error':
                        report.add_error(result)
                    else:
                        report.add_warning(result)
                    
                    # Use sanitized value if available
                    if result.suggestion:
                        sanitized[field] = result.suggestion
                    elif result.is_valid:
                        sanitized[field] = self._sanitize_value(field, value)
                else:
                    sanitized[field] = self._sanitize_value(field, value)
            
            # 3. Cross-field validation (business rules)
            self._validate_business_rules(data, report)
            
            # 4. Security validation
            self._validate_security(data, report)
            
            report.sanitized_data = sanitized
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            report.add_error(ValidationResult(
                is_valid=False,
                field='_system',
                value=None,
                message=f"Validation system error: {str(e)}",
                severity='error'
            ))
        
        return report
    
    def validate_field(self, field: str, value: Any) -> Optional[ValidationResult]:
        """Validate a single field."""
        
        # Handle None values
        if value is None:
            return ValidationResult(
                is_valid=False,
                field=field,
                value=value,
                message=f"{field} cannot be empty",
                severity='error'
            )
        
        # Categorical field validation
        if field == 'gender':
            return self._validate_categorical(field, value, self.VALID_GENDERS)
        elif field == 'education':
            return self._validate_categorical(field, value, self.VALID_EDUCATION)
        elif field == 'marital_status':
            return self._validate_categorical(field, value, self.VALID_MARITAL_STATUS)
        elif field == 'employment_type':
            return self._validate_categorical(field, value, self.VALID_EMPLOYMENT_TYPES)
        elif field == 'industry':
            return self._validate_categorical(field, value, self.VALID_INDUSTRIES)
        elif field == 'loan_purpose':
            return self._validate_categorical(field, value, self.VALID_LOAN_PURPOSES)
        
        # Numeric field validation
        elif field in self.CONSTRAINTS:
            return self._validate_numeric(field, value)
        
        # Boolean field validation
        elif field in ['has_defaults', 'owns_property']:
            return self._validate_boolean(field, value)
        
        # String field validation
        elif field in ['applicant_name', 'city']:
            return self._validate_string(field, value)
        
        return None
    
    def _check_required_fields(self, data: Dict, report: ValidationReport):
        """Check that all required fields are present."""
        required_fields = [
            'age', 'gender', 'monthly_income', 'loan_amount',
            'cibil_score', 'employment_type'
        ]
        
        for field in required_fields:
            if field not in data or data[field] is None:
                report.add_error(ValidationResult(
                    is_valid=False,
                    field=field,
                    value=None,
                    message=f"Required field '{field}' is missing",
                    severity='error'
                ))
    
    def _validate_categorical(self, field: str, value: Any, 
                             valid_options: set) -> Optional[ValidationResult]:
        """Validate categorical field."""
        str_value = str(value).strip()
        
        # Case-insensitive matching
        value_lower = str_value.lower()
        for option in valid_options:
            if option.lower() == value_lower:
                return None  # Valid
        
        # Try fuzzy matching for suggestions
        closest = self._find_closest_match(str_value, valid_options)
        
        return ValidationResult(
            is_valid=False,
            field=field,
            value=value,
            message=f"Invalid {field}: '{value}'. Must be one of: {', '.join(sorted(valid_options))}",
            severity='error',
            suggestion=closest
        )
    
    def _validate_numeric(self, field: str, value: Any) -> Optional[ValidationResult]:
        """Validate numeric field."""
        constraints = self.CONSTRAINTS[field]
        
        # Type check
        try:
            if constraints['type'] == int:
                num_value = int(float(value))
            else:
                num_value = float(value)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field=field,
                value=value,
                message=f"{field} must be a valid number",
                severity='error'
            )
        
        # Range check
        min_val = constraints.get('min', float('-inf'))
        max_val = constraints.get('max', float('inf'))
        
        if num_value < min_val:
            return ValidationResult(
                is_valid=False,
                field=field,
                value=value,
                message=f"{field} must be at least {min_val}. Got: {num_value}",
                severity='error',
                suggestion=str(min_val)
            )
        
        if num_value > max_val:
            return ValidationResult(
                is_valid=False,
                field=field,
                value=value,
                message=f"{field} must be at most {max_val}. Got: {num_value}",
                severity='error',
                suggestion=str(max_val)
            )
        
        # Warning for edge cases
        if field == 'cibil_score' and num_value < 500:
            return ValidationResult(
                is_valid=True,
                field=field,
                value=value,
                message=f"Very low CIBIL score ({num_value}). Loan approval unlikely.",
                severity='warning'
            )
        
        if field == 'age' and (num_value < 21 or num_value > 60):
            return ValidationResult(
                is_valid=True,
                field=field,
                value=value,
                message=f"Age {num_value} is outside typical lending range (21-60)",
                severity='warning'
            )
        
        return None
    
    def _validate_boolean(self, field: str, value: Any) -> Optional[ValidationResult]:
        """Validate boolean field."""
        if isinstance(value, bool):
            return None
        
        # Accept string representations
        if isinstance(value, str):
            if value.lower() in ('true', 'yes', '1'):
                return None
            elif value.lower() in ('false', 'no', '0'):
                return None
        
        # Accept numeric 0/1
        if value in (0, 1):
            return None
        
        return ValidationResult(
            is_valid=False,
            field=field,
            value=value,
            message=f"{field} must be a boolean value (true/false)",
            severity='error'
        )
    
    def _validate_string(self, field: str, value: Any) -> Optional[ValidationResult]:
        """Validate string field."""
        if not isinstance(value, str):
            value = str(value)
        
        # Length check
        max_length = 100 if field == 'applicant_name' else 50
        if len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                field=field,
                value=value,
                message=f"{field} exceeds maximum length of {max_length}",
                severity='error',
                suggestion=value[:max_length]
            )
        
        # Dangerous content check
        if self.dangerous_pattern.search(value):
            return ValidationResult(
                is_valid=False,
                field=field,
                value=value,
                message=f"{field} contains potentially dangerous content",
                severity='error'
            )
        
        return None
    
    def _validate_business_rules(self, data: Dict, report: ValidationReport):
        """Validate business rules that span multiple fields."""
        
        # Rule 1: Loan amount vs Income
        if 'loan_amount' in data and 'monthly_income' in data:
            loan_amount = float(data['loan_amount'])
            monthly_income = float(data['monthly_income'])
            annual_income = monthly_income * 12
            
            if loan_amount > annual_income * 5:
                report.add_warning(ValidationResult(
                    is_valid=True,
                    field='loan_amount',
                    value=loan_amount,
                    message=f"Loan amount (₹{loan_amount:,.0f}) is more than 5x annual income (₹{annual_income:,.0f}). High risk application.",
                    severity='warning'
                ))
        
        # Rule 2: DTI check
        if 'existing_emi' in data and 'monthly_income' in data:
            existing_emi = float(data.get('existing_emi', 0))
            monthly_income = float(data['monthly_income'])
            
            if monthly_income > 0:
                dti = existing_emi / monthly_income
                if dti > 0.5:
                    report.add_warning(ValidationResult(
                        is_valid=True,
                        field='existing_emi',
                        value=existing_emi,
                        message=f"Debt-to-Income ratio ({dti:.1%}) exceeds 50%. May impact approval.",
                        severity='warning'
                    ))
        
        # Rule 3: Age at loan maturity
        if 'age' in data and 'loan_tenure_months' in data:
            age = int(data['age'])
            tenure_years = int(data.get('loan_tenure_months', 36)) / 12
            age_at_maturity = age + tenure_years
            
            if age_at_maturity > 65:
                report.add_warning(ValidationResult(
                    is_valid=True,
                    field='age',
                    value=age,
                    message=f"Applicant will be {age_at_maturity:.0f} at loan maturity. May require additional guarantees.",
                    severity='warning'
                ))
        
        # Rule 4: Employment stability
        if 'years_at_current_job' in data and 'employment_type' in data:
            years = float(data.get('years_at_current_job', 0))
            emp_type = data.get('employment_type', '')
            
            if emp_type in ('Salaried', 'Self-Employed') and years < 0.5:
                report.add_warning(ValidationResult(
                    is_valid=True,
                    field='years_at_current_job',
                    value=years,
                    message="Less than 6 months at current job. May impact approval for non-government applicants.",
                    severity='warning'
                ))
        
        # Rule 5: CIBIL vs Defaults consistency
        if 'cibil_score' in data and 'has_defaults' in data:
            cibil = int(data['cibil_score'])
            has_defaults = data.get('has_defaults', False)
            
            if has_defaults and cibil > 700:
                report.add_warning(ValidationResult(
                    is_valid=True,
                    field='cibil_score',
                    value=cibil,
                    message="Inconsistency detected: High CIBIL score with previous defaults. Verify credit report.",
                    severity='warning'
                ))
    
    def _validate_security(self, data: Dict, report: ValidationReport):
        """Security-focused validation."""
        for field, value in data.items():
            if isinstance(value, str) and self.dangerous_pattern.search(value):
                report.add_error(ValidationResult(
                    is_valid=False,
                    field=field,
                    value='[REDACTED]',
                    message=f"Security: Potentially dangerous input detected in {field}",
                    severity='error'
                ))
    
    def _sanitize_value(self, field: str, value: Any) -> Any:
        """Sanitize a field value."""
        if isinstance(value, str):
            # Remove leading/trailing whitespace
            value = value.strip()
            # Remove control characters
            value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\t')
        
        # Type coercion for numeric fields
        if field in self.CONSTRAINTS:
            constraints = self.CONSTRAINTS[field]
            try:
                if constraints['type'] == int:
                    return int(float(value))
                else:
                    return float(value)
            except (ValueError, TypeError):
                return value
        
        # Boolean coercion
        if field in ['has_defaults', 'owns_property']:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1')
            return bool(value)
        
        return value
    
    def _find_closest_match(self, value: str, options: set) -> Optional[str]:
        """Find closest matching option (simple edit distance)."""
        value_lower = value.lower()
        best_match = None
        best_score = 0
        
        for option in options:
            option_lower = option.lower()
            # Simple similarity: common characters
            common = sum(1 for c in value_lower if c in option_lower)
            score = common / max(len(value_lower), len(option_lower))
            
            if score > best_score and score > 0.5:
                best_score = score
                best_match = option
        
        return best_match


class DataFrameValidator:
    """Validate pandas DataFrames for batch processing."""
    
    def __init__(self):
        self.validator = InputValidator()
    
    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[ValidationReport]]:
        """
        Validate all rows in a DataFrame.
        
        Returns:
        --------
        Tuple of (valid_rows_df, list_of_reports)
        """
        reports = []
        valid_indices = []
        
        for idx, row in df.iterrows():
            report = self.validator.validate_application(row.to_dict())
            reports.append(report)
            
            if report.is_valid:
                valid_indices.append(idx)
        
        valid_df = df.loc[valid_indices].copy() if valid_indices else pd.DataFrame()
        
        return valid_df, reports
    
    def get_validation_summary(self, reports: List[ValidationReport]) -> Dict:
        """Get summary statistics for batch validation."""
        total = len(reports)
        valid = sum(1 for r in reports if r.is_valid)
        with_warnings = sum(1 for r in reports if r.warnings)
        
        # Aggregate errors by field
        error_counts = {}
        for report in reports:
            for error in report.errors:
                error_counts[error.field] = error_counts.get(error.field, 0) + 1
        
        return {
            'total_records': total,
            'valid_records': valid,
            'invalid_records': total - valid,
            'records_with_warnings': with_warnings,
            'validation_rate': valid / total if total > 0 else 0,
            'error_breakdown': error_counts
        }


# Convenience function
def validate_loan_application(data: Dict) -> ValidationReport:
    """
    Validate a loan application.
    
    Parameters:
    -----------
    data : dict
        Application data
        
    Returns:
    --------
    ValidationReport
        Validation results
    """
    validator = InputValidator()
    return validator.validate_application(data)


if __name__ == "__main__":
    # Test validation
    test_data = {
        'applicant_name': 'Priya Sharma',
        'age': 28,
        'gender': 'Female',
        'city': 'Agra',
        'education': 'Graduate',
        'marital_status': 'Single',
        'num_dependents': 1,
        'employment_type': 'Salaried',
        'industry': 'Information Technology',
        'years_at_current_job': 3,
        'monthly_income': 45000,
        'existing_emi': 8000,
        'num_existing_loans': 1,
        'cibil_score': 680,
        'credit_history_years': 3,
        'late_payments_last_2_years': 2,
        'has_defaults': False,
        'owns_property': False,
        'savings_balance': 120000,
        'years_with_bank': 2,
        'loan_amount': 500000,
        'loan_tenure_months': 36,
        'loan_purpose': 'Personal Expenses'
    }
    
    report = validate_loan_application(test_data)
    print(f"Validation Result: {report.get_summary()}")
    
    if report.warnings:
        print("\nWarnings:")
        for w in report.warnings:
            print(f"  - {w.field}: {w.message}")
    
    if report.errors:
        print("\nErrors:")
        for e in report.errors:
            print(f"  - {e.field}: {e.message}")
