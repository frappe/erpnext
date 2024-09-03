import axios from 'axios';
import { refreshToken } from './auth';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const newToken = await refreshToken();
      axios.defaults.headers.common['Authorization'] = 'Bearer ' + newToken;
      return api(originalRequest);
    }
    return Promise.reject(error);
  }
);

export default api;