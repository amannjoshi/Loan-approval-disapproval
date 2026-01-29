import React, { useState } from 'react';
import { 
  FiShield, FiEye, FiEyeOff, FiCreditCard, FiUser, FiPhone, 
  FiMail, FiLock, FiCheck, FiAlertCircle, FiRefreshCw
} from 'react-icons/fi';
// Note: privacyService will be used when connecting to real backend
// import { privacyService } from '../services/api';
import { toast } from 'react-toastify';
import './PrivacyDemo.css';

const PrivacyDemo = () => {
  const [showOriginal, setShowOriginal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [customData, setCustomData] = useState({
    pan: '',
    aadhaar: '',
    phone: '',
    email: ''
  });
  const [maskedResult, setMaskedResult] = useState(null);

  // Demo data examples
  const demoData = {
    pan: {
      original: 'ABCDE1234F',
      masked: 'ABCD****F',
      description: 'PAN Number - First 4 and last 1 character visible'
    },
    aadhaar: {
      original: '123456789012',
      masked: '********9012',
      description: 'Aadhaar Number - Only last 4 digits visible'
    },
    phone: {
      original: '+91 98765 43210',
      masked: '+91 ****43210',
      description: 'Phone Number - Country code and last 5 digits visible'
    },
    email: {
      original: 'rahul.sharma@example.com',
      masked: 'r****@example.com',
      description: 'Email - First letter and domain visible'
    },
    account: {
      original: '1234567890123456',
      masked: '************3456',
      description: 'Bank Account - Only last 4 digits visible'
    },
    card: {
      original: '4532 1234 5678 9012',
      masked: '**** **** **** 9012',
      description: 'Card Number - Only last 4 digits visible'
    }
  };

  const handleCustomMask = async () => {
    if (!customData.pan && !customData.aadhaar && !customData.phone && !customData.email) {
      toast.warning('Please enter at least one field to mask');
      return;
    }

    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 800));

      // Mock masking logic (in real app, call privacyService.maskData)
      const result = {
        pan: customData.pan ? 
          customData.pan.slice(0, 4) + '****' + customData.pan.slice(-1) : null,
        aadhaar: customData.aadhaar ? 
          '********' + customData.aadhaar.slice(-4) : null,
        phone: customData.phone ? 
          customData.phone.slice(0, 3) + ' ****' + customData.phone.slice(-5) : null,
        email: customData.email ? 
          customData.email[0] + '****@' + customData.email.split('@')[1] : null
      };

      setMaskedResult(result);
      toast.success('Data masked successfully!');
    } catch (error) {
      toast.error('Failed to mask data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setCustomData({ pan: '', aadhaar: '', phone: '', email: '' });
    setMaskedResult(null);
  };

  return (
    <div className="privacy-demo">
      {/* Header */}
      <div className="privacy-header">
        <div className="privacy-icon">
          <FiShield />
        </div>
        <h1>Data Privacy & Masking</h1>
        <p>
          We take data privacy seriously. All sensitive information is masked before display 
          to protect your personal data. Here's how we handle different types of sensitive data.
        </p>
      </div>

      {/* Privacy Features */}
      <div className="features-section">
        <h2>Privacy Protection Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">
              <FiLock />
            </div>
            <h3>PII Masking</h3>
            <p>Personally Identifiable Information is automatically masked in all displays and logs.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">
              <FiShield />
            </div>
            <h3>Encrypted Storage</h3>
            <p>All sensitive data is encrypted at rest using AES-256 encryption.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">
              <FiEyeOff />
            </div>
            <h3>Role-Based Access</h3>
            <p>Only authorized personnel can access unmasked data with proper audit trails.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">
              <FiCheck />
            </div>
            <h3>GDPR Compliant</h3>
            <p>Our data handling practices comply with GDPR and Indian data protection laws.</p>
          </div>
        </div>
      </div>

      {/* Demo Section */}
      <div className="demo-section">
        <div className="demo-header">
          <h2>Masking Demonstration</h2>
          <button 
            className={`toggle-btn ${showOriginal ? 'active' : ''}`}
            onClick={() => setShowOriginal(!showOriginal)}
          >
            {showOriginal ? <FiEyeOff /> : <FiEye />}
            {showOriginal ? 'Hide Original' : 'Show Original'}
          </button>
        </div>

        <div className="demo-grid">
          {Object.entries(demoData).map(([key, data]) => (
            <div key={key} className="demo-item">
              <div className="demo-item-header">
                {key === 'pan' && <FiCreditCard />}
                {key === 'aadhaar' && <FiUser />}
                {key === 'phone' && <FiPhone />}
                {key === 'email' && <FiMail />}
                {key === 'account' && <FiCreditCard />}
                {key === 'card' && <FiCreditCard />}
                <span className="demo-item-type">{key.toUpperCase()}</span>
              </div>
              <div className="demo-item-values">
                <div className="value-row">
                  <span className="value-label">Masked:</span>
                  <span className="value-masked">{data.masked}</span>
                </div>
                {showOriginal && (
                  <div className="value-row original">
                    <span className="value-label">Original:</span>
                    <span className="value-original">{data.original}</span>
                  </div>
                )}
              </div>
              <p className="demo-item-description">{data.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Try It Section */}
      <div className="try-section">
        <h2>Try It Yourself</h2>
        <p>Enter your own data to see how the masking works:</p>

        <div className="try-form">
          <div className="try-grid">
            <div className="try-input-group">
              <label>
                <FiCreditCard />
                PAN Number
              </label>
              <input
                type="text"
                placeholder="e.g., ABCDE1234F"
                maxLength={10}
                value={customData.pan}
                onChange={(e) => setCustomData({ ...customData, pan: e.target.value.toUpperCase() })}
              />
            </div>
            <div className="try-input-group">
              <label>
                <FiUser />
                Aadhaar Number
              </label>
              <input
                type="text"
                placeholder="e.g., 123456789012"
                maxLength={12}
                value={customData.aadhaar}
                onChange={(e) => setCustomData({ ...customData, aadhaar: e.target.value.replace(/\D/g, '') })}
              />
            </div>
            <div className="try-input-group">
              <label>
                <FiPhone />
                Phone Number
              </label>
              <input
                type="text"
                placeholder="e.g., +91 98765 43210"
                value={customData.phone}
                onChange={(e) => setCustomData({ ...customData, phone: e.target.value })}
              />
            </div>
            <div className="try-input-group">
              <label>
                <FiMail />
                Email Address
              </label>
              <input
                type="email"
                placeholder="e.g., example@email.com"
                value={customData.email}
                onChange={(e) => setCustomData({ ...customData, email: e.target.value })}
              />
            </div>
          </div>

          <div className="try-actions">
            <button 
              className="btn btn-primary"
              onClick={handleCustomMask}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="btn-spinner"></span>
                  Processing...
                </>
              ) : (
                <>
                  <FiShield />
                  Mask Data
                </>
              )}
            </button>
            <button 
              className="btn btn-outline"
              onClick={handleClear}
            >
              <FiRefreshCw />
              Clear
            </button>
          </div>
        </div>

        {/* Results */}
        {maskedResult && (
          <div className="try-results">
            <h3>Masked Results</h3>
            <div className="results-grid">
              {maskedResult.pan && (
                <div className="result-item">
                  <span className="result-label">PAN</span>
                  <span className="result-value">{maskedResult.pan}</span>
                </div>
              )}
              {maskedResult.aadhaar && (
                <div className="result-item">
                  <span className="result-label">Aadhaar</span>
                  <span className="result-value">{maskedResult.aadhaar}</span>
                </div>
              )}
              {maskedResult.phone && (
                <div className="result-item">
                  <span className="result-label">Phone</span>
                  <span className="result-value">{maskedResult.phone}</span>
                </div>
              )}
              {maskedResult.email && (
                <div className="result-item">
                  <span className="result-label">Email</span>
                  <span className="result-value">{maskedResult.email}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Compliance Section */}
      <div className="compliance-section">
        <h2>Data Protection Compliance</h2>
        <div className="compliance-grid">
          <div className="compliance-card">
            <img src="https://img.shields.io/badge/GDPR-Compliant-green?style=for-the-badge" alt="GDPR Compliant" />
            <h4>General Data Protection Regulation</h4>
            <p>Compliant with EU data protection and privacy regulations.</p>
          </div>
          <div className="compliance-card">
            <img src="https://img.shields.io/badge/PDPA-Compliant-green?style=for-the-badge" alt="PDPA Compliant" />
            <h4>Personal Data Protection Act</h4>
            <p>Adheres to Indian data protection laws and standards.</p>
          </div>
          <div className="compliance-card">
            <img src="https://img.shields.io/badge/ISO_27001-Certified-blue?style=for-the-badge" alt="ISO 27001" />
            <h4>Information Security</h4>
            <p>Following ISO 27001 information security standards.</p>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="info-notice">
        <FiAlertCircle className="info-icon" />
        <div>
          <strong>Important:</strong> All data entered on this page is processed locally for demonstration 
          purposes only. No data is stored or transmitted to any server. In production, all masking is 
          performed server-side before data reaches the client.
        </div>
      </div>
    </div>
  );
};

export default PrivacyDemo;
