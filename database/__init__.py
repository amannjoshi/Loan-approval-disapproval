"""
Database Package for Loan Approval System
==========================================
PostgreSQL database integration with SQLAlchemy ORM.

This package provides:
- Connection management with pooling
- SQLAlchemy ORM models for Applicant and LoanApplication
- Repository pattern for data access
- Audit logging for compliance

Usage:
    from database import init_database, ApplicantRepository, LoanApplicationRepository
    
    # Initialize database connection
    db = init_database()
    
    # Create tables
    db.create_tables()
    
    # Use repositories
    with db.session_scope() as session:
        applicant_repo = ApplicantRepository(session)
        loan_repo = LoanApplicationRepository(session)
        
        # Create applicant
        applicant = Applicant(first_name='John', ...)
        applicant_repo.create(applicant)
"""

from .connection import (
    DatabaseConnection,
    DatabaseConfig,
    get_db,
    get_db_session,
    get_session_context,
    init_database,
    create_all_tables,
    check_database_health,
    setup_database
)

from .models import (
    Base,
    Applicant,
    LoanApplication,
    ApplicationAuditLog,
    ApplicationStatus,
    KYCStatus,
    EmploymentType,
    Gender,
    MaritalStatus,
    Education
)

from .repositories import (
    BaseRepository,
    ApplicantRepository,
    LoanApplicationRepository,
    AuditLogRepository
)

__all__ = [
    # Connection
    'DatabaseConnection',
    'DatabaseConfig',
    'get_db',
    'get_db_session',
    'get_session_context',
    'init_database',
    'create_all_tables',
    'check_database_health',
    'setup_database',
    
    # Models
    'Base',
    'Applicant',
    'LoanApplication',
    'ApplicationAuditLog',
    
    # Enums
    'ApplicationStatus',
    'KYCStatus',
    'EmploymentType',
    'Gender',
    'MaritalStatus',
    'Education',
    
    # Repositories
    'BaseRepository',
    'ApplicantRepository',
    'LoanApplicationRepository',
    'AuditLogRepository'
]

__version__ = '1.0.0'
