# Explainable AI Dashboard for Loan Approval 🏦

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/amannjoshi/Loan-approval-disapproval)
[![Python](https://img.shields.io/badge/Python-3.10+-green?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit)](https://streamlit.io)

A professional, transparent AI-powered loan assessment system with clear explanations for every decision. Built with fairness and accountability in mind.

**🔗 Repository:** [https://github.com/amannjoshi/Loan-approval-disapproval](https://github.com/amannjoshi/Loan-approval-disapproval)

---

## 🎯 What Problem Does This Solve?

**Traditional AI loan systems:**
- Give decisions without explanations
- Leave customers frustrated ("Why was I denied?")
- Create compliance and fairness risks
- Erode trust in banking institutions

**This XAI Dashboard:**
- ✅ Shows exactly WHY a decision was made
- ✅ Visual charts make it crystal clear
- ✅ Monitors for bias across demographics
- ✅ Provides improvement suggestions
- ✅ Builds trust with transparency

---

## 📸 Example Scenario

**Priya Sharma, 28 years old, Agra**  
Applying for ₹5,00,000 Personal Loan

**Without XAI (Old Way):**
> "Your loan has been denied." — No explanation given.

**With This Dashboard:**
> **Decision: NOT APPROVED**
> 
> **Why?**
> - Late payments in last 2 years → Impact: -0.42 (40% weight)
> - Low income relative to loan amount → Impact: -0.28
> - Short credit history (3 years) → Impact: -0.15
> 
> **In Your Favor:**
> - Stable employment (+0.12)
> - No previous defaults (+0.08)
> 
> **How to Improve:**
> 1. Improve CIBIL score to 700+
> 2. Clear late payment history for 6 months
> 3. Consider a smaller loan amount

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd "Loan Approval"
pip install -r requirements.txt
```

### 2. Run the Dashboard

```bash
streamlit run app.py
```

### 3. Open in Browser

The app will automatically open at `http://localhost:8501`

---

## 📂 Project Structure

```
Loan Approval/
│
├── app.py                    # Main Streamlit dashboard
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── data/
│   ├── __init__.py
│   ├── data_generator.py     # Synthetic data generation
│   └── loan_applications.csv # Generated training data
│
├── models/
│   ├── __init__.py
│   ├── loan_model.py         # ML model with SHAP explainability
│   └── loan_model.pkl        # Trained model (auto-generated)
│
└── utils/
    ├── __init__.py
    └── fairness_analyzer.py  # Bias detection & fairness metrics
```

---

## 🎨 Dashboard Features

### 1. 🎯 New Application Page
- Enter applicant details (personal, employment, credit)
- Get instant loan decision
- See visual explanation of decision factors
- Receive personalized improvement suggestions

### 2. 📊 Fairness Monitor
- Track approval rates across gender, age, income groups
- Disparate Impact Ratio calculation
- Automated bias detection alerts
- Regulatory compliance support

### 3. 📈 Model Insights
- Feature importance rankings
- Data distribution analysis
- Model performance metrics

### 4. ℹ️ About
- How XAI works (SHAP values explained simply)
- Fairness principles
- Technical documentation

---

## 🔬 How the Explainability Works

We use **SHAP (SHapley Additive exPlanations)** values:

1. **Game Theory Foundation**: Each feature gets fair credit for its contribution
2. **Additive**: All contributions sum to the final prediction
3. **Local Explanations**: Each decision explained individually
4. **Visual**: Bar charts and waterfall plots make it intuitive

**Example SHAP Breakdown:**
```
Base approval rate:        0.52
+ CIBIL Score (720):      +0.18
+ Stable employment:      +0.12
- Late payments (2):      -0.25
- Low income ratio:       -0.15
- Short credit history:   -0.08
= Final score:             0.34 → DENIED (threshold: 0.50)
```

---

## 📊 Fairness Metrics

| Metric | What It Measures | Target |
|--------|------------------|--------|
| Demographic Parity | Same approval rates across groups | < 10% difference |
| Disparate Impact | Ratio of approval rates | ≥ 80% |
| Equalized Odds | Equal TPR/FPR across groups | < 10% difference |

---

## 🛠️ Customization

### Using Your Own Data

Replace the synthetic data with real loan data:

```python
# In app.py, modify get_training_data():
df = pd.read_csv('your_actual_loan_data.csv')
```

Required columns:
- `age`, `gender`, `education`, `marital_status`
- `employment_type`, `monthly_income`, `existing_emi`
- `cibil_score`, `credit_history_years`, `late_payments_last_2_years`
- `has_defaults`, `loan_amount`, `loan_tenure_months`
- `loan_approved` (target: 0 or 1)

### Adjusting Model Parameters

Edit `models/loan_model.py`:

```python
self.model = GradientBoostingClassifier(
    n_estimators=150,      # Increase for more accuracy
    max_depth=5,           # Decrease to reduce overfitting
    learning_rate=0.1,     # Lower for smoother learning
)
```

---

## 🏛️ Regulatory Compliance

This dashboard helps banks comply with:

- **RBI Fair Practices Code** - Transparent lending decisions
- **Equal Credit Opportunity** - No discrimination in lending
- **GDPR Right to Explanation** - Automated decision explanations
- **Indian IT Act** - Algorithmic accountability

---

## 🤝 For Bank Staff

**Loan Officers can use this to:**
1. Quickly assess applications
2. Explain decisions to customers clearly
3. Identify areas where applicants can improve
4. Ensure fair treatment across customer segments

**Compliance Teams can use this to:**
1. Monitor model fairness continuously
2. Generate audit-ready reports
3. Detect and address bias early
4. Demonstrate regulatory compliance

---

## 📧 Support

For questions or issues:
- Review the "About" page in the dashboard
- Check the code comments for technical details
- Ensure all dependencies are correctly installed

---

## 📜 License

This project is for educational and demonstration purposes.  
Actual deployment in banking requires proper compliance review.

---

**Built with ❤️ for transparent, fair, and explainable AI in banking**
