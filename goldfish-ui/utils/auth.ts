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

// ... rest of the file remains the same