import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const auth = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/users/me'),
};

export const dashboard = {
  getStats: () => api.get('/dashboard/stats'),
};

export const employees = {
  getAll: () => api.get('/employees'),
  create: (data) => api.post('/employees', data),
};

export const accounts = {
  getAll: () => api.get('/accounts'),
  create: (data) => api.post('/accounts', data),
};

export const journals = {
  getAll: () => api.get('/journals'),
  create: (data) => api.post('/journals', data),
};

export default api;
