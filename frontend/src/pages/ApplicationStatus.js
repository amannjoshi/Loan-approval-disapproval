import React, { useState, useEffect } from 'react';
import { useLocation, useSearchParams, Link } from 'react-router-dom';
import { 
  FiSearch, FiCheckCircle, FiXCircle, FiClock, FiFileText, 
  FiUser, FiDollarSign, FiBriefcase, FiCalendar, FiInfo,
  FiDownload, FiRefreshCw, FiAlertTriangle
} from 'react-icons/fi';
// Note: loanService will be used when connecting to real backend
// import { loanService } from '../services/api';
import './ApplicationStatus.css';

const ApplicationStatus = () => {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [applicationId, setApplicationId] = useState(searchParams.get('id') || '');
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const initialSearch = (id) => {
      handleSearchInternal(id);
    };
    
    if (location.state?.applicationId) {
      setApplicationId(location.state.applicationId);
      initialSearch(location.state.applicationId);
    } else if (searchParams.get('id')) {
      initialSearch(searchParams.get('id'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state, searchParams]);

  const handleSearchInternal = async (id) => {
    if (!id.trim()) {
      setError('Please enter an application ID');
      return;
    }

    setLoading(true);
    setError('');
    setApplication(null);

    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock data - In real app, call: await loanService.getApplication(id);
      const mockApplications = {
        'LA-2024-001': {
          id: 'LA-2024-001',
          status: 'approved',
          applicantName: 'Rahul Sharma',
          email: 'rahul.sharma@email.com',
          phone: '+91 98765 43210',
          loanAmount: 500000,
          loanPurpose: 'Home Renovation',
          tenure: 36,
          interestRate: 11.5,
          emi: 16502,
          submittedAt: '2024-01-20T10:30:00',
          processedAt: '2024-01-22T14:45:00',
          approvalScore: 85,
          riskCategory: 'Low',
          timeline: [
            { status: 'submitted', date: '2024-01-20T10:30:00', description: 'Application submitted successfully' },
            { status: 'under_review', date: '2024-01-21T09:00:00', description: 'Application under review by credit team' },
            { status: 'documents_verified', date: '2024-01-22T11:30:00', description: 'Documents verified successfully' },
            { status: 'approved', date: '2024-01-22T14:45:00', description: 'Loan approved! Funds will be disbursed shortly.' }
          ],
          explanation: {
            decision: 'Your loan application has been approved based on strong financial indicators.',
            factors: [
              { factor: 'Credit Score', impact: 'positive', description: 'Excellent credit history (750+)' },
              { factor: 'Income Stability', impact: 'positive', description: '5+ years with current employer' },
              { factor: 'Debt-to-Income Ratio', impact: 'positive', description: 'Healthy DTI ratio of 28%' },
              { factor: 'Repayment History', impact: 'positive', description: 'No defaults in past loans' }
            ]
          }
        },
        'LA-2024-002': {
          id: 'LA-2024-002',
          status: 'pending',
          applicantName: 'Priya Patel',
          email: 'priya.patel@email.com',
          phone: '+91 87654 32109',
          loanAmount: 750000,
          loanPurpose: 'Business Expansion',
          tenure: 48,
          interestRate: null,
          emi: null,
          submittedAt: '2024-01-25T15:20:00',
          processedAt: null,
          approvalScore: 72,
          riskCategory: 'Medium',
          timeline: [
            { status: 'submitted', date: '2024-01-25T15:20:00', description: 'Application submitted successfully' },
            { status: 'under_review', date: '2024-01-26T10:00:00', description: 'Application is being reviewed' }
          ],
          explanation: null
        },
        'LA-2024-004': {
          id: 'LA-2024-004',
          status: 'rejected',
          applicantName: 'Sneha Gupta',
          email: 'sneha.gupta@email.com',
          phone: '+91 76543 21098',
          loanAmount: 1000000,
          loanPurpose: 'Debt Consolidation',
          tenure: 60,
          interestRate: null,
          emi: null,
          submittedAt: '2024-01-18T11:45:00',
          processedAt: '2024-01-20T16:30:00',
          approvalScore: 45,
          riskCategory: 'High',
          timeline: [
            { status: 'submitted', date: '2024-01-18T11:45:00', description: 'Application submitted successfully' },
            { status: 'under_review', date: '2024-01-19T09:15:00', description: 'Application under review' },
            { status: 'rejected', date: '2024-01-20T16:30:00', description: 'Application could not be approved at this time' }
          ],
          explanation: {
            decision: 'We are unable to approve your loan application at this time.',
            factors: [
              { factor: 'Credit Score', impact: 'negative', description: 'Credit score below required threshold' },
              { factor: 'Existing Debt', impact: 'negative', description: 'High existing debt obligations' },
              { factor: 'Employment Duration', impact: 'warning', description: 'Less than 1 year with current employer' }
            ],
            suggestions: [
              'Improve credit score by paying bills on time',
              'Reduce existing debt before reapplying',
              'Wait for 6 months with stable employment',
              'Consider a lower loan amount'
            ]
          }
        }
      };

      const app = mockApplications[id.toUpperCase()];
      if (app) {
        setApplication(app);
      } else {
        setError('Application not found. Please check the ID and try again.');
      }
    } catch (err) {
      setError('Failed to fetch application details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (id = applicationId) => {
    handleSearchInternal(id);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleSearch();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved':
        return <FiCheckCircle className="status-icon approved" />;
      case 'rejected':
        return <FiXCircle className="status-icon rejected" />;
      case 'pending':
      default:
        return <FiClock className="status-icon pending" />;
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      approved: 'badge-success',
      rejected: 'badge-danger',
      pending: 'badge-warning',
      submitted: 'badge-info',
      under_review: 'badge-info',
      documents_verified: 'badge-primary'
    };
    return badges[status] || 'badge-secondary';
  };

  const getFactorIcon = (impact) => {
    switch (impact) {
      case 'positive':
        return <FiCheckCircle className="factor-icon positive" />;
      case 'negative':
        return <FiXCircle className="factor-icon negative" />;
      case 'warning':
        return <FiAlertTriangle className="factor-icon warning" />;
      default:
        return <FiInfo className="factor-icon neutral" />;
    }
  };

  return (
    <div className="application-status">
      <div className="status-header">
        <h1>Application Status</h1>
        <p>Track your loan application progress</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <FiSearch className="search-icon" />
          <input
            type="text"
            placeholder="Enter Application ID (e.g., LA-2024-001)"
            value={applicationId}
            onChange={(e) => setApplicationId(e.target.value)}
            className="search-input"
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? (
            <>
              <span className="btn-spinner"></span>
              Searching...
            </>
          ) : (
            <>
              <FiSearch />
              Track Status
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="error-alert">
          <FiAlertTriangle />
          {error}
        </div>
      )}

      {/* Application Details */}
      {application && (
        <div className="application-details">
          {/* Status Card */}
          <div className={`status-card ${application.status}`}>
            <div className="status-main">
              {getStatusIcon(application.status)}
              <div className="status-text">
                <h2>
                  {application.status === 'approved' && 'Congratulations! Your Loan is Approved'}
                  {application.status === 'pending' && 'Application Under Review'}
                  {application.status === 'rejected' && 'Application Not Approved'}
                </h2>
                <p className="app-id">{application.id}</p>
              </div>
            </div>
            <div className="status-actions">
              <button className="btn btn-outline-white" onClick={() => handleSearch(application.id)}>
                <FiRefreshCw />
                Refresh
              </button>
              {application.status === 'approved' && (
                <button className="btn btn-white">
                  <FiDownload />
                  Download Letter
                </button>
              )}
            </div>
          </div>

          {/* Details Grid */}
          <div className="details-grid">
            {/* Applicant Info */}
            <div className="detail-card">
              <div className="detail-header">
                <FiUser />
                <h3>Applicant Information</h3>
              </div>
              <div className="detail-content">
                <div className="detail-row">
                  <span className="detail-label">Name</span>
                  <span className="detail-value">{application.applicantName}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Email</span>
                  <span className="detail-value">{application.email}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Phone</span>
                  <span className="detail-value">{application.phone}</span>
                </div>
              </div>
            </div>

            {/* Loan Info */}
            <div className="detail-card">
              <div className="detail-header">
                <FiDollarSign />
                <h3>Loan Details</h3>
              </div>
              <div className="detail-content">
                <div className="detail-row highlight">
                  <span className="detail-label">Loan Amount</span>
                  <span className="detail-value large">{formatCurrency(application.loanAmount)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Purpose</span>
                  <span className="detail-value">{application.loanPurpose}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Tenure</span>
                  <span className="detail-value">{application.tenure} months</span>
                </div>
                {application.interestRate && (
                  <div className="detail-row">
                    <span className="detail-label">Interest Rate</span>
                    <span className="detail-value">{application.interestRate}% p.a.</span>
                  </div>
                )}
                {application.emi && (
                  <div className="detail-row highlight">
                    <span className="detail-label">Monthly EMI</span>
                    <span className="detail-value large">{formatCurrency(application.emi)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Risk Assessment */}
            <div className="detail-card">
              <div className="detail-header">
                <FiBriefcase />
                <h3>Risk Assessment</h3>
              </div>
              <div className="detail-content">
                <div className="score-display">
                  <div className="score-circle" style={{
                    '--score': application.approvalScore,
                    '--color': application.approvalScore >= 70 ? '#10b981' : 
                               application.approvalScore >= 50 ? '#f59e0b' : '#ef4444'
                  }}>
                    <span className="score-value">{application.approvalScore}</span>
                    <span className="score-label">Score</span>
                  </div>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Risk Category</span>
                  <span className={`badge ${
                    application.riskCategory === 'Low' ? 'badge-success' :
                    application.riskCategory === 'Medium' ? 'badge-warning' : 'badge-danger'
                  }`}>
                    {application.riskCategory} Risk
                  </span>
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className="detail-card timeline-card">
              <div className="detail-header">
                <FiCalendar />
                <h3>Application Timeline</h3>
              </div>
              <div className="timeline">
                {application.timeline.map((event, index) => (
                  <div key={index} className={`timeline-item ${event.status}`}>
                    <div className="timeline-marker">
                      <div className="timeline-dot"></div>
                      {index < application.timeline.length - 1 && <div className="timeline-line"></div>}
                    </div>
                    <div className="timeline-content">
                      <span className={`badge ${getStatusBadge(event.status)}`}>
                        {event.status.replace('_', ' ')}
                      </span>
                      <p className="timeline-description">{event.description}</p>
                      <span className="timeline-date">{formatDate(event.date)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Decision Explanation */}
          {application.explanation && (
            <div className="explanation-card">
              <div className="explanation-header">
                <FiInfo />
                <h3>Decision Explanation</h3>
              </div>
              <p className="explanation-summary">{application.explanation.decision}</p>
              
              <div className="factors-list">
                <h4>Key Factors</h4>
                {application.explanation.factors.map((factor, index) => (
                  <div key={index} className={`factor-item ${factor.impact}`}>
                    {getFactorIcon(factor.impact)}
                    <div className="factor-content">
                      <span className="factor-name">{factor.factor}</span>
                      <span className="factor-description">{factor.description}</span>
                    </div>
                  </div>
                ))}
              </div>

              {application.explanation.suggestions && (
                <div className="suggestions-box">
                  <h4>Suggestions for Improvement</h4>
                  <ul>
                    {application.explanation.suggestions.map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="action-buttons">
            <Link to="/apply" className="btn btn-primary">
              <FiFileText />
              Apply for New Loan
            </Link>
            <Link to="/dashboard" className="btn btn-outline">
              Back to Dashboard
            </Link>
          </div>
        </div>
      )}

      {/* Demo Applications */}
      {!application && !loading && (
        <div className="demo-section">
          <h3>Try Demo Applications</h3>
          <p>Click on any ID below to view sample application status:</p>
          <div className="demo-cards">
            <button 
              className="demo-card approved" 
              onClick={() => { setApplicationId('LA-2024-001'); handleSearch('LA-2024-001'); }}
            >
              <FiCheckCircle />
              <span>LA-2024-001</span>
              <small>Approved</small>
            </button>
            <button 
              className="demo-card pending"
              onClick={() => { setApplicationId('LA-2024-002'); handleSearch('LA-2024-002'); }}
            >
              <FiClock />
              <span>LA-2024-002</span>
              <small>Pending</small>
            </button>
            <button 
              className="demo-card rejected"
              onClick={() => { setApplicationId('LA-2024-004'); handleSearch('LA-2024-004'); }}
            >
              <FiXCircle />
              <span>LA-2024-004</span>
              <small>Rejected</small>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicationStatus;
