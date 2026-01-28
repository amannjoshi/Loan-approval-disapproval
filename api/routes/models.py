"""
Model Management Routes
=======================
API endpoints for model management, rollback, and re-explanation.

Author: Loan Analytics Team
Version: 1.0.0
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, require_manager_or_admin, require_admin
from database.models import User
from services.rollback_service import (
    ModelRollbackService, 
    RollbackReason, 
    get_rollback_service
)
from utils.pii_redactor import redact_pii


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RollbackAnalysisRequest(BaseModel):
    """Request for rollback impact analysis."""
    to_model_id: str
    days_to_analyze: int = Field(default=7, ge=1, le=30)


class RollbackRequest(BaseModel):
    """Request to perform a rollback."""
    reason: str = Field(..., description="Reason code for rollback")
    to_model_id: Optional[str] = Field(None, description="Target model ID (optional)")
    trigger_details: str = Field(..., description="Detailed explanation")
    dry_run: bool = Field(default=False, description="If true, analyze only")


class ReExplainRequest(BaseModel):
    """Request to re-explain a decision."""
    decision_id: str
    use_model_id: Optional[str] = None


class BatchReExplainRequest(BaseModel):
    """Request for batch re-explanation."""
    model_id: str
    days_since: int = Field(default=7, ge=1, le=30)
    limit: int = Field(default=100, ge=1, le=1000)


class ModelComparisonRequest(BaseModel):
    """Request for model comparison."""
    model_ids: List[str]


class RollbackAnalysisResponse(BaseModel):
    """Response with rollback impact analysis."""
    from_model: dict
    to_model: dict
    impact: dict
    recommendation: str


class RollbackResponse(BaseModel):
    """Response after rollback operation."""
    rollback_id: str
    status: str
    from_model_id: str
    to_model_id: str
    affected_decisions_count: int
    message: str


class ReExplanationResponse(BaseModel):
    """Response with re-explanation results."""
    decision_id: str
    original_outcome: str
    new_outcome: str
    outcome_changed: bool
    original_probability: float
    new_probability: float
    explanation_summary: str
    recommendation: str
    requires_manual_review: bool


class ModelStatusResponse(BaseModel):
    """Response with current model status."""
    production_model_id: Optional[str]
    staging_model_id: Optional[str]
    total_models: int
    ab_testing_enabled: bool
    recent_rollbacks: List[dict]


# =============================================================================
# Routes
# =============================================================================

@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get current model deployment status.
    
    Returns information about production model, staging model,
    and recent rollback history.
    """
    service = get_rollback_service()
    
    stats = service.registry.get_registry_stats()
    history = service.get_rollback_history(limit=5)
    
    return ModelStatusResponse(
        production_model_id=stats.get('production_model'),
        staging_model_id=stats.get('staging_model'),
        total_models=stats.get('total_models', 0),
        ab_testing_enabled=stats.get('ab_testing_enabled', False),
        recent_rollbacks=[
            {
                'rollback_id': r.rollback_id,
                'from_model': r.from_model_id,
                'to_model': r.to_model_id,
                'reason': r.reason.value,
                'status': r.status.value,
                'initiated_at': r.initiated_at.isoformat()
            }
            for r in history
        ]
    )


@router.get("/list")
async def list_models(
    status: Optional[str] = Query(None, description="Filter by status"),
    model_type: Optional[str] = Query(None, description="Filter by type"),
    min_accuracy: float = Query(0.0, ge=0.0, le=1.0),
    current_user: User = Depends(require_manager_or_admin)
):
    """
    List all registered models with optional filtering.
    """
    from models.model_registry import ModelStatus
    
    service = get_rollback_service()
    
    status_filter = ModelStatus(status) if status else None
    
    models = service.registry.list_models(
        status=status_filter,
        model_type=model_type,
        min_accuracy=min_accuracy
    )
    
    return {
        'count': len(models),
        'models': [
            {
                'model_id': m.model_id,
                'model_type': m.model_type,
                'version': m.version,
                'status': m.status.value,
                'accuracy': m.accuracy,
                'roc_auc': m.roc_auc,
                'training_date': m.training_date.isoformat(),
                'total_predictions': m.total_predictions
            }
            for m in models
        ]
    }


