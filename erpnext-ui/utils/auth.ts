import axios from 'axios';
import api from './api';

const API_URL = 'http://localhost:8000/api/v1';

export const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  const response = await api.post('/refresh', { refresh_token: refreshToken });
  if (response.data.access_token) {
    localStorage.setItem('accessToken', response.data.access_token);
  }
  return response.data.access_token;
};

// Update login function to store refresh token
export const login = async (username: string, password: string) => {
  const response = await api.post('/token', { username, password });
  if (response.data.access_token && response.data.refresh_token) {
    localStorage.setItem('accessToken', response.data.access_token);
    localStorage.setItem('refreshToken', response.data.refresh_token);
  }
  return response.data;
};

export const logout = () => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  // Redirect to login page or update global state
};

export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  if (userStr) return JSON.parse(userStr);
  return null;
};

export const authHeader = () => {
  const user = getCurrentUser();
  if (user && user.access_token) {
    return { Authorization: 'Bearer ' + user.access_token };
  } else {
    return {};
  }
};