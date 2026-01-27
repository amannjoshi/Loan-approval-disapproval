"""
Backend Test Suite for Loan Approval System
============================================
Comprehensive tests for all backend components.

Run with: pytest tests/test_backend.py -v

Author: Loan Analytics Team
Version: 1.0.0
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInputValidator:
    """Test cases for InputValidator class."""
    
    def test_valid_application(self):
        """Test validation of a valid application."""
        from utils.validators import InputValidator
        
        validator = InputValidator()
        
        valid_data = {
            'age': 35,
            'gender': 'Male',
            'education': 'Graduate',
            'marital_status': 'Married',
            'num_dependents': 2,
            'employment_type': 'Salaried',
            'industry': 'IT',
            'years_at_current_job': 5,
            'monthly_income': 75000,
            'existing_emi': 10000,
            'num_existing_loans': 1,
            'savings_balance': 300000,
            'cibil_score': 750,
            'credit_history_years': 8,
            'late_payments_last_2_years': 0,
            'has_defaults': False,
            'owns_property': True,
            'years_with_bank': 5,
            'loan_amount': 1000000,
            'loan_tenure_months': 60
        }
        
        report = validator.validate_application(valid_data)
        assert report.is_valid, f"Valid application should pass: {[e.message for e in report.errors]}"
    
    def test_invalid_age(self):
        """Test validation catches invalid age."""
        from utils.validators import InputValidator
        
        validator = InputValidator()
        
        invalid_data = {'age': 15}  # Below minimum
        report = validator.validate_application(invalid_data)
        
        age_errors = [e for e in report.errors if 'age' in e.field.lower()]
        assert len(age_errors) > 0, "Should catch invalid age"
    
    def test_invalid_cibil_score(self):
        """Test validation catches invalid CIBIL score."""
        from utils.validators import InputValidator
        
        validator = InputValidator()
        
        invalid_data = {'cibil_score': 1000}  # Above maximum (900)
        report = validator.validate_application(invalid_data)
        
        cibil_errors = [e for e in report.errors if 'cibil' in e.field.lower()]
        assert len(cibil_errors) > 0, "Should catch invalid CIBIL score"
    
    def test_invalid_categorical(self):
        """Test validation catches invalid categorical values."""
        from utils.validators import InputValidator
        
        validator = InputValidator()
        
        invalid_data = {'gender': 'InvalidGender'}
        report = validator.validate_application(invalid_data)
        
        gender_errors = [e for e in report.errors if 'gender' in e.field.lower()]
        assert len(gender_errors) > 0, "Should catch invalid gender"
    
    def test_business_rule_dti(self):
        """Test DTI business rule validation."""
        from utils.validators import InputValidator
        
        validator = InputValidator()
        
        # High DTI ratio
        data = {
            'monthly_income': 50000,
            'existing_emi': 40000,  # 80% DTI
            'loan_amount': 500000,
            'loan_tenure_months': 36
        }
        report = validator.validate_application(data)
        
        # Should have warning or error about high DTI
        dti_issues = [e for e in report.warnings + report.errors 
                      if 'dti' in e.message.lower() or 'debt' in e.message.lower()]
        assert len(dti_issues) > 0, "Should warn about high DTI"
    
    def test_sql_injection_detection(self):
        """Test security check for SQL injection."""
        from utils.validators import InputValidator
        
        validator = InputValidator()
        
        malicious_data = {
            'industry': "IT'; DROP TABLE users; --"
        }
        report = validator.validate_application(malicious_data)
        
        security_errors = [e for e in report.errors 
                          if 'injection' in e.message.lower() or 'security' in e.message.lower()]
        assert len(security_errors) > 0, "Should detect SQL injection"


class TestDataGenerator:
    """Test cases for data generator."""
    
    def test_generate_data(self):
        """Test synthetic data generation."""
        from data.data_generator import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=100)
        
        assert len(df) == 100, "Should generate requested number of samples"
        assert 'loan_approved' in df.columns, "Should have target column"
        assert 'cibil_score' in df.columns, "Should have CIBIL score"
        assert 'monthly_income' in df.columns, "Should have monthly income"
    
    def test_data_quality(self):
        """Test data quality constraints."""
        from data.data_generator import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=500)
        
        # Check CIBIL score range
        assert df['cibil_score'].min() >= 300, "CIBIL should be >= 300"
        assert df['cibil_score'].max() <= 900, "CIBIL should be <= 900"
        
        # Check age range
        assert df['age'].min() >= 18, "Age should be >= 18"
        assert df['age'].max() <= 70, "Age should be <= 70"
        
        # Check no negative values for income
        assert (df['monthly_income'] > 0).all(), "Income should be positive"
    
    def test_class_balance(self):
        """Test reasonable class balance in generated data."""
        from data.data_generator import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=1000)
        
        approval_rate = df['loan_approved'].mean()
        
        # Approval rate should be reasonable (20-80%)
        assert 0.2 <= approval_rate <= 0.8, f"Unusual approval rate: {approval_rate}"


class TestLoanModel:
    """Test cases for LoanApprovalModel."""
    
    @pytest.fixture
    def trained_model(self):
        """Create a trained model for testing."""
        from data.data_generator import generate_synthetic_data
        from models.loan_model import LoanApprovalModel
        
        df = generate_synthetic_data(n_samples=1000)
        model = LoanApprovalModel(model_type='gradient_boosting')
        model.train(df, perform_cv=False, calibrate=False)
        return model, df
    
    def test_model_training(self, trained_model):
        """Test model training completes successfully."""
        model, df = trained_model
        
        assert model.is_trained, "Model should be trained"
        assert model.model is not None, "Model should not be None"
        assert len(model.feature_names) > 0, "Should have feature names"
    
    def test_model_prediction(self, trained_model):
        """Test model prediction."""
        model, df = trained_model
        
        sample = df.sample(1)
        prediction = model.predict(sample)
        
        assert 'approved' in prediction, "Should have approved field"
        assert 'approval_probability' in prediction, "Should have probability"
        assert 0 <= prediction['approval_probability'] <= 1, "Probability should be [0,1]"
    
    def test_model_explanation(self, trained_model):
        """Test SHAP explanation generation."""
        model, df = trained_model
        
        sample = df.sample(1)
        explanation = model.explain_prediction(sample)
        
        assert 'all_contributions' in explanation, "Should have contributions"
        assert 'positive_factors' in explanation, "Should have positive factors"
        assert 'negative_factors' in explanation, "Should have negative factors"
        assert len(explanation['all_contributions']) > 0, "Should have contributions"
    
    def test_batch_prediction(self, trained_model):
        """Test batch predictions."""
        model, df = trained_model
        
        batch = df.sample(10)
        results = model.predict_batch(batch)
        
        assert len(results) == 10, "Should return same number of results"
        assert 'predicted_approved' in results.columns, "Should have predictions"
        assert 'approval_probability' in results.columns, "Should have probabilities"
    
    def test_feature_importance(self, trained_model):
        """Test feature importance extraction."""
        model, df = trained_model
        
        importance = model.get_feature_importance()
        
        assert len(importance) > 0, "Should have feature importances"
        assert 'feature' in importance.columns, "Should have feature column"
        assert 'importance' in importance.columns, "Should have importance column"
        assert importance['importance'].sum() > 0, "Importances should be positive"
    
    def test_model_save_load(self, trained_model, tmp_path):
        """Test model save and load."""
        model, df = trained_model
        
        # Save
        filepath = str(tmp_path / "test_model.pkl")
        model.save_model(filepath)
        
        assert os.path.exists(filepath), "Model file should exist"
        
        # Load
        from models.loan_model import LoanApprovalModel
        new_model = LoanApprovalModel()
        new_model.load_model(filepath)
        
        assert new_model.is_trained, "Loaded model should be trained"
        
        # Verify predictions match
        sample = df.sample(1)
        orig_pred = model.predict(sample)
        loaded_pred = new_model.predict(sample)
        
        assert abs(orig_pred['approval_probability'] - loaded_pred['approval_probability']) < 0.01, \
            "Predictions should match"


class TestFairnessAnalyzer:
    """Test cases for FairnessAnalyzer."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data with predictions."""
        from data.data_generator import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=500)
        # Simulate predictions
        df['predicted'] = np.random.binomial(1, 0.6, len(df))
        return df
    
    def test_demographic_parity(self, sample_data):
        """Test demographic parity calculation."""
        from utils.fairness_analyzer import FairnessAnalyzer
        
        analyzer = FairnessAnalyzer()
        
        # Check by gender
        parity = analyzer.demographic_parity(
            sample_data, 'gender', 'predicted'
        )
        
        assert 'approval_rates' in parity, "Should have approval rates"
        assert 'disparity_ratio' in parity, "Should have disparity ratio"
        assert parity['disparity_ratio'] > 0, "Disparity ratio should be positive"
    
    def test_fairness_report(self, sample_data):
        """Test comprehensive fairness report."""
        from utils.fairness_analyzer import FairnessAnalyzer
        
        analyzer = FairnessAnalyzer()
        
        report = analyzer.generate_fairness_report(
            sample_data, 
            'predicted', 
            'loan_approved',
            protected_attributes=['gender', 'marital_status']
        )
        
        assert 'demographic_parity' in report, "Should have demographic parity"
        assert 'overall_fairness_score' in report, "Should have fairness score"


