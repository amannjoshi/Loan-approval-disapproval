"""
Loan Approval System - Main Entry Point
=======================================
Production-grade backend initialization and CLI interface.

Usage:
    python main.py train          # Train and register a new model
    python main.py serve          # Start the Streamlit server
    python main.py test           # Run backend tests
    python main.py predict        # Make a test prediction
    python main.py benchmark      # Benchmark model performance

Author: Loan Analytics Team
Version: 2.0.0
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train_model(args):
    """Train a new model and register it."""
    from data.data_generator import generate_synthetic_data
    from models.loan_model import LoanApprovalModel
    from models.model_registry import ModelRegistry
    
    print("\n" + "="*60)
    print("  LOAN APPROVAL MODEL TRAINING")
    print("="*60)
    
    # Generate data
    n_samples = args.samples if hasattr(args, 'samples') else 5000
    print(f"\n📊 Generating {n_samples} synthetic samples...")
    df = generate_synthetic_data(n_samples=n_samples)
    print(f"   ✓ Data generated: {df.shape[0]} samples, {df.shape[1]} features")
    print(f"   ✓ Approval rate: {df['loan_approved'].mean()*100:.1f}%")
    
    # Train model
    model_type = args.model_type if hasattr(args, 'model_type') else 'gradient_boosting'
    print(f"\n🤖 Training {model_type} model...")
    
    model = LoanApprovalModel(model_type=model_type)
    metrics = model.train(df, perform_cv=True, calibrate=True)
    
    print("\n📈 Training Results:")
    print(f"   ✓ Accuracy: {metrics['accuracy']*100:.2f}%")
    print(f"   ✓ Precision: {metrics['precision']*100:.2f}%")
    print(f"   ✓ Recall: {metrics['recall']*100:.2f}%")
    print(f"   ✓ F1-Score: {metrics['f1_score']*100:.2f}%")
    print(f"   ✓ ROC-AUC: {metrics['roc_auc']*100:.2f}%")
    
    if 'cv_accuracy_mean' in metrics:
        print(f"   ✓ CV Accuracy: {metrics['cv_accuracy_mean']*100:.2f}% (±{metrics['cv_accuracy_std']*100:.2f}%)")
    
    # Save model
    print("\n💾 Saving model...")
    model.save_model('models/loan_model.pkl')
    print("   ✓ Model saved to models/loan_model.pkl")
    
    # Register with registry (optional)
    try:
        registry = ModelRegistry()
        metadata = registry.register_model(
            model=model,
            model_type=model_type,
            training_metrics=metrics,
            description=f"Trained on {n_samples} samples",
            tags=['production-candidate'],
            auto_promote=True
        )
        print(f"\n📋 Registered in Model Registry:")
        print(f"   ✓ Model ID: {metadata.model_id}")
        print(f"   ✓ Version: {metadata.version}")
        print(f"   ✓ Status: {metadata.status.value}")
    except Exception as e:
        logger.warning(f"Could not register model: {e}")
    
    print("\n" + "="*60)
    print("  TRAINING COMPLETE ✓")
    print("="*60 + "\n")
    
    return model, metrics


def serve_app(args):
    """Start the Streamlit application."""
    import subprocess
    
    print("\n🚀 Starting Loan Approval Dashboard...")
    print("   URL: http://localhost:8501")
    print("   Press Ctrl+C to stop\n")
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])


def run_tests(args):
    """Run backend tests."""
    import subprocess
    
    print("\n🧪 Running Backend Tests...")
    print("="*60 + "\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=False
    )
    
    return result.returncode


def make_prediction(args):
    """Make a test prediction."""
    from models.loan_model import LoanApprovalModel, generate_human_explanation
    from services.loan_service import LoanApplicationService, create_application_from_dict
    from utils.validators import InputValidator
    import pandas as pd
    
    print("\n" + "="*60)
    print("  TEST PREDICTION")
    print("="*60)
    
    # Load model
    print("\n📂 Loading model...")
    model = LoanApprovalModel()
    
    try:
        model.load_model('models/loan_model.pkl')
        print("   ✓ Model loaded successfully")
    except FileNotFoundError:
        print("   ✗ No trained model found. Running training first...")
        model, _ = train_model(args)
    
    # Create service
    service = LoanApplicationService(
        model=model,
        validator=InputValidator()
    )
    
    # Test applications
    test_cases = [
        {
            'name': 'Good Applicant',
            'data': {
                'age': 35, 'gender': 'Male', 'education': 'Graduate',
                'marital_status': 'Married', 'num_dependents': 2,
                'employment_type': 'Salaried', 'industry': 'IT',
                'years_at_current_job': 5, 'monthly_income': 100000,
                'existing_emi': 10000, 'num_existing_loans': 1,
                'savings_balance': 500000, 'cibil_score': 780,
                'credit_history_years': 8, 'late_payments_last_2_years': 0,
                'has_defaults': False, 'owns_property': True,
                'years_with_bank': 5, 'loan_amount': 1000000,
                'loan_tenure_months': 60
            }
        },
        {
            'name': 'Risky Applicant',
            'data': {
                'age': 25, 'gender': 'Male', 'education': 'High School',
                'marital_status': 'Single', 'num_dependents': 0,
                'employment_type': 'Self-Employed', 'industry': 'Retail',
                'years_at_current_job': 1, 'monthly_income': 25000,
                'existing_emi': 10000, 'num_existing_loans': 3,
                'savings_balance': 10000, 'cibil_score': 580,
                'credit_history_years': 2, 'late_payments_last_2_years': 5,
                'has_defaults': True, 'owns_property': False,
                'years_with_bank': 1, 'loan_amount': 500000,
                'loan_tenure_months': 36
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n\n📋 {test_case['name'].upper()}")
        print("-"*60)
        
        application = create_application_from_dict(test_case['data'])
        result = service.process_application(application)
        
        print(service.get_decision_summary(result))
    
    print("\n")


def benchmark(args):
    """Benchmark model performance."""
    import time
    from data.data_generator import generate_synthetic_data
    from models.loan_model import LoanApprovalModel
    
    print("\n" + "="*60)
    print("  PERFORMANCE BENCHMARK")
    print("="*60)
    
    # Load or train model
    model = LoanApprovalModel()
    try:
        model.load_model('models/loan_model.pkl')
    except FileNotFoundError:
        print("\n📂 Training model for benchmark...")
        df = generate_synthetic_data(n_samples=2000)
        model.train(df, perform_cv=False, calibrate=False)
    
    # Generate test data
    n_samples = 1000
    print(f"\n📊 Generating {n_samples} test samples...")
    test_df = generate_synthetic_data(n_samples=n_samples)
    
    # Benchmark single predictions
    print("\n⏱️  Single Prediction Benchmark:")
    times = []
    for i in range(100):
        sample = test_df.sample(1)
        start = time.perf_counter()
        _ = model.predict(sample)
        times.append((time.perf_counter() - start) * 1000)
    
    print(f"   Mean latency: {sum(times)/len(times):.2f} ms")
    print(f"   Min latency: {min(times):.2f} ms")
    print(f"   Max latency: {max(times):.2f} ms")
    print(f"   Throughput: {1000/(sum(times)/len(times)):.0f} predictions/sec")
    
    # Benchmark with explanations
    print("\n⏱️  Prediction + Explanation Benchmark:")
    times = []
    for i in range(50):
        sample = test_df.sample(1)
        start = time.perf_counter()
        _ = model.predict(sample)
        _ = model.explain_prediction(sample)
        times.append((time.perf_counter() - start) * 1000)
    
    print(f"   Mean latency: {sum(times)/len(times):.2f} ms")
    print(f"   Throughput: {1000/(sum(times)/len(times)):.0f} predictions/sec")
    
    # Benchmark batch predictions
    print("\n⏱️  Batch Prediction Benchmark:")
    batch_sizes = [10, 50, 100, 500]
    for batch_size in batch_sizes:
        batch = test_df.sample(batch_size)
        start = time.perf_counter()
        _ = model.predict_batch(batch)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"   Batch size {batch_size}: {elapsed:.2f} ms ({batch_size*1000/elapsed:.0f} samples/sec)")
    
    print("\n" + "="*60)
    print("  BENCHMARK COMPLETE ✓")
    print("="*60 + "\n")


def show_status(args):
    """Show system status."""
    from models.model_registry import ModelRegistry
    
    print("\n" + "="*60)
    print("  LOAN APPROVAL SYSTEM STATUS")
    print("="*60)
    
    # Check model
    print("\n📦 Model Status:")
    if os.path.exists('models/loan_model.pkl'):
        size = os.path.getsize('models/loan_model.pkl') / 1024
        print(f"   ✓ Production model: models/loan_model.pkl ({size:.1f} KB)")
    else:
        print("   ✗ No production model found")
    
    # Check registry
    print("\n📋 Model Registry:")
    try:
        registry = ModelRegistry()
        stats = registry.get_registry_stats()
        print(f"   Total models: {stats['total_models']}")
        print(f"   Production model: {stats['production_model'] or 'None'}")
        print(f"   Staging model: {stats['staging_model'] or 'None'}")
        print(f"   A/B Testing: {'Enabled' if stats['ab_testing_enabled'] else 'Disabled'}")
        
        if stats['by_status']:
            print("   By status:")
            for status, count in stats['by_status'].items():
                print(f"     - {status}: {count}")
    except Exception as e:
        print(f"   Registry not initialized: {e}")
    
    # Check dependencies
    print("\n📚 Dependencies:")
    dependencies = [
        ('numpy', 'np'),
        ('pandas', 'pd'),
        ('sklearn', 'sklearn'),
        ('shap', 'shap'),
        ('streamlit', 'streamlit'),
        ('plotly', 'plotly')
    ]
    
    for name, module in dependencies:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'unknown')
            print(f"   ✓ {name}: {version}")
        except ImportError:
            print(f"   ✗ {name}: NOT INSTALLED")
    
    print("\n" + "="*60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Loan Approval System CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py train --samples 10000 --model-type ensemble
  python main.py serve
  python main.py test
  python main.py predict
  python main.py benchmark
  python main.py status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train a new model')
    train_parser.add_argument('--samples', type=int, default=5000,
                             help='Number of training samples')
    train_parser.add_argument('--model-type', choices=['gradient_boosting', 'random_forest', 'ensemble', 'stacking'],
                             default='gradient_boosting', help='Model type')
    train_parser.set_defaults(func=train_model)
    
    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start the dashboard')
    serve_parser.set_defaults(func=serve_app)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.set_defaults(func=run_tests)
    
    # Predict command
    predict_parser = subparsers.add_parser('predict', help='Make test predictions')
    predict_parser.set_defaults(func=make_prediction)
    
    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark performance')
    bench_parser.set_defaults(func=benchmark)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    status_parser.set_defaults(func=show_status)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
