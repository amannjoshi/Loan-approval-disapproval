"""
Model Registry for Loan Approval System
========================================
Manages model versions, metadata, and deployment lifecycle.

Features:
- Model versioning and tracking
- A/B testing support
- Model performance monitoring
- Rollback capabilities

Author: Loan Analytics Team
Version: 1.0.0
"""

import os
import json
import pickle
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    RETIRED = "retired"
    ARCHIVED = "archived"


@dataclass
class ModelMetadata:
    """Metadata for a registered model."""
    model_id: str
    model_type: str
    version: str
    status: ModelStatus
    
    # Training info
    training_date: datetime
    training_samples: int
    feature_count: int
    feature_names: List[str]
    
    # Performance metrics
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    
    # Cross-validation metrics
    cv_accuracy_mean: float = 0.0
    cv_accuracy_std: float = 0.0
    
    # File info
    file_path: str = ""
    file_hash: str = ""
    file_size_bytes: int = 0
    
    # Deployment info
    deployed_date: Optional[datetime] = None
    deployed_by: str = "system"
    
    # Notes
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Production metrics (updated over time)
    total_predictions: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    last_used: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['status'] = self.status.value
        result['training_date'] = self.training_date.isoformat()
        result['deployed_date'] = self.deployed_date.isoformat() if self.deployed_date else None
        result['last_used'] = self.last_used.isoformat() if self.last_used else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary."""
        data['status'] = ModelStatus(data['status'])
        data['training_date'] = datetime.fromisoformat(data['training_date'])
        if data.get('deployed_date'):
            data['deployed_date'] = datetime.fromisoformat(data['deployed_date'])
        if data.get('last_used'):
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        return cls(**data)


class ModelRegistry:
    """
    Central registry for managing model versions and deployments.
    
    Provides:
    - Model registration and versioning
    - Production model selection
    - A/B testing configuration
    - Performance tracking
    - Rollback support
    """
    
    def __init__(self, registry_path: str = "models/registry"):
        """
        Initialize the model registry.
        
        Parameters:
        -----------
        registry_path : str
            Path to store registry data and models
        """
        self.registry_path = registry_path
        self.models_path = os.path.join(registry_path, "models")
        self.metadata_path = os.path.join(registry_path, "metadata")
        self.config_file = os.path.join(registry_path, "config.json")
        
        # Create directories
        os.makedirs(self.models_path, exist_ok=True)
        os.makedirs(self.metadata_path, exist_ok=True)
        
        # Load or create config
        self.config = self._load_config()
        
        # Cache of loaded metadata
        self._metadata_cache: Dict[str, ModelMetadata] = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """Load registry configuration."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Default config
        config = {
            'production_model_id': None,
            'staging_model_id': None,
            'ab_test_config': {
                'enabled': False,
                'model_a': None,
                'model_b': None,
                'traffic_split': 0.5
            },
            'auto_promote': False,
            'promotion_threshold': {
                'min_accuracy': 0.85,
                'min_roc_auc': 0.80,
                'min_samples': 1000
            }
        }
        self._save_config(config)
        return config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save registry configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def register_model(
        self,
        model: Any,
        model_type: str,
        training_metrics: Dict[str, Any],
        description: str = "",
        tags: List[str] = None,
        auto_promote: bool = False
    ) -> ModelMetadata:
        """
        Register a new model in the registry.
        
        Parameters:
        -----------
        model : Any
            Trained model object with save_model method
        model_type : str
            Type of model (e.g., 'gradient_boosting', 'ensemble')
        training_metrics : dict
            Training metrics including accuracy, precision, etc.
        description : str
            Description of the model
        tags : list
            Tags for categorization
        auto_promote : bool
            Whether to auto-promote to staging if metrics meet threshold
            
        Returns:
        --------
        ModelMetadata
            Metadata for the registered model
        """
        tags = tags or []
        
        # Generate model ID and version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"{model_type}_{timestamp}"
        version = f"1.0.{timestamp}"
        
        # Save model file
        model_filename = f"{model_id}.pkl"
        model_filepath = os.path.join(self.models_path, model_filename)
        model.save_model(model_filepath)
        
        # Calculate file hash and size
        file_hash = self._calculate_file_hash(model_filepath)
        file_size = os.path.getsize(model_filepath)
        
        # Create metadata
        metadata = ModelMetadata(
            model_id=model_id,
            model_type=model_type,
            version=version,
            status=ModelStatus.DEVELOPMENT,
            training_date=datetime.now(),
            training_samples=training_metrics.get('training_samples', 0),
            feature_count=training_metrics.get('num_features', 0),
            feature_names=model.feature_names if hasattr(model, 'feature_names') else [],
            accuracy=training_metrics.get('accuracy', 0),
            precision=training_metrics.get('precision', 0),
            recall=training_metrics.get('recall', 0),
            f1_score=training_metrics.get('f1_score', 0),
            roc_auc=training_metrics.get('roc_auc', 0),
            cv_accuracy_mean=training_metrics.get('cv_accuracy_mean', 0),
            cv_accuracy_std=training_metrics.get('cv_accuracy_std', 0),
            file_path=model_filepath,
            file_hash=file_hash,
            file_size_bytes=file_size,
            description=description,
            tags=tags
        )
        
        # Save metadata
        self._save_metadata(metadata)
        
        logger.info(f"Registered model: {model_id} (v{version})")
        
        # Auto-promote if enabled and meets threshold
        if auto_promote and self._meets_promotion_threshold(metadata):
            self.promote_to_staging(model_id)
        
        return metadata
    
    def _save_metadata(self, metadata: ModelMetadata):
        """Save model metadata to disk."""
        filepath = os.path.join(self.metadata_path, f"{metadata.model_id}.json")
        with open(filepath, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        self._metadata_cache[metadata.model_id] = metadata
    
    def _load_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Load model metadata from disk."""
        if model_id in self._metadata_cache:
            return self._metadata_cache[model_id]
        
        filepath = os.path.join(self.metadata_path, f"{model_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
            metadata = ModelMetadata.from_dict(data)
            self._metadata_cache[model_id] = metadata
            return metadata
        return None
    
    def _meets_promotion_threshold(self, metadata: ModelMetadata) -> bool:
        """Check if model meets promotion threshold."""
        threshold = self.config['promotion_threshold']
        return (
            metadata.accuracy >= threshold['min_accuracy'] and
            metadata.roc_auc >= threshold['min_roc_auc'] and
            metadata.training_samples >= threshold['min_samples']
        )
    
    def promote_to_staging(self, model_id: str) -> bool:
        """Promote a model to staging."""
        metadata = self._load_metadata(model_id)
        if not metadata:
            logger.error(f"Model {model_id} not found")
            return False
        
        metadata.status = ModelStatus.STAGING
        metadata.deployed_date = datetime.now()
        self._save_metadata(metadata)
        
        self.config['staging_model_id'] = model_id
        self._save_config(self.config)
        
        logger.info(f"Promoted {model_id} to staging")
        return True
    
    def promote_to_production(self, model_id: str, deployed_by: str = "system") -> bool:
        """Promote a model to production."""
        metadata = self._load_metadata(model_id)
        if not metadata:
            logger.error(f"Model {model_id} not found")
            return False
        
        # Archive current production model
        current_prod = self.config.get('production_model_id')
        if current_prod:
            self._archive_model(current_prod)
        
        # Promote new model
        metadata.status = ModelStatus.PRODUCTION
        metadata.deployed_date = datetime.now()
        metadata.deployed_by = deployed_by
        self._save_metadata(metadata)
        
        self.config['production_model_id'] = model_id
        self._save_config(self.config)
        
        logger.info(f"Promoted {model_id} to production by {deployed_by}")
        return True
    
    def _archive_model(self, model_id: str):
        """Archive a model."""
        metadata = self._load_metadata(model_id)
        if metadata:
            metadata.status = ModelStatus.ARCHIVED
            self._save_metadata(metadata)
            logger.info(f"Archived model: {model_id}")
    
    def rollback_production(self, to_model_id: Optional[str] = None) -> Optional[str]:
        """
        Rollback to a previous production model.
        
        Args:
            to_model_id: Specific model to rollback to. If None, uses most recent archived.
            
        Returns:
            Model ID that was rolled back to, or None if failed.
        """
        if to_model_id:
            # Rollback to specific model
            metadata = self._load_metadata(to_model_id)
            if not metadata:
                logger.error(f"Target model {to_model_id} not found")
                return None
            
            self.promote_to_production(to_model_id, deployed_by="rollback")
            logger.info(f"Rolled back to specified model: {to_model_id}")
            return to_model_id
        
        # Find most recent archived production model
        all_models = self.list_models(status=ModelStatus.ARCHIVED)
        if not all_models:
            logger.error("No archived models available for rollback")
            return None
        
        # Sort by deployed date (most recent first)
        all_models.sort(key=lambda m: m.deployed_date or datetime.min, reverse=True)
        
        previous_model = all_models[0]
        self.promote_to_production(previous_model.model_id, deployed_by="rollback")
        
        logger.info(f"Rolled back to: {previous_model.model_id}")
        return previous_model.model_id
    
    def get_production_model(self) -> Optional[Any]:
        """Get the current production model."""
        model_id = self.config.get('production_model_id')
        if not model_id:
            return None
        return self.load_model(model_id)
    
    def get_staging_model(self) -> Optional[Any]:
        """Get the current staging model."""
        model_id = self.config.get('staging_model_id')
        if not model_id:
            return None
        return self.load_model(model_id)
    
    def load_model(self, model_id: str) -> Optional[Any]:
        """Load a model from the registry."""
        metadata = self._load_metadata(model_id)
        if not metadata:
            return None
        
        if not os.path.exists(metadata.file_path):
            logger.error(f"Model file not found: {metadata.file_path}")
            return None
        
        # Verify file integrity
        current_hash = self._calculate_file_hash(metadata.file_path)
        if current_hash != metadata.file_hash:
            logger.warning(f"Model file hash mismatch for {model_id}")
        
        with open(metadata.file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        # Update last used
        metadata.last_used = datetime.now()
        self._save_metadata(metadata)
        
        return model_data
    
    def list_models(
        self,
        status: Optional[ModelStatus] = None,
        model_type: Optional[str] = None,
        min_accuracy: float = 0.0
    ) -> List[ModelMetadata]:
        """
        List models matching criteria.
        
        Parameters:
        -----------
        status : ModelStatus, optional
            Filter by status
        model_type : str, optional
            Filter by model type
        min_accuracy : float
            Minimum accuracy threshold
            
        Returns:
        --------
        list
            List of matching ModelMetadata objects
        """
        results = []
        
        for filename in os.listdir(self.metadata_path):
            if filename.endswith('.json'):
                model_id = filename[:-5]
                metadata = self._load_metadata(model_id)
                
                if not metadata:
                    continue
                
                # Apply filters
                if status and metadata.status != status:
                    continue
                if model_type and metadata.model_type != model_type:
                    continue
                if metadata.accuracy < min_accuracy:
                    continue
                
                results.append(metadata)
        
        return results
    
    def update_production_metrics(
        self,
        model_id: str,
        predictions_count: int,
        avg_latency_ms: float,
        errors_count: int = 0
    ):
        """Update production metrics for a model."""
        metadata = self._load_metadata(model_id)
        if not metadata:
            return
        
        metadata.total_predictions += predictions_count
        
        # Running average for latency
        total_predictions = metadata.total_predictions
        old_weight = (total_predictions - predictions_count) / total_predictions
        new_weight = predictions_count / total_predictions
        metadata.avg_latency_ms = (
            metadata.avg_latency_ms * old_weight + 
            avg_latency_ms * new_weight
        )
        
        # Update error rate
        if total_predictions > 0:
            metadata.error_rate = errors_count / total_predictions
        
        metadata.last_used = datetime.now()
        self._save_metadata(metadata)
    
    def configure_ab_test(
        self,
        model_a_id: str,
        model_b_id: str,
        traffic_split: float = 0.5
    ):
        """Configure A/B testing between two models."""
        if not 0 <= traffic_split <= 1:
            raise ValueError("Traffic split must be between 0 and 1")
        
        self.config['ab_test_config'] = {
            'enabled': True,
            'model_a': model_a_id,
            'model_b': model_b_id,
            'traffic_split': traffic_split
        }
        self._save_config(self.config)
        
        logger.info(f"A/B test configured: {model_a_id} ({traffic_split*100}%) vs {model_b_id} ({(1-traffic_split)*100}%)")
    
    def disable_ab_test(self):
        """Disable A/B testing."""
        self.config['ab_test_config']['enabled'] = False
        self._save_config(self.config)
        logger.info("A/B testing disabled")
    
    def get_ab_test_model(self, request_id: str) -> Optional[str]:
        """Get model ID based on A/B test configuration."""
        ab_config = self.config.get('ab_test_config', {})
        if not ab_config.get('enabled'):
            return self.config.get('production_model_id')
        
        # Use hash of request_id for deterministic split
        hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        normalized = (hash_value % 1000) / 1000
        
        if normalized < ab_config['traffic_split']:
            return ab_config['model_a']
        return ab_config['model_b']
    
    def get_model_comparison(
        self,
        model_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Compare metrics across multiple models."""
        comparison = {}
        
        for model_id in model_ids:
            metadata = self._load_metadata(model_id)
            if metadata:
                comparison[model_id] = {
                    'model_type': metadata.model_type,
                    'version': metadata.version,
                    'status': metadata.status.value,
                    'accuracy': metadata.accuracy,
                    'precision': metadata.precision,
                    'recall': metadata.recall,
                    'f1_score': metadata.f1_score,
                    'roc_auc': metadata.roc_auc,
                    'cv_accuracy': f"{metadata.cv_accuracy_mean:.3f} ± {metadata.cv_accuracy_std:.3f}",
                    'training_samples': metadata.training_samples,
                    'total_predictions': metadata.total_predictions,
                    'avg_latency_ms': f"{metadata.avg_latency_ms:.1f}",
                    'training_date': metadata.training_date.strftime("%Y-%m-%d")
                }
        
        return comparison
    
    def cleanup_old_models(self, keep_latest: int = 5):
        """Remove old archived models, keeping the latest N."""
        archived = self.list_models(status=ModelStatus.ARCHIVED)
        archived.sort(key=lambda m: m.training_date, reverse=True)
        
        to_delete = archived[keep_latest:]
        
        for metadata in to_delete:
            # Remove model file
            if os.path.exists(metadata.file_path):
                os.remove(metadata.file_path)
            
            # Remove metadata file
            metadata_file = os.path.join(self.metadata_path, f"{metadata.model_id}.json")
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            
            # Clear from cache
            if metadata.model_id in self._metadata_cache:
                del self._metadata_cache[metadata.model_id]
            
            logger.info(f"Cleaned up old model: {metadata.model_id}")
        
        return len(to_delete)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get overall registry statistics."""
        all_models = self.list_models()
        
        stats = {
            'total_models': len(all_models),
            'by_status': {},
            'by_type': {},
            'production_model': self.config.get('production_model_id'),
            'staging_model': self.config.get('staging_model_id'),
            'ab_testing_enabled': self.config['ab_test_config'].get('enabled', False),
            'total_predictions': sum(m.total_predictions for m in all_models),
            'best_accuracy': max((m.accuracy for m in all_models), default=0),
            'best_roc_auc': max((m.roc_auc for m in all_models), default=0)
        }
        
        for model in all_models:
            # Count by status
            status = model.status.value
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Count by type
            model_type = model.model_type
            stats['by_type'][model_type] = stats['by_type'].get(model_type, 0) + 1
        
        return stats


if __name__ == "__main__":
    # Test the model registry
    print("Testing Model Registry...")
    
    registry = ModelRegistry()
    print(f"\nRegistry Stats: {registry.get_registry_stats()}")
    
    print("\nModel Registry ready!")
