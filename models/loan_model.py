"""
Loan Approval Prediction Model with Explainable AI
===================================================
This module implements a machine learning model for loan approval
prediction with built-in explainability using SHAP (SHapley Additive
exPlanations) values.

The model provides:
- Accurate loan approval predictions
- Individual explanation for each decision
- Feature importance analysis
- Confidence scores

Author: Loan Analytics Team
Last Updated: January 2026
"""

import numpy as np
import pandas as pd
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import shap
import warnings
warnings.filterwarnings('ignore')


class LoanApprovalModel:
    """
    Explainable Loan Approval Prediction Model.
    
    This class encapsulates the complete ML pipeline including:
    - Data preprocessing
    - Model training
    - Prediction with probability scores
    - SHAP-based explanations
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = None
        self.explainer = None
        self.is_trained = False
        
        # Features used for prediction
        self.categorical_features = [
            'gender', 'education', 'marital_status', 
            'employment_type', 'industry'
        ]
        
        self.numerical_features = [
            'age', 'num_dependents', 'years_at_current_job',
            'monthly_income', 'existing_emi', 'num_existing_loans',
            'cibil_score', 'credit_history_years', 
            'late_payments_last_2_years', 'savings_balance',
            'years_with_bank', 'loan_amount', 'loan_tenure_months'
        ]
        
        self.boolean_features = ['has_defaults', 'owns_property']
        
        # Human-readable feature names for display
        self.feature_display_names = {
            'age': 'Age',
            'gender': 'Gender',
            'education': 'Education Level',
            'marital_status': 'Marital Status',
            'num_dependents': 'Number of Dependents',
            'employment_type': 'Employment Type',
            'industry': 'Industry',
            'years_at_current_job': 'Years at Current Job',
            'monthly_income': 'Monthly Income (₹)',
            'existing_emi': 'Existing EMI (₹)',
            'num_existing_loans': 'Number of Existing Loans',
            'cibil_score': 'CIBIL Score',
            'credit_history_years': 'Credit History Length (Years)',
            'late_payments_last_2_years': 'Late Payments (Last 2 Years)',
            'has_defaults': 'Has Previous Defaults',
            'owns_property': 'Property Owner',
            'savings_balance': 'Savings Balance (₹)',
            'years_with_bank': 'Years with Bank',
            'loan_amount': 'Loan Amount Requested (₹)',
            'loan_tenure_months': 'Loan Tenure (Months)'
        }
    
    def preprocess_data(self, df, is_training=False):
        """
        Preprocess the input data for model training or prediction.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Input dataframe with raw features
        is_training : bool
            If True, fit the encoders and scaler
            
        Returns:
        --------
        np.ndarray
            Preprocessed feature matrix
        """
        df_processed = df.copy()
        
        # Encode categorical features
        for col in self.categorical_features:
            if col in df_processed.columns:
                if is_training:
                    self.label_encoders[col] = LabelEncoder()
                    df_processed[col] = self.label_encoders[col].fit_transform(
                        df_processed[col].astype(str)
                    )
                else:
                    if col in self.label_encoders:
                        # Handle unseen categories
                        known_classes = set(self.label_encoders[col].classes_)
                        df_processed[col] = df_processed[col].apply(
                            lambda x: x if x in known_classes else self.label_encoders[col].classes_[0]
                        )
                        df_processed[col] = self.label_encoders[col].transform(
                            df_processed[col].astype(str)
                        )
        
        # Convert boolean features to int
        for col in self.boolean_features:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].astype(int)
        
        # Select features in correct order
        all_features = self.categorical_features + self.numerical_features + self.boolean_features
        available_features = [f for f in all_features if f in df_processed.columns]
        
        X = df_processed[available_features].values
        
        if is_training:
            self.feature_names = available_features
            X = self.scaler.fit_transform(X)
        else:
            X = self.scaler.transform(X)
        
        return X
    
    def train(self, df, target_column='loan_approved'):
        """
        Train the loan approval model.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Training data with features and target
        target_column : str
            Name of the target column
            
        Returns:
        --------
        dict
            Training metrics
        """
        print("Starting model training...")
        
        # Preprocess features
        X = self.preprocess_data(df, is_training=True)
        y = df[target_column].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train Gradient Boosting model (good balance of accuracy and explainability)
        self.model = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            validation_fraction=0.1,
            n_iter_no_change=10
        )
        
        print("Training Gradient Boosting classifier...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'auc_roc': roc_auc_score(y_test, y_prob)
        }
        
        print(f"Model trained successfully!")
        print(f"  Accuracy: {metrics['accuracy']:.3f}")
        print(f"  AUC-ROC: {metrics['auc_roc']:.3f}")
        
        # Initialize SHAP explainer
        print("Initializing SHAP explainer...")
        self.explainer = shap.TreeExplainer(self.model)
        
        self.is_trained = True
        
        return metrics
    
    def predict(self, df):
        """
        Make loan approval prediction.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Applicant data (single row or multiple)
            
        Returns:
        --------
        dict
            Prediction result with probability
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet. Call train() first.")
        
        X = self.preprocess_data(df, is_training=False)
        
        prediction = self.model.predict(X)[0]
        probability = self.model.predict_proba(X)[0]
        
        return {
            'approved': bool(prediction),
            'approval_probability': float(probability[1]),
            'denial_probability': float(probability[0]),
            'confidence': float(max(probability))
        }
    
    def explain_prediction(self, df):
        """
        Generate SHAP explanation for a prediction.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Single applicant data
            
        Returns:
        --------
        dict
            Detailed explanation with feature contributions
        """
        if not self.is_trained or self.explainer is None:
            raise ValueError("Model not trained or explainer not initialized.")
        
        X = self.preprocess_data(df, is_training=False)
        
        # Get SHAP values
        shap_values = self.explainer.shap_values(X)
        
        # For binary classification, we want the values for positive class
        if isinstance(shap_values, list):
            shap_vals = shap_values[1][0]  # Positive class, first sample
        else:
            # Single array returned - take first row
            shap_vals = shap_values[0] if shap_values.ndim > 1 else shap_values
        
        # Base value (average prediction)
        base_value = self.explainer.expected_value
        if isinstance(base_value, np.ndarray):
            # Handle both single value and array cases
            base_value = base_value[1] if len(base_value) > 1 else base_value[0]
        
        # Create feature contribution dictionary
        contributions = []
        for i, feature in enumerate(self.feature_names):
            display_name = self.feature_display_names.get(feature, feature)
            contribution = float(shap_vals[i])
            
            # Get original feature value for display
            if feature in df.columns:
                original_value = df[feature].iloc[0]
            else:
                original_value = X[0, i]
            
            contributions.append({
                'feature': feature,
                'display_name': display_name,
                'contribution': contribution,
                'original_value': original_value,
                'impact': 'positive' if contribution > 0 else 'negative'
            })
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
        
        # Separate positive and negative factors
        positive_factors = [c for c in contributions if c['contribution'] > 0.01]
        negative_factors = [c for c in contributions if c['contribution'] < -0.01]
        
        return {
            'base_value': float(base_value),
            'all_contributions': contributions,
            'positive_factors': positive_factors[:5],  # Top 5 positive
            'negative_factors': negative_factors[:5],  # Top 5 negative
            'shap_values': shap_vals.tolist(),
            'feature_names': self.feature_names,
            'feature_display_names': [
                self.feature_display_names.get(f, f) for f in self.feature_names
            ]
        }
    
    def get_feature_importance(self):
        """
        Get overall feature importance from the trained model.
        
        Returns:
        --------
        pd.DataFrame
            Feature importance dataframe
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet.")
        
        importance = self.model.feature_importances_
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'display_name': [self.feature_display_names.get(f, f) for f in self.feature_names],
            'importance': importance
        })
        
        importance_df = importance_df.sort_values('importance', ascending=False)
        
        return importance_df
    
    def save_model(self, filepath='models/loan_model.pkl'):
        """Save the trained model to disk."""
        if not self.is_trained:
            raise ValueError("No trained model to save.")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'feature_display_names': self.feature_display_names,
            'categorical_features': self.categorical_features,
            'numerical_features': self.numerical_features,
            'boolean_features': self.boolean_features
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath='models/loan_model.pkl'):
        """Load a trained model from disk."""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data['label_encoders']
        self.feature_names = model_data['feature_names']
        self.feature_display_names = model_data['feature_display_names']
        self.categorical_features = model_data['categorical_features']
        self.numerical_features = model_data['numerical_features']
        self.boolean_features = model_data['boolean_features']
        
        # Reinitialize SHAP explainer
        self.explainer = shap.TreeExplainer(self.model)
        
        self.is_trained = True
        print(f"Model loaded from {filepath}")


def generate_human_explanation(prediction_result, explanation, applicant_data):
    """
    Generate a human-readable explanation of the loan decision.
    This is what would be shown to the applicant or loan officer.
    
    Parameters:
    -----------
    prediction_result : dict
        Output from predict()
    explanation : dict
        Output from explain_prediction()
    applicant_data : pd.DataFrame
        Original applicant data
        
    Returns:
    --------
    str
        Human-readable explanation
    """
    status = "APPROVED ✓" if prediction_result['approved'] else "NOT APPROVED ✗"
    confidence = prediction_result['confidence'] * 100
    
    lines = [
        f"═══════════════════════════════════════════════════════════",
        f"           LOAN DECISION: {status}",
        f"           Confidence: {confidence:.1f}%",
        f"═══════════════════════════════════════════════════════════",
        "",
        "EXPLANATION OF DECISION:",
        "─────────────────────────────────────────────────────────────",
    ]
    
    if explanation['negative_factors']:
        lines.append("")
        lines.append("⚠️  FACTORS WORKING AGAINST APPROVAL:")
        for factor in explanation['negative_factors']:
            impact_pct = abs(factor['contribution']) * 100
            value = factor['original_value']
            lines.append(
                f"   • {factor['display_name']}: {value}")
            lines.append(
                f"     → Impact on score: {factor['contribution']:.2f} ({impact_pct:.0f}% weight)"
            )
    
    if explanation['positive_factors']:
        lines.append("")
        lines.append("✅  FACTORS IN YOUR FAVOR:")
        for factor in explanation['positive_factors']:
            impact_pct = abs(factor['contribution']) * 100
            value = factor['original_value']
            lines.append(
                f"   • {factor['display_name']}: {value}")
            lines.append(
                f"     → Impact on score: +{factor['contribution']:.2f} ({impact_pct:.0f}% weight)"
            )
    
    lines.extend([
        "",
        "─────────────────────────────────────────────────────────────",
        "Note: This decision is based on multiple factors analyzed",
        "by our AI system. For questions, please speak with a loan",
        "officer who can provide additional guidance.",
        "═══════════════════════════════════════════════════════════"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the model
    from data_generator import generate_synthetic_data
    
    print("Generating training data...")
    df = generate_synthetic_data(n_samples=5000)
    
    print("\nTraining model...")
    model = LoanApprovalModel()
    metrics = model.train(df)
    
    print("\n--- Model Performance ---")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.3f}")
    
    # Test on a sample
    print("\n--- Testing on sample applicant ---")
    sample = df.sample(1)
    print(f"Applicant: {sample['applicant_name'].values[0]}")
    print(f"Actual result: {'Approved' if sample['loan_approved'].values[0] else 'Denied'}")
    
    prediction = model.predict(sample)
    explanation = model.explain_prediction(sample)
    
    human_text = generate_human_explanation(prediction, explanation, sample)
    print(human_text)
    
    # Save model
    model.save_model()
