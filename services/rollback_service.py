"""
Model Rollback and Decision Re-explanation Service
===================================================
Provides safe model rollback capabilities and the ability to
re-explain historical decisions when a model behaves badly.

Features:
- Safe rollback with pre-checks
- Decision history tracking
- Re-explanation of old decisions with new/old models
- Rollback impact analysis
- Audit trail for all rollback operations

Author: Loan Analytics Team
Version: 1.0.0
"""

import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollbackReason(Enum):
    """Reasons for model rollback."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    FAIRNESS_ISSUES = "fairness_issues"
    BIAS_DETECTED = "bias_detected"
    UNEXPECTED_BEHAVIOR = "unexpected_behavior"
    DATA_DRIFT = "data_drift"
    SECURITY_CONCERN = "security_concern"
    REGULATORY_REQUIREMENT = "regulatory_requirement"
    MANUAL_OVERRIDE = "manual_override"
    EMERGENCY = "emergency"


class RollbackStatus(Enum):
    """Status of rollback operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_FORWARD = "rolled_forward"


@dataclass
class DecisionRecord:
    """Record of a historical decision for re-explanation."""
    decision_id: str
    application_id: str
    model_id: str
    model_version: str
    
    # Input data (anonymized for storage)
    input_features: Dict[str, Any]
    
    # Original decision
    original_outcome: str  # approved, rejected, manual_review
    original_probability: float
    original_confidence: float
    original_explanation: Dict[str, Any]
    
    # Timestamps
    decision_timestamp: datetime
    
    # For re-explanation
    re_explained: bool = False
    re_explanation_model_id: Optional[str] = None
    re_explanation_timestamp: Optional[datetime] = None
    re_explanation_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['decision_timestamp'] = self.decision_timestamp.isoformat()
        if self.re_explanation_timestamp:
            result['re_explanation_timestamp'] = self.re_explanation_timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionRecord':
        """Create from dictionary."""
        data['decision_timestamp'] = datetime.fromisoformat(data['decision_timestamp'])
        if data.get('re_explanation_timestamp'):
            data['re_explanation_timestamp'] = datetime.fromisoformat(data['re_explanation_timestamp'])
        return cls(**data)


