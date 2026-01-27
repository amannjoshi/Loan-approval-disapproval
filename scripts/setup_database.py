#!/usr/bin/env python
"""
Database Setup Script
=====================
Script to initialize the PostgreSQL database for Loan Approval System.

Usage:
    python scripts/setup_database.py [--drop-existing]

Options:
    --drop-existing    Drop existing tables before creating new ones (use with caution!)

Environment Variables Required:
    DB_HOST        PostgreSQL host (default: localhost)
    DB_PORT        PostgreSQL port (default: 5432)
    DB_NAME        Database name (default: loan_approval)
    DB_USER        Database user (default: postgres)
    DB_PASSWORD    Database password (required)

Author: Loan Analytics Team
Version: 1.0.0
"""

import os
import sys
import argparse
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_prerequisites():
    """Check if required packages are installed."""
    missing = []
    
    try:
        import sqlalchemy
        logger.info(f"✓ SQLAlchemy {sqlalchemy.__version__} installed")
    except ImportError:
        missing.append('sqlalchemy')
    
    try:
        import psycopg2
        logger.info(f"✓ psycopg2 installed")
    except ImportError:
        missing.append('psycopg2-binary')
    
    if missing:
        logger.error(f"Missing packages: {', '.join(missing)}")
        logger.info(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True


def check_database_connection():
    """Test PostgreSQL connection."""
    import psycopg2
    
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        conn.close()
        logger.info(f"✓ Connected to PostgreSQL at {host}:{port}")
        return True
    except Exception as e:
        logger.error(f"✗ Cannot connect to PostgreSQL: {e}")
        return False


def create_database():
    """Create the database if it doesn't exist."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    db_name = os.getenv('DB_NAME', 'loan_approval')
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            logger.info(f"✓ Database '{db_name}' already exists")
        else:
            cursor.execute(f'CREATE DATABASE {db_name}')
            logger.info(f"✓ Created database '{db_name}'")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create database: {e}")
        return False


def create_extensions():
    """Create required PostgreSQL extensions."""
    import psycopg2
    
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    db_name = os.getenv('DB_NAME', 'loan_approval')
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name
        )
        cursor = conn.cursor()
        
        # Create UUID extension
        cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        conn.commit()
        logger.info("✓ Created uuid-ossp extension")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create extensions: {e}")
        return False


def create_tables(drop_existing=False):
    """Create all database tables."""
    from database import init_database, Base
    
    try:
        db = init_database()
        
        if drop_existing:
            logger.warning("Dropping existing tables...")
            db.drop_tables()
        
        db.create_tables()
        logger.info("✓ Created all database tables")
        
        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f"  Tables created: {', '.join(tables)}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        return False


def verify_setup():
    """Verify the database setup."""
    from database import get_db
    
    try:
        db = get_db()
        
        # Health check
        if db.health_check():
            logger.info("✓ Database health check passed")
        else:
            logger.error("✗ Database health check failed")
            return False
        
        # Connection stats
        stats = db.get_connection_stats()
        logger.info(f"  Connection pool: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Verification failed: {e}")
        return False


def create_sample_data():
    """Create sample data for testing."""
    from database import (
        get_session_context, Applicant, LoanApplication,
        KYCStatus, ApplicationStatus, EmploymentType, Gender, Education
    )
    from database.repositories import ApplicantRepository, LoanApplicationRepository
    from datetime import date
    
    logger.info("Creating sample data...")
    
    try:
        with get_session_context() as session:
            applicant_repo = ApplicantRepository(session)
            loan_repo = LoanApplicationRepository(session)
            
            # Create sample applicant
            applicant = Applicant(
                first_name='Rahul',
                last_name='Sharma',
                email='rahul.sharma@example.com',
                phone='9876543210',
                date_of_birth=date(1990, 5, 15),
                gender=Gender.MALE,
                education=Education.GRADUATE,
                monthly_income=75000,
                other_income=5000,
                employment_type=EmploymentType.SALARIED,
                employer_name='TechCorp India',
                industry='Information Technology',
                designation='Senior Developer',
                years_at_current_job=3.5,
                total_experience=8,
                cibil_score=745,
                credit_history_years=5,
                existing_emi=15000,
                number_of_existing_loans=1,
                owns_property=True,
                property_value=5000000,
                city='Mumbai',
                state='Maharashtra',
                pincode='400001',
                kyc_status=KYCStatus.VERIFIED,
                pan_number='ABCDE1234F',
                aadhaar_number='123456789012'
            )
            
            applicant = applicant_repo.create(applicant)
            logger.info(f"  Created sample applicant: {applicant.id}")
            
            # Create sample loan application
            application = LoanApplication(
                applicant_id=applicant.id,
                loan_amount=500000,
                tenure_months=36,
                loan_purpose='Home Renovation',
                loan_type='Personal Loan',
                interest_rate=12.5,
                status=ApplicationStatus.PENDING
            )
            
            application = loan_repo.create(application)
            logger.info(f"  Created sample application: {application.application_number}")
            
        logger.info("✓ Sample data created successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create sample data: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Setup PostgreSQL database for Loan Approval System'
    )
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing tables before creating (CAUTION: data loss!)'
    )
    parser.add_argument(
        '--sample-data',
        action='store_true',
        help='Create sample data for testing'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing setup'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Loan Approval System - Database Setup")
    print("=" * 60)
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    print()
    
    if args.verify_only:
        if verify_setup():
            print("\n✅ Database verification successful!")
        else:
            print("\n❌ Database verification failed!")
            sys.exit(1)
        return
    
    # Check connection
    if not check_database_connection():
        print("\n❌ Cannot connect to PostgreSQL. Please check:")
        print("   1. PostgreSQL is running")
        print("   2. Environment variables are set correctly")
        print("   3. User has correct permissions")
        sys.exit(1)
    
    print()
    
    # Create database
    if not create_database():
        sys.exit(1)
    
    # Create extensions
    if not create_extensions():
        sys.exit(1)
    
    print()
    
    # Create tables
    if args.drop_existing:
        confirm = input("⚠️  This will DELETE all existing data. Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    if not create_tables(drop_existing=args.drop_existing):
        sys.exit(1)
    
    print()
    
    # Verify setup
    if not verify_setup():
        sys.exit(1)
    
    # Create sample data if requested
    if args.sample_data:
        print()
        create_sample_data()
    
    print()
    print("=" * 60)
    print("✅ Database setup completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Copy .env.example to .env and update credentials")
    print("  2. Run: python main.py serve")
    print("  3. Or start Streamlit: streamlit run app.py")


if __name__ == '__main__':
    main()