@router.post("/rollback/analyze", response_model=RollbackAnalysisResponse)
async def analyze_rollback(
    request: RollbackAnalysisRequest,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Analyze the impact of a potential rollback.
    
    Returns detailed impact analysis including affected decisions
    and recommendations.
    """
    service = get_rollback_service()
    
    current_model = service.registry.config.get('production_model_id')
    if not current_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No production model deployed"
        )
    
    since = datetime.utcnow() - timedelta(days=request.days_to_analyze)
    
    analysis = service.analyze_rollback_impact(
        from_model_id=current_model,
        to_model_id=request.to_model_id,
        since=since
    )
    
    return RollbackAnalysisResponse(
        from_model=analysis['from_model'],
        to_model=analysis['to_model'],
        impact=analysis['impact'],
        recommendation=analysis['recommendation']
    )


@router.post("/rollback/execute", response_model=RollbackResponse)
async def execute_rollback(
    request: RollbackRequest,
    current_user: User = Depends(require_admin)
):
    """
    Execute a model rollback.
    
    **Admin only.** This will change the production model.
    Use dry_run=true to preview without executing.
    """
    service = get_rollback_service()
    
    # Validate reason
    try:
        reason = RollbackReason(request.reason)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reason. Must be one of: {[r.value for r in RollbackReason]}"
        )
    
    try:
        record = service.perform_safe_rollback(
            reason=reason,
            triggered_by=str(current_user.id),
            trigger_details=request.trigger_details,
            to_model_id=request.to_model_id,
            dry_run=request.dry_run
        )
        
        action = "analyzed" if request.dry_run else "executed"
        
        return RollbackResponse(
            rollback_id=record.rollback_id,
            status=record.status.value,
            from_model_id=record.from_model_id,
            to_model_id=record.to_model_id,
            affected_decisions_count=record.affected_decisions_count,
            message=f"Rollback {action} successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.post("/rollback/emergency", response_model=RollbackResponse)
async def emergency_rollback(
    reason: str = Query(..., description="Emergency reason"),
    current_user: User = Depends(require_admin)
):
    """
    Emergency rollback with minimal checks.
    
    **Admin only.** Use only when immediate action is required.
    """
    service = get_rollback_service()
    
    try:
        record = service.emergency_rollback(
            triggered_by=str(current_user.id),
            reason=reason
        )
        
        return RollbackResponse(
            rollback_id=record.rollback_id,
            status=record.status.value,
            from_model_id=record.from_model_id,
            to_model_id=record.to_model_id,
            affected_decisions_count=record.affected_decisions_count,
            message="Emergency rollback executed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency rollback failed: {str(e)}"
        )


@router.get("/rollback/history")
async def get_rollback_history(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get rollback history.
    """
    service = get_rollback_service()
    history = service.get_rollback_history(limit=limit)
    
    return {
        'count': len(history),
        'rollbacks': [
            {
                'rollback_id': r.rollback_id,
                'reason': r.reason.value,
                'status': r.status.value,
                'from_model_id': r.from_model_id,
                'to_model_id': r.to_model_id,
                'triggered_by': r.triggered_by,
                'initiated_at': r.initiated_at.isoformat(),
                'completed_at': r.completed_at.isoformat() if r.completed_at else None,
                'affected_decisions_count': r.affected_decisions_count
            }
            for r in history
        ]
    }


@router.get("/rollback/{rollback_id}")
async def get_rollback_details(
    rollback_id: str,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get details of a specific rollback operation.
    """
    service = get_rollback_service()
    record = service.get_rollback_status(rollback_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rollback {rollback_id} not found"
        )
    
    return {
        'rollback_id': record.rollback_id,
        'reason': record.reason.value,
        'status': record.status.value,
        'from_model_id': record.from_model_id,
        'to_model_id': record.to_model_id,
        'from_model_metrics': record.from_model_metrics,
        'to_model_metrics': record.to_model_metrics,
        'triggered_by': record.triggered_by,
        'trigger_details': record.trigger_details,
        'initiated_at': record.initiated_at.isoformat(),
        'completed_at': record.completed_at.isoformat() if record.completed_at else None,
        'affected_decisions_count': record.affected_decisions_count,
        'notes': record.notes
    }


# =============================================================================
# Re-explanation Routes
# =============================================================================

@router.post("/decisions/re-explain", response_model=ReExplanationResponse)
async def re_explain_decision(
    request: ReExplainRequest,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Re-explain a historical decision using current or specified model.
    
    Useful after a rollback to understand how decisions would change.
    """
    service = get_rollback_service()
    
    result = service.re_explain_decision(
        decision_id=request.decision_id,
        use_model_id=request.use_model_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {request.decision_id} not found or could not be re-explained"
        )
    
    return ReExplanationResponse(
        decision_id=result.decision_id,
        original_outcome=result.original_outcome,
        new_outcome=result.new_outcome,
        outcome_changed=result.outcome_changed,
        original_probability=result.original_probability,
        new_probability=result.new_probability,
        explanation_summary=result.explanation_summary,
        recommendation=result.recommendation,
        requires_manual_review=result.requires_manual_review
    )


@router.post("/decisions/re-explain/batch")
async def batch_re_explain_decisions(
    request: BatchReExplainRequest,
    current_user: User = Depends(require_admin)
):
    """
    Batch re-explain decisions made by a specific model.
    
    **Admin only.** Useful after a rollback to identify all affected decisions.
    """
    service = get_rollback_service()
    
    since = datetime.utcnow() - timedelta(days=request.days_since)
    
    results = service.batch_re_explain_decisions(
        model_id=request.model_id,
        since=since,
        limit=request.limit
    )
    
    return {
        'total_processed': results['total_processed'],
        'outcome_changed': results['outcome_changed'],
        'outcome_unchanged': results['outcome_unchanged'],
        'errors': results['errors'],
        'changed_decisions': [
            d for d in results['details'] if d['outcome_changed']
        ]
    }


@router.get("/decisions/{decision_id}/history")
async def get_decision_history(
    decision_id: str,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Get the full history of a decision including any re-explanations.
    """
    service = get_rollback_service()
    decision = service.decision_store.get_decision(decision_id)
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found"
        )
    
    # Redact PII from response
    response_data = {
        'decision_id': decision.decision_id,
        'application_id': decision.application_id,
        'model_id': decision.model_id,
        'model_version': decision.model_version,
        'original_outcome': decision.original_outcome,
        'original_probability': decision.original_probability,
        'original_confidence': decision.original_confidence,
        'decision_timestamp': decision.decision_timestamp.isoformat(),
        're_explained': decision.re_explained,
        're_explanation_model_id': decision.re_explanation_model_id,
        're_explanation_timestamp': (
            decision.re_explanation_timestamp.isoformat() 
            if decision.re_explanation_timestamp else None
        ),
        're_explanation_result': decision.re_explanation_result
    }
    
    return response_data


# =============================================================================
# Model Comparison Routes
# =============================================================================

@router.post("/compare")
async def compare_models(
    request: ModelComparisonRequest,
    current_user: User = Depends(require_manager_or_admin)
):
    """
    Compare metrics across multiple models.
    """
    service = get_rollback_service()
    
    comparison = service.registry.get_model_comparison(request.model_ids)
    
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No models found for comparison"
        )
    
    return {
        'models_compared': len(comparison),
        'comparison': comparison
    }
