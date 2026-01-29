import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiTrendingUp, FiTrendingDown, FiUsers, FiFileText, FiCheckCircle, FiXCircle, FiClock, FiArrowRight } from 'react-icons/fi';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
// Note: loanService will be used when connecting to real backend
// import { loanService } from '../services/api';
import './Dashboard.css';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalApplications: 0,
    approved: 0,
    rejected: 0,
    pending: 0,
    approvalRate: 0,
    avgProcessingTime: 0
  });
  const [recentApplications, setRecentApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // In a real app, these would be actual API calls
      // For demo, we'll use mock data
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      setStats({
        totalApplications: 1247,
        approved: 823,
        rejected: 312,
        pending: 112,
        approvalRate: 72.5,
        avgProcessingTime: 2.3
      });

      setRecentApplications([
        {
          id: 'LA-2024-001',
          applicantName: 'Rahul Sharma',
          amount: 500000,
          status: 'approved',
          date: '2024-01-26',
          riskScore: 85
        },
        {
          id: 'LA-2024-002',
          applicantName: 'Priya Patel',
          amount: 750000,
          status: 'pending',
          date: '2024-01-26',
          riskScore: 72
        },
        {
          id: 'LA-2024-003',
          applicantName: 'Amit Kumar',
          amount: 300000,
          status: 'approved',
          date: '2024-01-25',
          riskScore: 91
        },
        {
          id: 'LA-2024-004',
          applicantName: 'Sneha Gupta',
          amount: 1000000,
          status: 'rejected',
          date: '2024-01-25',
          riskScore: 45
        },
        {
          id: 'LA-2024-005',
          applicantName: 'Vikram Singh',
          amount: 450000,
          status: 'approved',
          date: '2024-01-24',
          riskScore: 78
        }
      ]);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Chart data for applications trend
  const trendChartData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
    datasets: [
      {
        label: 'Approved',
        data: [65, 78, 90, 85, 99, 112, 120],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Rejected',
        data: [28, 35, 40, 32, 45, 38, 42],
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true
      }
    ]
  };

  const trendChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: {
          usePointStyle: true,
          padding: 20
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      x: {
        grid: {
          display: false
        }
      }
    }
  };

  // Chart data for status distribution
  const statusChartData = {
    labels: ['Approved', 'Rejected', 'Pending'],
    datasets: [
      {
        data: [stats.approved, stats.rejected, stats.pending],
        backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
        borderWidth: 0,
        hoverOffset: 4
      }
    ]
  };

  const statusChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 20
        }
      }
    },
    cutout: '70%'
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'approved':
        return 'badge-success';
      case 'rejected':
        return 'badge-danger';
      case 'pending':
        return 'badge-warning';
      default:
        return 'badge-secondary';
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome back! Here's what's happening with your loan applications.</p>
        </div>
        <Link to="/apply" className="btn btn-primary">
          <FiFileText />
          New Application
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">
            <FiFileText />
          </div>
          <div className="stat-content">
            <span className="stat-label">Total Applications</span>
            <span className="stat-value">{stats.totalApplications.toLocaleString()}</span>
          </div>
          <div className="stat-trend up">
            <FiTrendingUp />
            <span>12% from last month</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <FiCheckCircle />
          </div>
          <div className="stat-content">
            <span className="stat-label">Approved</span>
            <span className="stat-value">{stats.approved.toLocaleString()}</span>
          </div>
          <div className="stat-trend up">
            <FiTrendingUp />
            <span>8% from last month</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon red">
            <FiXCircle />
          </div>
          <div className="stat-content">
            <span className="stat-label">Rejected</span>
            <span className="stat-value">{stats.rejected.toLocaleString()}</span>
          </div>
          <div className="stat-trend down">
            <FiTrendingDown />
            <span>3% from last month</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon yellow">
            <FiClock />
          </div>
          <div className="stat-content">
            <span className="stat-label">Pending Review</span>
            <span className="stat-value">{stats.pending.toLocaleString()}</span>
          </div>
          <div className="stat-trend neutral">
            <span>Avg. {stats.avgProcessingTime} days</span>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="charts-row">
        <div className="chart-card">
          <div className="chart-header">
            <h3>Applications Trend</h3>
            <select className="chart-filter">
              <option value="7d">Last 7 months</option>
              <option value="30d">Last 12 months</option>
              <option value="1y">This Year</option>
            </select>
          </div>
          <div className="chart-body trend-chart">
            <Line data={trendChartData} options={trendChartOptions} />
          </div>
        </div>

        <div className="chart-card small">
          <div className="chart-header">
            <h3>Status Distribution</h3>
          </div>
          <div className="chart-body doughnut-chart">
            <Doughnut data={statusChartData} options={statusChartOptions} />
            <div className="doughnut-center">
              <span className="doughnut-value">{stats.approvalRate}%</span>
              <span className="doughnut-label">Approval Rate</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Applications */}
      <div className="card">
        <div className="card-header">
          <h3>Recent Applications</h3>
          <Link to="/status" className="view-all-link">
            View All
            <FiArrowRight />
          </Link>
        </div>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Application ID</th>
                <th>Applicant Name</th>
                <th>Amount</th>
                <th>Risk Score</th>
                <th>Status</th>
                <th>Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentApplications.map((app) => (
                <tr key={app.id}>
                  <td>
                    <span className="app-id">{app.id}</span>
                  </td>
                  <td>{app.applicantName}</td>
                  <td>{formatCurrency(app.amount)}</td>
                  <td>
                    <div className="risk-score">
                      <div 
                        className="risk-bar"
                        style={{ 
                          width: `${app.riskScore}%`,
                          backgroundColor: app.riskScore >= 70 ? '#10b981' : app.riskScore >= 50 ? '#f59e0b' : '#ef4444'
                        }}
                      ></div>
                      <span>{app.riskScore}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${getStatusClass(app.status)}`}>
                      {app.status}
                    </span>
                  </td>
                  <td>{new Date(app.date).toLocaleDateString('en-IN')}</td>
                  <td>
                    <Link to={`/status?id=${app.id}`} className="btn btn-sm btn-outline">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <h3>Quick Actions</h3>
        <div className="actions-grid">
          <Link to="/apply" className="action-card">
            <div className="action-icon blue">
              <FiFileText />
            </div>
            <span>New Application</span>
          </Link>
          <Link to="/status" className="action-card">
            <div className="action-icon green">
              <FiCheckCircle />
            </div>
            <span>Check Status</span>
          </Link>
          <Link to="/privacy" className="action-card">
            <div className="action-icon purple">
              <FiUsers />
            </div>
            <span>Privacy Demo</span>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
