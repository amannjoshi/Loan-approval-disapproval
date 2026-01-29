import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
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
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API Service Functions
export const authService = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (userData) => api.post('/auth/register', userData),
  me: () => api.get('/auth/me'),
};

export const loanService = {
  apply: (applicationData) => api.post('/applications', applicationData),
  getAll: () => api.get('/applications'),
  getById: (id) => api.get(`/applications/${id}`),
  getStatus: (id) => api.get(`/applications/${id}/status`),
};

export const privacyService = {
  maskPan: (pan) => api.get(`/privacy/mask/pan/${pan}`),
  maskAadhaar: (aadhaar) => api.get(`/privacy/mask/aadhaar/${aadhaar}`),
  maskPhone: (phone) => api.get(`/privacy/mask/phone/${phone}`),
  maskEmail: (email) => api.get(`/privacy/mask/email/${email}`),
  maskBatch: (items) => api.post('/privacy/mask/batch', { items }),
  maskApplicant: (data) => api.post('/privacy/mask/applicant', data),
  getFormats: () => api.get('/privacy/formats'),
};

export const healthService = {
  check: () => api.get('/health'),
};
