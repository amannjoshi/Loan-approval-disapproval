import axios from 'axios';

// API base URL - connects to FastAPI backend
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// =============================================================================
// Authentication Service
// =============================================================================
export const authService = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', {
      email: credentials.email,
      password: credentials.password,
    });
    return response;
  },
  
  register: async (userData) => {
    const response = await api.post('/auth/register', {
      email: userData.email,
      password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName,
      phone: userData.phone || null,
    });
    return response;
  },
  
  me: () => api.get('/auth/me'),
  
  logout: () => api.post('/auth/logout'),
  
  refreshToken: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
};

// =============================================================================
// Loan Application Service
// =============================================================================
export const loanService = {
  // Create new application
  create: async (applicationData) => {
    return api.post('/applications', applicationData);
  },
  
  // Get all applications (with pagination)
  getAll: (params = {}) => {
    return api.get('/applications', { params });
  },
  
  // Get application by ID
  getById: (id) => api.get(`/applications/${id}`),
  
  // Get application status
  getStatus: (applicationNumber) => api.get(`/applications/status/${applicationNumber}`),
  
  // Update application
  update: (id, data) => api.put(`/applications/${id}`, data),
  
  // Submit application
  submit: (id) => api.post(`/applications/${id}/submit`),
  
  // Get ML prediction for application
  predict: (id) => api.post(`/applications/${id}/predict`),
  
  // Get dashboard stats
  getDashboardStats: () => api.get('/admin/dashboard'),
};

// =============================================================================
// Applicant Service
// =============================================================================
export const applicantService = {
  // Create applicant profile
  create: async (applicantData) => {
    return api.post('/applicants', applicantData);
  },
  
  // Get current user's applicant profile
  getProfile: () => api.get('/applicants/me'),
  
  // Update applicant profile
  updateProfile: (data) => api.put('/applicants/me', data),
  
  // Get applicant by ID
  getById: (id) => api.get(`/applicants/${id}`),
};

// =============================================================================
// Privacy Service (Data Masking)
// =============================================================================
export const privacyService = {
  // Mask single value
  mask: (data_type, value) => api.post('/privacy/mask', { data_type, value }),
  
  // Mask PAN number
  maskPan: (pan) => api.get(`/privacy/mask/pan/${encodeURIComponent(pan)}`),
  
  // Mask Aadhaar number
  maskAadhaar: (aadhaar) => api.get(`/privacy/mask/aadhaar/${encodeURIComponent(aadhaar)}`),
  
  // Mask phone number
  maskPhone: (phone) => api.get(`/privacy/mask/phone/${encodeURIComponent(phone)}`),
  
  // Mask email
  maskEmail: (email) => api.get(`/privacy/mask/email/${encodeURIComponent(email)}`),
  
  // Batch mask multiple values
  maskBatch: (items) => api.post('/privacy/mask/batch', { items }),
  
  // Mask applicant data
  maskApplicant: (data) => api.post('/privacy/mask/applicant', data),
  
  // Get supported formats
  getFormats: () => api.get('/privacy/formats'),
};

// =============================================================================
// Admin Service
// =============================================================================
export const adminService = {
  // Get system stats
  getStats: () => api.get('/admin/stats'),
  
  // Get dashboard data
  getDashboard: () => api.get('/admin/dashboard'),
  
  // Get all users
  getUsers: (params = {}) => api.get('/admin/users', { params }),
  
  // Get audit logs
  getAuditLogs: (params = {}) => api.get('/admin/audit-logs', { params }),
};

// =============================================================================
// Model Management Service
// =============================================================================
export const modelService = {
  // Get model status
  getStatus: () => api.get('/models/status'),
  
  // Get model list
  getList: () => api.get('/models/list'),
  
  // Rollback model
  rollback: (data) => api.post('/models/rollback/execute', data),
  
  // Emergency rollback
  emergencyRollback: () => api.post('/models/rollback/emergency'),
  
  // Get rollback history
  getRollbackHistory: () => api.get('/models/rollback/history'),
};

// =============================================================================
// Alerts & Anomaly Detection Service
// =============================================================================
export const alertsService = {
  // Get all alerts
  getAlerts: (params = {}) => api.get('/alerts/alerts', { params }),
  
  // Get critical alerts
  getCritical: () => api.get('/alerts/alerts/critical'),
  
  // Acknowledge alert
  acknowledge: (alertIds, userId) => api.post('/alerts/alerts/acknowledge', { alert_ids: alertIds, user_id: userId }),
  
  // Resolve alert
  resolve: (alertIds, userId, resolution) => api.post('/alerts/alerts/resolve', { 
    alert_ids: alertIds, 
    user_id: userId,
    resolution 
  }),
  
  // Get alert statistics
  getStatistics: () => api.get('/alerts/statistics'),
  
  // Get anomaly metrics
  getMetrics: () => api.get('/alerts/metrics'),
  
  // Get dashboard
  getDashboard: () => api.get('/alerts/dashboard'),
};

// =============================================================================
// Rejection Feedback Service
// =============================================================================
export const feedbackService = {
  // Get rejection feedback
  getFeedback: (data) => api.post('/rejection/feedback', data),
  
  // Quick check
  quickCheck: (data) => api.post('/rejection/quick-check', data),
  
  // Get improvement tips
  getImprovementTips: (params = {}) => api.get('/rejection/improvement-tips', { params }),
  
  // Get FAQ
  getFaq: () => api.get('/rejection/faq'),
};

// =============================================================================
// Health Check Service
// =============================================================================
export const healthService = {
  check: () => axios.get(`${API_BASE_URL}/health`),
  ready: () => axios.get(`${API_BASE_URL}/ready`),
  metrics: () => axios.get(`${API_BASE_URL}/metrics`),
};
