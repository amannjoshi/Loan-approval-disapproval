"""
Data Privacy & Masking Utility
===============================
Professional data masking for sensitive personal information.

Masking Formats:
- PAN: ABCDE****F (show first 5, last 1)
- Aadhaar: ****-****-1234 (show last 4 only)
- Phone: ******6789 (show last 4)
- Email: a****z@domain.com (show first and last of local part)
- Name: A**** K**** (show first letter of each word)
- Account: ******1234 (show last 4)
- Card: ****-****-****-5678 (show last 4)

Author: Loan Analytics Team
Version: 1.0.0
"""

import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class DataType(str, Enum):
    """Types of sensitive data."""
    PAN = "pan"
    AADHAAR = "aadhaar"
    PHONE = "phone"
    EMAIL = "email"
    NAME = "name"
    ACCOUNT_NUMBER = "account"
    CREDIT_CARD = "card"
    ADDRESS = "address"
    DATE_OF_BIRTH = "dob"
    PASSPORT = "passport"
    VOTER_ID = "voter_id"
    DRIVING_LICENSE = "dl"
    IP_ADDRESS = "ip"
    GENERIC = "generic"


@dataclass
class MaskedData:
    """Result of masking operation."""
    original_type: DataType
    masked_value: str
    is_valid: bool
    format_preserved: bool


