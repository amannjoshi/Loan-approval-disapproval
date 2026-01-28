"""
Alerts & Anomaly Detection Routes
==================================
API endpoints for fraud detection, anomaly monitoring, and alert management.

Author: Loan Analytics Team
Version: 1.0.0
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, require_admin, require_manager_or_admin
from database.models import User
from services.anomaly_detection_service import (
    AnomalyDetectionService,
    AlertSeverity,
    AlertType,
    AlertStatus,
    ApplicationEvent,
    get_anomaly_detection_service
)


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ApplicationEventRequest(BaseModel):
    """Application event for anomaly analysis."""
    application_id: str
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    loan_amount: float = Field(..., gt=0)
    monthly_income: float = Field(..., ge=0)
    outcome: str = Field(..., description="approved, rejected, or pending")
    location: Optional[str] = None
    user_agent: Optional[str] = None


class AlertResponse(BaseModel):
    """Alert response model."""
    alert_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    details: dict
    timestamp: str
    status: str
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[str]
    notes: List[str]


class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    alert_id: str


class AlertResolveRequest(BaseModel):
    """Request to resolve an alert."""
    alert_id: str
    resolution_note: str
    false_positive: bool = False


class AlertStatisticsResponse(BaseModel):
    """Alert statistics response."""
    total_alerts: int
    today_alerts: int
    active_alerts: int
    critical_unresolved: int
    by_severity: dict
    by_type: dict
    by_status: dict


class AnomalyMetricsResponse(BaseModel):
    """Anomaly metrics response."""
    total_applications: int
    total_rejections: int
    rejection_rate: float
    avg_loan_amount: float
    std_loan_amount: float
    unique_pans: int
    duplicate_pan_count: int
    period_start: str
    period_end: str


class ConfigUpdateRequest(BaseModel):
    """Request to update anomaly detection config."""
    rejection_rate_threshold: Optional[float] = Field(None, ge=0, le=1)
    max_applications_per_pan: Optional[int] = Field(None, ge=1)
    max_loan_to_income_ratio: Optional[int] = Field(None, ge=1)
    velocity_threshold: Optional[int] = Field(None, ge=1)
    velocity_window_minutes: Optional[int] = Field(None, ge=1)


# =============================================================================
# Alert Routes
# =============================================================================

@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    alert_type: Optional[str] = Query(None, description="Filter by type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get active alerts with optional filtering.
    
    Returns alerts sorted by timestamp (newest first).
    """
    service = get_anomaly_detection_service()
    
    severity_enum = AlertSeverity(severity) if severity else None
    alerts = service.get_active_alerts(severity=severity_enum)
    
    # Filter by type
    if alert_type:
        alerts = [a for a in alerts if a.alert_type.value == alert_type]
    
    # Filter by status
    if status_filter:
        alerts = [a for a in alerts if a.status.value == status_filter]
    
    # Limit results
    alerts = alerts[:limit]
    
    return [
        AlertResponse(
            alert_id=a.alert_id,
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            title=a.title,
            description=a.description,
            details=a.details,
            timestamp=a.timestamp.isoformat(),
            status=a.status.value,
            acknowledged_by=a.acknowledged_by,
            acknowledged_at=a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            resolved_by=a.resolved_by,
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            notes=a.notes
        )
        for a in alerts
    ]


