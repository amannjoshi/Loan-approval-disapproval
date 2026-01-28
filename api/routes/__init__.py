"""
API Routes Package
==================
FastAPI route definitions.
"""

from .auth import router as auth_router
from .applicants import router as applicants_router
from .applications import router as applications_router
from .admin import router as admin_router
from .models import router as models_router
from .rejection_feedback import router as rejection_feedback_router
from .alerts import router as alerts_router
from .privacy import router as privacy_router

__all__ = [
    'auth_router',
    'applicants_router',
    'applications_router',
    'admin_router',
    'models_router',
    'rejection_feedback_router',
    'alerts_router',
    'privacy_router'
]