class TestLoanService:
    """Test cases for LoanApplicationService."""
    
    @pytest.fixture
    def service_with_model(self):
        """Create service with trained model."""
        from data.data_generator import generate_synthetic_data
        from models.loan_model import LoanApprovalModel
        from services.loan_service import LoanApplicationService
        from utils.validators import InputValidator
        
        # Train model
        df = generate_synthetic_data(n_samples=1000)
        model = LoanApprovalModel(model_type='gradient_boosting')
        model.train(df, perform_cv=False, calibrate=False)
        
        # Create service
        service = LoanApplicationService(
            model=model,
            validator=InputValidator()
        )
        
        return service
    
    def test_process_application(self, service_with_model):
        """Test full application processing."""
        from services.loan_service import create_application_from_dict
        
        service = service_with_model
        
        app_data = {
            'age': 35,
            'gender': 'Male',
            'education': 'Graduate',
            'marital_status': 'Married',
            'num_dependents': 2,
            'employment_type': 'Salaried',
            'industry': 'IT',
            'years_at_current_job': 5,
            'monthly_income': 75000,
            'existing_emi': 10000,
            'num_existing_loans': 1,
            'savings_balance': 300000,
            'cibil_score': 750,
            'credit_history_years': 8,
            'late_payments_last_2_years': 0,
            'has_defaults': False,
            'owns_property': True,
            'years_with_bank': 5,
            'loan_amount': 1000000,
            'loan_tenure_months': 60
        }
        
        application = create_application_from_dict(app_data)
        result = service.process_application(application)
        
        assert result.application_id is not None, "Should have application ID"
        assert result.status is not None, "Should have status"
        assert 0 <= result.approval_probability <= 1, "Probability should be valid"
        assert result.processing_time_ms > 0, "Should track processing time"
    
    def test_emi_calculation(self, service_with_model):
        """Test EMI calculation."""
        service = service_with_model
        
        # Test known EMI calculation
        # P = 1,000,000, r = 12% annual, n = 12 months
        # Expected EMI ≈ 88,849
        emi = service._calculate_emi(1000000, 12.0, 12)
        
        assert 88000 <= emi <= 90000, f"EMI calculation seems off: {emi}"
    
    def test_interest_rate_by_risk(self, service_with_model):
        """Test interest rate varies by risk level."""
        service = service_with_model
        
        low_risk_rate = service._calculate_interest_rate('low')
        high_risk_rate = service._calculate_interest_rate('high')
        
        assert low_risk_rate < high_risk_rate, "Low risk should have lower rate"


