"""
Synthetic Data Generator for Indian Loan Applicants
=====================================================
Creates realistic loan application data for training and testing
the explainable AI model. Based on actual Indian banking patterns.

Author: Loan Analytics Team
Last Updated: January 2026
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

# Indian cities for realistic data
INDIAN_CITIES = [
    'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Ahmedabad', 'Chennai',
    'Kolkata', 'Pune', 'Jaipur', 'Lucknow', 'Kanpur', 'Nagpur', 'Indore',
    'Thane', 'Bhopal', 'Visakhapatnam', 'Patna', 'Vadodara', 'Ghaziabad',
    'Ludhiana', 'Agra', 'Nashik', 'Faridabad', 'Meerut', 'Rajkot',
    'Varanasi', 'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar', 'Noida'
]

# Common Indian names (first names)
MALE_NAMES = [
    'Rahul', 'Amit', 'Vijay', 'Suresh', 'Raj', 'Anil', 'Sanjay', 'Deepak',
    'Ravi', 'Manoj', 'Ajay', 'Vikram', 'Ashok', 'Ramesh', 'Sunil', 'Pradeep',
    'Rajesh', 'Rakesh', 'Nikhil', 'Arjun', 'Karan', 'Rohit', 'Vishal', 'Ankit'
]

FEMALE_NAMES = [
    'Priya', 'Anjali', 'Sunita', 'Kavita', 'Neha', 'Pooja', 'Ritu', 'Meena',
    'Shalini', 'Rekha', 'Anita', 'Geeta', 'Divya', 'Swati', 'Komal', 'Nisha',
    'Shreya', 'Aishwarya', 'Deepika', 'Sakshi', 'Megha', 'Pallavi', 'Sneha', 'Ritika'
]

LAST_NAMES = [
    'Sharma', 'Verma', 'Gupta', 'Singh', 'Kumar', 'Patel', 'Joshi', 'Yadav',
    'Agarwal', 'Jain', 'Mishra', 'Pandey', 'Reddy', 'Rao', 'Nair', 'Iyer',
    'Mehta', 'Shah', 'Malhotra', 'Kapoor', 'Bansal', 'Tiwari', 'Srivastava', 'Chauhan'
]

# Employment types and industries
EMPLOYMENT_TYPES = ['Salaried', 'Self-Employed', 'Business Owner', 'Government', 'Retired']
INDUSTRIES = [
    'Information Technology', 'Banking & Finance', 'Healthcare', 'Education',
    'Manufacturing', 'Retail', 'Real Estate', 'Hospitality', 'Agriculture',
    'Transportation', 'Telecommunications', 'Media & Entertainment', 'Government'
]

# Loan purposes
LOAN_PURPOSES = [
    'Personal Expenses', 'Home Renovation', 'Medical Emergency', 'Education',
    'Wedding', 'Debt Consolidation', 'Business Expansion', 'Vehicle Purchase',
    'Travel', 'Electronics/Appliances'
]


def generate_credit_score(income, employment_type, age, has_defaults):
    """
    Generate realistic CIBIL score based on applicant profile.
    CIBIL scores in India range from 300 to 900.
    """
    base_score = 650
    
    # Income factor
    if income > 100000:
        base_score += 80
    elif income > 75000:
        base_score += 50
    elif income > 50000:
        base_score += 25
    elif income < 25000:
        base_score -= 40
    
    # Employment stability factor
    if employment_type == 'Government':
        base_score += 40
    elif employment_type == 'Salaried':
        base_score += 20
    elif employment_type == 'Business Owner':
        base_score += 10
    elif employment_type == 'Self-Employed':
        base_score -= 10
    
    # Age factor (experience in credit)
    if age > 40:
        base_score += 30
    elif age > 30:
        base_score += 15
    elif age < 25:
        base_score -= 20
    
    # Defaults major negative impact
    if has_defaults:
        base_score -= 150
    
    # Add some randomness
    base_score += random.randint(-50, 50)
    
    # Clamp to valid range
    return max(300, min(900, base_score))


def generate_loan_decision(row):
    """
    Generate loan approval decision based on multiple factors.
    This mimics real bank decision logic.
    """
    score = 0
    
    # CIBIL Score - Major factor (40% weight)
    if row['cibil_score'] >= 750:
        score += 40
    elif row['cibil_score'] >= 700:
        score += 30
    elif row['cibil_score'] >= 650:
        score += 15
    elif row['cibil_score'] >= 600:
        score += 5
    else:
        score -= 20
    
    # Debt-to-Income Ratio (25% weight)
    dti = row['existing_emi'] / row['monthly_income'] if row['monthly_income'] > 0 else 1
    if dti < 0.2:
        score += 25
    elif dti < 0.35:
        score += 15
    elif dti < 0.5:
        score += 5
    else:
        score -= 15
    
    # Employment Stability (15% weight)
    if row['years_at_current_job'] >= 5:
        score += 15
    elif row['years_at_current_job'] >= 3:
        score += 10
    elif row['years_at_current_job'] >= 1:
        score += 5
    else:
        score -= 5
    
    # Credit History Length (10% weight)
    if row['credit_history_years'] >= 7:
        score += 10
    elif row['credit_history_years'] >= 4:
        score += 6
    elif row['credit_history_years'] >= 2:
        score += 3
    else:
        score -= 5
    
    # Late Payments - Negative factor
    if row['late_payments_last_2_years'] == 0:
        score += 10
    elif row['late_payments_last_2_years'] <= 2:
        score -= 5
    elif row['late_payments_last_2_years'] <= 5:
        score -= 15
    else:
        score -= 30
    
    # Loan Amount vs Income
    loan_to_income = row['loan_amount'] / (row['monthly_income'] * 12) if row['monthly_income'] > 0 else 10
    if loan_to_income <= 0.5:
        score += 10
    elif loan_to_income <= 1:
        score += 5
    elif loan_to_income > 2:
        score -= 15
    
    # Defaults - Major negative
    if row['has_defaults']:
        score -= 40
    
    # Age factor
    if 30 <= row['age'] <= 55:
        score += 5
    elif row['age'] < 23 or row['age'] > 60:
        score -= 10
    
    # Decision threshold with some noise
    threshold = 45 + random.randint(-5, 5)
    
    return 1 if score >= threshold else 0


def generate_synthetic_data(n_samples=5000, random_seed=42):
    """
    Generate synthetic loan application dataset.
    
    Parameters:
    -----------
    n_samples : int
        Number of samples to generate
    random_seed : int
        Random seed for reproducibility
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with loan application data
    """
    np.random.seed(random_seed)
    random.seed(random_seed)
    
    data = []
    
    for i in range(n_samples):
        # Basic demographics
        gender = random.choice(['Male', 'Female'])
        first_name = random.choice(MALE_NAMES if gender == 'Male' else FEMALE_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        
        age = int(np.random.normal(35, 10))
        age = max(21, min(65, age))  # Clamp to reasonable range
        
        city = random.choice(INDIAN_CITIES)
        
        # Employment details
        employment_type = random.choices(
            EMPLOYMENT_TYPES,
            weights=[45, 20, 15, 15, 5],
            k=1
        )[0]
        
        industry = random.choice(INDUSTRIES)
        
        # Years at job (correlated with age)
        max_years = min(age - 21, 30)
        years_at_current_job = max(0, int(np.random.exponential(3)))
        years_at_current_job = min(years_at_current_job, max_years)
        
        # Monthly income based on employment type and age
        base_income = {
            'Salaried': 45000,
            'Self-Employed': 55000,
            'Business Owner': 80000,
            'Government': 50000,
            'Retired': 35000
        }[employment_type]
        
        # Income grows with age/experience
        income_multiplier = 1 + (age - 25) * 0.03 + years_at_current_job * 0.05
        monthly_income = int(base_income * income_multiplier * np.random.uniform(0.6, 1.5))
        monthly_income = max(15000, monthly_income)  # Minimum income threshold
        
        # Credit history
        credit_history_years = min(age - 21, int(np.random.exponential(5)))
        credit_history_years = max(0, credit_history_years)
        
        # Financial behavior - correlated
        has_defaults = random.random() < 0.08  # 8% default rate
        
        if has_defaults:
            late_payments = random.randint(3, 12)
        else:
            late_payments = int(np.random.exponential(1))
            late_payments = min(late_payments, 8)
        
        # Existing EMI (debt)
        if random.random() < 0.6:  # 60% have existing loans
            existing_emi = int(monthly_income * np.random.uniform(0.05, 0.4))
        else:
            existing_emi = 0
        
        # Number of existing loans
        num_existing_loans = 0
        if existing_emi > 0:
            num_existing_loans = random.randint(1, 4)
        
        # CIBIL score
        cibil_score = generate_credit_score(monthly_income, employment_type, age, has_defaults)
        
        # Loan details
        loan_purpose = random.choice(LOAN_PURPOSES)
        
        # Loan amount based on income
        loan_amount = int(monthly_income * random.uniform(3, 24))
        # Round to nearest 25000
        loan_amount = round(loan_amount / 25000) * 25000
        loan_amount = max(50000, min(2000000, loan_amount))  # ₹50K to ₹20L range
        
        loan_tenure = random.choice([12, 24, 36, 48, 60])  # months
        
        # Property ownership
        owns_property = random.random() < (0.3 + age * 0.01)
        
        # Bank relationship
        years_with_bank = min(age - 18, int(np.random.exponential(4)))
        years_with_bank = max(0, years_with_bank)
        
        # Dependents
        num_dependents = random.choices([0, 1, 2, 3, 4], weights=[20, 25, 30, 15, 10], k=1)[0]
        
        # Marital status (correlated with age)
        if age < 25:
            marital_status = random.choices(['Single', 'Married'], weights=[80, 20], k=1)[0]
        elif age < 35:
            marital_status = random.choices(['Single', 'Married'], weights=[30, 70], k=1)[0]
        else:
            marital_status = random.choices(['Single', 'Married', 'Divorced'], weights=[15, 75, 10], k=1)[0]
        
        # Education
        education = random.choices(
            ['High School', 'Graduate', 'Post Graduate', 'Professional'],
            weights=[15, 40, 30, 15],
            k=1
        )[0]
        
        # Savings account balance (correlated with income)
        savings_balance = int(monthly_income * np.random.uniform(0.5, 6))
        
        record = {
            'applicant_id': f'APP{100000 + i}',
            'applicant_name': full_name,
            'age': age,
            'gender': gender,
            'city': city,
            'education': education,
            'marital_status': marital_status,
            'num_dependents': num_dependents,
            'employment_type': employment_type,
            'industry': industry,
            'years_at_current_job': years_at_current_job,
            'monthly_income': monthly_income,
            'existing_emi': existing_emi,
            'num_existing_loans': num_existing_loans,
            'cibil_score': cibil_score,
            'credit_history_years': credit_history_years,
            'late_payments_last_2_years': late_payments,
            'has_defaults': has_defaults,
            'owns_property': owns_property,
            'savings_balance': savings_balance,
            'years_with_bank': years_with_bank,
            'loan_amount': loan_amount,
            'loan_tenure_months': loan_tenure,
            'loan_purpose': loan_purpose
        }
        
        data.append(record)
    
    df = pd.DataFrame(data)
    
    # Generate loan decisions
    df['loan_approved'] = df.apply(generate_loan_decision, axis=1)
    
    return df


def save_dataset(df, filepath='loan_data.csv'):
    """Save generated dataset to CSV file."""
    df.to_csv(filepath, index=False)
    print(f"Dataset saved to {filepath}")
    print(f"Total records: {len(df)}")
    print(f"Approval rate: {df['loan_approved'].mean()*100:.1f}%")
    return filepath


if __name__ == "__main__":
    # Generate and save sample data
    print("Generating synthetic loan application data...")
    df = generate_synthetic_data(n_samples=5000)
    save_dataset(df, 'data/loan_applications.csv')
    
    # Show sample statistics
    print("\n--- Dataset Summary ---")
    print(f"Gender distribution:\n{df['gender'].value_counts()}")
    print(f"\nEmployment distribution:\n{df['employment_type'].value_counts()}")
    print(f"\nApproval by gender:")
    print(df.groupby('gender')['loan_approved'].mean())
