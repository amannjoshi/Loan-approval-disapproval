"""
Audit Logging Module for Loan Approval System
==============================================
Comprehensive audit trail for compliance with RBI regulations.
Tracks all loan decisions, model predictions, and system activities.

Features:
- Immutable audit logs
- Decision tracking
- Compliance reporting
- Performance monitoring

Author: Loan Analytics Team
Version: 3.0.0
Last Updated: January 2026
"""

import os
import json
import hashlib
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading
from enum import Enum
import uuid


class AuditEventType(Enum):
    """Types of audit events."""
    PREDICTION_MADE = "prediction_made"
    MODEL_TRAINED = "model_trained"
    MODEL_LOADED = "model_loaded"
    DATA_ACCESSED = "data_accessed"
    FAIRNESS_CHECK = "fairness_check"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    CONFIG_CHANGED = "config_changed"
    USER_ACTION = "user_action"
    MANUAL_REVIEW = "manual_review"
    EXPLANATION_GENERATED = "explanation_generated"


class DecisionOutcome(Enum):
    """Loan decision outcomes."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Single audit event record."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_type: str = ""
    
    # Application details
    application_id: Optional[str] = None
    applicant_name: Optional[str] = None
    
    # Decision details
    decision_outcome: Optional[str] = None
    confidence_score: Optional[float] = None
    risk_category: Optional[str] = None
    
    # Model details
    model_version: Optional[str] = None
    model_id: Optional[str] = None
    
    # Request details
    input_features: Optional[Dict] = None
    explanation_summary: Optional[Dict] = None
    
    # Fairness metrics
    fairness_flags: Optional[List[str]] = None
    
    # System details
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Metadata
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Integrity
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None
    
    def compute_hash(self, previous_hash: str = "") -> str:
        """Compute SHA-256 hash for event integrity."""
        self.previous_hash = previous_hash
        
        # Create deterministic string representation
        hash_content = json.dumps({
            'event_id': self.event_id,
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'application_id': self.application_id,
            'decision_outcome': self.decision_outcome,
            'confidence_score': self.confidence_score,
            'previous_hash': previous_hash
        }, sort_keys=True)
        
        self.event_hash = hashlib.sha256(hash_content.encode()).hexdigest()
        return self.event_hash
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class AuditLogger:
    """
    Thread-safe audit logger with file persistence.
    
    Features:
    - Blockchain-style hash chaining for integrity
    - Automatic log rotation
    - Compliance-ready formatting
    - Performance metrics
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for consistent audit trail."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_dir: str = "logs"):
        if self._initialized:
            return
            
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate log files
        self.decision_log_path = self.log_dir / "decisions"
        self.audit_log_path = self.log_dir / "audit"
        self.error_log_path = self.log_dir / "errors"
        self.metrics_log_path = self.log_dir / "metrics"
        
        for path in [self.decision_log_path, self.audit_log_path, 
                     self.error_log_path, self.metrics_log_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Hash chain for integrity
        self._last_hash = "GENESIS"
        self._event_count = 0
        
        # Configure standard logging
        self._setup_logging()
        
        # Session tracking
        self.session_id = str(uuid.uuid4())[:8]
        self.model_version = "3.0.0"
        
        self._initialized = True
        
        # Log initialization
        self.log_event(AuditEventType.CONFIG_CHANGED, {
            'action': 'audit_logger_initialized',
            'session_id': self.session_id
        })
    
    def _setup_logging(self):
        """Setup Python logging handlers."""
        self.logger = logging.getLogger('loan_audit')
        self.logger.setLevel(logging.INFO)
        
        # File handler for general audit
        fh = logging.FileHandler(self.audit_log_path / 'audit.log')
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def log_prediction(self, 
                       application_data: Dict,
                       prediction_result: Dict,
                       explanation: Optional[Dict] = None,
                       processing_time_ms: float = 0) -> AuditEvent:
        """
        Log a loan prediction decision.
        
        Parameters:
        -----------
        application_data : dict
            Input application data
        prediction_result : dict
            Model prediction output
        explanation : dict, optional
            SHAP explanation
        processing_time_ms : float
            Time taken for prediction
            
        Returns:
        --------
        AuditEvent
            The logged event
        """
        # Determine outcome
        if prediction_result.get('approved'):
            outcome = DecisionOutcome.APPROVED.value
        elif prediction_result.get('confidence', 0) < 0.6 and prediction_result.get('confidence', 0) > 0.4:
            outcome = DecisionOutcome.MANUAL_REVIEW.value
        else:
            outcome = DecisionOutcome.REJECTED.value
        
        # Create explanation summary (redact large data)
        explanation_summary = None
        if explanation:
            explanation_summary = {
                'top_positive_factors': [
                    f['display_name'] for f in explanation.get('positive_factors', [])[:3]
                ],
                'top_negative_factors': [
                    f['display_name'] for f in explanation.get('negative_factors', [])[:3]
                ],
                'base_value': explanation.get('base_value')
            }
        
        # Sanitize input features (remove sensitive data)
        sanitized_features = self._sanitize_features(application_data)
        
        # Risk categorization
        confidence = prediction_result.get('approval_probability', 0.5)
        if confidence >= 0.8:
            risk_category = "low"
        elif confidence >= 0.6:
            risk_category = "medium"
        elif confidence >= 0.4:
            risk_category = "high"
        else:
            risk_category = "very_high"
        
        event = AuditEvent(
            event_type=AuditEventType.PREDICTION_MADE.value,
            application_id=application_data.get('applicant_id', f"APP_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            applicant_name=self._mask_name(application_data.get('applicant_name', 'Unknown')),
            decision_outcome=outcome,
            confidence_score=round(confidence, 4),
            risk_category=risk_category,
            model_version=self.model_version,
            input_features=sanitized_features,
            explanation_summary=explanation_summary,
            processing_time_ms=round(processing_time_ms, 2),
            session_id=self.session_id
        )
        
        self._persist_event(event, 'decision')
        return event
    
    def log_fairness_check(self, 
                          fairness_report: Dict,
                          attributes_checked: List[str]) -> AuditEvent:
        """Log fairness analysis results."""
        
        # Extract key metrics
        flags = []
        summary = fairness_report.get('summary', {})
        
        if not summary.get('overall_fair', True):
            flags = summary.get('issues', [])
        
        event = AuditEvent(
            event_type=AuditEventType.FAIRNESS_CHECK.value,
            fairness_flags=flags[:5] if flags else None,
            explanation_summary={
                'attributes_analyzed': attributes_checked,
                'overall_fair': summary.get('overall_fair'),
                'issues_count': summary.get('issues_found', 0)
            },
            session_id=self.session_id
        )
        
        self._persist_event(event, 'audit')
        return event
    
    def log_model_training(self, metrics: Dict, 
                           training_samples: int,
                           training_time_ms: float) -> AuditEvent:
        """Log model training event."""
        event = AuditEvent(
            event_type=AuditEventType.MODEL_TRAINED.value,
            model_version=self.model_version,
            explanation_summary={
                'accuracy': metrics.get('accuracy'),
                'auc_roc': metrics.get('auc_roc'),
                'precision': metrics.get('precision'),
                'recall': metrics.get('recall'),
                'f1_score': metrics.get('f1_score'),
                'training_samples': training_samples
            },
            processing_time_ms=training_time_ms,
            session_id=self.session_id
        )
        
        self._persist_event(event, 'audit')
        return event
    
    def log_error(self, error: Exception, 
                  context: Dict = None) -> AuditEvent:
        """Log system error."""
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_ERROR.value,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            explanation_summary=context,
            session_id=self.session_id
        )
        
        self._persist_event(event, 'error')
        self.logger.error(f"Error logged: {error}")
        return event
    
    def log_event(self, event_type: AuditEventType, 
                  details: Dict = None) -> AuditEvent:
        """Log generic event."""
        event = AuditEvent(
            event_type=event_type.value,
            explanation_summary=details,
            session_id=self.session_id
        )
        
        self._persist_event(event, 'audit')
        return event
    
    def _persist_event(self, event: AuditEvent, log_type: str):
        """Persist event to appropriate log file."""
        with self._lock:
            # Compute hash chain
            event.compute_hash(self._last_hash)
            self._last_hash = event.event_hash
            self._event_count += 1
            
            # Determine log path
            if log_type == 'decision':
                base_path = self.decision_log_path
            elif log_type == 'error':
                base_path = self.error_log_path
            else:
                base_path = self.audit_log_path
            
            # Daily log rotation
            date_str = datetime.now().strftime('%Y-%m-%d')
            log_file = base_path / f"{log_type}_{date_str}.jsonl"
            
            # Append to log file (JSONL format)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(event.to_json().replace('\n', ' ') + '\n')
            
            # Also log to standard logger
            self.logger.info(f"Event logged: {event.event_type} - {event.event_id}")
    
    def _sanitize_features(self, data: Dict) -> Dict:
        """Remove/mask sensitive features for logging."""
        sanitized = {}
        
        # Features safe to log
        safe_features = [
            'age', 'gender', 'education', 'marital_status',
            'employment_type', 'industry', 'years_at_current_job',
            'cibil_score', 'credit_history_years', 'late_payments_last_2_years',
            'has_defaults', 'owns_property', 'num_dependents',
            'num_existing_loans', 'loan_tenure_months', 'loan_purpose'
        ]
        
        for feature in safe_features:
            if feature in data:
                sanitized[feature] = data[feature]
        
        # Mask financial amounts (log ranges instead of exact values)
        if 'monthly_income' in data:
            income = data['monthly_income']
            if income < 25000:
                sanitized['income_range'] = '<25K'
            elif income < 50000:
                sanitized['income_range'] = '25K-50K'
            elif income < 100000:
                sanitized['income_range'] = '50K-100K'
            else:
                sanitized['income_range'] = '>100K'
        
        if 'loan_amount' in data:
            amount = data['loan_amount']
            if amount < 200000:
                sanitized['loan_range'] = '<2L'
            elif amount < 500000:
                sanitized['loan_range'] = '2L-5L'
            elif amount < 1000000:
                sanitized['loan_range'] = '5L-10L'
            else:
                sanitized['loan_range'] = '>10L'
        
        return sanitized
    
    def _mask_name(self, name: str) -> str:
        """Mask name for privacy (keep first and last letter)."""
        if not name or len(name) < 3:
            return "***"
        
        parts = name.split()
        masked_parts = []
        for part in parts:
            if len(part) > 2:
                masked_parts.append(part[0] + '*' * (len(part) - 2) + part[-1])
            else:
                masked_parts.append('**')
        
        return ' '.join(masked_parts)
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session."""
        return {
            'session_id': self.session_id,
            'events_logged': self._event_count,
            'model_version': self.model_version,
            'last_hash': self._last_hash[:16] + '...'
        }
    
    def verify_chain_integrity(self, log_file: Path) -> Dict:
        """Verify integrity of a log file's hash chain."""
        results = {
            'file': str(log_file),
            'total_events': 0,
            'valid_hashes': 0,
            'invalid_hashes': 0,
            'broken_links': []
        }
        
        if not log_file.exists():
            results['error'] = 'File not found'
            return results
        
        previous_hash = "GENESIS"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line)
                    results['total_events'] += 1
                    
                    # Verify hash chain
                    if event.get('previous_hash') != previous_hash:
                        results['invalid_hashes'] += 1
                        results['broken_links'].append({
                            'line': line_num,
                            'event_id': event.get('event_id'),
                            'expected_prev': previous_hash,
                            'actual_prev': event.get('previous_hash')
                        })
                    else:
                        results['valid_hashes'] += 1
                    
                    previous_hash = event.get('event_hash', previous_hash)
                    
                except json.JSONDecodeError:
                    results['invalid_hashes'] += 1
        
        results['integrity_score'] = results['valid_hashes'] / results['total_events'] if results['total_events'] > 0 else 0
        
        return results


