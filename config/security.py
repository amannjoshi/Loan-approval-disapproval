"""
Security Configuration Module
==============================
Centralized security settings for the Loan Approval System.

Features:
- HTTPS/TLS configuration
- JWT token settings
- Password policies
- Rate limiting rules
- Security headers
- IP whitelist/blacklist

Author: Loan Analytics Team
Version: 1.0.0
"""

import os
from typing import List, Optional, Set
from pydantic_settings import BaseSettings
from pydantic import Field


class SecuritySettings(BaseSettings):
    """Security-related configuration."""
    
    # ==========================================================================
    # HTTPS/TLS Settings
    # ==========================================================================
    ssl_enabled: bool = Field(default=True, env="SSL_ENABLED")
    ssl_cert_path: str = Field(default="/etc/ssl/certs/server.crt", env="SSL_CERT_PATH")
    ssl_key_path: str = Field(default="/etc/ssl/private/server.key", env="SSL_KEY_PATH")
    ssl_ca_path: Optional[str] = Field(default=None, env="SSL_CA_PATH")
    force_https: bool = Field(default=True, env="FORCE_HTTPS")
    hsts_max_age: int = Field(default=31536000, env="HSTS_MAX_AGE")  # 1 year
    
    # ==========================================================================
    # JWT Settings
    # ==========================================================================
    jwt_secret_key: str = Field(
        default="change-this-in-production-use-at-least-256-bits-of-entropy",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=15, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    jwt_issuer: str = Field(default="loan-approval-system", env="JWT_ISSUER")
    jwt_audience: str = Field(default="loan-approval-api", env="JWT_AUDIENCE")
    jwt_token_blacklist_enabled: bool = Field(default=True, env="JWT_BLACKLIST_ENABLED")
    jwt_refresh_token_rotation: bool = Field(default=True, env="JWT_REFRESH_ROTATION")
    
    # ==========================================================================
    # Password Policy
    # ==========================================================================
    password_min_length: int = Field(default=12, env="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(default=True, env="PASSWORD_REQUIRE_UPPERCASE")
    password_require_lowercase: bool = Field(default=True, env="PASSWORD_REQUIRE_LOWERCASE")
    password_require_digit: bool = Field(default=True, env="PASSWORD_REQUIRE_DIGIT")
    password_require_special: bool = Field(default=True, env="PASSWORD_REQUIRE_SPECIAL")
    password_special_chars: str = Field(
        default="!@#$%^&*()_+-=[]{}|;:,.<>?",
        env="PASSWORD_SPECIAL_CHARS"
    )
    password_bcrypt_rounds: int = Field(default=12, env="PASSWORD_BCRYPT_ROUNDS")
    password_max_age_days: int = Field(default=90, env="PASSWORD_MAX_AGE_DAYS")
    password_history_count: int = Field(default=5, env="PASSWORD_HISTORY_COUNT")
    
    # ==========================================================================
    # Account Lockout
    # ==========================================================================
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=30, env="LOCKOUT_DURATION_MINUTES")
    progressive_lockout: bool = Field(default=True, env="PROGRESSIVE_LOCKOUT")
    
    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_RPM")
    rate_limit_requests_per_hour: int = Field(default=1000, env="RATE_LIMIT_RPH")
    rate_limit_burst_size: int = Field(default=20, env="RATE_LIMIT_BURST")
    auth_rate_limit_per_minute: int = Field(default=10, env="AUTH_RATE_LIMIT_PM")
    
    # ==========================================================================
    # IP Management
    # ==========================================================================
    ip_whitelist: List[str] = Field(default=[], env="IP_WHITELIST")
    ip_blacklist: List[str] = Field(default=[], env="IP_BLACKLIST")
    trusted_proxies: List[str] = Field(
        default=["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
        env="TRUSTED_PROXIES"
    )
    
    # ==========================================================================
    # Security Headers
    # ==========================================================================
    content_security_policy: str = Field(
        default="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; form-action 'self'",
        env="CONTENT_SECURITY_POLICY"
    )
    x_frame_options: str = Field(default="DENY", env="X_FRAME_OPTIONS")
    x_content_type_options: str = Field(default="nosniff", env="X_CONTENT_TYPE_OPTIONS")
    referrer_policy: str = Field(default="strict-origin-when-cross-origin", env="REFERRER_POLICY")
    permissions_policy: str = Field(
        default="geolocation=(), microphone=(), camera=()",
        env="PERMISSIONS_POLICY"
    )
    
    # ==========================================================================
    # Session Security
    # ==========================================================================
    session_cookie_secure: bool = Field(default=True, env="SESSION_COOKIE_SECURE")
    session_cookie_httponly: bool = Field(default=True, env="SESSION_COOKIE_HTTPONLY")
    session_cookie_samesite: str = Field(default="Strict", env="SESSION_COOKIE_SAMESITE")
    
    # ==========================================================================
    # CORS Settings
    # ==========================================================================
    cors_enabled: bool = Field(default=True, env="CORS_ENABLED")
    cors_allow_origins: List[str] = Field(
        default=["https://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_max_age: int = Field(default=600, env="CORS_MAX_AGE")
    
    # ==========================================================================
    # Input Validation
    # ==========================================================================
    max_request_size: int = Field(default=10 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 10MB
    allowed_content_types: List[str] = Field(
        default=["application/json", "multipart/form-data"],
        env="ALLOWED_CONTENT_TYPES"
    )
    
    # ==========================================================================
    # Audit & Logging
    # ==========================================================================
    audit_logging_enabled: bool = Field(default=True, env="AUDIT_LOGGING_ENABLED")
    pii_redaction_enabled: bool = Field(default=True, env="PII_REDACTION_ENABLED")
    log_sensitive_data: bool = Field(default=False, env="LOG_SENSITIVE_DATA")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# =============================================================================
# PII Fields Configuration
# =============================================================================
PII_FIELDS: Set[str] = {
    # Personal Information
    'name', 'first_name', 'last_name', 'full_name', 'applicant_name',
    'email', 'email_address', 'user_email',
    'phone', 'phone_number', 'mobile', 'mobile_number',
    'address', 'street_address', 'city', 'state', 'zip_code', 'postal_code',
    'date_of_birth', 'dob', 'birth_date', 'age',
    'gender', 'marital_status',
    
    # Financial Information
    'account_number', 'bank_account', 'iban',
    'credit_card', 'card_number', 'cvv',
    'ssn', 'social_security_number', 'tax_id', 'pan',
    'salary', 'income', 'monthly_income', 'annual_income',
    'bank_name', 'bank_branch',
    
    # Identity Documents
    'aadhaar', 'aadhaar_number', 'passport', 'passport_number',
    'drivers_license', 'license_number', 'voter_id',
    
    # Employment
    'employer_name', 'company_name', 'employer_address',
    
    # Login Credentials
    'password', 'password_hash', 'token', 'secret', 'api_key',
    
    # Network
    'ip_address', 'client_ip', 'user_agent',
}

# Fields that should be partially masked
PARTIAL_MASK_FIELDS: Set[str] = {
    'email', 'phone', 'phone_number', 'mobile',
    'account_number', 'credit_card', 'card_number',
    'ssn', 'aadhaar', 'pan', 'passport'
}


# =============================================================================
# Singleton Settings Instance
# =============================================================================
_security_settings: Optional[SecuritySettings] = None


def get_security_settings() -> SecuritySettings:
    """Get cached security settings instance."""
    global _security_settings
    if _security_settings is None:
        _security_settings = SecuritySettings()
    return _security_settings
