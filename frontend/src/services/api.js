import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token expiration & refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const res = await axios.post(`${API_BASE_URL}auth/token/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', res.data.access);
          originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
          return api(originalRequest);
        }
      } catch (err) {
        // Refresh token failed, logout user
        localStorage.clear();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (username, password) => {
    const res = await api.post('auth/login/', { username, password });
    localStorage.setItem('access_token', res.data.access);
    localStorage.setItem('refresh_token', res.data.refresh);
    localStorage.setItem('username', username);
    return res.data;
  },
  register: async (username, password, email = '') => {
    const res = await api.post('auth/register/', { username, password, email });
    return res.data;
  },
  logout: () => {
    localStorage.clear();
    window.location.href = '/login';
  },
  getCurrentUser: () => {
    return localStorage.getItem('username');
  },
};

export const groupsAPI = {
  list: async () => {
    const res = await api.get('groups/');
    return res.data;
  },
  create: async (name) => {
    const res = await api.post('groups/', { name });
    return res.data;
  },
  retrieve: async (id) => {
    const res = await api.get(`groups/${id}/`);
    return res.data;
  },
  members: async (id) => {
    const res = await api.get(`groups/${id}/members/`);
    return res.data;
  },
  join: async (id, userId, joinedAt) => {
    const res = await api.post(`groups/${id}/join/`, { user_id: userId, joined_at: joinedAt });
    return res.data;
  },
  leave: async (id, userId, leftAt) => {
    const res = await api.post(`groups/${id}/leave/`, { user_id: userId, left_at: leftAt });
    return res.data;
  },
  balances: async (id) => {
    const res = await api.get(`groups/${id}/balances/`);
    return res.data;
  },
  explain: async (id, username) => {
    const res = await api.get(`groups/${id}/explain_balance/`, { params: { username } });
    return res.data;
  },
};

export const expensesAPI = {
  list: async () => {
    const res = await api.get('expenses/');
    return res.data;
  },
  create: async (data) => {
    const res = await api.post('expenses/', data);
    return res.data;
  },
  delete: async (id) => {
    const res = await api.delete(`expenses/${id}/`);
    return res.data;
  },
};

export const settlementsAPI = {
  list: async () => {
    const res = await api.get('settlements/');
    return res.data;
  },
  create: async (data) => {
    const res = await api.post('settlements/', data);
    return res.data;
  },
};

export const importsAPI = {
  list: async () => {
    const res = await api.get('imports/');
    return res.data;
  },
  upload: async (groupId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('group_id', groupId);
    const res = await api.post('imports/upload_csv/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },
  anomalies: async (batchId) => {
    const res = await api.get(`imports/${batchId}/anomalies/`);
    return res.data;
  },
  resolve: async (batchId, anomalyId, status, resolvedData = null) => {
    const res = await api.post(`imports/${batchId}/resolve_anomaly/`, {
      anomaly_id: anomalyId,
      status,
      resolved_data: resolvedData,
    });
    return res.data;
  },
  commit: async (batchId) => {
    const res = await api.post(`imports/${batchId}/commit/`);
    return res.data;
  },
};

export const auditAPI = {
  list: async () => {
    const res = await api.get('audit-logs/');
    return res.data;
  },
};

export default api;
