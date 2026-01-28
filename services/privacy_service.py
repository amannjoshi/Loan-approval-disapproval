"""
Privacy Service
================
Centralized service for data privacy and PII protection.

Provides:
- Automatic PII detection and masking
- Privacy-safe logging
- Data export sanitization
- API response masking
- Audit trail with masked data

Author: Loan Analytics Team
Version: 1.0.0
"""

import logging
import json
import re
from typing import Any, Dict, List, Optional, Set, Callable
from functools import wraps
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from utils.data_masking import (
    DataMasker,
    get_data_masker,
    mask_pan,
    mask_aadhaar,
    mask_phone,
    mask_email,
    mask_name,
    mask_dict,
    MaskedDisplay
)


logger = logging.getLogger(__name__)


class PrivacyLevel(str, Enum):
    """Privacy levels for data handling."""
    PUBLIC = "public"           # No masking needed
    INTERNAL = "internal"       # Basic masking for internal use
    CONFIDENTIAL = "confidential"  # Full masking for external exposure
    RESTRICTED = "restricted"   # Maximum protection, no data exposure


class DataCategory(str, Enum):
    """Categories of sensitive data."""
    IDENTITY = "identity"       # PAN, Aadhaar, Passport
    CONTACT = "contact"         # Phone, Email, Address
    FINANCIAL = "financial"     # Account, Card, Income
    PERSONAL = "personal"       # Name, DOB, Gender
    HEALTH = "health"           # Medical records
    BIOMETRIC = "biometric"     # Fingerprint, Face ID


@dataclass
class PrivacyConfig:
    """Configuration for privacy handling."""
    default_level: PrivacyLevel = PrivacyLevel.CONFIDENTIAL
    mask_in_logs: bool = True
    mask_in_responses: bool = True
    audit_access: bool = True
    allowed_plain_fields: Set[str] = field(default_factory=set)
    
    # Field-specific privacy levels
    field_levels: Dict[str, PrivacyLevel] = field(default_factory=lambda: {
        'pan': PrivacyLevel.RESTRICTED,
        'aadhaar': PrivacyLevel.RESTRICTED,
        'password': PrivacyLevel.RESTRICTED,
        'phone': PrivacyLevel.CONFIDENTIAL,
        'email': PrivacyLevel.CONFIDENTIAL,
        'name': PrivacyLevel.INTERNAL,
        'address': PrivacyLevel.CONFIDENTIAL,
        'account_number': PrivacyLevel.RESTRICTED,
        'card_number': PrivacyLevel.RESTRICTED,
    })


