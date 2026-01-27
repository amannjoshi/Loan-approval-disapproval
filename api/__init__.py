"""
FastAPI Application Package
===========================
REST API for Loan Approval System.
"""

from .main import app, create_app
from .config import Settings, get_settings
from .dependencies import get_db, get_current_user

__all__ = [
    'app',
    'create_app',
    'Settings',
    'get_settings',
    'get_db',
    'get_current_user'
]
