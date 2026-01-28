"""
PII Redaction Utility
=====================
Utilities for masking and redacting Personally Identifiable Information (PII)
from logs, responses, and data exports.

Features:
- Field-level PII detection
- Multiple masking strategies
- Pattern-based detection
- Configurable redaction

Author: Loan Analytics Team
Version: 1.0.0
"""

import re
import hashlib
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum

from config.security import PII_FIELDS, PARTIAL_MASK_FIELDS, get_security_settings


class MaskingStrategy(Enum):
    """Masking strategies for PII data."""
    FULL = "full"           # Complete redaction: ***REDACTED***
    PARTIAL = "partial"     # Partial mask: joh****@email.com
    HASH = "hash"           # One-way hash: abc123def...
    TOKENIZE = "tokenize"   # Replace with token: [PII_TOKEN_123]
    TRUNCATE = "truncate"   # Show first/last chars: J***e


@dataclass
class RedactionConfig:
    """Configuration for PII redaction."""
    strategy: MaskingStrategy = MaskingStrategy.PARTIAL
    hash_algorithm: str = "sha256"
    preserve_format: bool = True
    show_field_type: bool = True
    mask_char: str = "*"


class PIIRedactor:
    """
    PII Redaction utility for removing sensitive data from logs and outputs.
    
    Features:
    - Automatic PII field detection
    - Multiple masking strategies
    - Pattern-based detection for unknown fields
    - Nested dictionary/list support
    """
    
    # Patterns for detecting PII in unknown fields
    PII_PATTERNS = {
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        'phone': re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{4,10}'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),
        'aadhaar': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        'pan': re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'),
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'date_of_birth': re.compile(r'\b(?:\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})\b'),
    }
    
    def __init__(self, config: Optional[RedactionConfig] = None):
        """Initialize the PII redactor."""
        self.config = config or RedactionConfig()
        self.settings = get_security_settings()
        self._custom_pii_fields: Set[str] = set()
    
    def add_pii_field(self, field_name: str) -> None:
        """Add a custom PII field to track."""
        self._custom_pii_fields.add(field_name.lower())
    
    def is_pii_field(self, field_name: str) -> bool:
        """Check if a field name is a known PII field."""
        normalized = field_name.lower().replace('-', '_').replace(' ', '_')
        return (
            normalized in PII_FIELDS or 
            normalized in self._custom_pii_fields or
            any(pii in normalized for pii in ['name', 'email', 'phone', 'address', 'ssn', 'password', 'secret'])
        )
    
    def should_partial_mask(self, field_name: str) -> bool:
        """Check if field should be partially masked."""
        normalized = field_name.lower().replace('-', '_').replace(' ', '_')
        return normalized in PARTIAL_MASK_FIELDS
    
    def mask_value(self, value: Any, field_name: str = "", strategy: Optional[MaskingStrategy] = None) -> str:
        """
        Mask a PII value based on the configured strategy.
        
        Args:
            value: The value to mask
            field_name: Optional field name for context
            strategy: Override strategy for this value
            
        Returns:
            Masked string representation
        """
        if value is None:
            return "[REDACTED]"
        
        str_value = str(value)
        use_strategy = strategy or self.config.strategy
        
        # Determine masking based on strategy
        if use_strategy == MaskingStrategy.FULL:
            return self._full_mask(str_value, field_name)
        elif use_strategy == MaskingStrategy.PARTIAL:
            return self._partial_mask(str_value, field_name)
        elif use_strategy == MaskingStrategy.HASH:
            return self._hash_mask(str_value)
        elif use_strategy == MaskingStrategy.TOKENIZE:
            return self._tokenize_mask(str_value, field_name)
        elif use_strategy == MaskingStrategy.TRUNCATE:
            return self._truncate_mask(str_value)
        else:
            return self._full_mask(str_value, field_name)
    
    def _full_mask(self, value: str, field_name: str = "") -> str:
        """Completely redact the value."""
        if self.config.show_field_type and field_name:
            return f"[REDACTED:{field_name.upper()}]"
        return "[REDACTED]"
    
    def _partial_mask(self, value: str, field_name: str = "") -> str:
        """Partially mask the value, preserving some format."""
        normalized_field = field_name.lower()
        
        # Email masking: j***@domain.com
        if 'email' in normalized_field or '@' in value:
            match = self.PII_PATTERNS['email'].search(value)
            if match:
                email = match.group()
                local, domain = email.rsplit('@', 1)
                if len(local) > 2:
                    masked_local = local[0] + self.config.mask_char * (len(local) - 2) + local[-1]
                else:
                    masked_local = self.config.mask_char * len(local)
                return f"{masked_local}@{domain}"
        
        # Phone masking: ***-***-1234
        if 'phone' in normalized_field or 'mobile' in normalized_field:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return self.config.mask_char * (len(digits) - 4) + digits[-4:]
        
        # Credit card masking: ****-****-****-1234
        if 'card' in normalized_field or 'credit' in normalized_field:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return self.config.mask_char * (len(digits) - 4) + digits[-4:]
        
        # SSN/Aadhaar masking: ***-**-1234
        if any(x in normalized_field for x in ['ssn', 'aadhaar', 'pan']):
            alphanums = re.sub(r'[^a-zA-Z0-9]', '', value)
            if len(alphanums) >= 4:
                return self.config.mask_char * (len(alphanums) - 4) + alphanums[-4:]
        
        # Name masking: J*** D***
        if 'name' in normalized_field:
            words = value.split()
            masked_words = []
            for word in words:
                if len(word) > 1:
                    masked_words.append(word[0] + self.config.mask_char * (len(word) - 1))
                else:
                    masked_words.append(self.config.mask_char)
            return ' '.join(masked_words)
        
        # Default partial masking
        if len(value) > 4:
            visible = max(1, len(value) // 4)
            return value[:visible] + self.config.mask_char * (len(value) - visible * 2) + value[-visible:]
        
        return self.config.mask_char * len(value)
    
    def _hash_mask(self, value: str) -> str:
        """Hash the value for consistent pseudonymization."""
        hash_obj = hashlib.new(self.config.hash_algorithm)
        hash_obj.update(value.encode('utf-8'))
        return f"[HASH:{hash_obj.hexdigest()[:12]}]"
    
    def _tokenize_mask(self, value: str, field_name: str = "") -> str:
        """Replace with a token identifier."""
        hash_obj = hashlib.sha256(value.encode('utf-8'))
        token_id = hash_obj.hexdigest()[:8]
        if field_name:
            return f"[{field_name.upper()}_TOKEN_{token_id}]"
        return f"[PII_TOKEN_{token_id}]"
    
    def _truncate_mask(self, value: str) -> str:
        """Show only first and last characters."""
        if len(value) <= 2:
            return self.config.mask_char * len(value)
        return value[0] + self.config.mask_char * (len(value) - 2) + value[-1]
    
    def detect_pii_patterns(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII patterns in free text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of detected PII types and their matches
        """
        detected = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                detected[pii_type] = matches
        return detected
    
    def redact_text(self, text: str) -> str:
        """
        Redact all detected PII patterns from free text.
        
        Args:
            text: Text to redact
            
        Returns:
            Text with PII redacted
        """
        result = text
        for pii_type, pattern in self.PII_PATTERNS.items():
            result = pattern.sub(f'[REDACTED:{pii_type.upper()}]', result)
        return result
    
    def redact_dict(self, data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
        """
        Redact PII fields from a dictionary.
        
        Args:
            data: Dictionary to redact
            deep: Whether to recursively redact nested structures
            
        Returns:
            Dictionary with PII redacted
        """
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            if self.is_pii_field(key):
                # Determine masking strategy based on field
                if self.should_partial_mask(key):
                    result[key] = self.mask_value(value, key, MaskingStrategy.PARTIAL)
                else:
                    result[key] = self.mask_value(value, key, MaskingStrategy.FULL)
            elif deep and isinstance(value, dict):
                result[key] = self.redact_dict(value, deep=True)
            elif deep and isinstance(value, list):
                result[key] = self.redact_list(value, deep=True)
            elif isinstance(value, str):
                # Check for PII patterns in string values
                detected = self.detect_pii_patterns(value)
                if detected:
                    result[key] = self.redact_text(value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def redact_list(self, data: List[Any], deep: bool = True) -> List[Any]:
        """
        Redact PII from a list.
        
        Args:
            data: List to redact
            deep: Whether to recursively redact nested structures
            
        Returns:
            List with PII redacted
        """
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(self.redact_dict(item, deep=deep))
            elif isinstance(item, list):
                result.append(self.redact_list(item, deep=deep))
            elif isinstance(item, str):
                detected = self.detect_pii_patterns(item)
                if detected:
                    result.append(self.redact_text(item))
                else:
                    result.append(item)
            else:
                result.append(item)
        return result


# =============================================================================
# Convenience Functions
# =============================================================================

_default_redactor: Optional[PIIRedactor] = None


def get_redactor() -> PIIRedactor:
    """Get the default PII redactor instance."""
    global _default_redactor
    if _default_redactor is None:
        _default_redactor = PIIRedactor()
    return _default_redactor


def redact_pii(data: Union[Dict, List, str]) -> Union[Dict, List, str]:
    """
    Convenience function to redact PII from any data structure.
    
    Args:
        data: Data to redact (dict, list, or string)
        
    Returns:
        Data with PII redacted
    """
    redactor = get_redactor()
    
    if isinstance(data, dict):
        return redactor.redact_dict(data)
    elif isinstance(data, list):
        return redactor.redact_list(data)
    elif isinstance(data, str):
        return redactor.redact_text(data)
    else:
        return data


def mask_field(value: Any, field_name: str, strategy: MaskingStrategy = MaskingStrategy.PARTIAL) -> str:
    """
    Mask a single field value.
    
    Args:
        value: Value to mask
        field_name: Name of the field
        strategy: Masking strategy to use
        
    Returns:
        Masked value
    """
    return get_redactor().mask_value(value, field_name, strategy)


def is_pii(field_name: str) -> bool:
    """Check if a field name is a PII field."""
    return get_redactor().is_pii_field(field_name)