@dataclass
class RollbackRecord:
    """Record of a rollback operation."""
    rollback_id: str
    reason: RollbackReason
    status: RollbackStatus
    
    # Models involved
    from_model_id: str
    to_model_id: str
    
    # Metrics at time of rollback
    from_model_metrics: Dict[str, float]
    to_model_metrics: Dict[str, float]
    
    # Who/what triggered
    triggered_by: str  # system, user_id, etc.
    trigger_details: str
    
    # Timestamps
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    
    # Impact analysis
    affected_decisions_count: int = 0
    decisions_to_re_explain: List[str] = field(default_factory=list)
    
    # Notes
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['reason'] = self.reason.value
        result['status'] = self.status.value
        result['initiated_at'] = self.initiated_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RollbackRecord':
        """Create from dictionary."""
        data['reason'] = RollbackReason(data['reason'])
        data['status'] = RollbackStatus(data['status'])
        data['initiated_at'] = datetime.fromisoformat(data['initiated_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class ReExplanationResult:
    """Result of re-explaining a decision."""
    decision_id: str
    original_model_id: str
    re_explanation_model_id: str
    
    # Original vs New comparison
    original_outcome: str
    new_outcome: str
    outcome_changed: bool
    
    original_probability: float
    new_probability: float
    probability_delta: float
    
    # Explanations
    original_factors: List[str]
    new_factors: List[str]
    factors_changed: List[str]
    
    # Summary
    explanation_summary: str
    recommendation: str
    requires_manual_review: bool
    
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DecisionHistoryStore:
    """
    Store for historical decisions.
    Enables re-explanation of past decisions.
    """
    
    def __init__(self, store_path: str = "data/decision_history"):
        """Initialize the decision history store."""
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # Index file for quick lookups
        self.index_file = self.store_path / "index.json"
        self._load_index()
    
    def _load_index(self):
        """Load the decision index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {
                'by_model': {},      # model_id -> [decision_ids]
                'by_date': {},       # date_str -> [decision_ids]
                'by_application': {} # application_id -> decision_id
            }
    
    def _save_index(self):
        """Save the decision index."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def store_decision(self, record: DecisionRecord) -> None:
        """Store a decision record."""
        # Save decision file
        decision_file = self.store_path / f"{record.decision_id}.json"
        with open(decision_file, 'w') as f:
            json.dump(record.to_dict(), f, indent=2)
        
        # Update indices
        model_id = record.model_id
        if model_id not in self.index['by_model']:
            self.index['by_model'][model_id] = []
        self.index['by_model'][model_id].append(record.decision_id)
        
        date_str = record.decision_timestamp.strftime('%Y-%m-%d')
        if date_str not in self.index['by_date']:
            self.index['by_date'][date_str] = []
        self.index['by_date'][date_str].append(record.decision_id)
        
        self.index['by_application'][record.application_id] = record.decision_id
        
        self._save_index()
    
    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Retrieve a decision record."""
        decision_file = self.store_path / f"{decision_id}.json"
        if not decision_file.exists():
            return None
        
        with open(decision_file, 'r') as f:
            data = json.load(f)
        return DecisionRecord.from_dict(data)
    
    def get_decisions_by_model(self, model_id: str) -> List[DecisionRecord]:
        """Get all decisions made by a specific model."""
        decision_ids = self.index['by_model'].get(model_id, [])
        return [self.get_decision(did) for did in decision_ids if self.get_decision(did)]
    
    def get_decisions_in_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        model_id: Optional[str] = None
    ) -> List[DecisionRecord]:
        """Get decisions within a date range."""
        results = []
        
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            decision_ids = self.index['by_date'].get(date_str, [])
            
            for did in decision_ids:
                record = self.get_decision(did)
                if record:
                    if model_id is None or record.model_id == model_id:
                        results.append(record)
            
            current += timedelta(days=1)
        
        return results
    
    def update_decision(self, record: DecisionRecord) -> None:
        """Update an existing decision record."""
        decision_file = self.store_path / f"{record.decision_id}.json"
        with open(decision_file, 'w') as f:
            json.dump(record.to_dict(), f, indent=2)
    
    def get_decisions_needing_re_explanation(
        self,
        model_id: str,
        since: Optional[datetime] = None
    ) -> List[DecisionRecord]:
        """Get decisions that may need re-explanation after rollback."""
        decisions = self.get_decisions_by_model(model_id)
        
        if since:
            decisions = [d for d in decisions if d.decision_timestamp >= since]
        
        # Filter to those not yet re-explained
        return [d for d in decisions if not d.re_explained]


class ModelRollbackService:
    """
    Service for safe model rollback and decision re-explanation.
    
    Provides:
    - Pre-rollback safety checks
    - Safe rollback execution
    - Decision re-explanation
    - Rollback impact analysis
    - Audit trail
    """
    
    def __init__(
        self,
        registry_path: str = "models/registry",
        history_path: str = "data/decision_history",
        rollback_path: str = "data/rollbacks"
    ):
        """Initialize the rollback service."""
        from models.model_registry import ModelRegistry
        
        self.registry = ModelRegistry(registry_path)
        self.decision_store = DecisionHistoryStore(history_path)
        self.rollback_path = Path(rollback_path)
        self.rollback_path.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # Rollback Operations
    # =========================================================================
    
    def analyze_rollback_impact(
        self,
        from_model_id: str,
        to_model_id: str,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze the impact of a potential rollback.
        
        Returns:
            Analysis of affected decisions and potential impact
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        # Get decisions made by the problematic model
        affected_decisions = self.decision_store.get_decisions_by_model(from_model_id)
        recent_decisions = [d for d in affected_decisions if d.decision_timestamp >= since]
        
        # Analyze outcomes
        outcomes = {'approved': 0, 'rejected': 0, 'manual_review': 0}
        for d in recent_decisions:
            outcomes[d.original_outcome] = outcomes.get(d.original_outcome, 0) + 1
        
        # Load model metrics
        from_metadata = self.registry._load_metadata(from_model_id)
        to_metadata = self.registry._load_metadata(to_model_id)
        
        analysis = {
            'from_model': {
                'model_id': from_model_id,
                'version': from_metadata.version if from_metadata else 'unknown',
                'accuracy': from_metadata.accuracy if from_metadata else 0,
                'roc_auc': from_metadata.roc_auc if from_metadata else 0,
                'total_predictions': from_metadata.total_predictions if from_metadata else 0
            },
            'to_model': {
                'model_id': to_model_id,
                'version': to_metadata.version if to_metadata else 'unknown',
                'accuracy': to_metadata.accuracy if to_metadata else 0,
                'roc_auc': to_metadata.roc_auc if to_metadata else 0
            },
            'impact': {
                'total_affected_decisions': len(affected_decisions),
                'recent_affected_decisions': len(recent_decisions),
                'outcome_distribution': outcomes,
                'needs_re_explanation': len([d for d in recent_decisions if not d.re_explained])
            },
            'recommendation': self._generate_rollback_recommendation(
                from_metadata, to_metadata, len(recent_decisions)
            )
        }
        
        return analysis
    
    def _generate_rollback_recommendation(
        self,
        from_metadata,
        to_metadata,
        affected_count: int
    ) -> str:
        """Generate a recommendation for rollback."""
        if not from_metadata or not to_metadata:
            return "CAUTION: Unable to compare models. Manual review required."
        
        accuracy_diff = from_metadata.accuracy - to_metadata.accuracy
        
        if accuracy_diff < -0.05:
            return f"RECOMMEND ROLLBACK: Current model accuracy is {accuracy_diff*100:.1f}% lower"
        elif affected_count > 1000:
            return f"CAUTION: {affected_count} decisions affected. Consider phased rollback."
        else:
            return "PROCEED WITH CAUTION: Monitor closely after rollback."
    
    def perform_safe_rollback(
        self,
        reason: RollbackReason,
        triggered_by: str,
        trigger_details: str,
        to_model_id: Optional[str] = None,
        dry_run: bool = False
    ) -> RollbackRecord:
        """
        Perform a safe model rollback with pre-checks.
        
        Args:
            reason: Reason for rollback
            triggered_by: Who/what triggered the rollback
            trigger_details: Details about the trigger
            to_model_id: Specific model to rollback to (or auto-select)
            dry_run: If True, only analyze without executing
            
        Returns:
            RollbackRecord with details of the operation
        """
        from models.model_registry import ModelStatus
        
        # Get current production model
        current_model_id = self.registry.config.get('production_model_id')
        if not current_model_id:
            raise ValueError("No production model to rollback from")
        
        # Determine target model
        if to_model_id is None:
            # Find the most recent archived model
            archived = self.registry.list_models(status=ModelStatus.ARCHIVED)
            if not archived:
                raise ValueError("No archived models available for rollback")
            archived.sort(key=lambda m: m.deployed_date or datetime.min, reverse=True)
            to_model_id = archived[0].model_id
        
        # Create rollback record
        rollback_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        from_metadata = self.registry._load_metadata(current_model_id)
        to_metadata = self.registry._load_metadata(to_model_id)
        
        record = RollbackRecord(
            rollback_id=rollback_id,
            reason=reason,
            status=RollbackStatus.PENDING,
            from_model_id=current_model_id,
            to_model_id=to_model_id,
            from_model_metrics={
                'accuracy': from_metadata.accuracy,
                'precision': from_metadata.precision,
                'recall': from_metadata.recall,
                'f1_score': from_metadata.f1_score,
                'roc_auc': from_metadata.roc_auc
            } if from_metadata else {},
            to_model_metrics={
                'accuracy': to_metadata.accuracy,
                'precision': to_metadata.precision,
                'recall': to_metadata.recall,
                'f1_score': to_metadata.f1_score,
                'roc_auc': to_metadata.roc_auc
            } if to_metadata else {},
            triggered_by=triggered_by,
            trigger_details=trigger_details,
            initiated_at=datetime.utcnow()
        )
        
        # Analyze impact
        impact = self.analyze_rollback_impact(current_model_id, to_model_id)
        record.affected_decisions_count = impact['impact']['total_affected_decisions']
        record.decisions_to_re_explain = [
            d.decision_id for d in 
            self.decision_store.get_decisions_needing_re_explanation(current_model_id)
        ]
        
        if dry_run:
            record.notes = "DRY RUN - No changes made"
            return record
        
        # Execute rollback
        try:
            record.status = RollbackStatus.IN_PROGRESS
            self._save_rollback_record(record)
            
            # Perform the actual rollback
            success = self.registry.promote_to_production(
                to_model_id, 
                deployed_by=f"rollback:{triggered_by}"
            )
            
            if success:
                record.status = RollbackStatus.COMPLETED
                record.completed_at = datetime.utcnow()
                logger.info(f"Rollback completed: {current_model_id} -> {to_model_id}")
            else:
                record.status = RollbackStatus.FAILED
                record.notes = "Registry promotion failed"
                logger.error(f"Rollback failed: {current_model_id} -> {to_model_id}")
                
        except Exception as e:
            record.status = RollbackStatus.FAILED
            record.notes = f"Error: {str(e)}"
            logger.error(f"Rollback error: {e}")
        
        self._save_rollback_record(record)
        return record
    
    def _save_rollback_record(self, record: RollbackRecord):
        """Save rollback record to disk."""
        filepath = self.rollback_path / f"{record.rollback_id}.json"
        with open(filepath, 'w') as f:
            json.dump(record.to_dict(), f, indent=2)
    
    def get_rollback_history(self, limit: int = 10) -> List[RollbackRecord]:
        """Get recent rollback history."""
        records = []
        
        for filepath in sorted(self.rollback_path.glob("*.json"), reverse=True)[:limit]:
            with open(filepath, 'r') as f:
                data = json.load(f)
            records.append(RollbackRecord.from_dict(data))
        
        return records
    
    # =========================================================================
    # Decision Re-explanation
    # =========================================================================
    
    def re_explain_decision(
        self,
        decision_id: str,
        use_model_id: Optional[str] = None
    ) -> Optional[ReExplanationResult]:
        """
        Re-explain a historical decision using a different model.
        
        Args:
            decision_id: ID of the decision to re-explain
            use_model_id: Model to use for re-explanation (default: current production)
            
        Returns:
            ReExplanationResult with comparison
        """
        # Get original decision
        original = self.decision_store.get_decision(decision_id)
        if not original:
            logger.error(f"Decision {decision_id} not found")
            return None
        
        # Get model for re-explanation
        if use_model_id is None:
            use_model_id = self.registry.config.get('production_model_id')
        
        if not use_model_id:
            logger.error("No model available for re-explanation")
            return None
        
        # Load the model
        model_data = self.registry.load_model(use_model_id)
        if not model_data:
            logger.error(f"Could not load model {use_model_id}")
            return None
        
        # Re-run prediction
        try:
            from models.loan_model import LoanApprovalModel
            import pandas as pd
            
            # Reconstruct model
            model = LoanApprovalModel()
            model.model = model_data['model']
            model.scaler = model_data['scaler']
            model.label_encoders = model_data['label_encoders']
            model.feature_names = model_data['feature_names']
            model.explainer = model_data.get('explainer')
            model.is_trained = True
            
            # Create dataframe from stored features
            df = pd.DataFrame([original.input_features])
            
            # Get new prediction
            new_prediction = model.predict(df)
            new_explanation = model.explain_prediction(df)
            
            # Determine new outcome
            if new_prediction['approval_probability'] >= 0.7:
                new_outcome = 'approved'
            elif new_prediction['approval_probability'] >= 0.4:
                new_outcome = 'manual_review'
            else:
                new_outcome = 'rejected'
            
            # Compare explanations
            original_factors = [
                f['display_name'] for f in 
                original.original_explanation.get('positive_factors', []) +
                original.original_explanation.get('negative_factors', [])
            ]
            
            new_factors = [
                f['display_name'] for f in 
                new_explanation.get('positive_factors', []) +
                new_explanation.get('negative_factors', [])
            ]
            
            factors_changed = list(set(new_factors) - set(original_factors))
            
            # Create result
            result = ReExplanationResult(
                decision_id=decision_id,
                original_model_id=original.model_id,
                re_explanation_model_id=use_model_id,
                original_outcome=original.original_outcome,
                new_outcome=new_outcome,
                outcome_changed=(original.original_outcome != new_outcome),
                original_probability=original.original_probability,
                new_probability=new_prediction['approval_probability'],
                probability_delta=new_prediction['approval_probability'] - original.original_probability,
                original_factors=original_factors,
                new_factors=new_factors,
                factors_changed=factors_changed,
                explanation_summary=self._generate_explanation_summary(
                    original.original_outcome, new_outcome,
                    original.original_probability, new_prediction['approval_probability']
                ),
                recommendation=self._generate_re_explanation_recommendation(
                    original.original_outcome, new_outcome
                ),
                requires_manual_review=(original.original_outcome != new_outcome)
            )
            
            # Update the original decision record
            original.re_explained = True
            original.re_explanation_model_id = use_model_id
            original.re_explanation_timestamp = datetime.utcnow()
            original.re_explanation_result = {
                'new_outcome': new_outcome,
                'new_probability': new_prediction['approval_probability'],
                'outcome_changed': result.outcome_changed
            }
            self.decision_store.update_decision(original)
            
            return result
            
        except Exception as e:
            logger.error(f"Error re-explaining decision {decision_id}: {e}")
            return None
    
    def _generate_explanation_summary(
        self,
        original_outcome: str,
        new_outcome: str,
        original_prob: float,
        new_prob: float
    ) -> str:
        """Generate a human-readable summary of the re-explanation."""
        prob_diff = abs(new_prob - original_prob) * 100
        
        if original_outcome == new_outcome:
            return (
                f"Decision remains {new_outcome}. "
                f"Probability changed by {prob_diff:.1f}% "
                f"({original_prob*100:.1f}% → {new_prob*100:.1f}%)."
            )
        else:
            return (
                f"DECISION CHANGED: {original_outcome} → {new_outcome}. "
                f"Probability changed from {original_prob*100:.1f}% to {new_prob*100:.1f}%. "
                f"Manual review recommended."
            )
    
    def _generate_re_explanation_recommendation(
        self,
        original_outcome: str,
        new_outcome: str
    ) -> str:
        """Generate a recommendation based on re-explanation."""
        if original_outcome == new_outcome:
            return "No action required - decision consistent across models."
        
        if original_outcome == 'approved' and new_outcome == 'rejected':
            return "URGENT: Approved application may be high-risk. Review immediately."
        
        if original_outcome == 'rejected' and new_outcome == 'approved':
            return "Review: Previously rejected application may be eligible."
        
        return "Manual review recommended to verify decision."
    
    def batch_re_explain_decisions(
        self,
        model_id: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Batch re-explain decisions made by a specific model.
        
        Useful after a rollback to identify affected decisions.
        
        Returns:
            Summary of re-explanation results
        """
        decisions = self.decision_store.get_decisions_needing_re_explanation(
            model_id, since
        )[:limit]
        
        results = {
            'total_processed': 0,
            'outcome_changed': 0,
            'outcome_unchanged': 0,
            'errors': 0,
            'details': []
        }
        
        current_model = self.registry.config.get('production_model_id')
        
        for decision in decisions:
            result = self.re_explain_decision(decision.decision_id, current_model)
            
            if result:
                results['total_processed'] += 1
                if result.outcome_changed:
                    results['outcome_changed'] += 1
                else:
                    results['outcome_unchanged'] += 1
                
                results['details'].append({
                    'decision_id': result.decision_id,
                    'outcome_changed': result.outcome_changed,
                    'original': result.original_outcome,
                    'new': result.new_outcome,
                    'recommendation': result.recommendation
                })
            else:
                results['errors'] += 1
        
        logger.info(
            f"Batch re-explanation complete: {results['total_processed']} processed, "
            f"{results['outcome_changed']} changed outcomes"
        )
        
        return results
    
    # =========================================================================
    # Emergency Rollback
    # =========================================================================
    
    def emergency_rollback(self, triggered_by: str, reason: str) -> RollbackRecord:
        """
        Perform an emergency rollback with minimal checks.
        
        Use only when immediate action is required.
        """
        logger.warning(f"EMERGENCY ROLLBACK initiated by {triggered_by}: {reason}")
        
        return self.perform_safe_rollback(
            reason=RollbackReason.EMERGENCY,
            triggered_by=triggered_by,
            trigger_details=reason,
            dry_run=False
        )
    
    def get_rollback_status(self, rollback_id: str) -> Optional[RollbackRecord]:
        """Get the status of a rollback operation."""
        filepath = self.rollback_path / f"{rollback_id}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        return RollbackRecord.from_dict(data)


# =============================================================================
# Factory Function
# =============================================================================

def get_rollback_service() -> ModelRollbackService:
    """Get a configured rollback service instance."""
    return ModelRollbackService()


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Rollback Service")
    parser.add_argument('action', choices=['analyze', 'rollback', 're-explain', 'history'])
    parser.add_argument('--model', help='Target model ID')
    parser.add_argument('--decision', help='Decision ID for re-explanation')
    parser.add_argument('--reason', help='Rollback reason')
    parser.add_argument('--dry-run', action='store_true', help='Analyze without executing')
    
    args = parser.parse_args()
    
    service = get_rollback_service()
    
    if args.action == 'analyze':
        from_model = service.registry.config.get('production_model_id')
        if from_model and args.model:
            analysis = service.analyze_rollback_impact(from_model, args.model)
            print(json.dumps(analysis, indent=2, default=str))
    
    elif args.action == 'rollback':
        reason = RollbackReason(args.reason) if args.reason else RollbackReason.MANUAL_OVERRIDE
        record = service.perform_safe_rollback(
            reason=reason,
            triggered_by="cli",
            trigger_details="Manual CLI rollback",
            to_model_id=args.model,
            dry_run=args.dry_run
        )
        print(f"Rollback {record.rollback_id}: {record.status.value}")
    
    elif args.action == 're-explain':
        if args.decision:
            result = service.re_explain_decision(args.decision, args.model)
            if result:
                print(f"Original: {result.original_outcome} ({result.original_probability:.2%})")
                print(f"New: {result.new_outcome} ({result.new_probability:.2%})")
                print(f"Changed: {result.outcome_changed}")
                print(f"Summary: {result.explanation_summary}")
    
    elif args.action == 'history':
        history = service.get_rollback_history()
        for record in history:
            print(f"{record.rollback_id}: {record.from_model_id} -> {record.to_model_id} ({record.status.value})")