class TestAuditLogger:
    """Test cases for AuditLogger."""
    
    def test_audit_logging(self, tmp_path):
        """Test audit event logging."""
        from utils.audit_logger import AuditLogger, AuditEventType
        
        log_dir = str(tmp_path / "audit_logs")
        logger = AuditLogger(log_directory=log_dir)
        
        # Log a decision
        logger.log_decision(
            application_id="test-123",
            approved=True,
            probability=0.85,
            risk_level="low",
            model_id="test-model",
            features={'age': 30},
            explanation={'key': 'value'}
        )
        
        # Check log was created
        assert os.path.exists(log_dir), "Log directory should exist"
        
        # Get events
        events = logger.get_events(application_id="test-123")
        assert len(events) > 0, "Should have logged events"


class TestModelRegistry:
    """Test cases for ModelRegistry."""
    
    def test_registry_initialization(self, tmp_path):
        """Test registry initialization."""
        from models.model_registry import ModelRegistry
        
        registry_path = str(tmp_path / "registry")
        registry = ModelRegistry(registry_path=registry_path)
        
        assert os.path.exists(registry_path), "Registry path should exist"
        
        stats = registry.get_registry_stats()
        assert 'total_models' in stats, "Should have stats"


class TestConfigSettings:
    """Test cases for configuration settings."""
    
    def test_system_config(self):
        """Test system configuration loading."""
        from config.settings import SystemConfig
        
        config = SystemConfig()
        
        assert config.credit_score.min_score == 300
        assert config.credit_score.max_score == 900
        assert config.model.test_size > 0
        assert config.model.test_size < 1
    
    def test_risk_categorization(self):
        """Test risk categorization from config."""
        from config.settings import SystemConfig
        
        config = SystemConfig()
        
        low_risk = config.get_risk_category(0.85)
        high_risk = config.get_risk_category(0.35)
        
        assert low_risk.name == 'LOW'
        assert high_risk.name in ['HIGH', 'VERY_HIGH']
    
    def test_interest_rate_calculation(self):
        """Test interest rate from config."""
        from config.settings import SystemConfig, RiskCategory
        
        config = SystemConfig()
        
        low_rate = config.get_interest_rate(RiskCategory.LOW)
        high_rate = config.get_interest_rate(RiskCategory.HIGH)
        
        assert low_rate < high_rate


class TestExceptions:
    """Test cases for custom exceptions."""
    
    def test_validation_exception(self):
        """Test validation exception."""
        from utils.exceptions import ValidationException
        
        exc = ValidationException(
            message="Invalid value",
            field_name="age",
            invalid_value=15
        )
        
        result = exc.to_dict()
        assert result['field'] == 'age'
        assert result['category'] == 'validation'
    
    def test_exception_handler(self):
        """Test centralized exception handler."""
        from utils.exceptions import ExceptionHandler, ValidationException
        
        handler = ExceptionHandler()
        
        exc = ValidationException("Test error", field_name="test")
        result = handler.handle(exc)
        
        assert result['error'] == True
        assert 'message' in result


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