class DataMasker:
    """
    Professional data masking utility for sensitive information.
    
    Provides consistent, professional masking across all data types
    while preserving enough information for identification.
    """
    
    # Validation patterns
    PATTERNS = {
        DataType.PAN: re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$'),
        DataType.AADHAAR: re.compile(r'^\d{12}$|^\d{4}[\s-]?\d{4}[\s-]?\d{4}$'),
        DataType.PHONE: re.compile(r'^[\+]?[0-9]{10,13}$'),
        DataType.EMAIL: re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        DataType.CREDIT_CARD: re.compile(r'^\d{13,19}$|^[\d\s-]{13,23}$'),
        DataType.ACCOUNT_NUMBER: re.compile(r'^\d{9,18}$'),
    }
    
    def __init__(self, mask_char: str = "*"):
        """
        Initialize the data masker.
        
        Args:
            mask_char: Character to use for masking (default: *)
        """
        self.mask_char = mask_char
    
    # =========================================================================
    # Core Masking Methods
    # =========================================================================
    
    def mask_pan(self, pan: str) -> str:
        """
        Mask PAN number.
        
        Format: ABCDE****F (show first 5 and last 1)
        Example: ABCDE1234F → ABCDE****F
        
        Args:
            pan: PAN number to mask
            
        Returns:
            Masked PAN number
        """
        if not pan:
            return "[NO PAN]"
        
        # Clean the PAN
        clean_pan = pan.upper().strip()
        
        # Validate format
        if len(clean_pan) != 10:
            return self._generic_mask(clean_pan, show_first=4, show_last=1)
        
        # Professional format: ABCDE****F
        return f"{clean_pan[:5]}{self.mask_char * 4}{clean_pan[-1]}"
    
    def mask_aadhaar(self, aadhaar: str) -> str:
        """
        Mask Aadhaar number.
        
        Format: ****-****-1234 (show last 4 only)
        Example: 123456781234 → ****-****-1234
        
        Args:
            aadhaar: Aadhaar number to mask
            
        Returns:
            Masked Aadhaar number
        """
        if not aadhaar:
            return "[NO AADHAAR]"
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(aadhaar))
        
        if len(digits) != 12:
            return self._generic_mask(aadhaar, show_first=0, show_last=4)
        
        # Professional format: ****-****-1234
        return f"{self.mask_char * 4}-{self.mask_char * 4}-{digits[-4:]}"
    
    def mask_phone(self, phone: str) -> str:
        """
        Mask phone number.
        
        Format: ******6789 (show last 4)
        Example: 9876543210 → ******3210
        
        Args:
            phone: Phone number to mask
            
        Returns:
            Masked phone number
        """
        if not phone:
            return "[NO PHONE]"
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(phone))
        
        if len(digits) < 4:
            return self.mask_char * len(digits)
        
        # Show last 4 digits
        return self.mask_char * (len(digits) - 4) + digits[-4:]
    
    def mask_email(self, email: str) -> str:
        """
        Mask email address.
        
        Format: a****z@domain.com (show first and last of local part)
        Example: john.doe@email.com → j******e@email.com
        
        Args:
            email: Email address to mask
            
        Returns:
            Masked email address
        """
        if not email or '@' not in email:
            return "[INVALID EMAIL]"
        
        try:
            local, domain = email.rsplit('@', 1)
            
            if len(local) <= 2:
                masked_local = self.mask_char * len(local)
            else:
                masked_local = local[0] + self.mask_char * (len(local) - 2) + local[-1]
            
            return f"{masked_local}@{domain}"
        except Exception:
            return "[MASKED EMAIL]"
    
    def mask_name(self, name: str) -> str:
        """
        Mask person's name.
        
        Format: A**** K**** (show first letter of each word)
        Example: Amit Kumar → A*** K****
        
        Args:
            name: Name to mask
            
        Returns:
            Masked name
        """
        if not name:
            return "[NO NAME]"
        
        words = name.strip().split()
        masked_words = []
        
        for word in words:
            if len(word) <= 1:
                masked_words.append(self.mask_char)
            else:
                masked_words.append(word[0].upper() + self.mask_char * (len(word) - 1))
        
        return ' '.join(masked_words)
    
    def mask_account_number(self, account: str) -> str:
        """
        Mask bank account number.
        
        Format: ******1234 (show last 4)
        Example: 12345678901234 → **********1234
        
        Args:
            account: Account number to mask
            
        Returns:
            Masked account number
        """
        if not account:
            return "[NO ACCOUNT]"
        
        # Extract alphanumeric
        clean = re.sub(r'[^a-zA-Z0-9]', '', str(account))
        
        if len(clean) < 4:
            return self.mask_char * len(clean)
        
        return self.mask_char * (len(clean) - 4) + clean[-4:]
    
    def mask_credit_card(self, card: str) -> str:
        """
        Mask credit/debit card number.
        
        Format: ****-****-****-5678 (show last 4)
        Example: 4111111111111111 → ****-****-****-1111
        
        Args:
            card: Card number to mask
            
        Returns:
            Masked card number
        """
        if not card:
            return "[NO CARD]"
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(card))
        
        if len(digits) < 13:
            return self.mask_char * len(digits)
        
        # Format as ****-****-****-XXXX
        last_four = digits[-4:]
        return f"{self.mask_char * 4}-{self.mask_char * 4}-{self.mask_char * 4}-{last_four}"
    
    def mask_address(self, address: str) -> str:
        """
        Mask physical address.
        
        Format: Show only city/state, mask house/street details
        Example: 123 Main St, Mumbai, MH → ***, Mumbai, MH
        
        Args:
            address: Address to mask
            
        Returns:
            Masked address
        """
        if not address:
            return "[NO ADDRESS]"
        
        # Split by comma
        parts = [p.strip() for p in address.split(',')]
        
        if len(parts) <= 1:
            # Mask most of it, show last few chars
            return self._generic_mask(address, show_first=0, show_last=min(10, len(address) // 3))
        
        # Mask first part (house/street), show city/state
        masked_parts = [self.mask_char * 3 + '...'] + parts[1:]
        return ', '.join(masked_parts)
    
    def mask_dob(self, dob: str) -> str:
        """
        Mask date of birth.
        
        Format: **/**/1990 (show only year)
        Example: 15/08/1990 → **/**/1990
        
        Args:
            dob: Date of birth to mask
            
        Returns:
            Masked date of birth
        """
        if not dob:
            return "[NO DOB]"
        
        # Try to extract year (assuming it's 4 digits)
        year_match = re.search(r'(19|20)\d{2}', str(dob))
        
        if year_match:
            year = year_match.group()
            return f"{self.mask_char * 2}/{self.mask_char * 2}/{year}"
        
        return f"{self.mask_char * 2}/{self.mask_char * 2}/{self.mask_char * 4}"
    
    def mask_ip_address(self, ip: str) -> str:
        """
        Mask IP address.
        
        Format: 192.168.***.*** (show first two octets)
        Example: 192.168.1.100 → 192.168.*.*
        
        Args:
            ip: IP address to mask
            
        Returns:
            Masked IP address
        """
        if not ip:
            return "[NO IP]"
        
        # IPv4
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{self.mask_char}.{self.mask_char}"
        
        # IPv6 or other
        return self._generic_mask(ip, show_first=4, show_last=0)
    
    def _generic_mask(self, value: str, show_first: int = 0, show_last: int = 4) -> str:
        """
        Generic masking for unknown data types.
        
        Args:
            value: Value to mask
            show_first: Number of characters to show at start
            show_last: Number of characters to show at end
            
        Returns:
            Masked value
        """
        if not value:
            return "[MASKED]"
        
        value = str(value)
        length = len(value)
        
        if length <= show_first + show_last:
            return self.mask_char * length
        
        mask_length = length - show_first - show_last
        return value[:show_first] + self.mask_char * mask_length + value[-show_last:] if show_last else value[:show_first] + self.mask_char * mask_length
    
    # =========================================================================
    # Auto-Detection & Smart Masking
    # =========================================================================
    
    def detect_and_mask(self, value: Any, field_name: str = "") -> str:
        """
        Auto-detect data type and apply appropriate masking.
        
        Args:
            value: Value to mask
            field_name: Optional field name for context
            
        Returns:
            Masked value
        """
        if value is None:
            return "[EMPTY]"
        
        str_value = str(value).strip()
        normalized_field = field_name.lower().replace('_', '').replace('-', '').replace(' ', '')
        
        # Field name based detection
        if any(x in normalized_field for x in ['pan', 'pannumber', 'panno', 'pancard']):
            return self.mask_pan(str_value)
        
        if any(x in normalized_field for x in ['aadhaar', 'aadhar', 'uid', 'uidai']):
            return self.mask_aadhaar(str_value)
        
        if any(x in normalized_field for x in ['phone', 'mobile', 'cell', 'contact', 'tel']):
            return self.mask_phone(str_value)
        
        if any(x in normalized_field for x in ['email', 'mail', 'emailid']):
            return self.mask_email(str_value)
        
        if any(x in normalized_field for x in ['name', 'fullname', 'firstname', 'lastname']):
            return self.mask_name(str_value)
        
        if any(x in normalized_field for x in ['account', 'accountno', 'acctno', 'bankaccount']):
            return self.mask_account_number(str_value)
        
        if any(x in normalized_field for x in ['card', 'creditcard', 'debitcard', 'cardno']):
            return self.mask_credit_card(str_value)
        
        if any(x in normalized_field for x in ['address', 'addr', 'street', 'location']):
            return self.mask_address(str_value)
        
        if any(x in normalized_field for x in ['dob', 'dateofbirth', 'birthdate', 'birthday']):
            return self.mask_dob(str_value)
        
        if any(x in normalized_field for x in ['ip', 'ipaddress', 'ipaddr']):
            return self.mask_ip_address(str_value)
        
        # Pattern-based detection
        if self.PATTERNS[DataType.PAN].match(str_value.upper()):
            return self.mask_pan(str_value)
        
        if self.PATTERNS[DataType.EMAIL].match(str_value):
            return self.mask_email(str_value)
        
        if self.PATTERNS[DataType.AADHAAR].match(re.sub(r'\D', '', str_value)):
            return self.mask_aadhaar(str_value)
        
        # Default: generic mask
        return self._generic_mask(str_value, show_first=2, show_last=2)
    
    def mask_dict(self, data: Dict[str, Any], pii_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Mask PII fields in a dictionary.
        
        Args:
            data: Dictionary to mask
            pii_fields: Optional list of field names to mask (auto-detect if None)
            
        Returns:
            Dictionary with masked values
        """
        if not data:
            return data
        
        # Default PII field names
        default_pii = {
            'pan', 'pan_number', 'panno', 'pan_no',
            'aadhaar', 'aadhar', 'aadhaar_number', 'aadhar_number', 'uid',
            'phone', 'mobile', 'phone_number', 'mobile_number', 'contact',
            'email', 'email_id', 'emailid', 'email_address',
            'name', 'full_name', 'first_name', 'last_name', 'applicant_name',
            'account', 'account_number', 'account_no', 'bank_account',
            'card', 'card_number', 'credit_card', 'debit_card',
            'address', 'street', 'home_address', 'residence',
            'dob', 'date_of_birth', 'birthdate',
            'ip', 'ip_address',
            'ssn', 'passport', 'voter_id', 'driving_license'
        }
        
        fields_to_mask = set(pii_fields) if pii_fields else default_pii
        
        result = {}
        for key, value in data.items():
            normalized_key = key.lower().replace('-', '_').replace(' ', '_')
            
            if normalized_key in fields_to_mask or any(pii in normalized_key for pii in fields_to_mask):
                result[key] = self.detect_and_mask(value, key)
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value, pii_fields)
            elif isinstance(value, list):
                result[key] = self.mask_list(value, pii_fields)
            else:
                result[key] = value
        
        return result
    
    def mask_list(self, data: List[Any], pii_fields: Optional[List[str]] = None) -> List[Any]:
        """
        Mask PII in a list of items.
        
        Args:
            data: List to process
            pii_fields: Optional list of field names to mask
            
        Returns:
            List with masked values
        """
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(self.mask_dict(item, pii_fields))
            elif isinstance(item, list):
                result.append(self.mask_list(item, pii_fields))
            else:
                result.append(item)
        return result


# =============================================================================
# Convenience Functions & Singleton
# =============================================================================

_default_masker: Optional[DataMasker] = None


def get_data_masker() -> DataMasker:
    """Get the default data masker instance."""
    global _default_masker
    if _default_masker is None:
        _default_masker = DataMasker()
    return _default_masker


# Quick masking functions
def mask_pan(pan: str) -> str:
    """Mask PAN: ABCDE****F"""
    return get_data_masker().mask_pan(pan)


def mask_aadhaar(aadhaar: str) -> str:
    """Mask Aadhaar: ****-****-1234"""
    return get_data_masker().mask_aadhaar(aadhaar)


def mask_phone(phone: str) -> str:
    """Mask Phone: ******6789"""
    return get_data_masker().mask_phone(phone)


def mask_email(email: str) -> str:
    """Mask Email: a****z@domain.com"""
    return get_data_masker().mask_email(email)


def mask_name(name: str) -> str:
    """Mask Name: A**** K****"""
    return get_data_masker().mask_name(name)


def mask_account(account: str) -> str:
    """Mask Account: ******1234"""
    return get_data_masker().mask_account_number(account)


def mask_card(card: str) -> str:
    """Mask Card: ****-****-****-5678"""
    return get_data_masker().mask_credit_card(card)


def mask_sensitive(value: Any, field_name: str = "") -> str:
    """Auto-detect and mask sensitive data."""
    return get_data_masker().detect_and_mask(value, field_name)


def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask all PII in a dictionary."""
    return get_data_masker().mask_dict(data)


# =============================================================================
# Display Helpers for API Responses
# =============================================================================

class MaskedDisplay:
    """Helper class for creating masked display values in API responses."""
    
    @staticmethod
    def pan(pan: str) -> Dict[str, str]:
        """
        Return masked PAN with display format.
        
        Returns:
            {"masked": "ABCDE****F", "last_char": "F"}
        """
        masked = mask_pan(pan)
        return {
            "masked": masked,
            "last_char": pan[-1] if pan else "",
            "format": "PAN"
        }
    
    @staticmethod
    def aadhaar(aadhaar: str) -> Dict[str, str]:
        """
        Return masked Aadhaar with display format.
        
        Returns:
            {"masked": "****-****-1234", "last_four": "1234"}
        """
        masked = mask_aadhaar(aadhaar)
        digits = re.sub(r'\D', '', str(aadhaar))
        return {
            "masked": masked,
            "last_four": digits[-4:] if len(digits) >= 4 else "",
            "format": "AADHAAR"
        }
    
    @staticmethod
    def phone(phone: str) -> Dict[str, str]:
        """
        Return masked phone with display format.
        
        Returns:
            {"masked": "******6789", "last_four": "6789"}
        """
        masked = mask_phone(phone)
        digits = re.sub(r'\D', '', str(phone))
        return {
            "masked": masked,
            "last_four": digits[-4:] if len(digits) >= 4 else "",
            "format": "PHONE"
        }
    
    @staticmethod
    def email(email: str) -> Dict[str, str]:
        """
        Return masked email with display format.
        
        Returns:
            {"masked": "a****z@domain.com", "domain": "domain.com"}
        """
        masked = mask_email(email)
        domain = email.split('@')[-1] if '@' in email else ""
        return {
            "masked": masked,
            "domain": domain,
            "format": "EMAIL"
        }
    
    @staticmethod
    def applicant_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a masked summary for applicant display.
        
        Args:
            data: Raw applicant data
            
        Returns:
            Masked summary suitable for display
        """
        masker = get_data_masker()
        
        summary = {
            "name": masker.mask_name(data.get('name', data.get('full_name', ''))),
            "pan": masker.mask_pan(data.get('pan', data.get('pan_number', ''))),
            "aadhaar": masker.mask_aadhaar(data.get('aadhaar', data.get('aadhaar_number', ''))),
            "phone": masker.mask_phone(data.get('phone', data.get('mobile', ''))),
            "email": masker.mask_email(data.get('email', data.get('email_id', '')))
        }
        
        # Include non-sensitive fields as-is
        for key in ['age', 'gender', 'city', 'state', 'loan_amount', 'loan_status']:
            if key in data:
                summary[key] = data[key]
        
        return summary