class ComplianceReporter:
    """Generate compliance reports from audit logs."""
    
    def __init__(self, audit_logger: AuditLogger):
        self.logger = audit_logger
    
    def generate_daily_report(self, date: datetime = None) -> Dict:
        """Generate daily compliance report."""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        decision_file = self.logger.decision_log_path / f"decision_{date_str}.jsonl"
        
        report = {
            'report_date': date_str,
            'generated_at': datetime.now().isoformat(),
            'decisions': {
                'total': 0,
                'approved': 0,
                'rejected': 0,
                'manual_review': 0
            },
            'risk_distribution': {
                'low': 0,
                'medium': 0,
                'high': 0,
                'very_high': 0
            },
            'processing_times': [],
            'fairness_checks': 0,
            'errors': 0
        }
        
        if not decision_file.exists():
            return report
        
        with open(decision_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line)
                    report['decisions']['total'] += 1
                    
                    outcome = event.get('decision_outcome', 'unknown')
                    if outcome in report['decisions']:
                        report['decisions'][outcome] += 1
                    
                    risk = event.get('risk_category', 'unknown')
                    if risk in report['risk_distribution']:
                        report['risk_distribution'][risk] += 1
                    
                    if event.get('processing_time_ms'):
                        report['processing_times'].append(event['processing_time_ms'])
                        
                except json.JSONDecodeError:
                    continue
        
        # Calculate stats
        if report['processing_times']:
            times = report['processing_times']
            report['avg_processing_time_ms'] = sum(times) / len(times)
            report['max_processing_time_ms'] = max(times)
            report['min_processing_time_ms'] = min(times)
        
        del report['processing_times']  # Remove raw data
        
        # Calculate approval rate
        if report['decisions']['total'] > 0:
            report['approval_rate'] = report['decisions']['approved'] / report['decisions']['total']
        
        return report


