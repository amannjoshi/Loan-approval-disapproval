"""
Anomaly Detection & Alerting Service
=====================================
Real-time fraud detection and anomaly monitoring for loan applications.

Monitors for:
1. Sudden spike in rejections
2. Same PAN/ID applying multiple times
3. Abnormally high loan amounts
4. Velocity attacks (rapid applications)
5. Geographic anomalies
6. Time-based patterns (unusual hours)

Author: Loan Analytics Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
import statistics
import logging
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    REJECTION_SPIKE = "rejection_spike"
    DUPLICATE_PAN = "duplicate_pan"
    DUPLICATE_AADHAAR = "duplicate_aadhaar"
    HIGH_LOAN_AMOUNT = "high_loan_amount"
    VELOCITY_ATTACK = "velocity_attack"
    UNUSUAL_HOURS = "unusual_hours"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    INCOME_MISMATCH = "income_mismatch"
    RAPID_REAPPLICATION = "rapid_reapplication"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    SYSTEM_ANOMALY = "system_anomaly"


class AlertStatus(str, Enum):
    """Alert status."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


# =============================================================================
# Data Transfer Objects
# =============================================================================

@dataclass
class Alert:
    """An anomaly alert."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: AlertStatus = AlertStatus.NEW
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'notes': self.notes
        }


@dataclass
class ApplicationEvent:
    """A single application event for tracking."""
    application_id: str
    pan_number: Optional[str]
    aadhaar_number: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    ip_address: Optional[str]
    device_fingerprint: Optional[str]
    loan_amount: float
    monthly_income: float
    timestamp: datetime
    outcome: str  # 'approved', 'rejected', 'pending'
    location: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class AnomalyMetrics:
    """Metrics for anomaly detection."""
    total_applications: int = 0
    total_rejections: int = 0
    rejection_rate: float = 0.0
    avg_loan_amount: float = 0.0
    std_loan_amount: float = 0.0
    unique_pans: int = 0
    duplicate_pan_count: int = 0
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Anomaly Detection Service
# =============================================================================

class AnomalyDetectionService:
    """
    Real-time anomaly detection and alerting service.
    
    Monitors application patterns and triggers alerts for suspicious activity.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the anomaly detection service.
        
        Args:
            config: Configuration dictionary with thresholds
        """
        self.config = config or {}
        
        # === Thresholds ===
        # Rejection spike
        self.rejection_rate_threshold = self.config.get('rejection_rate_threshold', 0.5)  # 50%
        self.rejection_spike_window_minutes = self.config.get('rejection_spike_window', 30)
        self.min_applications_for_spike = self.config.get('min_applications_for_spike', 10)
        
        # Duplicate detection
        self.duplicate_pan_window_hours = self.config.get('duplicate_pan_window', 24)
        self.max_applications_per_pan = self.config.get('max_applications_per_pan', 3)
        
        # Loan amount
        self.high_loan_multiplier = self.config.get('high_loan_multiplier', 3.0)  # 3x std dev
        self.max_loan_to_income_ratio = self.config.get('max_loan_to_income_ratio', 100)  # 100x monthly income
        
        # Velocity
        self.velocity_window_minutes = self.config.get('velocity_window', 5)
        self.velocity_threshold = self.config.get('velocity_threshold', 5)  # 5 apps in 5 mins from same source
        
        # Time-based
        self.suspicious_hours_start = self.config.get('suspicious_hours_start', 1)  # 1 AM
        self.suspicious_hours_end = self.config.get('suspicious_hours_end', 5)  # 5 AM
        
        # === Storage ===
        self.alerts: Dict[str, Alert] = {}
        self.application_history: List[ApplicationEvent] = []
        self.pan_applications: Dict[str, List[datetime]] = defaultdict(list)
        self.aadhaar_applications: Dict[str, List[datetime]] = defaultdict(list)
        self.ip_applications: Dict[str, List[datetime]] = defaultdict(list)
        self.device_applications: Dict[str, List[datetime]] = defaultdict(list)
        
        # Statistics for baseline
        self.loan_amounts: List[float] = []
        self.hourly_rejection_rates: Dict[int, List[float]] = defaultdict(list)
        self.baseline_rejection_rate: float = 0.2  # 20% baseline
        
        # Alert callbacks
        self.alert_callbacks: List[callable] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Alert counter
        self._alert_counter = 0
        
        logger.info("🔍 Anomaly Detection Service initialized")
    
    def register_alert_callback(self, callback: callable):
        """Register a callback to be called when alerts are triggered."""
        self.alert_callbacks.append(callback)
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        self._alert_counter += 1
        return f"ALT-{datetime.utcnow().strftime('%Y%m%d')}-{self._alert_counter:05d}"
    
    def _trigger_alert(self, alert: Alert):
        """Trigger an alert and notify callbacks."""
        with self._lock:
            self.alerts[alert.alert_id] = alert
        
        # Log alert
        log_level = {
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(alert.severity, logging.WARNING)
        
        logger.log(log_level, f"🚨 ALERT [{alert.severity.value.upper()}]: {alert.title}")
        logger.log(log_level, f"   Details: {alert.description}")
        
        # Save to file
        self._save_alert_to_file(alert)
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _save_alert_to_file(self, alert: Alert):
        """Save alert to JSONL file."""
        try:
            alerts_dir = Path("logs/alerts")
            alerts_dir.mkdir(parents=True, exist_ok=True)
            
            alert_file = alerts_dir / f"alerts_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
            
            with open(alert_file, 'a') as f:
                f.write(json.dumps(alert.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to save alert to file: {e}")
    
    # =========================================================================
    # Main Analysis Entry Point
    # =========================================================================
    
    def analyze_application(self, event: ApplicationEvent) -> List[Alert]:
        """
        Analyze a single application for anomalies.
        
        Args:
            event: Application event to analyze
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        # Store event
        with self._lock:
            self.application_history.append(event)
            self.loan_amounts.append(event.loan_amount)
            
            # Keep history manageable (last 10,000 events)
            if len(self.application_history) > 10000:
                self.application_history = self.application_history[-10000:]
            if len(self.loan_amounts) > 10000:
                self.loan_amounts = self.loan_amounts[-10000:]
        
        # Run all checks
        checks = [
            self._check_duplicate_pan,
            self._check_duplicate_aadhaar,
            self._check_high_loan_amount,
            self._check_velocity_attack,
            self._check_unusual_hours,
            self._check_income_mismatch,
            self._check_rapid_reapplication,
        ]
        
        for check in checks:
            try:
                alert = check(event)
                if alert:
                    self._trigger_alert(alert)
                    triggered_alerts.append(alert)
            except Exception as e:
                logger.error(f"Anomaly check failed: {e}")
        
        # Periodic checks (rejection spike)
        self._check_rejection_spike(event)
        
        return triggered_alerts
    
    # =========================================================================
    # Individual Anomaly Checks
    # =========================================================================
    
    def _check_duplicate_pan(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for multiple applications with same PAN."""
        if not event.pan_number:
            return None
        
        pan = event.pan_number.upper()
        window = datetime.utcnow() - timedelta(hours=self.duplicate_pan_window_hours)
        
        with self._lock:
            # Add current application
            self.pan_applications[pan].append(event.timestamp)
            
            # Clean old entries
            self.pan_applications[pan] = [
                t for t in self.pan_applications[pan] if t > window
            ]
            
            count = len(self.pan_applications[pan])
        
        if count > self.max_applications_per_pan:
            severity = AlertSeverity.HIGH if count > 5 else AlertSeverity.MEDIUM
            
            return Alert(
                alert_id=self._generate_alert_id(),
                alert_type=AlertType.DUPLICATE_PAN,
                severity=severity,
                title=f"🔴 Duplicate PAN Detected: {count} applications in {self.duplicate_pan_window_hours}h",
                description=(
                    f"PAN {pan[:4]}XXXX{pan[-2:]} has submitted {count} loan applications "
                    f"in the last {self.duplicate_pan_window_hours} hours. "
                    f"Maximum allowed: {self.max_applications_per_pan}."
                ),
                details={
                    'pan_masked': f"{pan[:4]}XXXX{pan[-2:]}",
                    'application_count': count,
                    'window_hours': self.duplicate_pan_window_hours,
                    'threshold': self.max_applications_per_pan,
                    'latest_application_id': event.application_id,
                    'latest_loan_amount': event.loan_amount
                }
            )
        
        return None
    
    def _check_duplicate_aadhaar(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for multiple applications with same Aadhaar."""
        if not event.aadhaar_number:
            return None
        
        aadhaar = event.aadhaar_number
        window = datetime.utcnow() - timedelta(hours=self.duplicate_pan_window_hours)
        
        with self._lock:
            self.aadhaar_applications[aadhaar].append(event.timestamp)
            self.aadhaar_applications[aadhaar] = [
                t for t in self.aadhaar_applications[aadhaar] if t > window
            ]
            count = len(self.aadhaar_applications[aadhaar])
        
        if count > self.max_applications_per_pan:
            return Alert(
                alert_id=self._generate_alert_id(),
                alert_type=AlertType.DUPLICATE_AADHAAR,
                severity=AlertSeverity.HIGH,
                title=f"🔴 Duplicate Aadhaar Detected: {count} applications",
                description=(
                    f"Aadhaar XXXX-XXXX-{aadhaar[-4:]} has submitted {count} applications "
                    f"in the last {self.duplicate_pan_window_hours} hours."
                ),
                details={
                    'aadhaar_masked': f"XXXX-XXXX-{aadhaar[-4:]}",
                    'application_count': count,
                    'latest_application_id': event.application_id
                }
            )
        
        return None
    
    def _check_high_loan_amount(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for abnormally high loan amounts."""
        # Check against income
        if event.monthly_income > 0:
            loan_to_income = event.loan_amount / event.monthly_income
            
            if loan_to_income > self.max_loan_to_income_ratio:
                return Alert(
                    alert_id=self._generate_alert_id(),
                    alert_type=AlertType.HIGH_LOAN_AMOUNT,
                    severity=AlertSeverity.HIGH,
                    title=f"🔴 Abnormally High Loan Amount: ₹{event.loan_amount:,.0f}",
                    description=(
                        f"Loan amount (₹{event.loan_amount:,.0f}) is {loan_to_income:.0f}x "
                        f"the monthly income (₹{event.monthly_income:,.0f}). "
                        f"Maximum ratio allowed: {self.max_loan_to_income_ratio}x."
                    ),
                    details={
                        'loan_amount': event.loan_amount,
                        'monthly_income': event.monthly_income,
                        'loan_to_income_ratio': round(loan_to_income, 2),
                        'threshold_ratio': self.max_loan_to_income_ratio,
                        'application_id': event.application_id,
                        'pan_masked': f"{event.pan_number[:4]}XXXX{event.pan_number[-2:]}" if event.pan_number else None
                    }
                )
        
        # Check against statistical baseline
        if len(self.loan_amounts) >= 100:
            mean_amount = statistics.mean(self.loan_amounts)
            std_amount = statistics.stdev(self.loan_amounts)
            
            if std_amount > 0:
                z_score = (event.loan_amount - mean_amount) / std_amount
                
                if z_score > self.high_loan_multiplier:
                    return Alert(
                        alert_id=self._generate_alert_id(),
                        alert_type=AlertType.HIGH_LOAN_AMOUNT,
                        severity=AlertSeverity.MEDIUM,
                        title=f"⚠️ Statistical Outlier: Loan Amount ₹{event.loan_amount:,.0f}",
                        description=(
                            f"Loan amount is {z_score:.1f} standard deviations above average. "
                            f"Average: ₹{mean_amount:,.0f}, This: ₹{event.loan_amount:,.0f}."
                        ),
                        details={
                            'loan_amount': event.loan_amount,
                            'average_amount': round(mean_amount, 2),
                            'std_deviation': round(std_amount, 2),
                            'z_score': round(z_score, 2),
                            'application_id': event.application_id
                        }
                    )
        
        return None
    
    def _check_velocity_attack(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for rapid applications from same source (velocity attack)."""
        window = datetime.utcnow() - timedelta(minutes=self.velocity_window_minutes)
        
        # Check by IP
        if event.ip_address:
            with self._lock:
                self.ip_applications[event.ip_address].append(event.timestamp)
                self.ip_applications[event.ip_address] = [
                    t for t in self.ip_applications[event.ip_address] if t > window
                ]
                ip_count = len(self.ip_applications[event.ip_address])
            
            if ip_count >= self.velocity_threshold:
                return Alert(
                    alert_id=self._generate_alert_id(),
                    alert_type=AlertType.VELOCITY_ATTACK,
                    severity=AlertSeverity.CRITICAL,
                    title=f"🚨 VELOCITY ATTACK: {ip_count} apps from same IP in {self.velocity_window_minutes} min",
                    description=(
                        f"Detected {ip_count} applications from IP {event.ip_address} "
                        f"in the last {self.velocity_window_minutes} minutes. "
                        f"This indicates a potential automated attack."
                    ),
                    details={
                        'ip_address': event.ip_address,
                        'application_count': ip_count,
                        'window_minutes': self.velocity_window_minutes,
                        'threshold': self.velocity_threshold,
                        'latest_application_id': event.application_id,
                        'action_recommended': 'Block IP temporarily'
                    }
                )
        
        # Check by device fingerprint
        if event.device_fingerprint:
            with self._lock:
                self.device_applications[event.device_fingerprint].append(event.timestamp)
                self.device_applications[event.device_fingerprint] = [
                    t for t in self.device_applications[event.device_fingerprint] if t > window
                ]
                device_count = len(self.device_applications[event.device_fingerprint])
            
            if device_count >= self.velocity_threshold:
                return Alert(
                    alert_id=self._generate_alert_id(),
                    alert_type=AlertType.VELOCITY_ATTACK,
                    severity=AlertSeverity.CRITICAL,
                    title=f"🚨 VELOCITY ATTACK: {device_count} apps from same device",
                    description=(
                        f"Detected {device_count} applications from same device fingerprint "
                        f"in {self.velocity_window_minutes} minutes."
                    ),
                    details={
                        'device_fingerprint': event.device_fingerprint[:16] + '...',
                        'application_count': device_count,
                        'window_minutes': self.velocity_window_minutes
                    }
                )
        
        return None
    
    def _check_unusual_hours(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for applications during unusual hours."""
        hour = event.timestamp.hour
        
        if self.suspicious_hours_start <= hour <= self.suspicious_hours_end:
            return Alert(
                alert_id=self._generate_alert_id(),
                alert_type=AlertType.UNUSUAL_HOURS,
                severity=AlertSeverity.LOW,
                title=f"⚠️ Unusual Hours Application: {hour}:00",
                description=(
                    f"Application submitted at {event.timestamp.strftime('%H:%M')} "
                    f"which is during unusual hours ({self.suspicious_hours_start}:00 - "
                    f"{self.suspicious_hours_end}:00). Flagged for review."
                ),
                details={
                    'application_id': event.application_id,
                    'submission_hour': hour,
                    'submission_time': event.timestamp.isoformat(),
                    'suspicious_range': f"{self.suspicious_hours_start}:00 - {self.suspicious_hours_end}:00"
                }
            )
        
        return None
    
    def _check_income_mismatch(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for suspicious income to loan amount patterns."""
        if event.monthly_income <= 0:
            return None
        
        # Very low income requesting high loan
        if event.monthly_income < 15000 and event.loan_amount > 500000:
            return Alert(
                alert_id=self._generate_alert_id(),
                alert_type=AlertType.INCOME_MISMATCH,
                severity=AlertSeverity.MEDIUM,
                title=f"⚠️ Income Mismatch: Low income, high loan request",
                description=(
                    f"Monthly income ₹{event.monthly_income:,.0f} seems inconsistent with "
                    f"loan request of ₹{event.loan_amount:,.0f}. Possible income inflation or fraud."
                ),
                details={
                    'monthly_income': event.monthly_income,
                    'loan_amount': event.loan_amount,
                    'ratio': round(event.loan_amount / event.monthly_income, 2),
                    'application_id': event.application_id
                }
            )
        
        return None
    
    def _check_rapid_reapplication(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for rapid reapplication after rejection."""
        if not event.pan_number:
            return None
        
        # Look for recent rejections with same PAN
        recent_window = datetime.utcnow() - timedelta(hours=1)
        
        with self._lock:
            recent_apps = [
                app for app in self.application_history
                if app.pan_number == event.pan_number
                and app.timestamp > recent_window
                and app.application_id != event.application_id
            ]
            
            rejected_recently = any(app.outcome == 'rejected' for app in recent_apps)
        
        if rejected_recently and len(recent_apps) >= 2:
            return Alert(
                alert_id=self._generate_alert_id(),
                alert_type=AlertType.RAPID_REAPPLICATION,
                severity=AlertSeverity.MEDIUM,
                title=f"⚠️ Rapid Reapplication After Rejection",
                description=(
                    f"PAN {event.pan_number[:4]}XXXX{event.pan_number[-2:]} reapplied within 1 hour "
                    f"of rejection. Total attempts: {len(recent_apps) + 1}."
                ),
                details={
                    'pan_masked': f"{event.pan_number[:4]}XXXX{event.pan_number[-2:]}",
                    'attempts_in_hour': len(recent_apps) + 1,
                    'application_id': event.application_id
                }
            )
        
        return None
    
    def _check_rejection_spike(self, event: ApplicationEvent) -> Optional[Alert]:
        """Check for sudden spike in rejection rates."""
        window = datetime.utcnow() - timedelta(minutes=self.rejection_spike_window_minutes)
        
        with self._lock:
            recent_apps = [
                app for app in self.application_history
                if app.timestamp > window
            ]
        
        if len(recent_apps) < self.min_applications_for_spike:
            return None
        
        rejections = sum(1 for app in recent_apps if app.outcome == 'rejected')
        rejection_rate = rejections / len(recent_apps)
        
        # Check if significantly higher than baseline
        if rejection_rate > self.rejection_rate_threshold and rejection_rate > self.baseline_rejection_rate * 1.5:
            alert = Alert(
                alert_id=self._generate_alert_id(),
                alert_type=AlertType.REJECTION_SPIKE,
                severity=AlertSeverity.HIGH,
                title=f"🔴 Rejection Spike: {rejection_rate:.0%} in last {self.rejection_spike_window_minutes} min",
                description=(
                    f"Rejection rate spiked to {rejection_rate:.0%} "
                    f"({rejections}/{len(recent_apps)} applications) in the last "
                    f"{self.rejection_spike_window_minutes} minutes. "
                    f"Baseline: {self.baseline_rejection_rate:.0%}."
                ),
                details={
                    'current_rejection_rate': round(rejection_rate, 3),
                    'baseline_rejection_rate': round(self.baseline_rejection_rate, 3),
                    'rejections': rejections,
                    'total_applications': len(recent_apps),
                    'window_minutes': self.rejection_spike_window_minutes,
                    'possible_causes': [
                        'System issue with approval logic',
                        'Coordinated fraud attempt',
                        'Data quality issues',
                        'Model drift'
                    ]
                }
            )
            self._trigger_alert(alert)
            return alert
        
        # Update baseline (slow moving average)
        self.baseline_rejection_rate = (self.baseline_rejection_rate * 0.95 + rejection_rate * 0.05)
        
        return None
    
    # =========================================================================
    # Alert Management
    # =========================================================================
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        with self._lock:
            alerts = [
                alert for alert in self.alerts.values()
                if alert.status not in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]
            ]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Get alerts by type."""
        with self._lock:
            return [a for a in self.alerts.values() if a.alert_type == alert_type]
    
    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            if alert_id in self.alerts:
                self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
                self.alerts[alert_id].acknowledged_by = user_id
                self.alerts[alert_id].acknowledged_at = datetime.utcnow()
                return True
        return False
    
    def resolve_alert(
        self, 
        alert_id: str, 
        user_id: str, 
        resolution_note: str,
        false_positive: bool = False
    ) -> bool:
        """Resolve an alert."""
        with self._lock:
            if alert_id in self.alerts:
                self.alerts[alert_id].status = (
                    AlertStatus.FALSE_POSITIVE if false_positive else AlertStatus.RESOLVED
                )
                self.alerts[alert_id].resolved_by = user_id
                self.alerts[alert_id].resolved_at = datetime.utcnow()
                self.alerts[alert_id].notes.append(f"Resolution: {resolution_note}")
                return True
        return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        with self._lock:
            alerts = list(self.alerts.values())
        
        today = datetime.utcnow().date()
        today_alerts = [a for a in alerts if a.timestamp.date() == today]
        
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        
        for alert in alerts:
            by_severity[alert.severity.value] += 1
            by_type[alert.alert_type.value] += 1
            by_status[alert.status.value] += 1
        
        return {
            'total_alerts': len(alerts),
            'today_alerts': len(today_alerts),
            'active_alerts': sum(1 for a in alerts if a.status == AlertStatus.NEW),
            'by_severity': dict(by_severity),
            'by_type': dict(by_type),
            'by_status': dict(by_status),
            'critical_unresolved': sum(
                1 for a in alerts 
                if a.severity == AlertSeverity.CRITICAL 
                and a.status not in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]
            )
        }
    
    def get_metrics(self) -> AnomalyMetrics:
        """Get current anomaly metrics."""
        with self._lock:
            window = datetime.utcnow() - timedelta(hours=1)
            recent = [app for app in self.application_history if app.timestamp > window]
        
        if not recent:
            return AnomalyMetrics()
        
        rejections = sum(1 for app in recent if app.outcome == 'rejected')
        unique_pans = len(set(app.pan_number for app in recent if app.pan_number))
        
        # Count duplicates
        pan_counts = defaultdict(int)
        for app in recent:
            if app.pan_number:
                pan_counts[app.pan_number] += 1
        duplicate_pans = sum(1 for count in pan_counts.values() if count > 1)
        
        amounts = [app.loan_amount for app in recent]
        
        return AnomalyMetrics(
            total_applications=len(recent),
            total_rejections=rejections,
            rejection_rate=rejections / len(recent) if recent else 0,
            avg_loan_amount=statistics.mean(amounts) if amounts else 0,
            std_loan_amount=statistics.stdev(amounts) if len(amounts) > 1 else 0,
            unique_pans=unique_pans,
            duplicate_pan_count=duplicate_pans,
            period_start=min(app.timestamp for app in recent),
            period_end=max(app.timestamp for app in recent)
        )


# =============================================================================
# Factory Function
# =============================================================================

_anomaly_service: Optional[AnomalyDetectionService] = None


def get_anomaly_detection_service(config: Optional[Dict] = None) -> AnomalyDetectionService:
    """Get singleton anomaly detection service."""
    global _anomaly_service
    if _anomaly_service is None:
        _anomaly_service = AnomalyDetectionService(config)
    return _anomaly_service
