import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiUser, FiDollarSign, FiBriefcase, FiFileText, FiCheck, FiChevronRight, FiChevronLeft, FiAlertCircle } from 'react-icons/fi';
import { toast } from 'react-toastify';
// Note: loanService will be used when connecting to real backend
// import { loanService } from '../services/api';
import './LoanApplication.css';

const LoanApplication = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const [formData, setFormData] = useState({
    // Personal Information
    fullName: '',
    email: '',
    phone: '',
    dateOfBirth: '',
    panNumber: '',
    aadhaarNumber: '',
    address: '',
    city: '',
    state: '',
    pincode: '',

    // Employment Details
    employmentType: '',
    companyName: '',
    designation: '',
    workExperience: '',
    monthlyIncome: '',

    // Loan Details
    loanAmount: '',
    loanPurpose: '',
    loanTenure: '',
    existingLoans: 'no',
    existingEMI: '',

    // Documents
    agreeTerms: false,
    consentDataProcessing: false
  });

  const steps = [
    { id: 1, title: 'Personal Info', icon: FiUser },
    { id: 2, title: 'Employment', icon: FiBriefcase },
    { id: 3, title: 'Loan Details', icon: FiDollarSign },
    { id: 4, title: 'Review', icon: FiFileText }
  ];

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateStep = (step) => {
    const newErrors = {};

    switch (step) {
      case 1:
        if (!formData.fullName.trim()) newErrors.fullName = 'Full name is required';
        if (!formData.email.trim()) {
          newErrors.email = 'Email is required';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
          newErrors.email = 'Invalid email format';
        }
        if (!formData.phone.trim()) {
          newErrors.phone = 'Phone number is required';
        } else if (!/^[6-9]\d{9}$/.test(formData.phone)) {
          newErrors.phone = 'Invalid phone number';
        }
        if (!formData.dateOfBirth) newErrors.dateOfBirth = 'Date of birth is required';
        if (!formData.panNumber.trim()) {
          newErrors.panNumber = 'PAN number is required';
        } else if (!/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(formData.panNumber.toUpperCase())) {
          newErrors.panNumber = 'Invalid PAN format (e.g., ABCDE1234F)';
        }
        if (!formData.address.trim()) newErrors.address = 'Address is required';
        if (!formData.city.trim()) newErrors.city = 'City is required';
        if (!formData.state.trim()) newErrors.state = 'State is required';
        if (!formData.pincode.trim()) {
          newErrors.pincode = 'Pincode is required';
        } else if (!/^\d{6}$/.test(formData.pincode)) {
          newErrors.pincode = 'Invalid pincode';
        }
        break;

      case 2:
        if (!formData.employmentType) newErrors.employmentType = 'Employment type is required';
        if (!formData.companyName.trim()) newErrors.companyName = 'Company name is required';
        if (!formData.designation.trim()) newErrors.designation = 'Designation is required';
        if (!formData.workExperience) newErrors.workExperience = 'Work experience is required';
        if (!formData.monthlyIncome) {
          newErrors.monthlyIncome = 'Monthly income is required';
        } else if (parseFloat(formData.monthlyIncome) < 15000) {
          newErrors.monthlyIncome = 'Minimum income should be ₹15,000';
        }
        break;

      case 3:
        if (!formData.loanAmount) {
          newErrors.loanAmount = 'Loan amount is required';
        } else if (parseFloat(formData.loanAmount) < 50000) {
          newErrors.loanAmount = 'Minimum loan amount is ₹50,000';
        } else if (parseFloat(formData.loanAmount) > 5000000) {
          newErrors.loanAmount = 'Maximum loan amount is ₹50,00,000';
        }
        if (!formData.loanPurpose) newErrors.loanPurpose = 'Loan purpose is required';
        if (!formData.loanTenure) newErrors.loanTenure = 'Loan tenure is required';
        if (formData.existingLoans === 'yes' && !formData.existingEMI) {
          newErrors.existingEMI = 'Existing EMI amount is required';
        }
        break;

      case 4:
        if (!formData.agreeTerms) newErrors.agreeTerms = 'You must agree to the terms';
        if (!formData.consentDataProcessing) newErrors.consentDataProcessing = 'Data processing consent is required';
        break;

      default:
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 4));
    }
  };

  const handlePrevious = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(4)) return;

    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // In real app, call: await loanService.createApplication(formData);
      
      toast.success('Application submitted successfully!', {
        position: 'top-right',
        autoClose: 3000
      });

      navigate('/status', { state: { applicationId: 'LA-2024-NEW' } });
    } catch (error) {
      toast.error('Failed to submit application. Please try again.', {
        position: 'top-right'
      });
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (!value) return '';
    return new Intl.NumberFormat('en-IN').format(value);
  };

  const renderStepIndicator = () => (
    <div className="step-indicator">
      {steps.map((step, index) => (
        <React.Fragment key={step.id}>
          <div className={`step ${currentStep >= step.id ? 'active' : ''} ${currentStep > step.id ? 'completed' : ''}`}>
            <div className="step-circle">
              {currentStep > step.id ? <FiCheck /> : <step.icon />}
            </div>
            <span className="step-title">{step.title}</span>
          </div>
          {index < steps.length - 1 && (
            <div className={`step-line ${currentStep > step.id ? 'completed' : ''}`}></div>
          )}
        </React.Fragment>
      ))}
    </div>
  );

  const renderStep1 = () => (
    <div className="form-step">
      <h2 className="step-heading">Personal Information</h2>
      <p className="step-description">Please provide your basic details for verification.</p>

      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="fullName">Full Name <span className="required">*</span></label>
          <input
            type="text"
            id="fullName"
            name="fullName"
            value={formData.fullName}
            onChange={handleChange}
            placeholder="Enter your full name"
            className={errors.fullName ? 'error' : ''}
          />
          {errors.fullName && <span className="error-message"><FiAlertCircle /> {errors.fullName}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="email">Email Address <span className="required">*</span></label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Enter your email"
            className={errors.email ? 'error' : ''}
          />
          {errors.email && <span className="error-message"><FiAlertCircle /> {errors.email}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="phone">Phone Number <span className="required">*</span></label>
          <div className="input-with-prefix">
            <span className="input-prefix">+91</span>
            <input
              type="tel"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              placeholder="Enter 10-digit number"
              maxLength={10}
              className={errors.phone ? 'error' : ''}
            />
          </div>
          {errors.phone && <span className="error-message"><FiAlertCircle /> {errors.phone}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="dateOfBirth">Date of Birth <span className="required">*</span></label>
          <input
            type="date"
            id="dateOfBirth"
            name="dateOfBirth"
            value={formData.dateOfBirth}
            onChange={handleChange}
            className={errors.dateOfBirth ? 'error' : ''}
          />
          {errors.dateOfBirth && <span className="error-message"><FiAlertCircle /> {errors.dateOfBirth}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="panNumber">PAN Number <span className="required">*</span></label>
          <input
            type="text"
            id="panNumber"
            name="panNumber"
            value={formData.panNumber}
            onChange={handleChange}
            placeholder="e.g., ABCDE1234F"
            maxLength={10}
            className={errors.panNumber ? 'error' : ''}
            style={{ textTransform: 'uppercase' }}
          />
          {errors.panNumber && <span className="error-message"><FiAlertCircle /> {errors.panNumber}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="aadhaarNumber">Aadhaar Number (Optional)</label>
          <input
            type="text"
            id="aadhaarNumber"
            name="aadhaarNumber"
            value={formData.aadhaarNumber}
            onChange={handleChange}
            placeholder="Enter 12-digit Aadhaar"
            maxLength={12}
          />
        </div>
      </div>

      <h3 className="section-title">Address Details</h3>
      
      <div className="form-grid">
        <div className="form-group full-width">
          <label htmlFor="address">Street Address <span className="required">*</span></label>
          <textarea
            id="address"
            name="address"
            value={formData.address}
            onChange={handleChange}
            placeholder="Enter your complete address"
            rows={3}
            className={errors.address ? 'error' : ''}
          />
          {errors.address && <span className="error-message"><FiAlertCircle /> {errors.address}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="city">City <span className="required">*</span></label>
          <input
            type="text"
            id="city"
            name="city"
            value={formData.city}
            onChange={handleChange}
            placeholder="Enter city"
            className={errors.city ? 'error' : ''}
          />
          {errors.city && <span className="error-message"><FiAlertCircle /> {errors.city}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="state">State <span className="required">*</span></label>
          <select
            id="state"
            name="state"
            value={formData.state}
            onChange={handleChange}
            className={errors.state ? 'error' : ''}
          >
            <option value="">Select State</option>
            <option value="andhra-pradesh">Andhra Pradesh</option>
            <option value="delhi">Delhi</option>
            <option value="gujarat">Gujarat</option>
            <option value="karnataka">Karnataka</option>
            <option value="maharashtra">Maharashtra</option>
            <option value="rajasthan">Rajasthan</option>
            <option value="tamil-nadu">Tamil Nadu</option>
            <option value="uttar-pradesh">Uttar Pradesh</option>
            <option value="west-bengal">West Bengal</option>
          </select>
          {errors.state && <span className="error-message"><FiAlertCircle /> {errors.state}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="pincode">Pincode <span className="required">*</span></label>
          <input
            type="text"
            id="pincode"
            name="pincode"
            value={formData.pincode}
            onChange={handleChange}
            placeholder="Enter 6-digit pincode"
            maxLength={6}
            className={errors.pincode ? 'error' : ''}
          />
          {errors.pincode && <span className="error-message"><FiAlertCircle /> {errors.pincode}</span>}
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="form-step">
      <h2 className="step-heading">Employment Details</h2>
      <p className="step-description">Help us understand your professional background.</p>

      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="employmentType">Employment Type <span className="required">*</span></label>
          <select
            id="employmentType"
            name="employmentType"
            value={formData.employmentType}
            onChange={handleChange}
            className={errors.employmentType ? 'error' : ''}
          >
            <option value="">Select Type</option>
            <option value="salaried">Salaried</option>
            <option value="self-employed">Self Employed</option>
            <option value="business">Business Owner</option>
            <option value="professional">Professional (Doctor, CA, etc.)</option>
          </select>
          {errors.employmentType && <span className="error-message"><FiAlertCircle /> {errors.employmentType}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="companyName">Company/Business Name <span className="required">*</span></label>
          <input
            type="text"
            id="companyName"
            name="companyName"
            value={formData.companyName}
            onChange={handleChange}
            placeholder="Enter company name"
            className={errors.companyName ? 'error' : ''}
          />
          {errors.companyName && <span className="error-message"><FiAlertCircle /> {errors.companyName}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="designation">Designation <span className="required">*</span></label>
          <input
            type="text"
            id="designation"
            name="designation"
            value={formData.designation}
            onChange={handleChange}
            placeholder="Enter your designation"
            className={errors.designation ? 'error' : ''}
          />
          {errors.designation && <span className="error-message"><FiAlertCircle /> {errors.designation}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="workExperience">Work Experience <span className="required">*</span></label>
          <select
            id="workExperience"
            name="workExperience"
            value={formData.workExperience}
            onChange={handleChange}
            className={errors.workExperience ? 'error' : ''}
          >
            <option value="">Select Experience</option>
            <option value="0-1">Less than 1 year</option>
            <option value="1-3">1-3 years</option>
            <option value="3-5">3-5 years</option>
            <option value="5-10">5-10 years</option>
            <option value="10+">10+ years</option>
          </select>
          {errors.workExperience && <span className="error-message"><FiAlertCircle /> {errors.workExperience}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="monthlyIncome">Monthly Income (₹) <span className="required">*</span></label>
          <div className="input-with-prefix">
            <span className="input-prefix">₹</span>
            <input
              type="number"
              id="monthlyIncome"
              name="monthlyIncome"
              value={formData.monthlyIncome}
              onChange={handleChange}
              placeholder="Enter monthly income"
              min="15000"
              className={errors.monthlyIncome ? 'error' : ''}
            />
          </div>
          {errors.monthlyIncome && <span className="error-message"><FiAlertCircle /> {errors.monthlyIncome}</span>}
          {formData.monthlyIncome && (
            <span className="helper-text">₹{formatCurrency(formData.monthlyIncome)} per month</span>
          )}
        </div>
      </div>

      <div className="info-box">
        <FiAlertCircle className="info-icon" />
        <div>
          <strong>Note:</strong> Your income information will be verified against your bank statements and salary slips.
          Please ensure accurate details for faster processing.
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="form-step">
      <h2 className="step-heading">Loan Details</h2>
      <p className="step-description">Specify your loan requirements.</p>

      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="loanAmount">Loan Amount (₹) <span className="required">*</span></label>
          <div className="input-with-prefix">
            <span className="input-prefix">₹</span>
            <input
              type="number"
              id="loanAmount"
              name="loanAmount"
              value={formData.loanAmount}
              onChange={handleChange}
              placeholder="Enter loan amount"
              min="50000"
              max="5000000"
              className={errors.loanAmount ? 'error' : ''}
            />
          </div>
          {errors.loanAmount && <span className="error-message"><FiAlertCircle /> {errors.loanAmount}</span>}
          {formData.loanAmount && (
            <span className="helper-text">₹{formatCurrency(formData.loanAmount)}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="loanPurpose">Loan Purpose <span className="required">*</span></label>
          <select
            id="loanPurpose"
            name="loanPurpose"
            value={formData.loanPurpose}
            onChange={handleChange}
            className={errors.loanPurpose ? 'error' : ''}
          >
            <option value="">Select Purpose</option>
            <option value="home-renovation">Home Renovation</option>
            <option value="education">Education</option>
            <option value="medical">Medical Expenses</option>
            <option value="wedding">Wedding</option>
            <option value="travel">Travel</option>
            <option value="debt-consolidation">Debt Consolidation</option>
            <option value="business">Business Expansion</option>
            <option value="other">Other</option>
          </select>
          {errors.loanPurpose && <span className="error-message"><FiAlertCircle /> {errors.loanPurpose}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="loanTenure">Loan Tenure <span className="required">*</span></label>
          <select
            id="loanTenure"
            name="loanTenure"
            value={formData.loanTenure}
            onChange={handleChange}
            className={errors.loanTenure ? 'error' : ''}
          >
            <option value="">Select Tenure</option>
            <option value="12">12 months</option>
            <option value="24">24 months</option>
            <option value="36">36 months</option>
            <option value="48">48 months</option>
            <option value="60">60 months</option>
          </select>
          {errors.loanTenure && <span className="error-message"><FiAlertCircle /> {errors.loanTenure}</span>}
        </div>

        <div className="form-group">
          <label>Do you have existing loans? <span className="required">*</span></label>
          <div className="radio-group">
            <label className="radio-label">
              <input
                type="radio"
                name="existingLoans"
                value="no"
                checked={formData.existingLoans === 'no'}
                onChange={handleChange}
              />
              <span className="radio-custom"></span>
              No
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="existingLoans"
                value="yes"
                checked={formData.existingLoans === 'yes'}
                onChange={handleChange}
              />
              <span className="radio-custom"></span>
              Yes
            </label>
          </div>
        </div>

        {formData.existingLoans === 'yes' && (
          <div className="form-group">
            <label htmlFor="existingEMI">Current Monthly EMI (₹) <span className="required">*</span></label>
            <div className="input-with-prefix">
              <span className="input-prefix">₹</span>
              <input
                type="number"
                id="existingEMI"
                name="existingEMI"
                value={formData.existingEMI}
                onChange={handleChange}
                placeholder="Total existing EMIs"
                className={errors.existingEMI ? 'error' : ''}
              />
            </div>
            {errors.existingEMI && <span className="error-message"><FiAlertCircle /> {errors.existingEMI}</span>}
          </div>
        )}
      </div>

      {/* EMI Calculator Preview */}
      {formData.loanAmount && formData.loanTenure && (
        <div className="emi-preview">
          <h4>Estimated EMI</h4>
          <div className="emi-amount">
            ₹{formatCurrency(Math.round(
              (parseFloat(formData.loanAmount) * 0.12 / 12 * Math.pow(1 + 0.12 / 12, parseInt(formData.loanTenure))) /
              (Math.pow(1 + 0.12 / 12, parseInt(formData.loanTenure)) - 1)
            ))}
            <span>/month</span>
          </div>
          <p className="emi-note">*Based on 12% interest rate. Actual EMI may vary.</p>
        </div>
      )}
    </div>
  );

  const renderStep4 = () => (
    <div className="form-step">
      <h2 className="step-heading">Review & Submit</h2>
      <p className="step-description">Please review your application details before submitting.</p>

      <div className="review-sections">
        <div className="review-section">
          <h4><FiUser /> Personal Information</h4>
          <div className="review-grid">
            <div className="review-item">
              <span className="review-label">Full Name</span>
              <span className="review-value">{formData.fullName}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Email</span>
              <span className="review-value">{formData.email}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Phone</span>
              <span className="review-value">+91 {formData.phone}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Date of Birth</span>
              <span className="review-value">{formData.dateOfBirth}</span>
            </div>
            <div className="review-item">
              <span className="review-label">PAN Number</span>
              <span className="review-value">{formData.panNumber.substring(0, 4)}****{formData.panNumber.slice(-1)}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Address</span>
              <span className="review-value">{formData.address}, {formData.city}, {formData.state} - {formData.pincode}</span>
            </div>
          </div>
        </div>

        <div className="review-section">
          <h4><FiBriefcase /> Employment Details</h4>
          <div className="review-grid">
            <div className="review-item">
              <span className="review-label">Employment Type</span>
              <span className="review-value">{formData.employmentType}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Company</span>
              <span className="review-value">{formData.companyName}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Designation</span>
              <span className="review-value">{formData.designation}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Experience</span>
              <span className="review-value">{formData.workExperience} years</span>
            </div>
            <div className="review-item">
              <span className="review-label">Monthly Income</span>
              <span className="review-value">₹{formatCurrency(formData.monthlyIncome)}</span>
            </div>
          </div>
        </div>

        <div className="review-section">
          <h4><FiDollarSign /> Loan Details</h4>
          <div className="review-grid">
            <div className="review-item highlight">
              <span className="review-label">Loan Amount</span>
              <span className="review-value">₹{formatCurrency(formData.loanAmount)}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Purpose</span>
              <span className="review-value">{formData.loanPurpose}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Tenure</span>
              <span className="review-value">{formData.loanTenure} months</span>
            </div>
            <div className="review-item">
              <span className="review-label">Existing Loans</span>
              <span className="review-value">{formData.existingLoans === 'yes' ? `Yes - ₹${formatCurrency(formData.existingEMI)}/month` : 'No'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="consent-section">
        <label className="checkbox-label">
          <input
            type="checkbox"
            name="agreeTerms"
            checked={formData.agreeTerms}
            onChange={handleChange}
          />
          <span className="checkbox-custom"></span>
          I agree to the <a href="#terms" target="_blank">Terms & Conditions</a> and <a href="#privacy" target="_blank">Privacy Policy</a>
        </label>
        {errors.agreeTerms && <span className="error-message"><FiAlertCircle /> {errors.agreeTerms}</span>}

        <label className="checkbox-label">
          <input
            type="checkbox"
            name="consentDataProcessing"
            checked={formData.consentDataProcessing}
            onChange={handleChange}
          />
          <span className="checkbox-custom"></span>
          I consent to the processing of my personal data for loan evaluation purposes
        </label>
        {errors.consentDataProcessing && <span className="error-message"><FiAlertCircle /> {errors.consentDataProcessing}</span>}
      </div>
    </div>
  );

  return (
    <div className="loan-application">
      <div className="application-container">
        {/* Step Indicator */}
        {renderStepIndicator()}

        {/* Form Content */}
        <div className="form-content">
          {currentStep === 1 && renderStep1()}
          {currentStep === 2 && renderStep2()}
          {currentStep === 3 && renderStep3()}
          {currentStep === 4 && renderStep4()}
        </div>

        {/* Navigation Buttons */}
        <div className="form-navigation">
          {currentStep > 1 && (
            <button 
              type="button" 
              className="btn btn-outline"
              onClick={handlePrevious}
              disabled={loading}
            >
              <FiChevronLeft />
              Previous
            </button>
          )}

          {currentStep < 4 ? (
            <button 
              type="button" 
              className="btn btn-primary"
              onClick={handleNext}
            >
              Next Step
              <FiChevronRight />
            </button>
          ) : (
            <button 
              type="button" 
              className="btn btn-primary btn-submit"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="btn-spinner"></span>
                  Processing...
                </>
              ) : (
                <>
                  <FiCheck />
                  Submit Application
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoanApplication;