# Global audit logger instance
audit_logger = AuditLogger()


def log_prediction(application_data: Dict, prediction_result: Dict,
                   explanation: Dict = None, processing_time_ms: float = 0) -> AuditEvent:
    """Convenience function for logging predictions."""
    return audit_logger.log_prediction(
        application_data, prediction_result, explanation, processing_time_ms
    )


def log_error(error: Exception, context: Dict = None) -> AuditEvent:
    """Convenience function for logging errors."""
    return audit_logger.log_error(error, context)


if __name__ == "__main__":
    # Test audit logging
    print("Testing Audit Logger...")
    
    # Test prediction logging
    app_data = {
        'applicant_id': 'APP123456',
        'applicant_name': 'Rahul Kumar',
        'age': 30,
        'monthly_income': 75000,
        'loan_amount': 500000,
        'cibil_score': 720,
        'employment_type': 'Salaried'
    }
    
    prediction = {
        'approved': True,
        'approval_probability': 0.78,
        'confidence': 0.78
    }
    
    explanation = {
        'positive_factors': [
            {'display_name': 'Good CIBIL Score'},
            {'display_name': 'Stable Employment'}
        ],
        'negative_factors': [
            {'display_name': 'Limited Credit History'}
        ],
        'base_value': 0.5
    }
    
    event = log_prediction(app_data, prediction, explanation, processing_time_ms=125.5)
    print(f"Logged event: {event.event_id}")
    print(f"Session summary: {audit_logger.get_session_summary()}")