@router.get("/alerts/critical")
async def get_critical_alerts(
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get all unresolved critical and high severity alerts.
    
    These require immediate attention.
    """
    service = get_anomaly_detection_service()
    
    critical = service.get_active_alerts(severity=AlertSeverity.CRITICAL)
    high = service.get_active_alerts(severity=AlertSeverity.HIGH)
    
    all_urgent = critical + high
    unresolved = [
        a for a in all_urgent 
        if a.status not in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]
    ]
    
    return {
        'count': len(unresolved),
        'critical_count': len([a for a in unresolved if a.severity == AlertSeverity.CRITICAL]),
        'high_count': len([a for a in unresolved if a.severity == AlertSeverity.HIGH]),
        'alerts': [
            {
                'alert_id': a.alert_id,
                'severity': a.severity.value,
                'title': a.title,
                'description': a.description,
                'timestamp': a.timestamp.isoformat(),
                'status': a.status.value,
                'details': a.details
            }
            for a in sorted(unresolved, key=lambda x: (
                0 if x.severity == AlertSeverity.CRITICAL else 1,
                x.timestamp
            ), reverse=True)
        ]
    }


@router.get("/alerts/{alert_id}")
async def get_alert_details(
    alert_id: str,
    current_user: User = Depends(require_manager_or_admin)
):
    """Get detailed information about a specific alert."""
    service = get_anomaly_detection_service()
    
    if alert_id not in service.alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    alert = service.alerts[alert_id]
    
    return AlertResponse(
        alert_id=alert.alert_id,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        title=alert.title,
        description=alert.description,
        details=alert.details,
        timestamp=alert.timestamp.isoformat(),
        status=alert.status.value,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        notes=alert.notes
    )


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AlertAcknowledgeRequest,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Acknowledge an alert.
    
    Acknowledging indicates someone is looking at the alert.
    """
    service = get_anomaly_detection_service()
    
    success = service.acknowledge_alert(
        request.alert_id,
        str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {request.alert_id} not found"
        )
    
    return {
        'message': 'Alert acknowledged',
        'alert_id': request.alert_id,
        'acknowledged_by': str(current_user.id)
    }


@router.post("/alerts/resolve")
async def resolve_alert(
    request: AlertResolveRequest,
    current_user: User = Depends(require_admin)
):
    """
    Resolve an alert.
    
    **Admin only.** Provide resolution notes and whether it was a false positive.
    """
    service = get_anomaly_detection_service()
    
    success = service.resolve_alert(
        request.alert_id,
        str(current_user.id),
        request.resolution_note,
        request.false_positive
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {request.alert_id} not found"
        )
    
    return {
        'message': 'Alert resolved' if not request.false_positive else 'Alert marked as false positive',
        'alert_id': request.alert_id,
        'resolved_by': str(current_user.id)
    }


# =============================================================================
# Statistics & Metrics Routes
# =============================================================================

@router.get("/statistics", response_model=AlertStatisticsResponse)
async def get_alert_statistics(
    current_user: User = Depends(require_manager_or_admin)
):
    """Get alert statistics and summary."""
    service = get_anomaly_detection_service()
    stats = service.get_alert_statistics()
    
    return AlertStatisticsResponse(**stats)


@router.get("/metrics", response_model=AnomalyMetricsResponse)
async def get_anomaly_metrics(
    current_user: User = Depends(require_manager_or_admin)
):
    """Get current anomaly detection metrics."""
    service = get_anomaly_detection_service()
    metrics = service.get_metrics()
    
    return AnomalyMetricsResponse(
        total_applications=metrics.total_applications,
        total_rejections=metrics.total_rejections,
        rejection_rate=round(metrics.rejection_rate, 4),
        avg_loan_amount=round(metrics.avg_loan_amount, 2),
        std_loan_amount=round(metrics.std_loan_amount, 2),
        unique_pans=metrics.unique_pans,
        duplicate_pan_count=metrics.duplicate_pan_count,
        period_start=metrics.period_start.isoformat(),
        period_end=metrics.period_end.isoformat()
    )


@router.get("/dashboard")
async def get_anomaly_dashboard(
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get comprehensive anomaly detection dashboard data.
    
    Returns alerts, metrics, and trends in one call.
    """
    service = get_anomaly_detection_service()
    
    # Get statistics
    stats = service.get_alert_statistics()
    
    # Get metrics
    metrics = service.get_metrics()
    
    # Get critical alerts
    critical_alerts = [
        a for a in service.get_active_alerts() 
        if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]
        and a.status not in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]
    ]
    
    # Get recent alerts (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_alerts = [
        a for a in service.alerts.values()
        if a.timestamp > yesterday
    ]
    
    return {
        'summary': {
            'total_alerts_today': stats['today_alerts'],
            'active_alerts': stats['active_alerts'],
            'critical_unresolved': stats['critical_unresolved'],
            'current_rejection_rate': f"{metrics.rejection_rate:.1%}",
            'duplicate_pan_alerts': len([
                a for a in recent_alerts 
                if a.alert_type == AlertType.DUPLICATE_PAN
            ]),
            'velocity_attacks': len([
                a for a in recent_alerts 
                if a.alert_type == AlertType.VELOCITY_ATTACK
            ])
        },
        'alerts_by_severity': stats['by_severity'],
        'alerts_by_type': stats['by_type'],
        'critical_alerts': [
            {
                'alert_id': a.alert_id,
                'title': a.title,
                'severity': a.severity.value,
                'timestamp': a.timestamp.isoformat()
            }
            for a in critical_alerts[:10]
        ],
        'metrics': {
            'applications_last_hour': metrics.total_applications,
            'rejections_last_hour': metrics.total_rejections,
            'rejection_rate': f"{metrics.rejection_rate:.1%}",
            'avg_loan_amount': f"₹{metrics.avg_loan_amount:,.0f}",
            'unique_applicants': metrics.unique_pans,
            'duplicate_applications': metrics.duplicate_pan_count
        },
        'health_status': 'critical' if stats['critical_unresolved'] > 0 else (
            'warning' if stats['active_alerts'] > 10 else 'healthy'
        )
    }


# =============================================================================
# Analysis Routes
# =============================================================================

@router.post("/analyze")
async def analyze_application(
    request: ApplicationEventRequest,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Analyze a single application for anomalies.
    
    This is typically called automatically during application processing,
    but can also be used for manual analysis.
    """
    service = get_anomaly_detection_service()
    
    event = ApplicationEvent(
        application_id=request.application_id,
        pan_number=request.pan_number,
        aadhaar_number=request.aadhaar_number,
        phone_number=request.phone_number,
        email=request.email,
        ip_address=request.ip_address,
        device_fingerprint=request.device_fingerprint,
        loan_amount=request.loan_amount,
        monthly_income=request.monthly_income,
        timestamp=datetime.utcnow(),
        outcome=request.outcome,
        location=request.location,
        user_agent=request.user_agent
    )
    
    triggered_alerts = service.analyze_application(event)
    
    return {
        'application_id': request.application_id,
        'alerts_triggered': len(triggered_alerts),
        'alerts': [
            {
                'alert_id': a.alert_id,
                'type': a.alert_type.value,
                'severity': a.severity.value,
                'title': a.title,
                'description': a.description
            }
            for a in triggered_alerts
        ],
        'risk_level': 'critical' if any(a.severity == AlertSeverity.CRITICAL for a in triggered_alerts) else (
            'high' if any(a.severity == AlertSeverity.HIGH for a in triggered_alerts) else (
                'medium' if triggered_alerts else 'low'
            )
        )
    }


@router.get("/check-pan/{pan_number}")
async def check_pan_history(
    pan_number: str,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Check application history for a specific PAN.
    
    Useful for investigating duplicate applications.
    """
    service = get_anomaly_detection_service()
    
    pan = pan_number.upper()
    
    # Get applications with this PAN
    applications = [
        app for app in service.application_history
        if app.pan_number and app.pan_number.upper() == pan
    ]
    
    # Get alerts related to this PAN
    related_alerts = [
        a for a in service.alerts.values()
        if a.details.get('pan_masked', '').upper()[:4] == pan[:4]
        or pan in str(a.details)
    ]
    
    return {
        'pan_masked': f"{pan[:4]}XXXX{pan[-2:]}",
        'total_applications': len(applications),
        'applications': [
            {
                'application_id': app.application_id,
                'loan_amount': app.loan_amount,
                'outcome': app.outcome,
                'timestamp': app.timestamp.isoformat()
            }
            for app in sorted(applications, key=lambda x: x.timestamp, reverse=True)[:10]
        ],
        'related_alerts': len(related_alerts),
        'risk_assessment': 'high' if len(applications) > 5 else (
            'medium' if len(applications) > 2 else 'low'
        )
    }


# =============================================================================
# Configuration Routes
# =============================================================================

@router.get("/config")
async def get_anomaly_config(
    current_user: User = Depends(require_admin)
):
    """Get current anomaly detection configuration."""
    service = get_anomaly_detection_service()
    
    return {
        'thresholds': {
            'rejection_rate_threshold': service.rejection_rate_threshold,
            'rejection_spike_window_minutes': service.rejection_spike_window_minutes,
            'min_applications_for_spike': service.min_applications_for_spike,
            'duplicate_pan_window_hours': service.duplicate_pan_window_hours,
            'max_applications_per_pan': service.max_applications_per_pan,
            'high_loan_multiplier': service.high_loan_multiplier,
            'max_loan_to_income_ratio': service.max_loan_to_income_ratio,
            'velocity_window_minutes': service.velocity_window_minutes,
            'velocity_threshold': service.velocity_threshold,
            'suspicious_hours_start': service.suspicious_hours_start,
            'suspicious_hours_end': service.suspicious_hours_end
        },
        'baseline': {
            'rejection_rate': service.baseline_rejection_rate
        }
    }


@router.post("/config")
async def update_anomaly_config(
    request: ConfigUpdateRequest,
    current_user: User = Depends(require_admin)
):
    """
    Update anomaly detection configuration.
    
    **Admin only.** Changes take effect immediately.
    """
    service = get_anomaly_detection_service()
    
    updated = []
    
    if request.rejection_rate_threshold is not None:
        service.rejection_rate_threshold = request.rejection_rate_threshold
        updated.append('rejection_rate_threshold')
    
    if request.max_applications_per_pan is not None:
        service.max_applications_per_pan = request.max_applications_per_pan
        updated.append('max_applications_per_pan')
    
    if request.max_loan_to_income_ratio is not None:
        service.max_loan_to_income_ratio = request.max_loan_to_income_ratio
        updated.append('max_loan_to_income_ratio')
    
    if request.velocity_threshold is not None:
        service.velocity_threshold = request.velocity_threshold
        updated.append('velocity_threshold')
    
    if request.velocity_window_minutes is not None:
        service.velocity_window_minutes = request.velocity_window_minutes
        updated.append('velocity_window_minutes')
    
    return {
        'message': 'Configuration updated',
        'updated_fields': updated
    }