class PrivacyService:
    """
    Centralized privacy management service.
    
    Handles all PII protection across the application.
    """
    
    # PII field patterns for auto-detection
    PII_FIELD_PATTERNS = {
        'pan': r'pan|pan_number|pan_no|pan_card',
        'aadhaar': r'aadhaar|aadhar|uid|uidai',
        'phone': r'phone|mobile|cell|contact|tel',
        'email': r'email|mail|email_id|email_address',
        'name': r'^name$|full_name|first_name|last_name|applicant_name',
        'account': r'account|acc_no|bank_account|acct',
        'card': r'card|credit_card|debit_card|card_no',
        'address': r'address|street|addr|residence|location',
        'dob': r'dob|date_of_birth|birthdate|birthday',
        'password': r'password|passwd|pwd|secret|token',
    }
    
    def __init__(self, config: Optional[PrivacyConfig] = None):
        """
        Initialize the privacy service.
        
        Args:
            config: Privacy configuration settings
        """
        self.config = config or PrivacyConfig()
        self.masker = get_data_masker()
        self._access_log: List[Dict] = []
    
    # =========================================================================
    # Core Privacy Methods
    # =========================================================================
    
    def is_pii_field(self, field_name: str) -> bool:
        """
        Check if a field name indicates PII data.
        
        Args:
            field_name: Name of the field to check
            
        Returns:
            True if field likely contains PII
        """
        normalized = field_name.lower().replace('-', '_').replace(' ', '_')
        
        for pii_type, pattern in self.PII_FIELD_PATTERNS.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        
        return normalized in self.config.allowed_plain_fields is False and any([
            'id' in normalized and len(normalized) > 3,  # Avoid 'id' alone
            'number' in normalized,
            'secret' in normalized,
            'key' in normalized and 'primary' not in normalized,
        ])
    
    def get_privacy_level(self, field_name: str) -> PrivacyLevel:
        """
        Get the privacy level for a field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Privacy level for the field
        """
        normalized = field_name.lower().replace('-', '_').replace(' ', '_')
        
        for config_field, level in self.config.field_levels.items():
            if config_field in normalized or normalized in config_field:
                return level
        
        return self.config.default_level if self.is_pii_field(field_name) else PrivacyLevel.PUBLIC
    
    def mask_value(
        self,
        value: Any,
        field_name: str = "",
        level: Optional[PrivacyLevel] = None
    ) -> str:
        """
        Mask a value based on its type and privacy level.
        
        Args:
            value: Value to mask
            field_name: Field name for context
            level: Override privacy level
            
        Returns:
            Masked value
        """
        if value is None:
            return "[EMPTY]"
        
        actual_level = level or self.get_privacy_level(field_name)
        
        if actual_level == PrivacyLevel.PUBLIC:
            return str(value)
        
        if actual_level == PrivacyLevel.RESTRICTED:
            # For restricted data, show minimal info
            return self._restricted_mask(value, field_name)
        
        # Standard masking for confidential/internal
        return self.masker.detect_and_mask(value, field_name)
    
    def _restricted_mask(self, value: Any, field_name: str) -> str:
        """Apply restricted-level masking (maximum protection)."""
        normalized = field_name.lower()
        
        if 'password' in normalized or 'secret' in normalized or 'token' in normalized:
            return "[REDACTED]"
        
        if 'pan' in normalized:
            return mask_pan(str(value))
        
        if 'aadhaar' in normalized or 'aadhar' in normalized:
            return mask_aadhaar(str(value))
        
        # For other restricted fields, show very limited info
        str_val = str(value)
        if len(str_val) > 4:
            return "*" * (len(str_val) - 2) + str_val[-2:]
        return "*" * len(str_val)
    
    # =========================================================================
    # Data Structure Masking
    # =========================================================================
    
    def sanitize_dict(
        self,
        data: Dict[str, Any],
        level: Optional[PrivacyLevel] = None,
        preserve_fields: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Sanitize a dictionary by masking PII fields.
        
        Args:
            data: Dictionary to sanitize
            level: Override privacy level for all fields
            preserve_fields: Fields to not mask
            
        Returns:
            Sanitized dictionary
        """
        if not data:
            return data
        
        preserve = preserve_fields or self.config.allowed_plain_fields
        result = {}
        
        for key, value in data.items():
            if key in preserve:
                result[key] = value
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value, level, preserve_fields)
            elif isinstance(value, list):
                result[key] = self.sanitize_list(value, level, preserve_fields)
            elif self.is_pii_field(key):
                result[key] = self.mask_value(value, key, level)
            else:
                result[key] = value
        
        return result
    
    def sanitize_list(
        self,
        data: List[Any],
        level: Optional[PrivacyLevel] = None,
        preserve_fields: Optional[Set[str]] = None
    ) -> List[Any]:
        """Sanitize a list by masking PII in nested structures."""
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(self.sanitize_dict(item, level, preserve_fields))
            elif isinstance(item, list):
                result.append(self.sanitize_list(item, level, preserve_fields))
            else:
                result.append(item)
        return result
    
    # =========================================================================
    # Logging Integration
    # =========================================================================
    
    def safe_log(self, data: Any, level: str = "info") -> str:
        """
        Create a safe log message with PII masked.
        
        Args:
            data: Data to log
            level: Log level
            
        Returns:
            Masked log string
        """
        if isinstance(data, dict):
            sanitized = self.sanitize_dict(data, PrivacyLevel.CONFIDENTIAL)
            return json.dumps(sanitized, default=str, indent=2)
        elif isinstance(data, list):
            sanitized = self.sanitize_list(data, PrivacyLevel.CONFIDENTIAL)
            return json.dumps(sanitized, default=str, indent=2)
        elif isinstance(data, str):
            return self._mask_text(data)
        else:
            return str(data)
    
    def _mask_text(self, text: str) -> str:
        """Mask PII patterns in free text."""
        # PAN pattern
        text = re.sub(
            r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
            lambda m: mask_pan(m.group()),
            text
        )
        
        # Aadhaar pattern
        text = re.sub(
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            lambda m: mask_aadhaar(m.group()),
            text
        )
        
        # Phone pattern
        text = re.sub(
            r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b',
            lambda m: mask_phone(m.group()),
            text
        )
        
        # Email pattern
        text = re.sub(
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            lambda m: mask_email(m.group()),
            text
        )
        
        return text
    
    # =========================================================================
    # API Response Helpers
    # =========================================================================
    
    def create_safe_response(
        self,
        data: Dict[str, Any],
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Create a privacy-safe API response.
        
        Args:
            data: Response data to sanitize
            include_metadata: Whether to include privacy metadata
            
        Returns:
            Safe response with masked PII
        """
        sanitized = self.sanitize_dict(data, PrivacyLevel.CONFIDENTIAL)
        
        if include_metadata:
            sanitized['_privacy'] = {
                'masked': True,
                'timestamp': datetime.now().isoformat(),
                'level': 'confidential'
            }
        
        return sanitized
    
    def create_applicant_display(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a masked applicant display for UI.
        
        Args:
            applicant_data: Raw applicant data
            
        Returns:
            Masked display-safe data
        """
        return {
            'display': MaskedDisplay.applicant_summary(applicant_data),
            'identifiers': {
                'pan': MaskedDisplay.pan(applicant_data.get('pan', '')),
                'aadhaar': MaskedDisplay.aadhaar(applicant_data.get('aadhaar', '')),
                'phone': MaskedDisplay.phone(applicant_data.get('phone', '')),
                'email': MaskedDisplay.email(applicant_data.get('email', '')),
            },
            'verified': applicant_data.get('verified', False),
            'application_id': applicant_data.get('application_id', '')
        }
    
    # =========================================================================
    # Export & Audit
    # =========================================================================
    
    def prepare_export(
        self,
        data: List[Dict[str, Any]],
        purpose: str = "analytics"
    ) -> List[Dict[str, Any]]:
        """
        Prepare data for export with appropriate masking.
        
        Args:
            data: Data to export
            purpose: Purpose of export (determines masking level)
            
        Returns:
            Export-safe data
        """
        level_map = {
            'analytics': PrivacyLevel.CONFIDENTIAL,
            'audit': PrivacyLevel.INTERNAL,
            'public': PrivacyLevel.RESTRICTED,
            'internal': PrivacyLevel.INTERNAL,
        }
        
        level = level_map.get(purpose, PrivacyLevel.RESTRICTED)
        
        return self.sanitize_list(data, level)
    
    def log_data_access(
        self,
        user_id: str,
        data_type: str,
        fields_accessed: List[str],
        purpose: str
    ):
        """
        Log data access for audit purposes.
        
        Args:
            user_id: User who accessed the data
            data_type: Type of data accessed
            fields_accessed: Fields that were accessed
            purpose: Reason for access
        """
        access_record = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'data_type': data_type,
            'fields': fields_accessed,
            'purpose': purpose,
            'pii_fields': [f for f in fields_accessed if self.is_pii_field(f)]
        }
        
        self._access_log.append(access_record)
        
        if self.config.audit_access:
            logger.info(f"Data access logged: {json.dumps(access_record)}")


# =============================================================================
# Decorator for Automatic Privacy Protection
# =============================================================================

def privacy_protected(
    level: PrivacyLevel = PrivacyLevel.CONFIDENTIAL,
    preserve_fields: Optional[Set[str]] = None
):
    """
    Decorator to automatically mask PII in function return values.
    
    Args:
        level: Privacy level to apply
        preserve_fields: Fields to exclude from masking
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            service = get_privacy_service()
            
            if isinstance(result, dict):
                return service.sanitize_dict(result, level, preserve_fields)
            elif isinstance(result, list):
                return service.sanitize_list(result, level, preserve_fields)
            else:
                return result
        
        return wrapper
    return decorator


# =============================================================================
# Singleton Instance
# =============================================================================

_privacy_service: Optional[PrivacyService] = None


def get_privacy_service(config: Optional[PrivacyConfig] = None) -> PrivacyService:
    """Get the global privacy service instance."""
    global _privacy_service
    if _privacy_service is None:
        _privacy_service = PrivacyService(config)
    return _privacy_service


def configure_privacy(config: PrivacyConfig):
    """Configure the global privacy service."""
    global _privacy_service
    _privacy_service = PrivacyService(config)


# =============================================================================
# Quick Access Functions
# =============================================================================

def mask_for_log(data: Any) -> str:
    """Quick function to mask data for logging."""
    return get_privacy_service().safe_log(data)


def mask_for_display(data: Dict[str, Any]) -> Dict[str, Any]:
    """Quick function to mask data for UI display."""
    return get_privacy_service().sanitize_dict(data)


def mask_applicant(applicant: Dict[str, Any]) -> Dict[str, Any]:
    """Quick function to mask applicant data."""
    return get_privacy_service().create_applicant_display(applicant)


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field contains sensitive data."""
    return get_privacy_service().is_pii_field(field_name)
