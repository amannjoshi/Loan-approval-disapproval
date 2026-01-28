"""
Privacy API Routes
==================
API endpoints for data privacy and masking operations.

Author: Loan Analytics Team
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.privacy_service import (
    get_privacy_service,
    PrivacyLevel,
    mask_applicant
)
from utils.data_masking import (
    mask_pan,
    mask_aadhaar,
    mask_phone,
    mask_email,
    mask_name,
    mask_dict,
    MaskedDisplay
)


router = APIRouter(prefix="/privacy", tags=["Privacy & Data Masking"])


# =============================================================================
# Request/Response Models
# =============================================================================

class MaskRequest(BaseModel):
    """Request to mask a single value."""
    value: str = Field(..., description="Value to mask")
    data_type: str = Field(..., description="Type: pan, aadhaar, phone, email, name")


class MaskBatchRequest(BaseModel):
    """Request to mask multiple values."""
    items: List[MaskRequest] = Field(..., description="List of items to mask")


class MaskDictRequest(BaseModel):
    """Request to mask a dictionary."""
    data: Dict[str, Any] = Field(..., description="Dictionary with PII to mask")
    pii_fields: Optional[List[str]] = Field(None, description="Optional: specific fields to mask")


class ApplicantMaskRequest(BaseModel):
    """Request to mask applicant data."""
    name: Optional[str] = None
    pan: Optional[str] = None
    aadhaar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None
    account_number: Optional[str] = None


class MaskResponse(BaseModel):
    """Response with masked value."""
    original_type: str
    masked: str
    format: str


class MaskBatchResponse(BaseModel):
    """Response with multiple masked values."""
    results: List[MaskResponse]
    count: int


class ApplicantDisplayResponse(BaseModel):
    """Masked applicant display for UI."""
    display: Dict[str, str]
    identifiers: Dict[str, Dict[str, str]]
    privacy_level: str


# =============================================================================
# Masking Endpoints
# =============================================================================

@router.post("/mask", response_model=MaskResponse)
async def mask_single_value(request: MaskRequest):
    """
    Mask a single sensitive value.
    
    Supported types:
    - pan: ABCDE****F
    - aadhaar: ****-****-1234
    - phone: ******6789
    - email: a****z@domain.com
    - name: A**** K****
    
    Example:
    ```
    POST /privacy/mask
    {"value": "ABCDE1234F", "data_type": "pan"}
    
    Response: {"masked": "ABCDE****F", "format": "PAN"}
    ```
    """
    maskers = {
        'pan': mask_pan,
        'aadhaar': mask_aadhaar,
        'phone': mask_phone,
        'email': mask_email,
        'name': mask_name
    }
    
    data_type = request.data_type.lower()
    
    if data_type not in maskers:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported data type. Use: {list(maskers.keys())}"
        )
    
    masked_value = maskers[data_type](request.value)
    
    return MaskResponse(
        original_type=data_type,
        masked=masked_value,
        format=data_type.upper()
    )


@router.post("/mask/batch", response_model=MaskBatchResponse)
async def mask_batch_values(request: MaskBatchRequest):
    """
    Mask multiple sensitive values in one request.
    
    Example:
    ```
    POST /privacy/mask/batch
    {
      "items": [
        {"value": "ABCDE1234F", "data_type": "pan"},
        {"value": "123456789012", "data_type": "aadhaar"}
      ]
    }
    ```
    """
    maskers = {
        'pan': mask_pan,
        'aadhaar': mask_aadhaar,
        'phone': mask_phone,
        'email': mask_email,
        'name': mask_name
    }
    
    results = []
    for item in request.items:
        data_type = item.data_type.lower()
        
        if data_type in maskers:
            masked = maskers[data_type](item.value)
            results.append(MaskResponse(
                original_type=data_type,
                masked=masked,
                format=data_type.upper()
            ))
        else:
            results.append(MaskResponse(
                original_type=data_type,
                masked="[UNSUPPORTED TYPE]",
                format="ERROR"
            ))
    
    return MaskBatchResponse(results=results, count=len(results))


@router.post("/mask/dict")
async def mask_dictionary(request: MaskDictRequest):
    """
    Automatically detect and mask PII in a dictionary.
    
    Automatically detects fields like:
    - pan, pan_number
    - aadhaar, aadhar_number
    - phone, mobile
    - email, email_id
    - name, full_name
    
    Example:
    ```
    POST /privacy/mask/dict
    {
      "data": {
        "name": "Amit Kumar",
        "pan": "ABCDE1234F",
        "phone": "9876543210"
      }
    }
    
    Response:
    {
      "masked_data": {
        "name": "A*** K****",
        "pan": "ABCDE****F",
        "phone": "******3210"
      }
    }
    ```
    """
    masked = mask_dict(request.data)
    
    return {
        "original_fields": list(request.data.keys()),
        "masked_data": masked,
        "pii_fields_detected": [
            k for k in request.data.keys() 
            if get_privacy_service().is_pii_field(k)
        ]
    }


@router.post("/mask/applicant", response_model=ApplicantDisplayResponse)
async def mask_applicant_data(request: ApplicantMaskRequest):
    """
    Create a masked applicant display for UI.
    
    Returns professionally masked data suitable for:
    - Customer-facing displays
    - Agent dashboards
    - Audit logs
    
    Example:
    ```
    POST /privacy/mask/applicant
    {
      "name": "Amit Kumar",
      "pan": "ABCDE1234F",
      "aadhaar": "123456789012",
      "phone": "9876543210",
      "email": "amit.kumar@email.com"
    }
    
    Response:
    {
      "display": {
        "name": "A*** K****",
        "pan": "ABCDE****F",
        "aadhaar": "****-****-9012",
        "phone": "******3210",
        "email": "a*********r@email.com"
      },
      "identifiers": {
        "pan": {"masked": "ABCDE****F", "last_char": "F"},
        "aadhaar": {"masked": "****-****-9012", "last_four": "9012"}
      }
    }
    ```
    """
    applicant_data = request.dict(exclude_none=True)
    result = mask_applicant(applicant_data)
    
    return ApplicantDisplayResponse(
        display=result.get('display', {}),
        identifiers=result.get('identifiers', {}),
        privacy_level="confidential"
    )


# =============================================================================
# Quick Masking Endpoints (GET)
# =============================================================================

@router.get("/mask/pan/{pan_number}")
async def quick_mask_pan(pan_number: str):
    """
    Quick PAN masking.
    
    Example: GET /privacy/mask/pan/ABCDE1234F
    Response: {"masked": "ABCDE****F"}
    """
    return MaskedDisplay.pan(pan_number)


@router.get("/mask/aadhaar/{aadhaar_number}")
async def quick_mask_aadhaar(aadhaar_number: str):
    """
    Quick Aadhaar masking.
    
    Example: GET /privacy/mask/aadhaar/123456789012
    Response: {"masked": "****-****-9012"}
    """
    return MaskedDisplay.aadhaar(aadhaar_number)


@router.get("/mask/phone/{phone_number}")
async def quick_mask_phone(phone_number: str):
    """
    Quick phone masking.
    
    Example: GET /privacy/mask/phone/9876543210
    Response: {"masked": "******3210"}
    """
    return MaskedDisplay.phone(phone_number)


@router.get("/mask/email/{email}")
async def quick_mask_email(email: str):
    """
    Quick email masking.
    
    Example: GET /privacy/mask/email/amit.kumar@email.com
    Response: {"masked": "a*********r@email.com"}
    """
    return MaskedDisplay.email(email)


# =============================================================================
# Privacy Info Endpoints
# =============================================================================

@router.get("/formats")
async def get_masking_formats():
    """
    Get documentation of masking formats used.
    
    Returns the format specifications for each data type.
    """
    return {
        "formats": {
            "PAN": {
                "pattern": "ABCDE****F",
                "description": "Show first 5 characters and last 1",
                "example": {
                    "input": "ABCDE1234F",
                    "output": "ABCDE****F"
                }
            },
            "Aadhaar": {
                "pattern": "****-****-1234",
                "description": "Show only last 4 digits",
                "example": {
                    "input": "123456789012",
                    "output": "****-****-9012"
                }
            },
            "Phone": {
                "pattern": "******6789",
                "description": "Show only last 4 digits",
                "example": {
                    "input": "9876543210",
                    "output": "******3210"
                }
            },
            "Email": {
                "pattern": "a****z@domain.com",
                "description": "Show first and last character of local part",
                "example": {
                    "input": "amit.kumar@email.com",
                    "output": "a*********r@email.com"
                }
            },
            "Name": {
                "pattern": "A**** K****",
                "description": "Show first letter of each word",
                "example": {
                    "input": "Amit Kumar",
                    "output": "A*** K****"
                }
            },
            "Account": {
                "pattern": "******1234",
                "description": "Show only last 4 digits",
                "example": {
                    "input": "12345678901234",
                    "output": "**********1234"
                }
            },
            "Card": {
                "pattern": "****-****-****-5678",
                "description": "Show only last 4 digits in card format",
                "example": {
                    "input": "4111111111111111",
                    "output": "****-****-****-1111"
                }
            }
        },
        "supported_types": ["pan", "aadhaar", "phone", "email", "name", "account", "card"],
        "auto_detection": True
    }


@router.get("/check/{field_name}")
async def check_if_pii_field(field_name: str):
    """
    Check if a field name is considered PII.
    
    Example: GET /privacy/check/pan_number
    Response: {"is_pii": true, "category": "identity"}
    """
    service = get_privacy_service()
    is_pii = service.is_pii_field(field_name)
    level = service.get_privacy_level(field_name)
    
    return {
        "field_name": field_name,
        "is_pii": is_pii,
        "privacy_level": level.value,
        "requires_masking": is_pii
    }
